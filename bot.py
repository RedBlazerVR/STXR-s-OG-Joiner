import os, asyncio, aiohttp, uvicorn
from fastapi import FastAPI, Request

# --- CONFIG ---
WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
SECRET = "BRAINROT_2026"

app = FastAPI()
session_container = {"session": None}

async def stxr_warp_scan(place_id, user_id):
    if not session_container["session"]: 
        session_container["session"] = aiohttp.ClientSession()
    session = session_container["session"]
    
    # 1. Get Target Headshot (Wait for it to be 'Completed')
    target_img = None
    thumb_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=48x48&format=Png"
    for _ in range(3):
        async with session.get(thumb_url) as r:
            t_data = await r.json()
            if t_data and 'data' in t_data and t_data['data'][0]['state'] == 'Completed':
                target_img = t_data['data'][0]['imageUrl']
                break
        await asyncio.sleep(1)
    
    if not target_img: return None

    # 2. Deep Scan ALL Servers (Parallelized)
    cursor = ""
    for _ in range(40): # Scan up to 4,000 players
        api_url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=100&cursor={cursor}"
        async with session.get(api_url) as r:
            data = await r.json()
            if 'data' not in data: break
            
            tasks, s_ids = [], []
            for s in data['data']:
                tokens = s.get('playerTokens', [])
                if tokens:
                    payload = [{"token": t, "type": "AvatarHeadShot", "size": "48x48", "format": "png"} for t in tokens]
                    tasks.append(session.post("https://thumbnails.roblox.com/v1/batch", json=payload))
                    s_ids.append(s.get('id'))

            responses = await asyncio.gather(*tasks)
            for i, res in enumerate(responses):
                batch = await res.json()
                if any(img.get('imageUrl') == target_img for img in batch.get('data', [])):
                    return s_ids[i]
            
            cursor = data.get('nextPageCursor')
            if not cursor: break
    return None

@app.post("/stxr-log")
async def handle_snipe(request: Request):
    data = await request.json()
    if data.get("secret") != SECRET: return {"status": "unauthorized"}
    
    uid, pid = data.get("userId"), data.get("placeId")
    item, mut = data.get("itemName", "Unknown"), data.get("mutation", "None")

    job_id = await stxr_warp_scan(pid, uid)
    
    if job_id and WEBHOOK_URL:
        async with aiohttp.ClientSession() as log_session:
            link = f"https://www.roblox.com/games/{pid}?jobId={job_id}"
            payload = {
                "embeds": [{
                    "title": "🎯 TARGET VERIFIED",
                    "color": 16777215,
                    "fields": [
                        {"name": "Item", "value": f"**{item}**", "inline": True},
                        {"name": "Mutation", "value": mut, "inline": True},
                        {"name": "Join", "value": f"[CLICK TO JOIN]({link})"}
                    ],
                    "thumbnail": {"url": f"https://www.roblox.com/headshot-thumbnail/image?userId={uid}&width=150&height=150&format=png"}
                }]
            }
            await log_session.post(WEBHOOK_URL, json=payload)
    
    return {"status": "success" if job_id else "not_found", "jobId": job_id}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
