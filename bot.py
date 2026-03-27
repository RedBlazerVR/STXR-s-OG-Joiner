import os
import asyncio
import aiohttp
import discord
from discord.ext import commands
from quart import Quart
import uvicorn

# --- 1. THE WEB ENGINE (Keep Render Alive) ---
app = Quart(__name__)

@app.route('/')
async def home():
    return "STXR's OG Joiner: SYSTEM ACTIVE"

@app.route('/health')
async def health():
    return "OK", 200

# --- 2. THE SNIPER ENGINE ---
TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.all() # Ensure Message Content Intent is ON in Dev Portal
bot = commands.Bot(command_prefix="!", intents=intents)

async def deep_scan(place_id, target_uid):
    async with aiohttp.ClientSession() as session:
        # Get Target Avatar
        t_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={target_uid}&size=48x48&format=Png"
        async with session.get(t_url) as r:
            t_data = await r.json()
            if not t_data.get('data'): return None
            target_img = t_data['data'][0]['imageUrl']

        # Scan all pages
        cursor = ""
        page = 1
        while True:
            s_url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=100&cursor={cursor}"
            async with session.get(s_url) as r:
                servers = await r.json()
                if not servers or not servers.get('data'): break
                
                async def check_s(s):
                    if not s.get('playerTokens'): return None
                    payload = [{"token": t, "type": "AvatarHeadShot", "size": "48x48", "format": "png"} for t in s['playerTokens']]
                    async with session.post("https://thumbnails.roblox.com/v1/batch", json=payload) as br:
                        batch = await br.json()
                        if any(img.get('imageUrl') == target_img for img in batch.get('data', [])):
                            return s['id']
                    return None

                results = await asyncio.gather(*(check_s(s) for s in servers['data']))
                found = next((res for res in results if res), None)
                if found: return found, page
                
                cursor = servers.get('nextPageCursor')
                if not cursor: break
                page += 1
        return None, page

@bot.event
async def on_ready():
    print(f"⚡ STXR's OG Joiner | LOGGED IN: {bot.user}")

@bot.event
async def on_message(message):
    if "STXR_LOG" in message.content:
        try:
            _, uid, pid, item = message.content.split("|")
            status = await message.channel.send(f"🛰️ **STXR_LOG:** Searching for `{item}`...")
            
            job_id, pages = await deep_scan(pid, uid)
            
            if job_id:
                await status.edit(content=f"🎯 **STXR's OG Joiner | SUCCESS**\n`STXR_WARP|{job_id}`\nScanned {pages} pages.")
            else:
                await status.edit(content=f"❌ **STXR's OG Joiner | MISS**\nTarget not found in {pages} pages.")
        except Exception as e:
            print(f"Error: {e}")

# --- 3. THE HYPER-BOOT SEQUENCE ---
async def main():
    port = int(os.environ.get("PORT", 10000))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    
    # Run Web Server and Discord Bot simultaneously
    await asyncio.gather(
        server.serve(),
        bot.start(TOKEN)
    )

if __name__ == "__main__":
    asyncio.run(main())
