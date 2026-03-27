import os
import asyncio
import aiohttp
import discord
from discord.ext import commands
from quart import Quart

# --- 1. THE HEARTBEAT (Keep Render Online) ---
app = Quart(__name__)

@app.route('/')
async def home():
    return "STXR's OG Joiner: STATUS - ACTIVE"

# --- 2. THE SNIPER LOGIC ---
TOKEN = os.getenv('DISCORD_TOKEN') or 'PASTE_TOKEN_HERE'

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

async def scan_servers(place_id, target_uid):
    async with aiohttp.ClientSession() as session:
        # Get Target Thumbnail
        thumb_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={target_uid}&size=48x48&format=Png&isCircular=false"
        async with session.get(thumb_url) as r:
            t_data = await r.json()
            if not t_data.get('data'): return None
            target_img = t_data['data'][0]['imageUrl']

        # Grab top 100 servers (Roblox Max API Limit)
        s_url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=100"
        async with session.get(s_url) as r:
            servers = await r.json()
            if not servers.get('data'): return None

        # Turbo-Race check
        async def check(server):
            if not server.get('playerTokens'): return None
            payload = [{"token": t, "type": "AvatarHeadShot", "size": "48x48", "format": "png"} for t in server['playerTokens']]
            async with session.post("https://thumbnails.roblox.com/v1/batch", json=payload) as r:
                batch = await r.json()
                if any(img.get('imageUrl') == target_img for img in batch.get('data', [])):
                    return server['id']
            return None

        results = await asyncio.gather(*(check(s) for s in servers['data']))
        return next((res for res in results if res), None)

@bot.event
async def on_ready():
    print(f"--- STXR's OG Joiner ---")
    print(f"Logged in as: {bot.user}")
    print(f"Ready for signal...")

@bot.event
async def on_message(message):
    if "STXR_HUNT" in message.content:
        # Format: STXR_HUNT|UserId|PlaceId|ItemName
        _, uid, pid, item = message.content.split("|")
        log = await message.channel.send(f"🔍 **OG JOINER:** Searching for `{item}`...")
        
        job_id = await scan_servers(pid, uid)
        
        if job_id:
            await log.edit(content=f"🎯 **STXR's OG Joiner | TARGET FOUND**\n`STXR_WARP|{job_id}`")
        else:
            await log.edit(content=f"⚠️ **OG JOINER:** Target not in current top 100 servers.")

# --- 3. PRODUCTION BOOT ---
@bot.event
async def setup_hook():
    port = int(os.environ.get("PORT", 8080))
    bot.loop.create_task(app.run_task(host='0.0.0.0', port=port))

bot.run(TOKEN)
