import os
import asyncio
import discord
import aiohttp
from discord.ext import commands
from fastapi import FastAPI, Request
import uvicorn

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
    if session_container["session"] is None:
        session_container["session"] = aiohttp.ClientSession()
    print(f"✅ STXR ENGINE ONLINE: {bot.user}")

async def stxr_scan(place_id, user_id):
    session = session_container["session"]
    for attempt in range(3): # 3 Retries for API lag
        try:
            # 1. Get Target Thumb
            thumb_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=48x48&format=Png"
            async with session.get(thumb_url) as r:
                t_data = await r.json()
                if not t_data.get('data'): continue
                target_img = t_data['data'][0]['imageUrl']

            # 2. Scan Servers
            cursor = ""
            for _ in range(8): # Scan up to 800 players
                api_url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=100&cursor={cursor}"
                async with session.get(api_url) as r:
                    servers = await r.json()
                    if 'data' not in servers: break
                    
                    for s in servers['data']:
                        tokens = s.get('playerTokens', [])
                        if not tokens: continue
                        
                        # Batch check thumbnails
                        payload = [{"token": t, "type": "AvatarHeadShot", "size": "48x48", "format": "png"} for t in tokens]
                        async with session.post("https://thumbnails.roblox.com/v1/batch", json=payload) as b_res:
                            batch = await b_res.json()
                            if any(img.get('imageUrl') == target_img for img in batch.get('data', [])):
                                return s.get('id')
                    
                    cursor = servers.get('nextPageCursor')
                    if not cursor: break
            await asyncio.sleep(1.5)
        except Exception as e:
            print(f"Scan Error: {e}")
    return None

@app.post("/stxr-log")
async def handle_snipe(request: Request):
    data = await request.json()
    if data.get("secret") != SECRET: return {"status": "unauthorized"}

    uid, pid = data.get("userId"), data.get("placeId")
    item, mut = data.get("itemName", "Unknown"), data.get("mutation", "None")

    job_id = await stxr_scan(pid, uid)
    if job_id:
        channel = bot.get_channel(LOG_CHANNEL_ID)
        if channel:
            link = f"https://www.roblox.com/games/{pid}?jobId={job_id}"
            embed = discord.Embed(title="🎯 TARGET VERIFIED", color=0xFFFFFF)
            embed.set_thumbnail(url=f"https://www.roblox.com/headshot-thumbnail/image?userId={uid}&width=150&height=150&format=png")
            embed.add_field(name="Item", value=item, inline=True)
            embed.add_field(name="Mutation", value=mut, inline=True)
            embed.add_field(name="Action", value=f"[JOIN SERVER]({link})")
            bot.loop.create_task(channel.send(embed=embed))
        return {"status": "success", "jobId": job_id, "itemName": item, "mutation": mut}
    
    return {"status": "not_found"}

@app.on_event("startup")
async def startup(): asyncio.create_task(bot.start(TOKEN))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
