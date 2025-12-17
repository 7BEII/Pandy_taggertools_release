"""
Pandy AI 打标器 - 桌面启动器
使用 pywebview 将 Web UI 打包为桌面应用
"""
import webview
import threading
import sys
import os
import platform
import ctypes

# 将 backend 目录添加到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app import app


class FileAPI:
    """文件选择 API - 暴露给前端 JavaScript"""
    
    def minimize(self):
        """最小化窗口"""
        window.minimize()
    
    def toggle_fullscreen(self):
        """切换全屏"""
        window.toggle_fullscreen()
    
    def close(self):
        """关闭窗口"""
        window.destroy()
    
    def select_files(self, file_types_filter='image'):
        """
        选择文件
        :param file_types_filter: 'image' 或 'log'
        """
        if file_types_filter == 'log':
            file_types = ('Log Files (*.log;*.txt;*.json)', 'All files (*.*)')
        else:
            file_types = ('Image Files (*.jpg;*.jpeg;*.png;*.webp)', 'All files (*.*)')
            
        result = window.create_file_dialog(
            dialog_type=webview.OPEN_DIALOG,
            allow_multiple=True,
            file_types=file_types
        )
        return result if result else []
    
    def select_folder(self):
        """选择文件夹"""
        result = window.create_file_dialog(
            dialog_type=webview.FOLDER_DIALOG
        )
        return result[0] if result else None

    def save_file(self, filename='config.json'):
        """保存文件对话框"""
        result = window.create_file_dialog(
            dialog_type=webview.SAVE_DIALOG,
            save_filename=filename,
            file_types=('JSON Files (*.json)', 'All files (*.*)')
        )
        return result if result else None


def start_flask():
    """启动 Flask 后端服务"""
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False, threaded=True)


# 全局窗口对象
window = None

def create_window():
    """创建桌面窗口"""
    global window
    
    # 创建窗口并暴露 API
    window = webview.create_window(
        title='Pandy AI 打标器',
        url='http://127.0.0.1:5000',
        width=1400,
        height=900,
        resizable=True,
        fullscreen=False,
        min_size=(1200, 800),
        background_color='#F9FAFB',  # 浅灰背景
        js_api=FileAPI()
    )
    
    def _try_set_native_titlebar_color():
        try:
            if platform.system().lower() != 'windows':
                return

            hwnd = None
            try:
                hwnd = getattr(window, '_hWnd', None) or getattr(window, '_hwnd', None)
            except Exception:
                hwnd = None

            if not hwnd:
                hwnd = ctypes.windll.user32.FindWindowW(None, 'Pandy AI 打标器')

            if not hwnd:
                return

            DWMWA_BORDER_COLOR = 34
            DWMWA_CAPTION_COLOR = 35
            colorref = ctypes.c_int(0x00F65C8B)  # #8B5CF6 -> 0x00BBGGRR

            dwmapi = ctypes.windll.dwmapi
            dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR, ctypes.byref(colorref), ctypes.sizeof(colorref))
            dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_BORDER_COLOR, ctypes.byref(colorref), ctypes.sizeof(colorref))
        except Exception:
            return

    # 启动 webview
    webview.start(_try_set_native_titlebar_color, debug=False)


if __name__ == '__main__':
    print("="*60)
    print("Pandy AI Tagger - Starting...")
    print("="*60)
    print("[1/3] Starting Flask backend service...")
    
    # 在后台线程启动 Flask
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    
    # 等待 Flask 启动
    import time
    time.sleep(2)
    
    print("[2/3] Backend service started successfully")
    print("[3/3] Opening desktop window...")
    print("="*60)
    
    # 创建并显示窗口
    create_window()
