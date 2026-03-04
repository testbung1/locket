import os
import threading
import http.server
import socketserver
from app.bot import run_bot

# --- CẤU HÌNH WEB SERVER GIẢ LẬP CHO RENDER ---
def run_dummy_server():
    """
    Tạo một server HTTP đơn giản để Render có thể kiểm tra cổng (Port Binding).
    Giúp tránh lỗi 'Port scan timeout' và giữ bot không bị tắt.
    """
    # Render cung cấp cổng qua biến môi trường PORT, mặc định là 8080 nếu chạy local
    port = int(os.environ.get("PORT", 8080))
    
    # Cấu hình Handler đơn giản
    handler = http.server.SimpleHTTPRequestHandler
    
    # Cho phép sử dụng lại địa chỉ port ngay lập tức khi khởi động lại
    socketserver.TCPServer.allow_reuse_address = True
    
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"🚀 [System] Dummy server đang chạy tại cổng: {port}")
            httpd.serve_forever()
    except Exception as e:
        print(f"⚠️ [System] Không thể khởi động Dummy Server: {e}")

# --- KHỞI CHẠY HỆ THỐNG ---
if __name__ == "__main__":
    print("🤖 [System] Đang khởi động Locket Gold Activator...")

    # 1. Chạy Server giả trong một luồng riêng (Background Thread)
    # daemon=True đảm bảo server này sẽ tắt khi bot chính tắt
    threading.Thread(target=run_dummy_server, daemon=True).start()
    
    # 2. Chạy Telegram Bot chính
    # Hàm này sẽ chặn (block) tiến trình ở đây để duy trì bot
    run_bot()
