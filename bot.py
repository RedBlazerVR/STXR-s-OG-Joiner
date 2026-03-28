import os
import asyncio
import discord
from discord.ext import commands
from quart import Quart
from hypercorn.asyncio import serve
from hypercorn.config import Config

# 1. THE WEB SERVER (Answering Render's door)
app = Quart(__name__)

@app.route('/')
async def home():
    return "STXR_SYSTEM: ONLINE"

@app.route('/healthz')
async def health():
    return "OK", 200

# 2. THE BOT ENGINE
TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ BOT CONNECTED: {bot.user}")

@bot.event
async def on_message(message):
    if "STXR_LOG" in message.content:
        await message.channel.send("🛰️ **System Online.** Scanning module ready.")

# 3. THE STABLE STARTUP
async def main():
    # Setup Hypercorn Config for Render's Port
    config = Config()
    config.bind = [f"0.0.0.0:{os.environ.get('PORT', '10000')}"]
    
    print("⏳ Waiting 15s to bypass Discord Rate Limits...")
    await asyncio.sleep(15) # Giving the IP a "Cool Down" period
    
    # Run both the Web Server and the Discord Bot together
    try:
        await asyncio.gather(
            serve(app, config),
            bot.start(TOKEN)
        )
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
