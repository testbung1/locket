import aiohttp
import os
import json
import re
from app.config import HEADERS

# Lấy thông tin từ ENV Render
GIST_URL = os.environ.get("GIST_URL")
EMAIL = os.environ.get("EMAIL_ACC")
PASSWORD = os.environ.get("PASSWORD_ACC")

async def get_credentials_from_gist():
    """Lấy mã fetch_token và app_transaction từ Gist URL"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(GIST_URL) as res:
                if res.status == 200:
                    data = await res.json()
                    return data.get("fetch_token"), data.get("app_transaction")
        except:
            return None, None

async def login_admin():
    """Đăng nhập bằng Email/Pass từ ENV để lấy Session Token của bạn"""
    url = "https://api.locket.cam/v1/auth/login"
    payload = {"email": EMAIL, "password": PASSWORD}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload) as res:
                if res.status == 200:
                    data = await res.json()
                    return data.get("session_token")
        except:
            return None

async def inject_gold(target_uid, log_callback=None):
    """Kích hoạt Gold cho người dùng sử dụng Session của Admin và mã từ Gist"""
    def log(msg): 
        if log_callback: log_callback(msg)

    # 1. Lấy mã Gold từ Gist
    fetch, trans = await get_credentials_from_gist()
    # 2. Lấy Session Token của bạn
    admin_token = await login_admin()

    if not fetch or not admin_token:
        return False, "Lỗi: Không lấy được mã Gold từ Gist hoặc Login thất bại."

    url = "https://api.revenuecat.com/v1/receipts"
    headers = HEADERS.copy()
    headers['Authorization'] = f'Bearer {admin_token}'
    
    body = {
        "product_id": "locket_199_1m",
        "fetch_token": fetch,
        "app_transaction": trans,
        "app_user_id": target_uid,
        "is_restore": True,
        "store_country": "VNM"
    }

    async with aiohttp.ClientSession() as session:
        try:
            log(f"[*] Đang thực hiện kích hoạt cho: {target_uid}")
            async with session.post(url, headers=headers, json=body) as res:
                if res.status == 200:
                    return True, "SUCCESS"
                return False, f"RevenueCat Rejected: {res.status}"
        except Exception as e:
            return False, str(e)

async def resolve_uid(username):
    """Tìm UID từ username công khai của người dùng"""
    url = f"https://locket.cam/{username}"
    headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as res:
                html = await res.text()
                m = re.search(r'/invites/([A-Za-z0-9]{28})', html)
                return m.group(1) if m else None
        except: return None
