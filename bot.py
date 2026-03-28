import os
import asyncio
import discord
import aiohttp
from discord.ext import commands
from fastapi import FastAPI, Request
import uvicorn

# --- CONFIGURATION ---
TOKEN = os.getenv('DISCORD_TOKEN')
# CRITICAL: Ensure this is a number (no quotes)
LOG_CHANNEL_ID = 1487223696887255192 
SECRET = "BRAINROT_2026"

# Initialize FastAPI and Discord Bot
app = FastAPI()
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Global session to keep things fast
session_container = {"session": None}

@bot.event
async def on_ready():
    session_container["session"] = aiohttp.ClientSession()
    print(f"✅ STXR ENGINE ONLINE: {bot.user}")
    await bot.change_presence(activity=discord.Game(name="Scanning OGs..."))

# --- ⚡ HIGH-SPEED SERVER SCANNER ---
async def stxr_scan(place_id, user_id):
    session = session_container["session"]
    if not session: return None
    try:
        # Get target headshot to compare
        thumb_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=48x48&format=Png"
        async with session.get(thumb_url) as r:
            t_data = await r.json()
            if not t_data.get('data'): return None
            target_img = t_data['data'][0]['imageUrl']

        cursor = ""
        # Scan top 500 players across servers
        for _ in range(5): 
            api_url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=100&cursor={cursor}"
            async with session.get(api_url) as r:
                servers = await r.json()
                if not servers or 'data' not in servers: break
                
                tasks = []
                for s in servers['data']:
                    tokens = s.get('playerTokens', [])
                    if tokens:
                        payload = [{"token": t, "type": "AvatarHeadShot", "size": "48x48", "format": "png"} for t in tokens]
                        tasks.append(session.post("https://thumbnails.roblox.com/v1/batch", json=payload))
                
                responses = await asyncio.gather(*tasks)
                for i, res in enumerate(responses):
                    batch = await res.json()
                    if any(img.get('imageUrl') == target_img for img in batch.get('data', [])):
                        return servers['data'][i].get('id')
                
                cursor = servers.get('nextPageCursor')
                if not cursor: break
    except Exception as e:
        print(f"Scan Error: {e}")
    return None

# --- 🛰️ API RECEIVER (Roblox talks to this) ---
@app.post("/stxr-log")
async def handle_snipe(request: Request):
    data = await request.json()
    
    # Security Check
    if data.get("secret") != SECRET:
        return {"status": "unauthorized"}

    uid = data.get("userId")
    pid = data.get("placeId")
    item = data.get("itemName", "Unknown Item")
    mutation = data.get("mutation", "None")

    print(f"📡 Received Auto-Snipe: {item} from User {uid}")

    # 1. Run the Scanner
    job_id = await stxr_scan(pid, uid)
    
    if job_id:
        # 2. Send to Discord IMMEDIATELY
        channel = bot.get_channel(LOG_CHANNEL_ID)
        if channel:
            join_link = f"https://www.roblox.com/games/{pid}?jobId={job_id}"
            embed = discord.Embed(title="🎯 TARGET VERIFIED", color=0xFFFFFF)
            embed.set_thumbnail(url=f"https://www.roblox.com/headshot-thumbnail/image?userId={uid}&width=150&height=150&format=png")
            embed.add_field(name="Item", value=f"**{item}**", inline=False)
            embed.add_field(name="Mutation", value=mutation, inline=True)
            embed.add_field(name="Action", value=f"[**CLICK TO JOIN SERVER**]({join_link})", inline=False)
            embed.set_footer(text="STXR'S OG JOINER • Automated Scan")
            
            # Use task to send without blocking the HTTP response
            bot.loop.create_task(channel.send(embed=embed))

        # 3. Success response back to Roblox UI
        return {
            "status": "success",
            "jobId": job_id,
            "itemName": item,
            "userId": uid,
            "mutation": mutation
        }
    
    print(f"❌ Scan Failed: Could not find server for {uid}")
    return {"status": "not_found"}

# --- 🚀 RAILWAY DEPLOYMENT ---
async def start_services():
    port = int(os.environ.get("PORT", 8080))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, loop="asyncio")
    server = uvicorn.Server(config)
    
    # Run both the FastAPI server and Discord Bot together
    await asyncio.gather(
        server.serve(),
        bot.start(TOKEN)
    )

if __name__ == "__main__":
    try:
        asyncio.run(start_services())
    except KeyboardInterrupt:
        pass
