import os, asyncio, aiohttp, uvicorn, discord
from discord.ext import commands
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager

# --- CONFIG ---
TOKEN = os.getenv('DISCORD_TOKEN')
try:
    LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID', 0))
except:
    LOG_CHANNEL_ID = 0
SECRET = "BRAINROT_2026"

# 1. Lifespan handler (Fixes the "Deprecation" and "Shutdown" issues)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if not session_container["session"]:
        session_container["session"] = aiohttp.ClientSession()
    asyncio.create_task(bot.start(TOKEN))
    yield
    # Shutdown
    if session_container["session"]:
        await session_container["session"].close()

app = FastAPI(lifespan=lifespan)
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
session_container = {"session": None}

@bot.event
async def on_ready():
    print(f"✅ BOT ONLINE: {bot.user}")
    print(f"📢 CHANNEL ID: {LOG_CHANNEL_ID}")

async def stxr_warp_scan(place_id, user_id):
    session = session_container["session"]
    
    # 🟢 IMPROVED THUMBNAIL FETCH (Retries if Pending)
    target_img = None
    thumb_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=48x48&format=Png"
    
    for attempt in range(5):
        async with session.get(thumb_url) as r:
            t_data = await r.json()
            if t_data and 'data' in t_data and len(t_data['data']) > 0:
                state = t_data['data'][0].get('state')
                if state == 'Completed':
                    target_img = t_data['data'][0]['imageUrl']
                    print(f"🖼️ Thumbnail Acquired on attempt {attempt+1}")
                    break
                else:
                    print(f"⏳ Thumbnail state: {state}. Retrying...")
            await asyncio.sleep(2)

    if not target_img:
        print("❌ FAILED: Roblox Thumbnail never completed.")
        return None

    # 🔵 DEEP SCAN LOGIC
    cursor = ""
    for page in range(40):
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
                    return s_ids[i]
            
            cursor = data.get('nextPageCursor', "")
            if not cursor: break
    return None

@app.post("/stxr-log")
async def handle_request(request: Request):
    print("📨 Roblox request received!")
    data = await request.json()
    if data.get("secret") != SECRET: return {"status": "unauthorized"}

    uid, pid = data.get("userId"), data.get("placeId")
    item = data.get("itemName", "Unknown")

    job_id = await stxr_warp_scan(pid, uid)

    if job_id:
        channel = bot.get_channel(LOG_CHANNEL_ID) or await bot.fetch_channel(LOG_CHANNEL_ID)
        if channel:
            embed = discord.Embed(title="🎯 TARGET VERIFIED", color=0xFFFFFF)
            embed.set_thumbnail(url=f"https://www.roblox.com/headshot-thumbnail/image?userId={uid}&width=150&height=150&format=png")
            embed.add_field(name="Item", value=f"**{item}**")
            embed.add_field(name="Action", value=f"[JOIN SERVER](https://www.roblox.com/games/{pid}?jobId={job_id})")
            bot.loop.create_task(channel.send(embed=embed))
            print("✅ DISCORD SENT")
            return {"status": "success", "jobId": job_id}
    
    print("⚠️ Player not found in any server.")
    return {"status": "not_found"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
