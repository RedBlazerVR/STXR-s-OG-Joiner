import os
import asyncio
import discord
import aiohttp
from discord.ext import commands
from fastapi import FastAPI, Request
import uvicorn

# --- CONFIG ---
# These should be set in Railway Variables tab for safety
TOKEN = os.getenv('DISCORD_TOKEN')
try:
    LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID', 0))
except:
    LOG_CHANNEL_ID = 0

SECRET = "BRAINROT_2026"

# Init
app = FastAPI()
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
session_container = {"session": None}

@bot.event
async def on_ready():
    if session_container["session"] is None:
        session_container["session"] = aiohttp.ClientSession()
    print(f"✅ STXR ENGINE ONLINE: {bot.user}")

# --- SCANNER LOGIC ---
async def stxr_scan(place_id, user_id):
    session = session_container["session"]
    if not session: return None
    try:
        # Get headshot
        async with session.get(f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=48x48&format=Png") as r:
            t_data = await r.json()
            if not t_data.get('data'): return None
            target_img = t_data['data'][0]['imageUrl']

        cursor = ""
        for _ in range(3): # Scan 300 players (faster)
            async with session.get(f"https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=100&cursor={cursor}") as r:
                servers = await r.json()
                if 'data' not in servers: break
                for s in servers['data']:
                    # Simple check: If user is in this server
                    if any(user_id == p_id for p_id in s.get('playerIds', [])):
                        return s.get('id')
                cursor = servers.get('nextPageCursor')
                if not cursor: break
    except Exception as e:
        print(f"Scan Error: {e}")
    return None

# --- API ENDPOINT ---
@app.post("/stxr-log")
async def handle_snipe(request: Request):
    data = await request.json()
    if data.get("secret") != SECRET:
        return {"status": "unauthorized"}

    uid = data.get("userId")
    pid = data.get("placeId")
    item = data.get("itemName", "Unknown")
    mutation = data.get("mutation", "None")

    # ⚡ Run Scan
    job_id = await stxr_scan(pid, uid)
    
    if job_id:
        # 🔊 Discord Log
        channel = bot.get_channel(LOG_CHANNEL_ID)
        if channel:
            link = f"https://www.roblox.com/games/{pid}?jobId={job_id}"
            embed = discord.Embed(title="🎯 TARGET FOUND", color=0xFFFFFF)
            embed.add_field(name="Item", value=item, inline=True)
            embed.add_field(name="Mutation", value=mutation, inline=True)
            embed.add_field(name="Link", value=f"[CLICK TO JOIN]({link})", inline=False)
            # Fire and forget the discord message so we don't hang the API
            bot.loop.create_task(channel.send(embed=embed))

        return {"status": "success", "jobId": job_id, "itemName": item, "mutation": mutation}
    
    return {"status": "not_found"}

# --- LIFECYCLE MANAGEMENT ---
@app.on_event("startup")
async def startup_event():
    # Start Discord Bot in the background
    asyncio.create_task(bot.start(TOKEN))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
