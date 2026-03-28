import os, asyncio, aiohttp, uvicorn, discord
from discord.ext import commands
from fastapi import FastAPI, Request

# --- CONFIG ---
TOKEN = os.getenv('DISCORD_TOKEN')
try:
    LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID', 0))
except:
    LOG_CHANNEL_ID = 0
SECRET = "BRAINROT_2026"

app = FastAPI()
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
session_container = {"session": None}

@bot.event
async def on_ready():
    if not session_container["session"]:
        session_container["session"] = aiohttp.ClientSession()
    print(f"✅ BOT IS ONLINE: {bot.user}")
    print(f"📢 LOGGING TO CHANNEL ID: {LOG_CHANNEL_ID}")

async def stxr_warp_scan(place_id, user_id):
    print(f"🔍 Starting Scan for User: {user_id} in Place: {place_id}")
    session = session_container["session"]
    
    # 1. Get headshot
    async with session.get(f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=48x48&format=Png") as r:
        t_data = await r.json()
        if not t_data or 'data' not in t_data: 
            print("❌ Could not get Roblox Thumbnail")
            return None
        target_img = t_data['data'][0]['imageUrl']
        print(f"🖼️ Target Image Found: {target_img[:50]}...")

    # 2. Parallel Scan
    cursor = ""
    for page in range(30):
        url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=100&cursor={cursor}"
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
                    print(f"🎯 MATCH FOUND in server {s_ids[i]}")
                    return s_ids[i]
            
            cursor = data.get('nextPageCursor', "")
            if not cursor: break
    print("⚠️ Scan finished: Player not found in any server.")
    return None

@app.post("/stxr-log")
async def handle_request(request: Request):
    print("📨 Received request from Roblox...")
    data = await request.json()
    if data.get("secret") != SECRET: 
        print("⛔ Unauthorized Secret!")
        return {"status": "unauthorized"}

    uid, pid = data.get("userId"), data.get("placeId")
    item = data.get("itemName", "Unknown")

    job_id = await stxr_warp_scan(pid, uid)

    if job_id:
        print(f"📡 Attempting to send Discord message to {LOG_CHANNEL_ID}...")
        channel = bot.get_channel(LOG_CHANNEL_ID) or await bot.fetch_channel(LOG_CHANNEL_ID)
        if channel:
            embed = discord.Embed(title="🎯 TARGET VERIFIED", color=0xFFFFFF)
            embed.add_field(name="Item", value=f"**{item}**")
            embed.add_field(name="Link", value=f"https://www.roblox.com/games/{pid}?jobId={job_id}")
            bot.loop.create_task(channel.send(embed=embed))
            print("✅ DISCORD MESSAGE TASK CREATED")
            return {"status": "success", "jobId": job_id}
        else:
            print("❌ CHANNEL NOT FOUND! Check LOG_CHANNEL_ID.")
    
    return {"status": "not_found"}

@app.on_event("startup")
async def startup():
    asyncio.create_task(bot.start(TOKEN))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
