import os, asyncio, discord, aiohttp
from discord.ext import commands
from fastapi import FastAPI, Request
import uvicorn

# --- BOT SETUP ---
TOKEN = os.getenv('DISCORD_TOKEN')
LOG_CHANNEL_ID = 1234567890  # <--- Change this to your channel ID!

class STXR_Sniper(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        self.session = None

    async def setup_hook(self):
        print("🚀 STXR Engine: Active and Direct.")

bot = STXR_Sniper()
app = FastAPI()

@bot.event
async def on_ready():
    if bot.session is None:
        bot.session = aiohttp.ClientSession()
    print(f"✅ STXR SNIPER ONLINE: {bot.user}")

# --- 🛰️ THE NEW EXECUTOR HANDLER ---
@app.post("/stxr-log")
async def handle_executor_snipe(request: Request):
    data = await request.json()
    
    # Check the secret to prevent random people from spamming your bot
    if data.get("secret") != "BRAINROT_2026":
        return {"status": "unauthorized"}

    uid = data.get("userId")
    pid = data.get("placeId")
    item = data.get("itemName", "Unknown Brainrot")

    # 🛡️ Skip if unclaimed (as we set up before)
    if not uid or str(uid) == "0" or str(uid).lower() == "unclaimed":
        return {"status": "skipped_unclaimed"}

    # Start the High-Speed Scan
    job_id = await stxr_scan(pid, uid)
    
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        if job_id:
            join_link = f"https://www.roblox.com/games/{pid}?jobId={job_id}"
            
            embed = discord.Embed(
                title="🎯 TARGET VERIFIED", 
                description=f"**{item}** found!", 
                color=0xFFFFFF # Black & White Theme
            )
            embed.set_thumbnail(url=f"https://www.roblox.com/headshot-thumbnail/image?userId={uid}&width=150&height=150&format=png")
            embed.add_field(name="👤 Owner ID", value=f"`{uid}`", inline=True)
            embed.add_field(name="🕹️ Server ID", value=f"`{job_id[:15]}...`", inline=True)
            embed.add_field(name="🔗 Action", value=f"[**CLICK TO JOIN SERVER**]({join_link})", inline=False)
            embed.set_footer(text="STXR's OG Joiner | High-Speed Scan")
            
            await channel.send(embed=embed)
        else:
            # Optional: Log failures to a different channel or ignore
            print(f"❌ Scan failed for {uid} in {pid}")

    return {"status": "success"}

# --- ⚡ THE SCANNER (Direct & Fast) ---
async def stxr_scan(place_id, user_id):
    try:
        # Get target headshot
        thumb_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=48x48&format=Png"
        async with bot.session.get(thumb_url) as r:
            t_data = await r.json()
            if not t_data.get('data'): return None
            target_img = t_data['data'][0].get('imageUrl')

        # Scan 3 pages (300 players)
        cursor = ""
        for _ in range(3):
            s_url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=100&cursor={cursor}"
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
                for i, res in enumerate(responses):
                    batch = await res.json()
                    if any(img.get('imageUrl') == target_img for img in batch.get('data', [])):
                        return servers['data'][i].get('id')
                
                cursor = servers.get('nextPageCursor')
                if not cursor: break
    except Exception as e:
        print(f"⚠️ Scan Error: {e}")
    return None

# --- 🚀 RUN COMMAND ---
async def main():
    # Railway provides the PORT env variable automatically
    port = int(os.environ.get("PORT", 8080))
    config = uvicorn.Config(app, host="0.0.0.0", port=port)
    server = uvicorn.Server(config)
    
    # Runs both FastAPI (for Roblox) and the Discord Bot at the same time
    await asyncio.gather(server.serve(), bot.start(TOKEN))

if __name__ == "__main__":
    asyncio.run(main())
