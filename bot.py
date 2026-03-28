import os, asyncio, aiohttp, uvicorn, discord
from discord.ext import commands
from fastapi import FastAPI, Request

# --- CONFIG ---
TOKEN = os.getenv('DISCORD_TOKEN')
# Ensure Channel ID is a pure integer
try:
    LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID', 0))
except (ValueError, TypeError):
    LOG_CHANNEL_ID = 0

SECRET = "BRAINROT_2026"

app = FastAPI()
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Global session to be opened on bot startup
session_container = {"session": None}

@bot.event
async def on_ready():
    if not session_container["session"]:
        session_container["session"] = aiohttp.ClientSession()
    print(f"🤖 BOT ONLINE: {bot.user}")
    print(f"📢 TARGETING CHANNEL: {LOG_CHANNEL_ID}")

async def scan_logic(pid, uid):
    session = session_container["session"]
    if not session: return None
    
    # Get headshot
    async with session.get(f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={uid}&size=48x48&format=Png") as r:
        t_data = await r.json()
        if not t_data or 'data' not in t_data: return None
        target_img = t_data['data'][0]['imageUrl']

    cursor = ""
    for _ in range(30): # Scan 30 pages
        url = f"https://games.roblox.com/v1/games/{pid}/servers/Public?limit=100&cursor={cursor}"
        async with session.get(url) as r:
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
            
            cursor = data.get('nextPageCursor', "")
            if not cursor: break
    return None

@app.post("/stxr-log")
async def handle_request(request: Request):
    data = await request.json()
    if data.get("secret") != SECRET: return {"status": "unauthorized"}

    uid, pid = data.get("userId"), data.get("placeId")
    item = data.get("itemName", "Unknown")

    job_id = await scan_logic(pid, uid)

    if job_id:
        channel = bot.get_channel(LOG_CHANNEL_ID)
        if channel:
            embed = discord.Embed(title="🎯 TARGET FOUND", color=0xFFFFFF)
            embed.add_field(name="Item", value=item)
            embed.add_field(name="Link", value=f"https://www.roblox.com/games/{pid}?jobId={job_id}")
            # Ensure the task is scheduled in the bot's loop
            bot.loop.create_task(channel.send(embed=embed))
            return {"status": "success", "jobId": job_id}
        else:
            print(f"❌ Channel {LOG_CHANNEL_ID} not found!")
    
    return {"status": "not_found"}

@app.on_event("startup")
async def startup():
    # Start bot in the background without blocking FastAPI
    asyncio.create_task(bot.start(TOKEN))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
