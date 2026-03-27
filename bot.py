import os, asyncio, aiohttp, discord, uvicorn
from discord.ext import commands
from quart import Quart

# 1. THE WEB SERVER (RENDER'S HEARTBEAT)
app = Quart(__name__)
@app.route('/')
async def home(): return "STXR_LOG: ACTIVE"

# 2. THE BOT ENGINE
TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Persistent session to prevent "Unclosed Connector" errors
bot.session = None

@bot.event
async def on_ready():
    if bot.session is None:
        bot.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=10))
    print(f"✅ STXR_LOG IS LIVE: {bot.user}")

async def safe_get(url):
    """Fetch data but handle Cloudflare HTML errors gracefully"""
    try:
        async with bot.session.get(url, timeout=10) as r:
            if "text/html" in r.headers.get("Content-Type", ""):
                return None # It's a Cloudflare block page, not data
            return await r.json()
    except:
        return None

async def deep_scan(place_id, target_uid):
    # Get target headshot
    t_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={target_uid}&size=48x48&format=Png"
    data = await safe_get(t_url)
    if not data or not data.get('data'):
        return "BLOCKED", 0

    target_img = data['data'][0]['imageUrl']
    cursor = ""
    
    for page in range(1, 4): # Scan 3 pages to be safe/fast
        s_url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=100&cursor={cursor}"
        s_data = await safe_get(s_url)
        if not s_data or not s_data.get('data'): break
        
        for s in s_data['data']:
            if not s.get('playerTokens'): continue
            # Batch check
            payload = [{"token": t, "type": "AvatarHeadShot", "size": "48x48", "format": "png"} for t in s['playerTokens']]
            async with bot.session.post("https://thumbnails.roblox.com/v1/batch", json=payload, timeout=10) as br:
                if br.status == 200:
                    batch = await br.json()
                    if any(img.get('imageUrl') == target_img for img in batch.get('data', [])):
                        return s['id'], page
        
        cursor = s_data.get('nextPageCursor')
        if not cursor: break
    return None, page

@bot.event
async def on_message(message):
    if "STXR_LOG" in message.content:
        parts = message.content.split("|")
        if len(parts) < 4: return
        uid, pid, item = parts[1], parts[2], parts[3]
        
        status_msg = await message.channel.send(f"🛰️ **STXR_LOG** | Scanning for `{item}`...")
        
        job_id, pages = await deep_scan(pid, uid)
        
        if job_id == "BLOCKED":
            await status_msg.edit(content="❌ **STXR_LOG ERROR**\nRoblox is blocking Render's IP (Cloudflare). Use a different host or wait.")
        elif job_id:
            await status_msg.edit(content=f"🎯 **TARGET FOUND**\n`STXR_WARP|{job_id}`")
        else:
            await status_msg.edit(content=f"❌ **NOT FOUND** (Checked {pages} pages)")

# 3. BOOT ENGINE
async def start():
    port = int(os.environ.get("PORT", 10000))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    await asyncio.gather(server.serve(), bot.start(TOKEN))

if __name__ == "__main__":
    asyncio.run(start())
