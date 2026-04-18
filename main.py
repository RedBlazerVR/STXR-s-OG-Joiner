import os, asyncio, aiohttp, uvicorn, discord, io
from discord.ext import commands
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from PIL import Image

# --- CONFIG ---
TOKEN = os.getenv('DISCORD_TOKEN')
LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID', 0))
SECRET = "BRAINROT_2026"

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not session_container["session"]:
        session_container["session"] = aiohttp.ClientSession()
    asyncio.create_task(bot.start(TOKEN))
    yield
    if session_container["session"]:
        await session_container["session"].close()

app = FastAPI(lifespan=lifespan)
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
session_container = {"session": None}

# --- IMAGE PROCESSING ---
async def get_image_bytes(session, url):
    try:
        async with session.get(url, timeout=10) as r:
            if r.status == 200:
                return await r.read()
    except: pass
    return None

def images_match(img1_bytes, img2_bytes):
    try:
        img1 = Image.open(io.BytesIO(img1_bytes)).convert('RGB').resize((48, 48))
        img2 = Image.open(io.BytesIO(img2_bytes)).convert('RGB').resize((48, 48))
        return list(img1.getdata()) == list(img2.getdata())
    except:
        return False

# --- SCANNING ENGINE ---
async def stxr_warp_scan(place_id, user_id):
    session = session_container["session"]
    
    # 1. Get Target Image safely
    target_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=48x48&format=Png&isCircular=false"
    try:
        async with session.get(target_url) as r:
            t_data = await r.json()
            if not t_data or 'data' not in t_data or len(t_data['data']) == 0:
                print(f"⚠️ Could not find thumbnail data for {user_id}")
                return None
            target_img_url = t_data['data'][0].get('imageUrl')
    except Exception as e:
        print(f"❌ Thumbnail API Error: {e}")
        return None
    
    target_bytes = await get_image_bytes(session, target_img_url)
    if not target_bytes: return None

    cursor = ""
    for page in range(60): 
        print(f"📡 Page {page+1} scanning...")
        api_url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=100&cursor={cursor}"
        
        try:
            async with session.get(api_url) as r:
                data = await r.json()
                if not data or 'data' not in data: 
                    print(f"🛑 Roblox API blocked or empty at page {page+1}")
                    break
                
                tasks, s_ids = [], []
                for s in data['data']:
                    tokens = s.get('playerTokens', [])
                    if tokens:
                        payload = [{"token": t, "type": "AvatarHeadShot", "size": "48x48", "format": "png"} for t in tokens]
                        tasks.append(session.post("https://thumbnails.roblox.com/v1/batch", json=payload))
                        s_ids.append(s.get('id'))

                if not tasks: continue
                
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                for i, res in enumerate(responses):
                    if isinstance(res, Exception): continue
                    
                    try:
                        batch = await res.json()
                        if not batch or 'data' not in batch: continue
                        
                        for img_data in batch['data']:
                            current_url = img_data.get('imageUrl')
                            if current_url:
                                current_bytes = await get_image_bytes(session, current_url)
                                if current_bytes and images_match(target_bytes, current_bytes):
                                    print(f"🎯 PIXEL MATCH FOUND!")
                                    return s_ids[i]
                    except: continue
                
                cursor = data.get('nextPageCursor', "")
                if not cursor: break
                await asyncio.sleep(0.1) # Small delay to prevent local spam
        except Exception as e:
            print(f"❌ Error during server scan: {e}")
            break
            
    return None

@app.post("/stxr-log")
async def handle_request(request: Request):
    try:
        data = await request.json()
    except:
        return {"status": "bad_json"}

    if data.get("secret") != SECRET: return {"status": "unauthorized"}

    uid, pid, item = data.get("userId"), data.get("placeId"), data.get("itemName", "Unknown")
    print(f"📨 Claim Received: {item} (UID: {uid})")

    if not uid or not pid:
        return {"status": "missing_info"}

    await asyncio.sleep(5) 
    job_id = await stxr_warp_scan(pid, uid)

    if job_id:
        try:
            channel = bot.get_channel(LOG_CHANNEL_ID) or await bot.fetch_channel(LOG_CHANNEL_ID)
            if channel:
                embed = discord.Embed(title="🎯 TARGET VERIFIED", color=0x00FF00)
                embed.set_thumbnail(url=f"https://www.roblox.com/headshot-thumbnail/image?userId={uid}&width=150&height=150&format=png")
                embed.add_field(name="Item", value=f"**{item}**", inline=False)
                embed.add_field(name="Join", value=f"[CLICK TO JOIN](https://www.roblox.com/games/{pid}?jobId={job_id})")
                bot.loop.create_task(channel.send(embed=embed))
                return {"status": "success", "jobId": job_id}
        except Exception as e:
            print(f"❌ Discord Logging Error: {e}")
    
    return {"status": "not_found"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
