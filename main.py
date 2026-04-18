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

async def get_target_thumb(session, user_id):
    """Retries 5 times to get a valid headshot URL for the target"""
    url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=48x48&format=Png&isCircular=false"
    for _ in range(5):
        async with session.get(url) as r:
            data = await r.json()
            if data and 'data' in data and len(data['data']) > 0:
                item = data['data'][0]
                if item.get('state') == 'Completed':
                    return item.get('imageUrl')
        await asyncio.sleep(2)
    return None

async def stxr_warp_scan(place_id, user_id):
    session = session_container["session"]
    target_img = await get_target_thumb(session, user_id)
    
    if not target_img:
        print(f"❌ THUMBNAIL FAIL: Could not find headshot for {user_id}")
        return None

    # DEEP SCAN: Check up to 100 pages (10,000 servers/slots)
    cursor = ""
    for page in range(100): 
        api_url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=100&cursor={cursor}"
        async with session.get(api_url) as r:
            if r.status != 200: break
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
                try:
                    batch = await res.json()
                    for img in batch.get('data', []):
                        if img.get('imageUrl') == target_img:
                            print(f"🎯 FOUND MATCH IN PAGE {page+1}!")
                            return s_ids[i]
                except: continue
            
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

    print(f"📨 Logged Claim: {item} (User: {uid})")

    # 🚀 THE "NEVER-MISS" LOOP
    # We try scanning 3 times over 30 seconds to wait for Roblox API to update
    for attempt in range(3):
        print(f"🔎 Search attempt {attempt + 1} for {uid}...")
        job_id = await stxr_warp_scan(pid, uid)
        
        if job_id:
            channel = bot.get_channel(LOG_CHANNEL_ID) or await bot.fetch_channel(LOG_CHANNEL_ID)
            if channel:
                embed = discord.Embed(title="🎯 TARGET LOCATED", color=0x00FF00)
                embed.set_thumbnail(url=f"https://www.roblox.com/headshot-thumbnail/image?userId={uid}&width=150&height=150&format=png")
                embed.add_field(name="Item", value=f"**{item}**", inline=False)
                embed.add_field(name="Join Link", value=f"[CLICK HERE TO JOIN](https://www.roblox.com/games/{pid}?jobId={job_id})")
                bot.loop.create_task(channel.send(embed=embed))
                return {"status": "success", "jobId": job_id}
        
        if attempt < 2:
            print("⏳ Not found yet. Waiting 10s for API refresh...")
            await asyncio.sleep(10)

    print(f"❌ SCAN EXPIRED: {uid} was not found in the public server list.")
    return {"status": "not_found"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
