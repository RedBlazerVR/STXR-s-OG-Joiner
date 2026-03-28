import os, asyncio, discord, aiohttp
from discord.ext import commands
from quart import Quart

# 1. THE WEB ENGINE
app = Quart(__name__)
@app.route('/')
async def home(): return "STXR_SPEED: ACTIVE"

# 2. THE BOT ENGINE
TOKEN = os.getenv('DISCORD_TOKEN')
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_ready():
    # We create one session for the whole bot to keep it fast
    bot.session = aiohttp.ClientSession()
    print(f"🚀 READY TO HUNT: {bot.user}")

async def fast_scan(pid, uid):
    # 1. Get Target Headshot (Fast cached request)
    t_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={uid}&size=48x48&format=Png"
    async with bot.session.get(t_url) as r:
        t_data = await r.json()
        target_img = t_data['data'][0]['imageUrl']

    # 2. Scan Servers (Multi-threaded style)
    cursor = ""
    for _ in range(5): # Check top 500 players instantly
        s_url = f"https://games.roblox.com/v1/games/{pid}/servers/Public?limit=100&cursor={cursor}"
        async with bot.session.get(s_url) as r:
            servers = await r.json()
            if not servers.get('data'): break
            
            # Create a list of "Batch Requests" to run all at once
            tasks = []
            for s in servers['data']:
                tokens = s.get('playerTokens', [])
                if tokens:
                    payload = [{"token": t, "type": "AvatarHeadShot", "size": "48x48", "format": "png"} for t in tokens]
                    tasks.append(bot.session.post("https://thumbnails.roblox.com/v1/batch", json=payload))
            
            # Execute ALL server checks at the same time
            responses = await asyncio.gather(*tasks)
            for res in responses:
                batch = await res.json()
                if any(img.get('imageUrl') == target_img for img in batch.get('data', [])):
                    # Extract Job ID from the batch (this part requires mapping back)
                    # For speed, we return the first one that matches
                    return "FOUND", 1 

            cursor = servers.get('nextPageCursor')
            if not cursor: break
    return None, 0

@bot.event
async def on_message(message):
    if "STXR_LOG" in message.content:
        # Split: STXR_LOG|UID|PID|ITEM
        p = message.content.split("|")
        res, _ = await fast_scan(p[2], p[1])
        if res: await message.channel.send(f"🎯 **TARGET SPOTTED**")

# 3. THE "STABLE" BOOT
async def main():
    # START WEB SERVER
    loop = asyncio.get_event_loop()
    loop.create_task(app.run_task(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))))
    
    # WAIT FOR IP COOL DOWN (The "Anti-Ban" shield)
    print("🛡️ Anti-Ban Shield: Waiting 20 seconds...")
    await asyncio.sleep(20) 
    
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
