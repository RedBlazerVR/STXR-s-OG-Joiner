import os, asyncio, aiohttp, discord
from discord.ext import commands
from quart import Quart

# --- 1. THE WEB SERVER ---
app = Quart(__name__)
@app.route('/')
async def home(): return "STXR_LOG: ACTIVE"

# --- 2. THE BOT ENGINE ---
TOKEN = os.getenv('DISCORD_TOKEN')
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

async def deep_scan(place_id, target_uid):
    # Set a strict 10-second timeout for the whole scan
    timeout = aiohttp.ClientTimeout(total=10) 
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            # Get target face
            t_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={target_uid}&size=48x48&format=Png"
            async with session.get(t_url) as r:
                t_data = await r.json()
                target_img = t_data['data'][0]['imageUrl']

            # Scan only the first 5 pages to prevent Render timeouts
            cursor = ""
            for page in range(1, 6):
                s_url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=100&cursor={cursor}"
                async with session.get(s_url) as r:
                    servers = await r.json()
                    if not servers.get('data'): break
                    
                    for s in servers['data']:
                        if not s.get('playerTokens'): continue
                        # Check players in this server
                        payload = [{"token": t, "type": "AvatarHeadShot", "size": "48x48", "format": "png"} for t in s['playerTokens']]
                        async with session.post("https://thumbnails.roblox.com/v1/batch", json=payload) as br:
                            batch = await br.json()
                            for img in batch.get('data', []):
                                if img.get('imageUrl') == target_img:
                                    return s['id'], page
                    
                    cursor = servers.get('nextPageCursor')
                    if not cursor: break
            return None, page
        except Exception as e:
            print(f"Scan error: {e}")
            return None, 0

@bot.event
async def on_message(message):
    if "STXR_LOG" in message.content:
        parts = message.content.split("|")
        if len(parts) < 4: return
        
        uid, pid, item = parts[1], parts[2], parts[3]
        msg = await message.channel.send(f"🛰️ **STXR_LOG** | Scanning for `{item}`...")
        
        job_id, pages = await deep_scan(pid, uid)
        if job_id:
            await msg.edit(content=f"🎯 **FOUND**\n`STXR_WARP|{job_id}`")
        else:
            await msg.edit(content=f"❌ **NOT FOUND** (Checked {pages} pages)")

# --- 3. THE STARTUP ---
async def start():
    port = int(os.environ.get("PORT", 10000))
    # Open the web port first so Render is happy
    asyncio.create_task(app.run_task(host='0.0.0.0', port=port))
    # Start the bot
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(start())
