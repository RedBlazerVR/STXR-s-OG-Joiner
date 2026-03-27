import discord
from discord.ext import commands
import aiohttp
import asyncio
import os
from flask import Flask
from threading import Thread

# --- STEP 1: KEEP-ALIVE SERVER (For Render) ---
app = Flask('')
@app.route('/')
def home():
    return "STXR TURBO BOT IS ONLINE"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# --- STEP 2: TURBO SNIPER BOT ---
# Use an environment variable for the token if possible, or paste it below
TOKEN = os.getenv('DISCORD_TOKEN') or 'YOUR_BOT_TOKEN_HERE'

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

async def turbo_scan(place_id, target_uid):
    async with aiohttp.ClientSession() as session:
        # 1. Get Target Avatar Token
        thumb_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={target_uid}&size=48x48&format=Png&isCircular=false"
        async with session.get(thumb_url) as r:
            thumb_data = await r.json()
            if not thumb_data.get('data'): return None
            target_img = thumb_data['data'][0]['imageUrl']

        # 2. Get Public Servers (Limit 100 for speed)
        server_url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=100"
        async with session.get(server_url) as r:
            servers = await r.json()
            if not servers.get('data'): return None

        # 3. Parallel Racing (Scan all servers at once)
        async def check_server(server):
            if not server.get('playerTokens'): return None
            batch_payload = [{"token": t, "type": "AvatarHeadShot", "size": "48x48", "format": "png"} for t in server['playerTokens']]
            async with session.post("https://thumbnails.roblox.com/v1/batch", json=batch_payload) as r:
                batch = await r.json()
                if any(img.get('imageUrl') == target_img for img in batch.get('data', [])):
                    return server['id']
            return None

        # Run all server checks in parallel
        tasks = [check_server(s) for s in servers['data']]
        results = await asyncio.gather(*tasks)
        
        # Return the first JobID found
        for res in results:
            if res: return res
    return None

@bot.event
async def on_ready():
    print(f'⚡ STXR BOT LOGGED IN AS {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user: return

    # Format: STXR_HUNT|UserId|PlaceId|ItemName
    if "STXR_HUNT" in message.content:
        try:
            parts = message.content.split("|")
            uid, pid, item = parts[1], parts[2], parts[3]
            
            sent_msg = await message.channel.send(f"🛰️ **LOCKING ON:** {item}...")
            
            job_id = await turbo_scan(pid, uid)
            
            if job_id:
                await sent_msg.edit(content=f"✅ **TARGET LOCATED!**\n`STXR_WARP|{job_id}`")
            else:
                await sent_msg.edit(content=f"❌ **MISS:** Target not in top 100 servers.")
        except Exception as e:
            print(f"Error: {e}")

# Run the Keep-Alive and the Bot
keep_alive()
bot.run(TOKEN)
