import os, asyncio, aiohttp, discord, uvicorn
from discord.ext import commands
from quart import Quart

# --- 1. WEB SERVER (Satisfies Render Instantly) ---
app = Quart(__name__)
@app.route('/')
async def home(): return "STXR_SYSTEM: ONLINE"

# --- 2. THE BOT ENGINE ---
TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Single session to prevent the "Unclosed Connector" crash
bot.session = None

@bot.event
async def on_ready():
    if bot.session is None:
        # Limit connections so we don't trigger Cloudflare as hard
        connector = aiohttp.TCPConnector(limit=5)
        bot.session = aiohttp.ClientSession(connector=connector)
    print(f"✅ BOT IS LIVE: {bot.user}")

async def deep_scan(place_id, target_uid):
    if not bot.session: return "ERROR", 0
    try:
        # Get headshot
        t_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={target_uid}&size=48x48&format=Png"
        async with bot.session.get(t_url, timeout=5) as r:
            if r.status != 200: return "BLOCKED", 0
            # If Roblox sends HTML (The Error Footer), this line will fail safely
            if "application/json" not in r.headers.get("Content-Type", ""): return "BLOCKED", 0
            data = await r.json()
            target_img = data['data'][0]['imageUrl']

        # Scan max 3 pages to prevent Render timeout
        cursor = ""
        for page in range(1, 4):
            s_url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=100&cursor={cursor}"
            async with bot.session.get(s_url, timeout=5) as r:
                if r.status != 200: break
                s_data = await r.json()
                for s in s_data.get('data', []):
                    if not s.get('playerTokens'): continue
                    payload = [{"token": t, "type": "AvatarHeadShot", "size": "48x48", "format": "png"} for t in s['playerTokens']]
                    async with bot.session.post("https://thumbnails.roblox.com/v1/batch", json=payload, timeout=5) as br:
                        if br.status == 200:
                            batch = await br.json()
                            if any(img.get('imageUrl') == target_img for img in batch.get('data', [])):
                                return s['id'], page
                cursor = s_data.get('nextPageCursor')
                if not cursor: break
        return None, page
    except Exception as e:
        print(f"Scan Error: {e}")
        return None, 0

@bot.event
async def on_message(message):
    if "STXR_LOG" in message.content:
        parts = message.content.split("|")
        if len(parts) < 4: return
        uid, pid, item = parts[1], parts[2], parts[3]
        
        msg = await message.channel.send(f"🛰️ **STXR_LOG** | Hunting `{item}`...")
        job_id, pages = await deep_scan(pid, uid)
        
        if job_id == "BLOCKED":
            await msg.edit(content="⚠️ **SCAN FAILED**\nRoblox blocked the request. Render's IP is currently flagged. Try again in a few minutes.")
        elif job_id:
            await msg.edit(content=f"🎯 **TARGET FOUND**\n`STXR_WARP|{job_id}`")
        else:
            await msg.edit(content=f"❌ **NOT FOUND** (Checked {pages} pages)")

# --- 3. THE STARTUP (THE FIX) ---
async def start():
    port = int(os.environ.get("PORT", 10000))
    # Start web server and bot together
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    await asyncio.gather(server.serve(), bot.start(TOKEN))

if __name__ == "__main__":
    asyncio.run(start())
