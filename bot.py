import os, asyncio, aiohttp, discord
from discord.ext import commands
from quart import Quart

# --- 1. THE WEB SERVER (The "Doorbell" for Render) ---
app = Quart(__name__)

@app.route('/')
async def home():
    return "STXR's OG Joiner: PORT ACTIVE"

@app.route('/healthz')
async def health():
    return "OK", 200

# --- 2. THE BOT ENGINE ---
TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

async def deep_scan(place_id, target_uid):
    async with aiohttp.ClientSession() as session:
        t_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={target_uid}&size=48x48&format=Png"
        async with session.get(t_url) as r:
            t_data = await r.json()
            if not t_data.get('data'): return None, 0
            target_img = t_data['data'][0]['imageUrl']

        cursor = ""
        page = 1
        while page <= 15: # Safety cap
            s_url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=100&cursor={cursor}"
            async with session.get(s_url) as r:
                servers = await r.json()
                if not servers or not servers.get('data'): break
                
                for s in servers['data']:
                    if not s.get('playerTokens'): continue
                    payload = [{"token": t, "type": "AvatarHeadShot", "size": "48x48", "format": "png"} for t in s['playerTokens']]
                    async with session.post("https://thumbnails.roblox.com/v1/batch", json=payload) as br:
                        batch = await br.json()
                        if any(img.get('imageUrl') == target_img for img in batch.get('data', [])):
                            return s['id'], page
                
                cursor = servers.get('nextPageCursor')
                if not cursor: break
                page += 1
        return None, page

@bot.event
async def on_message(message):
    if "STXR_LOG" in message.content:
        try:
            parts = message.content.split("|")
            uid, pid, item = parts[1], parts[2], parts[3]
            status = await message.channel.send(f"🛰️ **STXR_LOG:** Scanning for `{item}`...")
            job_id, pages = await deep_scan(pid, uid)
            if job_id:
                await status.edit(content=f"🎯 **TARGET FOUND**\n`STXR_WARP|{job_id}`")
            else:
                await status.edit(content=f"❌ **MISS** (Pages: {pages})")
        except: pass

# --- 3. THE "PORT FORCER" STARTUP ---
async def start():
    port = int(os.environ.get("PORT", 10000))
    # We start the web server in the background FIRST
    loop = asyncio.get_event_loop()
    loop.create_task(app.run_task(host='0.0.0.0', port=port))
    # Then we start the bot
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(start())
