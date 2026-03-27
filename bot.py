import os, asyncio, aiohttp, discord, uvicorn
from discord.ext import commands
from quart import Quart

app = Quart(__name__)
@app.route('/')
async def home(): return "STXR's OG Joiner: STABLE"

TOKEN = os.getenv('DISCORD_TOKEN')
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# Limit simultaneous requests so Cloudflare doesn't ban you
MAX_CONCURRENT_TASKS = 10 

async def deep_scan(place_id, target_uid):
    connector = aiohttp.TCPConnector(limit=50) # Strict connection limit
    async with aiohttp.ClientSession(connector=connector) as session:
        # 1. Get Target Image
        t_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={target_uid}&size=48x48&format=Png"
        async with session.get(t_url) as r:
            t_data = await r.json()
            if not t_data.get('data'): return None, 0
            target_img = t_data['data'][0]['imageUrl']

        cursor = ""
        page = 1
        sem = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

        while True:
            s_url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=100&cursor={cursor}"
            async with session.get(s_url) as r:
                servers = await r.json()
                if not servers or not servers.get('data'): break
                
                async def check_s(s):
                    async with sem: # Controlled flow
                        if not s.get('playerTokens'): return None
                        payload = [{"token": t, "type": "AvatarHeadShot", "size": "48x48", "format": "png"} for t in s['playerTokens']]
                        try:
                            async with session.post("https://thumbnails.roblox.com/v1/batch", json=payload, timeout=5) as br:
                                batch = await br.json()
                                if any(img.get('imageUrl') == target_img for img in batch.get('data', [])):
                                    return s['id']
                        except: pass
                        return None

                results = await asyncio.gather(*(check_s(s) for s in servers['data']))
                found = next((res for res in results if res), None)
                if found: return found, page
                
                cursor = servers.get('nextPageCursor')
                if not cursor: break
                page += 1
        return None, page

@bot.event
async def on_message(message):
    if "STXR_LOG" in message.content:
        try:
            parts = message.content.split("|")
            uid, pid, item = parts[1], parts[2], parts[3]
            status = await message.channel.send(f"🛰️ **STXR_LOG:** Scanning Servers for `{item}`...")
            
            job_id, pages = await deep_scan(pid, uid)
            
            if job_id:
                await status.edit(content=f"🎯 **TARGET FOUND**\n`STXR_WARP|{job_id}`\nScanned {pages} pages.")
            else:
                await status.edit(content=f"❌ **MISS**\nScanned {pages} pages. Not found.")
        except Exception as e: print(f"Error: {e}")

async def main():
    port = int(os.environ.get("PORT", 10000))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    await asyncio.gather(server.serve(), bot.start(TOKEN))

if __name__ == "__main__":
    asyncio.run(main())
