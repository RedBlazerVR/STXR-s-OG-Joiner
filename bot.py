import os, asyncio, aiohttp, discord
from discord.ext import commands
from quart import Quart

app = Quart(__name__)
@app.route('/')
async def home(): return "STXR's OG Joiner: SEARCHING..."

TOKEN = os.getenv('DISCORD_TOKEN') or 'YOUR_TOKEN_HERE'
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

async def scan_all_pages(session, pid, target_img):
    cursor = ""
    page_count = 1
    
    while True:
        url = f"https://games.roblox.com/v1/games/{pid}/servers/Public?limit=100&cursor={cursor}"
        async with session.get(url) as r:
            s_data = await r.json()
            if not s_data.get('data'): break
            
            # Check all servers on this page in parallel
            async def check_s(s):
                if not s.get('playerTokens'): return None
                payload = [{"token": t, "type": "AvatarHeadShot", "size": "48x48", "format": "png"} for t in s['playerTokens']]
                async with session.post("https://thumbnails.roblox.com/v1/batch", json=payload) as br:
                    batch = await br.json()
                    if any(img.get('imageUrl') == target_img for img in batch.get('data', [])):
                        return s['id']
                return None

            results = await asyncio.gather(*(check_s(s) for s in s_data['data']))
            found = next((res for res in results if res), None)
            if found: return found, page_count
            
            cursor = s_data.get('nextPageCursor')
            if not cursor: break
            page_count += 1
    return None, page_count

@bot.event
async def on_message(message):
    if "STXR_HUNT" in message.content:
        _, uid, pid, item = message.content.split("|")
        status_msg = await message.channel.send(f"🛰️ **OG JOINER:** Searching all servers for `{item}`...")
        
        async with aiohttp.ClientSession() as session:
            # 1. Get Target Image
            t_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={uid}&size=48x48&format=Png"
            async with session.get(t_url) as r:
                t_data = await r.json()
                target_img = t_data['data'][0]['imageUrl']

            # 2. Deep Scan
            job_id, pages = await scan_all_pages(session, pid, target_img)
            
            if job_id:
                await status_msg.edit(content=f"🎯 **TARGET FOUND (Page {pages})**\n`STXR_WARP|{job_id}`")
            else:
                await status_msg.edit(content=f"❌ **MISS:** Scanned {pages} pages. Target not found.")

@bot.event
async def setup_hook():
    port = int(os.environ.get("PORT", 8080))
    bot.loop.create_task(app.run_task(host='0.0.0.0', port=port))

bot.run(TOKEN)
