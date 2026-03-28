import os, asyncio, aiohttp, uvicorn, discord
from discord.ext import commands
from fastapi import FastAPI, Request

TOKEN = os.getenv('DISCORD_TOKEN')
try:
    LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID', 0))
except:
    LOG_CHANNEL_ID = 0
SECRET = "BRAINROT_2026"

app = FastAPI()
intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix="!", intents=intents)
session_container = {"session": None}

@bot.event
async def on_ready():
    if not session_container["session"]:
        session_container["session"] = aiohttp.ClientSession()
    print(f"✅ STXR ENGINE ONLINE: {bot.user}")

async def stxr_warp_scan(place_id, user_id):
    session = session_container["session"]
    # 1. Get headshot
    async with session.get(f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=48x48&format=Png") as r:
        t_data = await r.json()
        if not t_data or 'data' not in t_data: return None
        target_img = t_data['data'][0]['imageUrl']

    # 2. Deep Parallel Scan
    cursor = ""
    for _ in range(35): # 3500 players depth
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
    data = await request.json()
    if data.get("secret") != SECRET: return {"status": "unauthorized"}

    uid, pid = data.get("userId"), data.get("placeId")
    item = data.get("itemName", "Unknown")

    job_id = await stxr_warp_scan(pid, uid)

    if job_id:
        try:
            # Force fetch the channel to avoid 'NoneType' errors
            channel = bot.get_channel(LOG_CHANNEL_ID) or await bot.fetch_channel(LOG_CHANNEL_ID)
            if channel:
                embed = discord.Embed(title="🎯 TARGET VERIFIED", color=0xFFFFFF)
                embed.set_thumbnail(url=f"https://www.roblox.com/headshot-thumbnail/image?userId={uid}&width=150&height=150&format=png")
                embed.add_field(name="Item", value=f"**{item}**", inline=True)
                embed.add_field(name="Action", value=f"[JOIN SERVER](https://www.roblox.com/games/{pid}?jobId={job_id})")
                bot.loop.create_task(channel.send(embed=embed))
                return {"status": "success", "jobId": job_id}
        except Exception as e:
            print(f"❌ Discord Error: {e}")
    
    return {"status": "not_found"}

@app.on_event("startup")
async def startup():
    asyncio.create_task(bot.start(TOKEN))

@app.on_event("shutdown")
async def shutdown():
    if session_container["session"]:
        await session_container["session"].close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
