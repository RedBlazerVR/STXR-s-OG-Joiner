import os, asyncio, discord, aiohttp
from discord.ext import commands
from flask import Flask
from threading import Thread

# --- 1. WEB SERVER (Keep-Alive for Render) ---
app = Flask('')
@app.route('/')
def home(): return "STXR_PROXY_SYSTEM: ONLINE"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- 2. THE BYPASS BOT ENGINE ---
TOKEN = os.getenv('DISCORD_TOKEN')

class STXR_Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        self.session = None

    async def setup_hook(self):
        # 🛡️ THE BYPASS: This tunnels your requests so Discord doesn't see Render's Banned IP
        self.http.API_BASE_URL = "https://discordproxy.info/api"
        print("🛰️ Proxy Tunnel Established. Bypassing Error 1015...")

bot = STXR_Bot()

@bot.event
async def on_ready():
    bot.session = aiohttp.ClientSession()
    print(f"✅ SUCCESS: {bot.user} IS ONLINE VIA PROXY")

# --- 3. THE SPEED SCANNER ---
async def fast_scan(pid, uid):
    try:
        # Get target headshot
        t_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={uid}&size=48x48&format=Png"
        async with bot.session.get(t_url) as r:
            t_data = await r.json()
            if not t_data.get('data'): return False
            target_img = t_data['data'][0]['imageUrl']

        # Scan 200 players instantly
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
        parts = message.content.split("|")
        if len(parts) >= 3:
            await message.channel.send("🔎 **Proxy Scan Initiated...**")
            found = await fast_scan(parts[2], parts[1])
            status = "🎯 **FOUND**" if found else "❌ **NOT FOUND**"
            await message.channel.send(f"{status} | Item: {parts[3] if len(parts)>3 else 'Unknown'}")

# --- 4. STARTUP ---
if __name__ == "__main__":
    Thread(target=run_web).start()
    if TOKEN:
        try:
            # We don't need a long delay with the Proxy, but 5s is safe
            import time
            time.sleep(5)
            bot.run(TOKEN)
        except Exception as e:
            print(f"❌ LOGIN ERROR: {e}")
    else:
        print("❌ ERROR: No DISCORD_TOKEN found.")
