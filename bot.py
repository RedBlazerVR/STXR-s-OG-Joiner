import os, asyncio, discord, aiohttp
from discord.ext import commands

# --- 1. THE ENGINE ---
TOKEN = os.getenv('DISCORD_TOKEN')

class STXR_Sniper(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        self.session = None

    async def setup_hook(self):
        print("🚀 Railway Network Active: Filtering Unclaimed/Unknown.")

bot = STXR_Sniper()

@bot.event
async def on_ready():
    if bot.session is None:
        bot.session = aiohttp.ClientSession()
    print(f"✅ STXR SNIPER ONLINE: {bot.user}")

# --- 2. THE LIGHTNING SCANNER ---
async def stxr_scan(place_id, user_id):
    # 🛡️ FILTER 1: Immediate skip if ID is invalid or 0
    if not user_id or str(user_id) == "0" or str(user_id).lower() == "none":
        return None

    try:
        # Step A: Get the Target's Headshot URL
        thumb_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=48x48&format=Png"
        async with bot.session.get(thumb_url) as r:
            t_data = await r.json()
            # 🛡️ FILTER 2: Skip if Roblox can't find the user profile
            if not t_data.get('data') or len(t_data['data']) == 0:
                return None
            
            target_img = t_data['data'][0].get('imageUrl')
            if not target_img: return None

        # Step B: Scan Public Servers
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

# --- 3. THE HANDLER ---
@bot.event
async def on_message(message):
    if message.author == bot.user: return
    
    # Format: STXR_LOG|USER_ID|PLACE_ID|ITEM_NAME
    if "STXR_LOG" in message.content:
        parts = message.content.split("|")
        
        # 🛡️ FILTER 3: Block if message is broken or missing UserID
        if len(parts) < 3: return
        
        uid = parts[1].strip()
        pid = parts[2].strip()
        item = parts[3].strip() if len(parts) > 3 else "Unknown"

        # 🛡️ FILTER 4: The "Unclaimed" check
        if uid.lower() in ["unclaimed", "unknown", "0", "none", ""]:
            print(f"⏭️ Skipping Unclaimed Item: {item}")
            return

        # If it passes all filters, we scan
        job_id = await stxr_scan(pid, uid)
        
        if job_id:
            join_link = f"https://www.roblox.com/games/{pid}?jobId={job_id}"
            
            embed = discord.Embed(title="🎯 TARGET VERIFIED", color=0x00ff00)
            embed.set_thumbnail(url=f"https://www.roblox.com/headshot-thumbnail/image?userId={uid}&width=150&height=150&format=png")
            embed.add_field(name="Item", value=f"**{item}**", inline=False)
            embed.add_field(name="Owner ID", value=f"`{uid}`", inline=True)
            embed.add_field(name="Action", value=f"[**JOIN SERVER**]({join_link})", inline=False)
            
            await message.channel.send(embed=embed)

if __name__ == "__main__":
    bot.run(TOKEN)
