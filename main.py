import os, asyncio, aiohttp, uvicorn, discord
from discord.ext import commands
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager

TOKEN = os.getenv('DISCORD_TOKEN')
try:
    LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID', 0))
except:
    LOG_CHANNEL_ID = 0
SECRET = "BRAINROT_2026"

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
    print(f"✅ STXR ACTIVE: {bot.user}")

async def stxr_warp_scan(place_id, user_id):
    session = session_container["session"]
    
    # 🎯 NEW: Direct Template Bypass (No more "Refused to provide thumbnail")
    target_img_url = f"https://tr.rbxcdn.com/avatar-headshot/png/48/48/{user_id}/1"
    print(f"🔍 Searching for UID: {user_id}")

    cursor = ""
    for _ in range(45): 
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
                # We check if any image in the server batch matches our target's predicted URL
                for img in batch.get('data', []):
                    # We check if the image URL contains the UserID or matches the pattern
                    if str(user_id) in img.get('imageUrl', '') or img.get('imageUrl') == target_img_url:
                        print(f"🎯 TARGET FOUND: {s_ids[i]}")
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

    job_id = await stxr_warp_scan(pid, uid)

    if job_id:
        channel = bot.get_channel(LOG_CHANNEL_ID) or await bot.fetch_channel(LOG_CHANNEL_ID)
        if channel:
            embed = discord.Embed(title="🎯 TARGET VERIFIED", color=0x000000)
            embed.set_thumbnail(url=f"https://www.roblox.com/headshot-thumbnail/image?userId={uid}&width=150&height=150&format=png")
            embed.add_field(name="Item", value=f"**{item}**")
            embed.add_field(name="Join", value=f"[CLICK TO JOIN](https://www.roblox.com/games/{pid}?jobId={job_id})")
            bot.loop.create_task(channel.send(embed=embed))
            print("✅ DISCORD SENT")
            return {"status": "success", "jobId": job_id}
    
    print(f"⚠️ {item} not found in public servers.")
    return {"status": "not_found"}

if __name__ == "__main__":
    # 🛠️ RAILWAY STAY ALIVE FIX: Use 0.0.0.0 and dynamic port
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
