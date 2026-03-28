import os, asyncio, discord, aiohttp
from discord.ext import commands
from flask import Flask
from threading import Thread

# --- 1. WEB SERVER (Answering Render's Health Check) ---
app = Flask('')
@app.route('/')
def home(): return "STXR_SYSTEM_V3: ONLINE"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 2. THE BOT ENGINE (Speed Optimized) ---
TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.all() # Ensure all intents are ON in Dev Portal
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    bot.session = aiohttp.ClientSession()
    print(f"✅ SUCCESS: {bot.user} IS ONLINE AND SCANNING")

async def fast_scan(pid, uid):
    """Ultra-fast batch scanning for target user"""
    try:
        # Get target's headshot once
        t_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={uid}&size=48x48&format=Png"
        async with bot.session.get(t_url) as r:
            t_data = await r.json()
            target_img = t_data['data'][0]['imageUrl']

        # Scan first 200 players (2 pages) instantly
        cursor = ""
        for _ in range(2):
            s_url = f"https://games.roblox.com/v1/games/{pid}/servers/Public?limit=100&cursor={cursor}"
            async with bot.session.get(s_url) as r:
                servers = await r.json()
                if not servers.get('data'): break
                
                tasks = []
                for s in servers['data']:
                    tokens = s.get('playerTokens', [])
                    if tokens:
                        payload = [{"token": t, "type": "AvatarHeadShot", "size": "48x48", "format": "png"} for t in tokens]
                        tasks.append(bot.session.post("https://thumbnails.roblox.com/v1/batch", json=payload))
                
                responses = await asyncio.gather(*tasks)
                for res in responses:
                    batch = await res.json()
                    if any(img.get('imageUrl') == target_img for img in batch.get('data', [])):
                        return True
                cursor = servers.get('nextPageCursor')
                if not cursor: break
    except Exception as e:
        print(f"Scan Error: {e}")
    return False

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    if "STXR_LOG" in message.content:
        # Expected format: STXR_LOG|UID|PID|ITEM
        parts = message.content.split("|")
        if len(parts) >= 3:
            found = await fast_scan(parts[2], parts[1])
            status = "🎯 **FOUND**" if found else "❌ **NOT IN SERVERS**"
            await message.channel.send(f"{status} | Item: {parts[3] if len(parts)>3 else 'Unknown'}")

# --- 3. THE STARTUP (Anti-Ban Sequence) ---
if __name__ == "__main__":
    # Start web server first so Render doesn't kill us
    Thread(target=run_web).start()
    
    if TOKEN:
        # 20s Delay is the 'Shield' against Error 1015
        print("🛡️ Anti-Ban Shield active. Waiting 20s to log in...")
        import time
        time.sleep(20)
        bot.run(TOKEN)
    else:
        print("❌ ERROR: No DISCORD_TOKEN found in Environment Variables.")
