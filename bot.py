import os, asyncio, aiohttp, discord
from discord.ext import commands
from quart import Quart

# --- 1. THE WEB SERVER (RENDER'S DOORBELL) ---
app = Quart(__name__)
@app.route('/')
async def home(): return "STXR_LOG: ACTIVE"

# --- 2. THE BOT ENGINE ---
TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.default()
intents.message_content = True # MUST BE ON IN DEV PORTAL
bot = commands.Bot(command_prefix="!", intents=intents)

# THE SCANNER (Optimized for Render Free Tier)
async def deep_scan(place_id, target_uid):
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            t_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={target_uid}&size=48x48&format=Png"
            async with session.get(t_url) as r:
                if r.status != 200: return "BLOCKED", 0
                t_data = await r.json()
                target_img = t_data['data'][0]['imageUrl']

            cursor = ""
            for page in range(1, 6):
                s_url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=100&cursor={cursor}"
                async with session.get(s_url) as r:
                    if r.status != 200: break
                    servers = await r.json()
                    if not servers or not servers.get('data'): break
                    
                    for s in servers['data']:
                        if not s.get('playerTokens'): continue
                        payload = [{"token": t, "type": "AvatarHeadShot", "size": "48x48", "format": "png"} for t in s['playerTokens']]
                        async with session.post("https://thumbnails.roblox.com/v1/batch", json=payload) as br:
                            if br.status == 200:
                                batch = await br.json()
                                for img in batch.get('data', []):
                                    if img.get('imageUrl') == target_img:
                                        return s['id'], page
                    
                    cursor = servers.get('nextPageCursor')
                    if not cursor: break
            return None, page
        except Exception as e:
            print(f"DEBUG: Scan Error -> {e}")
            return None, 0

@bot.event
async def on_ready():
    print(f"✅ SUCCESS: {bot.user} IS NOW ONLINE")

@bot.event
async def on_message(message):
    if "STXR_LOG" in message.content:
        parts = message.content.split("|")
        if len(parts) < 4: return
        uid, pid, item = parts[1], parts[2], parts[3]
        msg = await message.channel.send(f"🛰️ **STXR_LOG** | Scanning for `{item}`...")
        job_id, pages = await deep_scan(pid, uid)
        if job_id == "BLOCKED":
            await msg.edit(content="⚠️ **ROBLOX BLOCKED** (Cloudflare). Wait 60s.")
        elif job_id:
            await msg.edit(content=f"🎯 **FOUND**\n`STXR_WARP|{job_id}`")
        else:
            await msg.edit(content=f"❌ **NOT FOUND** ({pages} pages checked)")

# --- 3. THE "FORCE START" ---
async def start_all():
    port = int(os.environ.get("PORT", 10000))
    # Run Web Server
    loop = asyncio.get_event_loop()
    loop.create_task(app.run_task(host='0.0.0.0', port=port))
    # Run Bot
    print("🛰️ ATTEMPTING DISCORD LOGIN...")
    await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(start_all())
    except Exception as e:
        print(f"❌ CRITICAL BOOT ERROR: {e}")
