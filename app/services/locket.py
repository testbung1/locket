import aiohttp
import json
import re
import time
import asyncio
import random
from app.config import LOCKET_EMAIL, LOCKET_PASSWORD, GIST_TOKEN_URL

# Headers giả lập thiết bị iOS
HEADERS = {
    'Host': 'api.revenuecat.com',
    'Authorization': 'Bearer appl_JngFETzdodyLmCREOlwTUtXdQik',
    'Content-Type': 'application/json',
    'X-Platform': 'iOS',
    'User-Agent': 'Locket/1.82.0 (iPhone; iOS 18.0; Scale/3.00)',
    'X-Is-Sandbox': 'true'
}

class AsyncLocketAuth:
    """Xử lý đăng nhập lấy Token (Từ auth.py)"""
    async def get_token(self):
        url = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key=AIzaSyCQngaaXQIfJaH0aS2l7REgIjD7nL431So"
        payload = {
            "email": LOCKET_EMAIL,
            "password": LOCKET_PASSWORD,
            "clientType": "CLIENT_TYPE_IOS",
            "returnSecureToken": True
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('idToken')
                raise Exception("Đăng nhập Locket thất bại!")

async def resolve_uid(input_text):
    """Xử lý link locket.cam và lấy UID 28 ký tự"""
    username = input_text.strip()
    if "locket.cam/" in username:
        username = username.split("locket.cam/")[-1].split("?")[0].replace("/", "")

    url = f"https://locket.cam/{username}"
    headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU OS 17_0 like Mac OS X)"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as res:
                if res.status != 200: return None
                html = await res.text()
                # Tìm mã UID 28 ký tự trong HTML
                match = re.search(r'/invites/([A-Za-z0-9]{28})', html)
                if match: return match.group(1)
                match_alt = re.search(r'data-target-id="([A-Za-z0-9]{28})"', html)
                return match_alt.group(1) if match_alt else None
    except:
        return None

async def check_status(uid):
    """Kiểm tra gói Gold qua RevenueCat"""
    url = f"https://api.revenuecat.com/v1/subscribers/{uid}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as res:
            if res.status == 200:
                data = await res.json()
                ent = data.get('subscriber', {}).get('entitlements', {}).get('Gold', {})
                if ent: return {"active": True, "expires": ent.get('expires_date')}
            return {"active": False}

async def inject_gold(uid, token_config, log_callback=None):
    """Hợp nhất logic buff Gold từ app.py và api.py"""
    def log(msg):
        if log_callback: log_callback(msg)

    log("🔑 Đang lấy Token đăng nhập...")
    auth = AsyncLocketAuth()
    try:
        token = await auth.get_token()
        log("✅ Đăng nhập Admin thành công.")
    except Exception as e:
        return False, str(e)

    log("📥 Đang tải Payload từ Gist...")
    async with aiohttp.ClientSession() as session:
        async with session.get(GIST_TOKEN_URL) as resp:
            if resp.status != 200: return False, "Lỗi tải Gist"
            tokens = await resp.json()
            payload_data = random.choice(tokens) # Chọn ngẫu nhiên payload

    # Gán UID khách vào Payload
    payload_data["app_user_id"] = uid
    if "attributes" in payload_data:
        payload_data["attributes"]["$attConsentStatus"]["updated_at_ms"] = int(time.time() * 1000)

    log(f"🚀 Đang Inject Gold cho: {uid}")
    async with aiohttp.ClientSession() as session:
        async with session.post("https://api.revenuecat.com/v1/receipts", headers=HEADERS, json=payload_data) as res:
            if res.status == 200:
                log("⚡ Đã gửi Receipt. Đang xác minh...")
                await asyncio.sleep(2)
                status = await check_status(uid)
                if status["active"]:
                    log("🏆 KÍCH HOẠT THÀNH CÔNG!")
                    return True, "SUCCESS"
                return False, "Receipt OK nhưng không có Gold."
            return False, f"Lỗi API: {res.status}"
