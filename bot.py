import os
import discord
from discord.ext import commands
import asyncio

# --- MINIMALIST SETUP ---
TOKEN = os.getenv('DISCORD_TOKEN')

# Use basic intents to prevent "Privileged Intent" crashes
intents = discord.Intents.default()
intents.message_content = True 

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ BOT IS ONLINE AS: {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if "STXR_LOG" in message.content:
        await message.channel.send("🛰️ **System Received Log.** Standing by...")

# --- THE STARTUP ---
async def main():
    if not TOKEN:
        print("❌ ERROR: DISCORD_TOKEN is missing in Render Environment Variables!")
        return
    try:
        await bot.start(TOKEN)
    except Exception as e:
        print(f"❌ LOGIN ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(main())
