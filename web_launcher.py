"""
Pandy AI 打标器 - Web 启动器
直接启动 Flask 后端并自动打开浏览器
"""
import sys
import os
import threading
import webbrowser
import time

# 将 backend 目录添加到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app import app

def start_browser():
    """等待服务器启动后打开浏览器"""
    time.sleep(1.5)
    print(f"Opening browser at http://127.0.0.1:5000")
    webbrowser.open('http://127.0.0.1:5000')

if __name__ == '__main__':
    print("="*60)
    print("Pandy AI Tagger - Web Launcher")
    print("="*60)
    
    # 在后台线程启动浏览器打开
    threading.Thread(target=start_browser, daemon=True).start()
    
    # 启动 Flask 服务
    print("Starting Flask backend service...")
    # 注意: debug=True 会导致重载器启动，可能会导致浏览器打开两次，
    # 但在开发阶段很有用。生产环境应设为 False。
    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)
