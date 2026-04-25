import discord
from discord.ext import commands
import os
import datetime
import threading
from flask import Flask, request, jsonify

# --- RAILWAY SECRETS ---
TOKEN = os.environ.get('DISCORD_TOKEN')
CHANNEL_ID = int(os.environ.get('LOG_CHANNEL_ID', 0))
PORT = int(os.environ.get('PORT', 5000))

# --- BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix="!", intents=intents)

# Image Mapping (Case Sensitive)
IMAGE_MAPPING = {
    "SKIBIDI TOILET": "Skibidi_toilet.png",
    "MEOWL": "Clear_background_clear_meowl_image.png",
    "STRAWBERRY ELEPHANT": "Strawberryelephant.png"
}

# --- FLASK WEBHOOK RECEIVER ---
app = Flask(__name__)

@app.route('/stxr-log', methods=['POST'])
def webhook_receiver():
    # force=True allows the bot to read Roblox data properly
    data = request.get_json(force=True, silent=True)
    
    if data:
        # Pass the data to the Discord sending function
        bot.loop.create_task(send_to_discord(data))
        return jsonify({"status": "success"}), 200
    
    return jsonify({"status": "error", "message": "No data received"}), 400

async def send_to_discord(data):
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)
    if not channel: return

    pet_name = data.get("pet_name", "Unknown")
    owner = data.get("owner", "N/A")
    uid = data.get("user_id", "0")
    
    image_file = IMAGE_MAPPING.get(pet_name.upper())

    embed = discord.Embed(
        title="🚨 NEW BRAINROT DETECTED 🚨",
        description=f"A rare **{pet_name}** has just spawned!",
        color=discord.Color.red(),
        timestamp=datetime.datetime.utcnow()
    )
    
    embed.add_field(name="Owner", value=f"`{owner}`", inline=True)
    embed.add_field(name="User ID", value=f"`{uid}`", inline=True)
    embed.set_footer(text="STXR OG FINDER")

    # If the image file exists in your Railway folder, attach it
    if image_file and os.path.exists(image_file):
        file = discord.File(image_file, filename=image_file)
        embed.set_image(url=f"attachment://{image_file}")
        await channel.send(file=file, embed=embed)
    else:
        await channel.send(embed=embed)

# --- EXECUTION ---
def run_server():
    app.run(host='0.0.0.0', port=PORT)

@bot.event
async def on_ready():
    print(f"STXR Bot Online as {bot.user}")

if __name__ == "__main__":
    # Start the server in the background
    threading.Thread(target=run_server, daemon=True).start()
    # Start the bot
    bot.run(TOKEN)
