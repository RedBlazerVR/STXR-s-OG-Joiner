import os
import asyncio
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread

# 1. THE WEB SERVER (Required for Render Free Tier)
app = Flask('')

@app.route('/')
def home():
    return "STXR_SYSTEM: ONLINE"

def run_web():
    # Render uses port 10000 by default
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# 2. THE BOT ENGINE
TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ SUCCESS: {bot.user} IS ONLINE")

@bot.event
async def on_message(message):
    if "STXR_LOG" in message.content:
        await message.channel.send("🛰️ **System Received.** Scanning module loading...")

# 3. THE STARTUP
if __name__ == "__main__":
    # Start the web server in a separate thread so it doesn't block the bot
    t = Thread(target=run_web)
    t.start()
    
    # Start the bot
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ ERROR: DISCORD_TOKEN is missing!")
