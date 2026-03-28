import os, asyncio, discord, aiohttp
from discord.ext import commands
from flask import Flask
from threading import Thread

# --- 1. WEB SERVER (For Render Health Checks) ---
app = Flask('')
@app.route('/')
def home(): return "STXR_SYSTEM_V4: ONLINE"

def run_web():
    # Render uses port 10000 by default
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 2. THE BOT ENGINE (Speed Optimized) ---
TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.all() 
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    # Create the aiohttp session once for maximum speed
    bot.session = aiohttp.ClientSession()
    print(f"✅ SUCCESS: {bot.user} IS ONLINE AND SCANNING")

async def fast_scan(pid, uid):
    """Checks servers for a specific player headshot"""
    try:
        # Get target's headshot once
        t_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={uid}&size=48x48&format=Png"
        async with bot.session.get(t_url) as r:
            t_data = await r.json()
            if not t_data.get('data'): return False
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
        print(f"⚠️ Scan Error: {e}")
    return False

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    if "STXR_LOG" in message.content:
        # Format: STXR_LOG|UID|PID|ITEM
        parts = message.content.split("|")
        if len(parts) >= 3:
            await message.channel.send("🔎 **Scanning servers...**")
            found = await fast_scan(parts[2], parts[1])
            status = "🎯 **TARGET FOUND**" if found else "❌ **TARGET NOT FOUND**"
            await message.channel.send(f"{status} | Item: {parts[3] if len(parts)>3 else 'Unknown'}")

# --- 3. THE STARTUP SEQUENCE ---
if __name__ == "__main__":
    # Start web server in a separate thread
    Thread(target=run_web).start()
    
    if TOKEN:
        print("🛡️ Anti-Ban Shield: Waiting 20s...")
        # Use a small synchronous sleep before starting the event loop
        import time
        time.sleep(20)
        
        try:
            bot.run(TOKEN)
        except discord.errors.PrivilegedIntentsRequired:
            print("❌ ERROR: You forgot to turn on INTENTS in the Discord Dev Portal!")
        except discord.errors.LoginFailure:
            print("❌ ERROR: Your DISCORD_TOKEN is invalid or expired!")
        except Exception as e:
            print(f"❌ CRITICAL LOGIN ERROR: {e}")
    else:
        print("❌ ERROR: No DISCORD_TOKEN found in Render Environment Variables.")
