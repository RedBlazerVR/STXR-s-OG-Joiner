import discord
from discord.ext import commands
import os
import datetime
from flask import Flask, request, jsonify
import threading

# --- RAILWAY SECRETS ---
TOKEN = os.environ.get('DISCORD_TOKEN')
CHANNEL_ID = int(os.environ.get('LOG_CHANNEL_ID'))

# --- BOT SETUP ---
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

IMAGE_MAPPING = {
    "SKIBIDI TOILET": "Skibidi_toilet.png",
    "MEOWL": "Clear_background_clear_meowl_image.png",
    "STRAWBERRY ELEPHANT": "Strawberryelephant.png"
}

# --- WEB SERVER (Receiver for Roblox) ---
app = Flask(__name__)

@app.route('/spawn', methods=['POST'])
def roblox_payload():
    data = request.json
    bot.loop.create_task(send_spawn_message(data))
    return jsonify({"status": "success"}), 200

async def send_spawn_message(data):
    channel = bot.get_channel(CHANNEL_ID)
    if not channel: return

    pet_name = data.get("pet_name", "Unknown")
    owner = data.get("owner", "N/A")
    user_id = data.get("user_id", "0")
    
    image_file = IMAGE_MAPPING.get(pet_name.upper())

    embed = discord.Embed(
        title="🚨 NEW BRAINROT DETECTED 🚨",
        color=discord.Color.from_rgb(255, 0, 0),
        timestamp=datetime.datetime.utcnow()
    )
    embed.add_field(name="Brainrot Name", value=f"**{pet_name}**", inline=False)
    embed.add_field(name="Owner", value=owner, inline=True)
    embed.add_field(name="User ID", value=user_id, inline=True)
    
    # UPDATED FOOTER
    embed.set_footer(text="STXR OG FINDER")

    if image_file and os.path.exists(image_file):
        file = discord.File(image_file, filename=image_file)
        embed.set_image(url=f"attachment://{image_file}")
        await channel.send(file=file, embed=embed)
    else:
        await channel.send(embed=embed)

def run_flask():
    # Railway uses the PORT env var to listen for traffic
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

@bot.event
async def on_ready():
    print(f'Bot is online as {bot.user}')

threading.Thread(target=run_flask, daemon=True).start()
bot.run(TOKEN)
