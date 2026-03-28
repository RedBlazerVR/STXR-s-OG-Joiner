import os, asyncio, discord, aiohttp
from discord.ext import commands
from fastapi import FastAPI, Request
import uvicorn

# --- CONFIGURATION ---
TOKEN = os.getenv('DISCORD_TOKEN')
LOG_CHANNEL_ID = 1487223696887255192  # <--- REPLACE THIS WITH YOUR CHANNEL ID
SECRET = "BRAINROT_2026"

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
app = FastAPI()
session_container = {"session": None}

@bot.event
async def on_ready():
    session_container["session"] = aiohttp.ClientSession()
    print(f"✅ STXR ENGINE ONLINE: {bot.user}")
    await bot.change_presence(activity=discord.Game(name="STXR's OG Joiner"))

# --- ⚡ HIGH SPEED SCANNER ---
async def stxr_scan(place_id, user_id):
    session = session_container["session"]
    if not session: return None
    try:
        # Get target headshot to compare against server list
        async with session.get(f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=48x48&format=Png") as r:
            t_data = await r.json()
            target_img = t_data['data'][0]['imageUrl']

        cursor = ""
        for _ in range(5): # Scan up to 500 players
            async with session.get(f"https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=100&cursor={cursor}") as r:
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

# --- 🛰️ API RECEIVER (Talks to Roblox) ---
@app.post("/stxr-log")
async def handle_snipe(request: Request):
    data = await request.json()
    
    if data.get("secret") != SECRET:
        return {"status": "unauthorized"}

    uid = data.get("userId")
    pid = data.get("placeId")
    item = data.get("itemName", "Unknown")
    mutation = data.get("mutation", "None")

    # Start the scan
    job_id = await stxr_scan(pid, uid)
    
    if job_id:
        # 1. Send Discord Embed
        channel = bot.get_channel(LOG_CHANNEL_ID)
        if channel:
            join_link = f"https://www.roblox.com/games/{pid}?jobId={job_id}"
            embed = discord.Embed(title="🎯 TARGET VERIFIED", color=0xFFFFFF)
            embed.set_thumbnail(url=f"https://www.roblox.com/headshot-thumbnail/image?userId={uid}&width=150&height=150&format=png")
            embed.add_field(name="Item", value=f"**{item}**", inline=False)
            embed.add_field(name="Mutation", value=mutation, inline=True)
            embed.add_field(name="Action", value=f"[**CLICK TO JOIN**]({join_link})", inline=False)
            await channel.send(embed=embed)

        # 2. Return data to Roblox for the UI Entry
        return {
            "status": "success",
            "jobId": job_id,
            "itemName": item,
            "userId": uid,
            "mutation": mutation
        }
    
    return {"status": "not_found"}

# --- 🚀 RAILWAY BOOT ---
async def main():
    port = int(os.environ.get("PORT", 8080))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, loop="asyncio")
    server = uvicorn.Server(config)
    await asyncio.gather(server.serve(), bot.start(TOKEN))

if __name__ == "__main__":
    asyncio.run(main())
