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

# 1. LIFESPAN HANDLER
@asynccontextmanager
async def lifespan(app: FastAPI):
    if not session_container["session"]:
        session_container["session"] = aiohttp.ClientSession()
    asyncio.create_task(bot.start(TOKEN))
    yield
    if session_container["session"]:
        await session_container["session"].close()

app = FastAPI(lifespan=lifespan)
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
session_container = {"session": None}

@bot.event
async def on_ready():
    print(f"✅ STXR ENGINE ONLINE: {bot.user}")
    print(f"📢 LOGGING TO: {LOG_CHANNEL_ID}")

async def stxr_warp_scan(place_id, user_id):
    session = session_container["session"]
    target_img = None
    
    # 🟢 TRIPLE-CHECK THUMBNAIL (Ensures we have a face to look for)
    thumb_types = [
        f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=48x48&format=Png",
        f"https://thumbnails.roblox.com/v1/users/avatar?userIds={user_id}&size=48x48&format=Png"
    ]
    
    for url in thumb_types:
        for _ in range(3):
            async with session.get(url) as r:
                t_data = await r.json()
                if t_data and 'data' in t_data and len(t_data['data']) > 0:
                    item = t_data['data'][0]
                    if item.get('state') == 'Completed' and item.get('imageUrl'):
                        target_img = item.get('imageUrl')
                        break
            await asyncio.sleep(1)
        if target_img: break

    if not target_img:
        print(f"❌ FAILED: Could not acquire thumbnail for {user_id}")
        return None

    # 🔵 PARALLEL DEEP SCAN (Batches of 100)
    cursor = ""
    for page in range(45): 
        print(f"📡 Scanning Page {page+1}...")
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
                    print(f"🎯 MATCH FOUND: {s_ids[i]}")
                    return s_ids[i]
            
            cursor = data.get('nextPageCursor', "")
            if not cursor: break
    return None

@app.post("/stxr-log")
async def handle_request(request: Request):
    data = await request.json()
    if data.get("secret") != SECRET: return {"status": "unauthorized"}

    uid = data.get("userId")
    pid = data.get("placeId")
    item = data.get("itemName", "Unknown")

    print(f"📨 Claim Received! Item: {item} | User: {uid}")

    # ⏳ GRACE PERIOD: Wait for Roblox API to catch up with the server change
    await asyncio.sleep(5) 

    job_id = await stxr_warp_scan(pid, uid)

    if job_id:
        channel = bot.get_channel(LOG_CHANNEL_ID) or await bot.fetch_channel(LOG_CHANNEL_ID)
        if channel:
            embed = discord.Embed(title="🎯 TARGET VERIFIED", color=0x000000)
            embed.set_thumbnail(url=f"https://www.roblox.com/headshot-thumbnail/image?userId={uid}&width=150&height=150&format=png")
            embed.add_field(name="Item", value=f"**{item}**", inline=True)
            embed.add_field(name="Join", value=f"[CLICK TO JOIN](https://www.roblox.com/games/{pid}?jobId={job_id})")
            bot.loop.create_task(channel.send(embed=embed))
            print("✅ DISCORD NOTIFIED")
            return {"status": "success", "jobId": job_id}
    
    print(f"⚠️ {item} scan finished. No match found.")
    return {"status": "not_found"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
