import discord
from discord.ext import commands
import os
import datetime
import threading
from flask import Flask, request, jsonify

# --- RAILWAY CONFIGURATION ---
TOKEN = os.environ.get('DISCORD_TOKEN')
CHANNEL_ID_RAW = os.environ.get('LOG_CHANNEL_ID')
PORT = int(os.environ.get('PORT', 5000))

# Convert Channel ID safely
try:
    CHANNEL_ID = int(CHANNEL_ID_RAW)
except (ValueError, TypeError):
    print("CRITICAL: LOG_CHANNEL_ID variable is missing or invalid!")
    CHANNEL_ID = 0

# --- BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True  # Ensure this is ON in Discord Dev Portal
bot = commands.Bot(command_prefix="!", intents=intents)

# Image Mapping (Make sure files are in the same folder)
IMAGE_MAPPING = {
    "SKIBIDI TOILET": "Skibidi_toilet.png",
    "MEOWL": "Clear_background_clear_meowl_image.png",
    "STRAWBERRY ELEPHANT": "Strawberryelephant.png"
}

# --- FLASK SERVER (Roblox Receiver) ---
app = Flask(__name__)

@app.route('/stxr-log', methods=['POST'])
def roblox_payload():
    # force=True fixes the 415 error by ignoring the Content-Type header
    data = request.get_json(force=True, silent=True)
    
    if data:
        print(f"Payload Received: {data}")
        # Send to Discord without blocking the web response
        bot.loop.create_task(send_spawn_message(data))
        return jsonify({"status": "success"}), 200
    
    print("Invalid Payload Received")
    return jsonify({"status": "error", "message": "Invalid JSON"}), 400

async def send_spawn_message(data):
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)
    
    if not channel:
        print(f"Could not find channel {CHANNEL_ID}")
        return

    pet_name = data.get("pet_name", "Unknown")
    owner = data.get("owner", "N/A")
    user_id = data.get("user_id", "0")
    
    image_file = IMAGE_MAPPING.get(pet_name.upper())

    embed = discord.Embed(
        title="🚨 NEW SPAWN DETECTED 🚨",
        description=f"A rare **{pet_name}** has just spawned!",
        color=discord.Color.red(),
        timestamp=datetime.datetime.utcnow()
    )
    
    embed.add_field(name="Owner", value=f"`{owner}`", inline=True)
    embed.add_field(name="User ID", value=f"`{user_id}`", inline=True)
    embed.set_footer(text="STXR OG FINDER")

    # Image Logic
    if image_file and os.path.exists(image_file):
        file = discord.File(image_file, filename=image_file)
        embed.set_image(url=f"attachment://{image_file}")
        await channel.send(file=file, embed=embed)
    else:
        await channel.send(embed=embed)

# --- EXECUTION ---

def run_flask():
    # Railway listens on 0.0.0.0
    app.run(host='0.0.0.0', port=PORT)

@bot.event
async def on_ready():
    print(f"Logged in as: {bot.user}")
    print(f"Monitoring Channel: {CHANNEL_ID}")
    print(f"Server Route: /stxr-log")

if __name__ == "__main__":
    # Start Flask in a background thread
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    
    # Start Discord Bot in the main thread
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"Error starting bot: {e}")
