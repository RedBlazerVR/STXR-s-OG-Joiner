import os, asyncio, discord, aiohttp, uvicorn
from discord.ext import commands
from fastapi import FastAPI, Request

# --- CONFIG ---
TOKEN = os.getenv('DISCORD_TOKEN')
LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID', 0))
SECRET = "BRAINROT_2026"

# 1. Setup Discord Bot
intents = discord.Intents.default()
# You only need message_content if the bot needs to READ your messages.
# For SENDING logs, default intents are usually fine.
bot = commands.Bot(command_prefix="!", intents=intents)

# 2. Setup FastAPI
app = FastAPI()
session_container = {"session": None}

@bot.event
async def on_ready():
    if not session_container["session"]:
        session_container["session"] = aiohttp.ClientSession()
    print(f"🤖 BOT LOGGED IN AS: {bot.user}")

async def stxr_warp_scan(place_id, user_id):
    session = session_container["session"]
    # Get target headshot
    async with session.get(f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=48x48&format=Png") as r:
        t_data = await r.json()
        if not t_data.get('data'): return None
        target_img = t_data['data'][0]['imageUrl']

    cursor = ""
    for _ in range(40): # Scan 4,000 players
        api_url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=100&cursor={cursor}"
        async with session.get(api_url) as r:
            data = await r.json()
            if 'data' not in data: break
            
            tasks, s_ids = [], []
            for s in data['data']:
                tokens = s.get('playerTokens', [])
                if tokens:
                    payload = [{"token": t, "type": "AvatarHeadShot", "size": "48x48", "format": "png"} for t in tokens]
                    tasks.append(session.post("https://thumbnails.roblox.com/v1/batch", json=payload))
                    s_ids.append(s.get('id'))

            responses = await asyncio.gather(*tasks)
            for i, res in enumerate(responses):
                batch = await res.json()
                if any(img.get('imageUrl') == target_img for img in batch.get('data', [])):
                    return s_ids[i]
            
            cursor = data.get('nextPageCursor')
            if not cursor: break
    return None

@app.post("/stxr-log")
async def handle_snipe(request: Request):
    data = await request.json()
    if data.get("secret") != SECRET: return {"status": "unauthorized"}
    
    uid, pid = data.get("userId"), data.get("placeId")
    item, mut = data.get("itemName", "Unknown"), data.get("mutation", "None")

    job_id = await stxr_warp_scan(pid, uid)
    
    if job_id:
        # THE BOT SENDS THE MESSAGE HERE
        channel = bot.get_channel(LOG_CHANNEL_ID)
        if channel:
            embed = discord.Embed(title="🎯 TARGET VERIFIED", color=0x000000)
            embed.set_thumbnail(url=f"https://www.roblox.com/headshot-thumbnail/image?userId={uid}&width=150&height=150&format=png")
            embed.add_field(name="Item", value=f"**{item}**")
            embed.add_field(name="Join", value=f"[CLICK TO JOIN](https://www.roblox.com/games/{pid}?jobId={job_id})")
            
            # This pushes the message to the Discord loop
            bot.loop.create_task(channel.send(embed=embed))
            print(f"✅ Bot sent message to channel {LOG_CHANNEL_ID}")
        else:
            print(f"❌ Error: Bot can't find channel {LOG_CHANNEL_ID}")
        
        return {"status": "success", "jobId": job_id}
    
    return {"status": "not_found"}

# This is the "Magic" part that runs both at once
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(bot.start(TOKEN))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
