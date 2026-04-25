import discord
from discord.ext import commands
import os
import datetime
from flask import Flask, request, jsonify
import threading

# --- RAILWAY CONFIGURATION ---
# These pull from your "Variables" tab in Railway
TOKEN = os.environ.get('DISCORD_TOKEN')
CHANNEL_ID_RAW = os.environ.get('LOG_CHANNEL_ID')
PORT = int(os.environ.get('PORT', 5000))

# Convert Channel ID to integer
try:
    CHANNEL_ID = int(CHANNEL_ID_RAW)
except (ValueError, TypeError):
    print("ERROR: LOG_CHANNEL_ID is not a valid number in Railway variables!")
    CHANNEL_ID = 0

# --- BOT SETUP ---
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# This maps the pet name from Roblox to the files you uploaded to GitHub/Railway
IMAGE_MAPPING = {
    "SKIBIDI TOILET": "Skibidi_toilet.png",
    "MEOWL": "Clear_background_clear_meowl_image.png",
    "STRAWBERRY ELEPHANT": "Strawberryelephant.png"
}

# --- WEB SERVER (Receiver for Roblox) ---
app = Flask(__name__)

@app.route('/stxr-log', methods=['POST'])
def roblox_payload():
    data = request.json
    if data:
        # Pushes the message sending to the bot's background loop
        bot.loop.create_task(send_spawn_message(data))
        return jsonify({"status": "received"}), 200
    return jsonify({"status": "error", "message": "No data"}), 400

async def send_spawn_message(data):
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)
    
    if not channel:
        print(f"ERROR: Could not find channel with ID {CHANNEL_ID}")
        return

    pet_name = data.get("pet_name", "Unknown Brainrot")
    owner = data.get("owner", "Unclaimed")
    user_id = data.get("user_id", "0")
    
    # Check if we have a special image for this spawn
    image_file = IMAGE_MAPPING.get(pet_name.upper())

    embed = discord.Embed(
        title="🚨 NEW BRAINROT DETECTED 🚨",
        description=f"A new **{pet_name}** has appeared in the world!",
        color=discord.Color.from_rgb(255, 0, 0),
        timestamp=datetime.datetime.utcnow()
    )
    
    embed.add_field(name="👤 Owner", value=f"`{owner}`", inline=True)
    embed.add_field(name="🆔 User ID", value=f"`{user_id}`", inline=True)
    embed.set_footer(text="STXR OG FINDER")

    # If the image file exists in the folder, attach it
    if image_file and os.path.exists(image_file):
        file = discord.File(image_file, filename=image_file)
        embed.set_image(url=f"attachment://{image_file}")
        await channel.send(file=file, embed=embed)
    else:
        # Fallback if image is missing or pet isn't in the mapping
        await channel.send(embed=embed)

# --- EXECUTION ---
def run_flask():
    # Railway must have host '0.0.0.0' to be reachable
    app.run(host='0.0.0.0', port=PORT)

@bot.event
async def on_ready():
    print(f'-----------------------------------')
    print(f'STXR OG FINDER BOT ONLINE')
    print(f'Logged in as: {bot.user}')
    print(f'Listening on Port: {PORT}')
    print(f'-----------------------------------')

if __name__ == "__main__":
    # Start the Flask web server in a separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Run the Discord Bot
    bot.run(TOKEN)
