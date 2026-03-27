import os, asyncio, aiohttp, discord, uvicorn
from discord.ext import commands
from quart import Quart

# --- 1. WEB SERVER ---
app = Quart(__name__)
@app.route('/')
async def home(): return "STXR_LOG: ACTIVE"

# --- 2. THE BOT ENGINE ---
TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Global session to prevent "Unclosed connector"
bot.session = None

@bot.event
async def on_ready():
    # Create the session once when the bot starts
    if bot.session is None:
        bot.session = aiohttp.ClientSession()
    print(f"✅ SUCCESS: {bot.user} IS ONLINE")

async def deep_scan(place_id, target_uid):
    if bot.session is None: return "ERROR", 0
    
    try:
        # Get target headshot
        t_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={target_uid}&size=48x48&format=Png"
        async with bot.session.get(t_url, timeout=10) as r:
            if r.status != 200: return "BLOCKED", 0
            t_data = await r.json()
            target_img = t_data['data'][0]['imageUrl']

        cursor = ""
        for page in range(1, 5): # Scan 5 pages max for speed
            s_url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=100&cursor={cursor}"
            async with bot.session.get(s_url, timeout=10) as r:
                if r.status != 200: break
                servers = await r.json()
                
                for s in servers.get('data', []):
                    if not s.get('playerTokens'): continue
                    payload = [{"token": t, "type": "AvatarHeadShot", "size": "48x48", "format": "png"} for t in s['playerTokens']]
                    async with bot.session.post("https://thumbnails.roblox.com/v1/batch", json=payload, timeout=10) as br:
                        if br.status == 200:
                            batch = await br.json()
                            if any(img.get('imageUrl') == target_img for img in batch.get('data', [])):
                                return s['id'], page
                
                cursor = servers.get('nextPageCursor')
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
            await msg.edit(content="⚠️ **ROBLOX BLOCKED** (Cloudflare). Wait 60s.")
        elif job_id:
            await msg.edit(content=f"🎯 **FOUND**\n`STXR_WARP|{job_id}`")
        else:
            await msg.edit(content=f"❌ **NOT FOUND** ({pages} pages checked)")

# --- 3. THE BOOT ENGINE ---
async def start_all():
    port = int(os.environ.get("PORT", 10000))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    
    # We use gather to run both simultaneously
    await asyncio.gather(server.serve(), bot.start(TOKEN))

if __name__ == "__main__":
    asyncio.run(start_all())
