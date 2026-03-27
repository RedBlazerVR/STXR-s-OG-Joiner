import os, asyncio, aiohttp, discord, uvicorn
from discord.ext import commands
from quart import Quart

# 1. IMMEDIATE WEB SERVER (Starts in 0.1s to satisfy Render)
app = Quart(__name__)
@app.route('/')
async def home(): return "SYSTEM_ACTIVE"

@app.route('/healthz')
async def health(): return "OK", 200

# 2. BOT SETUP
TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Global Session to prevent "Unclosed Connector" errors
bot.session = None

@bot.event
async def on_ready():
    if bot.session is None:
        bot.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=5))
    print(f"✅ DISCORD CONNECTED: {bot.user}")

async def deep_scan(place_id, target_uid):
    if not bot.session: return "ERROR", 0
    try:
        t_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={target_uid}&size=48x48&format=Png"
        async with bot.session.get(t_url, timeout=5) as r:
            if r.status != 200: return "BLOCKED", 0
            data = await r.json()
            target_img = data['data'][0]['imageUrl']

        cursor = ""
        for page in range(1, 4): # Fast scan 3 pages
            s_url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=100&cursor={cursor}"
            async with bot.session.get(s_url, timeout=5) as r:
                if r.status != 200: break
                s_data = await r.json()
                for s in s_data.get('data', []):
                    if not s.get('playerTokens'): continue
                    # Simple batch check
                    payload = [{"token": t, "type": "AvatarHeadShot", "size": "48x48", "format": "png"} for t in s['playerTokens']]
                    async with bot.session.post("https://thumbnails.roblox.com/v1/batch", json=payload, timeout=5) as br:
                        if br.status == 200:
                            batch = await br.json()
                            if any(img.get('imageUrl') == target_img for img in batch.get('data', [])):
                                return s['id'], page
                cursor = s_data.get('nextPageCursor')
                if not cursor: break
        return None, page
    except: return None, 0

@bot.event
async def on_message(message):
    if "STXR_LOG" in message.content:
        parts = message.content.split("|")
        if len(parts) < 4: return
        uid, pid, item = parts[1], parts[2], parts[3]
        msg = await message.channel.send(f"🛰️ **STXR_LOG** | Hunting `{item}`...")
        job_id, pages = await deep_scan(pid, uid)
        if job_id == "BLOCKED":
            await msg.edit(content="⚠️ **ROBLOX BLOCKED** (Cloudflare). Try again later.")
        elif job_id:
            await msg.edit(content=f"🎯 **FOUND**\n`STXR_WARP|{job_id}`")
        else:
            await msg.edit(content=f"❌ **NOT FOUND** ({pages} pages)")

# 3. THE STARTUP (THE FIX)
async def main():
    port = int(os.environ.get("PORT", 10000))
    # Create the uvicorn config
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    
    # We start both, but uvicorn starts the web port immediately
    await asyncio.gather(
        server.serve(),
        bot.start(TOKEN)
    )

if __name__ == "__main__":
    asyncio.run(main())
