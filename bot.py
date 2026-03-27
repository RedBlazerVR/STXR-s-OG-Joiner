import os, asyncio, aiohttp, discord
from discord.ext import commands
from quart import Quart

app = Quart(__name__)
@app.route('/')
async def home(): return "STXR's OG Joiner: LOGGING..."

TOKEN = os.getenv('DISCORD_TOKEN')
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

async def scan_all_pages(session, pid, target_img):
    cursor = ""
    page_count = 1
    while True:
        url = f"https://games.roblox.com/v1/games/{pid}/servers/Public?limit=100&cursor={cursor}"
        async with session.get(url) as r:
            s_data = await r.json()
            if not s_data or not s_data.get('data'): break
            
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
    # This allows the bot to read the Webhook/Script data
    if "STXR_LOG" in message.content:
        try:
            parts = message.content.split("|")
            uid, pid, item = parts[1], parts[2], parts[3]
            
            # OG Joiner Style Embed
            embed = discord.Embed(title="🛰️ STXR_LOG | SIGNAL DETECTED", color=0xFFFFFF)
            embed.add_field(name="Target Item", value=f"`{item}`", inline=True)
            embed.add_field(name="Status", value="Searching all servers...", inline=False)
            status_msg = await message.channel.send(embed=embed)
            
            async with aiohttp.ClientSession() as session:
                t_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={uid}&size=48x48&format=Png"
                async with session.get(t_url) as r:
                    t_data = await r.json()
                    target_img = t_data['data'][0]['imageUrl']

                job_id, pages = await scan_all_pages(session, pid, target_img)
                
                if job_id:
                    res_embed = discord.Embed(title="🎯 STXR's OG Joiner | SUCCESS", color=0x00FF66)
                    res_embed.add_field(name="Item", value=item)
                    res_embed.add_field(name="Location", value=f"Page {pages}")
                    res_embed.add_field(name="Join Code", value=f"```STXR_WARP|{job_id}```")
                    await status_msg.edit(embed=res_embed)
                else:
                    err_embed = discord.Embed(title="❌ STXR's OG Joiner | MISS", color=0xFF0000)
                    err_embed.description = f"Scanned {pages} pages. Target is not in a public server."
                    await status_msg.edit(embed=err_embed)
        except Exception as e:
            print(f"Log Error: {e}")

@bot.event
async def setup_hook():
    # Render automatically tells the bot which port to use via an environment variable
    import os
    port = int(os.environ.get("PORT", 10000)) # Render's default is 10000
    bot.loop.create_task(app.run_task(host='0.0.0.0', port=port))

bot.run(TOKEN)
