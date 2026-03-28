import os, asyncio, discord, aiohttp, uvicorn
from discord.ext import commands
from fastapi import FastAPI, Request

# --- CONFIG ---
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
    print(f"✅ DEEP SCANNER ONLINE: {bot.user}")

async def stxr_deep_scan(place_id, user_id):
    session = session_container["session"]
    try:
        # 1. Get the target's unique headshot URL
        thumb_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=48x48&format=Png"
        async with session.get(thumb_url) as r:
            t_data = await r.json()
            if not t_data.get('data'): return None
            target_img = t_data['data'][0]['imageUrl']

        cursor = ""
        # 2. Iterate through ALL server pages (up to 25 pages / 2500 players)
        for _ in range(25): 
            api_url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=100&cursor={cursor}"
            async with session.get(api_url) as r:
                data = await r.json()
                if 'data' not in data: break
                
                # Prepare batch check for all players in these 100 servers
                tasks = []
                server_map = {}
                for s in data['data']:
                    tokens = s.get('playerTokens', [])
                    if tokens:
                        payload = [{"token": t, "type": "AvatarHeadShot", "size": "48x48", "format": "png"} for t in tokens]
                        tasks.append(session.post("https://thumbnails.roblox.com/v1/batch", json=payload))
                        server_map[len(tasks)-1] = s.get('id')

                # Execute batch requests in parallel
                responses = await asyncio.gather(*tasks)
                for idx, res in enumerate(responses):
                    batch_data = await res.json()
                    if any(img.get('imageUrl') == target_img for img in batch_data.get('data', [])):
                        return server_map[idx]
                
                cursor = data.get('nextPageCursor')
                if not cursor: break
    except Exception as e:
        print(f"Deep Scan Error: {e}")
    return None

@app.post("/stxr-log")
async def handle_snipe(request: Request):
    data = await request.json()
    if data.get("secret") != SECRET: return {"status": "unauthorized"}

    uid, pid = data.get("userId"), data.get("placeId")
    item, mut = data.get("itemName", "Unknown"), data.get("mutation", "None")

    job_id = await stxr_deep_scan(pid, uid)
    if job_id:
        channel = bot.get_channel(LOG_CHANNEL_ID)
        if channel:
            link = f"https://www.roblox.com/games/{pid}?jobId={job_id}"
            embed = discord.Embed(title="🎯 TARGET VERIFIED", color=0xFFFFFF)
            embed.set_thumbnail(url=f"https://www.roblox.com/headshot-thumbnail/image?userId={uid}&width=150&height=150&format=png")
            embed.add_field(name="Item", value=f"**{item}**", inline=True)
            embed.add_field(name="Mutation", value=mut, inline=True)
            embed.add_field(name="Action", value=f"[JOIN SERVER]({link})")
            bot.loop.create_task(channel.send(embed=embed))
        return {"status": "success", "jobId": job_id, "itemName": item, "mutation": mut}
    
    return {"status": "not_found"}

@app.on_event("startup")
async def startup(): asyncio.create_task(bot.start(TOKEN))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
