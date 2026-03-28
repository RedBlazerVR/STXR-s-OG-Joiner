import os
import asyncio
import aiohttp
import discord
from discord.ext import commands
from quart import Quart

# 1. THE WEB SERVER (Answering Render's door immediately)
app = Quart(__name__)

@app.route('/')
async def home():
    return "STXR SYSTEM ONLINE"

# 2. THE BOT ENGINE
TOKEN = os.getenv('DISCORD_TOKEN')
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

async def get_target_data(session, uid):
    """Gracefully handle the Roblox/Cloudflare 'Error Footer'"""
    url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={uid}&size=48x48&format=Png"
    async with session.get(url) as r:
        if r.status != 200 or "application/json" not in r.headers.get("Content-Type", ""):
            return None
        data = await r.json()
        return data['data'][0]['imageUrl'] if data.get('data') else None

@bot.event
async def on_ready():
    print(f"✅ STXR_LOG IS LIVE: {bot.user}")

@bot.event
async def on_message(message):
    if "STXR_LOG" in message.content:
        try:
            # Format: STXR_LOG|UserId|PlaceId|ItemName
            parts = message.content.split("|")
            uid, pid, item = parts[1], parts[2], parts[3]
            
            status = await message.channel.send(f"🛰️ **STXR_LOG** | Searching for `{item}`...")
            
            async with aiohttp.ClientSession() as session:
                target_img = await get_target_data(session, uid)
                
                if not target_img:
                    return await status.edit(content="⚠️ **ROBLOX BLOCKED** (Cloudflare Error). Try again in a minute.")

                # Scan first 3 pages
                cursor = ""
                for page in range(1, 4):
                    s_url = f"https://games.roblox.com/v1/games/{pid}/servers/Public?limit=100&cursor={cursor}"
                    async with session.get(s_url) as r:
                        if r.status != 200: break
                        s_data = await r.json()
                        
                        for s in s_data.get('data', []):
                            tokens = s.get('playerTokens', [])
                            if not tokens: continue
                            
                            payload = [{"token": t, "type": "AvatarHeadShot", "size": "48x48", "format": "png"} for t in tokens]
                            async with session.post("https://thumbnails.roblox.com/v1/batch", json=payload) as br:
                                if br.status == 200:
                                    batch = await br.json()
                                    if any(img.get('imageUrl') == target_img for img in batch.get('data', [])):
                                        return await status.edit(content=f"🎯 **FOUND**\n`STXR_WARP|{s['id']}`")
                        
                        cursor = s_data.get('nextPageCursor')
                        if not cursor: break
                
                await status.edit(content="❌ **NOT FOUND** (Scanned 3 pages)")
        except Exception as e:
            print(f"Error: {e}")

# 3. THE "INSTANT-ON" STARTUP
async def main():
    port = int(os.environ.get("PORT", 10000))
    # This starts the web server in the background so Render is happy instantly
    bot.loop.create_task(app.run_task(host='0.0.0.0', port=port))
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
