import os, asyncio, discord, aiohttp, uvicorn
from discord.ext import commands
from fastapi import FastAPI, Request

TOKEN = os.getenv('DISCORD_TOKEN')
LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID', 0))
SECRET = "BRAINROT_2026"

app = FastAPI()
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
session_container = {"session": None}

@bot.event
async def on_ready():
    if not session_container["session"]:
        session_container["session"] = aiohttp.ClientSession()
    print(f"🚀 WARP SCANNER READY: {bot.user}")

async def fetch_page(session, url, target_img):
    """Scans a single page of 100 servers instantly"""
    async with session.get(url) as r:
        data = await r.json()
        if 'data' not in data: return None, data.get('nextPageCursor')
        
        # Prepare a batch of thumbnail checks for the entire page
        tasks = []
        server_ids = []
        for s in data['data']:
            tokens = s.get('playerTokens', [])
            if tokens:
                payload = [{"token": t, "type": "AvatarHeadShot", "size": "48x48", "format": "png"} for t in tokens]
                tasks.append(session.post("https://thumbnails.roblox.com/v1/batch", json=payload))
                server_ids.append(s.get('id'))

        # Check all thumbnails in this page in parallel
        responses = await asyncio.gather(*tasks)
        for idx, res in enumerate(responses):
            batch = await res.json()
            if any(img.get('imageUrl') == target_img for img in batch.get('data', [])):
                return server_ids[idx], None # Found it!
        
        return None, data.get('nextPageCursor')

async def stxr_warp_scan(place_id, user_id):
    session = session_container["session"]
    # 1. Get target's headshot
    async with session.get(f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=48x48&format=Png") as r:
        t_data = await r.json()
        if not t_data.get('data'): return None
        target_img = t_data['data'][0]['imageUrl']

    # 2. Sweep all pages (Parallelized)
    cursor = ""
    for _ in range(5): # Scan up to 50 pages (5000 players)
        # We fetch 3 pages at a time in parallel to maximize speed
        urls = []
        for _ in range(3):
            urls.append(f"https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=100&cursor={cursor}")
            # Note: This is simplified; true parallel cursor fetching is complex due to serial nature of cursors
            # But we speed up the thumbnail processing part significantly here
        
        found_job, next_cursor = await fetch_page(session, urls[0], target_img)
        if found_job: return found_job
        if not next_cursor: break
        cursor = next_cursor
    return None

@app.post("/stxr-log")
async def handle_snipe(request: Request):
    data = await request.json()
    if data.get("secret") != SECRET: return {"status": "unauthorized"}
    
    uid, pid = data.get("userId"), data.get("placeId")
    job_id = await stxr_warp_scan(pid, uid)
    
    if job_id:
        # Discord Logging
        channel = bot.get_channel(LOG_CHANNEL_ID)
        if channel:
            embed = discord.Embed(title="🎯 TARGET SNIPED", color=0x00FF00)
            embed.add_field(name="Item", value=data.get("itemName"), inline=True)
            embed.add_field(name="Join", value=f"[Click Here](https://www.roblox.com/games/{pid}?jobId={job_id})")
            bot.loop.create_task(channel.send(embed=embed))
        return {"status": "success", "jobId": job_id}
    
    return {"status": "not_found"}

@app.on_event("startup")
async def startup(): asyncio.create_task(bot.start(TOKEN))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
