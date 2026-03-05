import aiohttp
import json
import re
import time
import asyncio
import random
from app.config import LOCKET_EMAIL, LOCKET_PASSWORD, GIST_TOKEN_URL

# Headers tiêu chuẩn để giả lập thiết bị iOS
HEADERS = {
    'Host': 'api.revenuecat.com',
    'Authorization': 'Bearer appl_JngFETzdodyLmCREOlwTUtXdQik',
    'Content-Type': 'application/json',
    'X-Platform': 'iOS',
    'User-Agent': 'Locket/1.82.0 (iPhone; iOS 18.0; Scale/3.00)',
    'X-Is-Sandbox': 'true'
}

class AsyncLocketAPI:
    """Hợp nhất logic từ auth.py và api.py sang chế độ Bất đồng bộ"""
    def __init__(self):
        self.email = LOCKET_EMAIL
        self.password = LOCKET_PASSWORD

    async def get_token(self):
        """Lấy idToken từ Google Identity Toolkit (auth.py)"""
        url = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key=AIzaSyCQngaaXQIfJaH0aS2l7REgIjD7nL431So"
        payload = {
            "email": self.email,
            "password": self.password,
            "clientType": "CLIENT_TYPE_IOS",
            "returnSecureToken": True
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('idToken')
                raise Exception("Đăng nhập Locket thất bại. Kiểm tra lại tài khoản!")

async def resolve_uid(username):
    """Tìm UID 28 ký tự từ username Locket"""
    url = f"https://locket.cam/{username}"
    headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU OS 17_0 like Mac OS X)"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as res:
                text = await res.text()
                match = re.search(r'/invites/([A-Za-z0-9]{28})', text)
                return match.group(1) if match else None
    except:
        return None

async def check_status(uid):
    """Kiểm tra xem User đã có Gold hay chưa"""
    url = f"https://api.revenuecat.com/v1/subscribers/{uid}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as res:
            if res.status == 200:
                data = await res.json()
                gold = data.get('subscriber', {}).get('entitlements', {}).get('Gold', {})
                if gold:
                    return {"active": True, "expires": gold.get('expires_date')}
            return {"active": False}

async def inject_gold(uid, token_config, log_callback=None):
    """Hàm xử lý chính: Login -> Lấy Payload từ Gist -> Kích hoạt Gold"""
    def log(msg):
        if log_callback: log_callback(msg)

    log("🔑 Đang đăng nhập hệ thống Locket...")
    api = AsyncLocketAPI()
    try:
        token = await api.get_token()
        log("✅ Đăng nhập thành công.")
    except Exception as e:
        return False, str(e)

    log("📥 Đang tải danh sách Payload từ Gist...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(GIST_TOKEN_URL) as resp:
                if resp.status != 200: return False, "Lỗi tải Gist"
                tokens_list = await resp.json()
                # Chọn random 1 payload từ danh sách như trong api.py của bạn
                payload_data = random.choice(tokens_list)
    except Exception as e:
        return False, f"Lỗi Gist: {str(e)}"

    # Cập nhật thông tin UID và thời gian thực vào Payload
    payload_data["app_user_id"] = uid
    if "attributes" in payload_data:
        payload_data["attributes"]["$attConsentStatus"]["updated_at_ms"] = int(time.time() * 1000)

    url = "https://api.revenuecat.com/v1/receipts"
    log(f"🚀 Đang thực hiện kích hoạt Gold cho: {uid}")

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=HEADERS, json=payload_data) as res:
            if res.status == 200:
                log("⚡ Receipt đã được gửi. Đang đợi xác minh...")
                await asyncio.sleep(2)
                status = await check_status(uid)
                if status["active"]:
                    log("🏆 KÍCH HOẠT THÀNH CÔNG!")
                    return True, "SUCCESS"
                return False, "Receipt OK nhưng không thấy gói Gold."
            else:
                return False, f"RevenueCat từ chối: {res.status}"
