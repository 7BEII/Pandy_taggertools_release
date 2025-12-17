"""
Flask 后端主服务
提供 RESTful API 供前端调用
"""
import os
import sys
import json
import uuid
import re
import shutil
import threading
import webbrowser
import tkinter as tk
from tkinter import filedialog
from datetime import datetime
import traceback
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from api_handler import APIHandler
from image_processor import ImageProcessor

# 添加父目录到路径，以便导入 training_analyzer
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入训练分析器模块
try:
    from training_analyzer import (
        parse_log_file,
        save_record,
        get_records_summary,
        delete_record,
        get_record_by_id,
        copy_to_log_dir,
        move_to_history,
        get_pending_logs,
        get_history_logs
    )
    TRAINING_ANALYZER_AVAILABLE = True
except ImportError as e:
    print(f"警告: 训练分析器模块未能加载 - {e}")
    TRAINING_ANALYZER_AVAILABLE = False

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

# 初始化 hidden root window for tkinter dialogs
def get_tk_root():
    try:
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        root.attributes('-topmost', True)  # Make dialogs appear on top
        return root
    except Exception:
        return None

# ... (rest of the file)

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "apikey_config", "config.json")
APIKEY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "apikey_config", "apikey.json")
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "apikey_config")
images_data = {}
pairs_data = {}
processing_tasks = {}

DEFAULT_SYSTEM_PROMPT = "You are an AI prompt expert who can analyze images. Please look closely at the image and provide a detailed and accurate description as required."
DEFAULT_USER_PROMPT = "Describe this image in detail for text-to-image training dataset captions."

DEFAULT_EDITING_SYSTEM_PROMPT = """你是一位专业的视觉分析师。你的目标是分析图像并产生简短准确的描述， 描述为了将第一张图转变为第二张图所做的改变。请重点关注第二张图具体发生的修改、添加、删除或变更，无需描述他们原来的服装场景,尽量不描述颜色，如果是小女孩要用girl 女生用woman。

输出格式：

除了描述提示词本身外，不要回应任何其他内容

不要将描述分成两部分或多行
PD 是触发词，需要放置最前面

请提供不超过160字的详细描述来解释这个转变过程，根据参考示例用英语描述,示例提示词：
PD, Turn the pet into a Vector illustration painting style,and soft shading to define fur texture and facial features,set against a clean white background."""
DEFAULT_EDITING_USER_PROMPT = "Generate the transformation prompt."


def _ensure_prompt_templates(config):
    if not isinstance(config, dict):
        return

    prompt_templates = config.get('prompt_templates')
    if not isinstance(prompt_templates, dict):
        prompt_templates = {}
        config['prompt_templates'] = prompt_templates

    def _ensure_mode(mode, default_name, system_prompt, user_prompt):
        mode_obj = prompt_templates.get(mode)
        if not isinstance(mode_obj, dict):
            mode_obj = {}
            prompt_templates[mode] = mode_obj

        templates = mode_obj.get('templates')
        if not isinstance(templates, list) or len(templates) == 0:
            templates = [{
                'id': 'default',
                'name': default_name,
                'system_prompt': system_prompt,
                'user_prompt': user_prompt
            }]
            mode_obj['templates'] = templates

        selected = mode_obj.get('selected')
        if not selected:
            mode_obj['selected'] = templates[0].get('id', 'default')
        else:
            exists = any(tpl.get('id') == selected for tpl in templates if isinstance(tpl, dict))
            if not exists:
                mode_obj['selected'] = templates[0].get('id', 'default')

    legacy_system = config.get('system_prompt') or DEFAULT_SYSTEM_PROMPT
    legacy_user = config.get('user_prompt') or DEFAULT_USER_PROMPT

    _ensure_mode('tagging', '默认(单图反推)', legacy_system, legacy_user)
    _ensure_mode('editing', '默认(编辑模型)', DEFAULT_EDITING_SYSTEM_PROMPT, DEFAULT_EDITING_USER_PROMPT)


def _get_selected_prompts(config, mode):
    prompt_templates = (config or {}).get('prompt_templates')
    if not isinstance(prompt_templates, dict):
        return DEFAULT_SYSTEM_PROMPT, DEFAULT_USER_PROMPT

    mode_obj = prompt_templates.get(mode)
    if not isinstance(mode_obj, dict):
        return DEFAULT_SYSTEM_PROMPT, DEFAULT_USER_PROMPT

    templates = mode_obj.get('templates')
    selected = mode_obj.get('selected')
    if isinstance(templates, list):
        for tpl in templates:
            if isinstance(tpl, dict) and tpl.get('id') == selected:
                return tpl.get('system_prompt') or DEFAULT_SYSTEM_PROMPT, tpl.get('user_prompt') or DEFAULT_USER_PROMPT

        for tpl in templates:
            if isinstance(tpl, dict):
                return tpl.get('system_prompt') or DEFAULT_SYSTEM_PROMPT, tpl.get('user_prompt') or DEFAULT_USER_PROMPT

    return DEFAULT_SYSTEM_PROMPT, DEFAULT_USER_PROMPT


def load_config():
    """加载配置文件"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            _ensure_prompt_templates(config)
            return config
    
    config = {
        "providers": {
            "siliconflow": {"api_key": "", "base_url": "https://api.siliconflow.cn/v1"},
            "modelscope": {"api_key": "", "base_url": "https://api.modelscope.cn/v1"},
            "tuzi": {"api_key": "", "base_url": "https://api.tuziapi.com/v1"}
        },
        "current_provider": "siliconflow",
        "model": "Qwen/Qwen2.5-VL-72B-Instruct",
        "system_prompt": DEFAULT_SYSTEM_PROMPT,
        "user_prompt": DEFAULT_USER_PROMPT
    }

    _ensure_prompt_templates(config)
    return config


def save_config(config):
    """保存配置文件"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def load_apikey_config():
    """加载API Key配置文件"""
    if os.path.exists(APIKEY_FILE):
        try:
            with open(APIKEY_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
        except (json.JSONDecodeError, Exception):
            pass
    
    return {
        "providers": {
            "siliconflow": {"api_key": "", "base_url": "https://api.siliconflow.cn/v1"},
            "modelscope": {"api_key": "", "base_url": "https://api.modelscope.cn/v1"},
            "tuzi": {"api_key": "", "base_url": "https://api.tuziapi.com/v1"}
        },
        "current_provider": "siliconflow",
        "model": "Qwen/Qwen2.5-VL-72B-Instruct"
    }


def save_apikey_config(config):
    """保存API Key配置文件"""
    os.makedirs(os.path.dirname(APIKEY_FILE), exist_ok=True)
    with open(APIKEY_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def list_prompt_templates():
    """列出所有提示词模板文件"""
    templates = []
    if os.path.exists(TEMPLATES_DIR):
        for filename in os.listdir(TEMPLATES_DIR):
            if filename.endswith('.json') and filename not in ['apikey.json', 'config.json']:
                filepath = os.path.join(TEMPLATES_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        templates.append({
                            "filename": filename,
                            "name": data.get("name", filename.replace('.json', '')),
                            "mode": data.get("mode", "tagging"),
                            "system_prompt": data.get("system_prompt", ""),
                            "user_prompt": data.get("user_prompt", "")
                        })
                except (json.JSONDecodeError, Exception):
                    pass
    return templates


def load_prompt_template(filename):
    """加载指定的提示词模板"""
    filepath = os.path.join(TEMPLATES_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def save_prompt_template(filename, data):
    """保存提示词模板"""
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    filepath = os.path.join(TEMPLATES_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def delete_prompt_template(filename):
    """删除提示词模板"""
    if filename in ['apikey.json', 'config.json']:
        return False
    filepath = os.path.join(TEMPLATES_DIR, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False


def _build_pair_side_info(image_path):
    info = ImageProcessor.load_image_with_txt(image_path)
    if not info:
        return None

    return {
        "path": info.get("path"),
        "name": info.get("name"),
        "width": info.get("width"),
        "height": info.get("height"),
        "thumbnail": info.get("thumbnail"),
        "text": info.get("text", ""),
        "status": info.get("status", "idle")
    }


def _get_pair_text(left_side, right_side):
    left_text = (left_side or {}).get('text')
    if isinstance(left_text, str) and left_text.strip():
        return left_text
    right_text = (right_side or {}).get('text')
    if isinstance(right_text, str) and right_text.strip():
        return right_text
    return ""


def _pair_contains_path(path, exclude_pair_id=None):
    if not path:
        return False
    for pid, pair in pairs_data.items():
        if exclude_pair_id and pid == exclude_pair_id:
            continue
        left = (pair.get('left') or {}).get('path')
        right = (pair.get('right') or {}).get('path')
        if left == path or right == path:
            return True
    return False


@app.route('/')
def index():
    """返回前端主页"""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/preview', methods=['POST'])
def preview_local_image():
    """预览本地图片，返回Base64"""
    try:
        data = request.get_json(silent=True) or {}
        path = data.get('path')
        if not path or not os.path.exists(path):
            return jsonify({"success": False, "message": "文件不存在"}), 404
            
        info = ImageProcessor.load_image_with_txt(path)
        if not info:
            return jsonify({"success": False, "message": "无法读取图片"}), 500
            
        return jsonify({
            "success": True,
            "thumbnail": info.get("thumbnail")
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/config', methods=['GET'])
def get_config():
    """获取配置"""
    config = load_config()
    config['available_providers'] = APIHandler.PROVIDERS
    return jsonify(config)


@app.route('/api/config', methods=['POST'])
def update_config():
    """更新配置"""
    try:
        config = request.get_json(silent=True) or {}
        if isinstance(config, dict) and 'available_providers' in config:
            del config['available_providers']
        _ensure_prompt_templates(config)
        save_config(config)
        return jsonify({"success": True, "message": "配置已保存"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/apikey', methods=['GET'])
def get_apikey_config():
    """获取API Key配置"""
    config = load_apikey_config()
    config['available_providers'] = APIHandler.PROVIDERS
    return jsonify({"success": True, "config": config})


@app.route('/api/apikey', methods=['POST'])
def update_apikey_config():
    """更新API Key配置"""
    try:
        config = request.get_json(silent=True) or {}
        if 'available_providers' in config:
            del config['available_providers']
        save_apikey_config(config)
        return jsonify({"success": True, "message": "API Key配置已保存"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/apikey/test', methods=['POST'])
def test_api_connection():
    """测试API连通性"""
    try:
        data = request.get_json(silent=True) or {}
        api_key = data.get('api_key', '')
        base_url = data.get('base_url', '')
        model = data.get('model', 'Qwen/Qwen2.5-VL-72B-Instruct')
        
        if not api_key:
            return jsonify({"success": False, "message": "API Key不能为空"})
        if not base_url:
            return jsonify({"success": False, "message": "Base URL不能为空"})
        
        # 使用OpenAI兼容接口测试连通性
        import requests
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 尝试调用models接口检测连通性
        test_url = f"{base_url.rstrip('/')}/models"
        try:
            response = requests.get(test_url, headers=headers, timeout=10)
            if response.status_code == 200:
                return jsonify({"success": True, "message": "连接成功！API可用"})
            elif response.status_code == 401:
                return jsonify({"success": False, "message": "API Key无效或已过期"})
            elif response.status_code == 403:
                return jsonify({"success": False, "message": "API Key权限不足"})
            else:
                # 有些API不支持/models接口，尝试简单的chat请求
                chat_url = f"{base_url.rstrip('/')}/chat/completions"
                chat_data = {
                    "model": model,
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5
                }
                chat_response = requests.post(chat_url, headers=headers, json=chat_data, timeout=15)
                if chat_response.status_code == 200:
                    return jsonify({"success": True, "message": "连接成功！API可用"})
                else:
                    return jsonify({"success": False, "message": f"连接失败: HTTP {chat_response.status_code}"})
        except requests.exceptions.Timeout:
            return jsonify({"success": False, "message": "连接超时，请检查网络或Base URL"})
        except requests.exceptions.ConnectionError:
            return jsonify({"success": False, "message": "无法连接到服务器，请检查Base URL"})
        except Exception as e:
            return jsonify({"success": False, "message": f"连接错误: {str(e)}"})
            
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/templates', methods=['GET'])
def get_templates():
    """获取所有提示词模板列表"""
    templates = list_prompt_templates()
    return jsonify({"success": True, "templates": templates})


@app.route('/api/templates/<filename>', methods=['GET'])
def get_template(filename):
    """获取指定模板"""
    template = load_prompt_template(filename)
    if template:
        return jsonify({"success": True, "template": template})
    return jsonify({"success": False, "message": "模板不存在"}), 404


@app.route('/api/templates', methods=['POST'])
def create_template():
    """创建新模板"""
    try:
        data = request.get_json(silent=True) or {}
        name = data.get('name', '').strip()
        if not name:
            return jsonify({"success": False, "message": "模板名称不能为空"}), 400
        
        filename = f"{name}.json"
        filepath = os.path.join(TEMPLATES_DIR, filename)
        if os.path.exists(filepath):
            return jsonify({"success": False, "message": "模板已存在"}), 400
        
        template_data = {
            "name": name,
            "mode": data.get('mode', 'tagging'),
            "system_prompt": data.get('system_prompt', ''),
            "user_prompt": data.get('user_prompt', '')
        }
        save_prompt_template(filename, template_data)
        return jsonify({"success": True, "message": "模板已创建", "filename": filename})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/templates/<filename>', methods=['PUT'])
def update_template(filename):
    """更新模板"""
    try:
        if filename in ['apikey.json', 'config.json']:
            return jsonify({"success": False, "message": "无法修改此文件"}), 400
        
        data = request.get_json(silent=True) or {}
        template_data = {
            "name": data.get('name', filename.replace('.json', '')),
            "mode": data.get('mode', 'tagging'),
            "system_prompt": data.get('system_prompt', ''),
            "user_prompt": data.get('user_prompt', '')
        }
        save_prompt_template(filename, template_data)
        return jsonify({"success": True, "message": "模板已更新"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/templates/<filename>', methods=['DELETE'])
def remove_template(filename):
    """删除模板"""
    try:
        if delete_prompt_template(filename):
            return jsonify({"success": True, "message": "模板已删除"})
        return jsonify({"success": False, "message": "无法删除此模板"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/images/add', methods=['POST'])
def add_images():
    """添加图片"""
    try:
        data = request.get_json(silent=True) or {}
        paths = data.get('paths', [])
        
        added = 0
        for path in paths:
            if not os.path.exists(path):
                continue
            
            if any(img['path'] == path for img in images_data.values()):
                continue
            
            img_info = ImageProcessor.load_image_with_txt(path)
            if img_info:
                img_id = str(uuid.uuid4())
                img_info['id'] = img_id
                images_data[img_id] = img_info
                added += 1
        
        return jsonify({
            "success": True,
            "added": added,
            "total": len(images_data),
            "images": list(images_data.values())
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/pairs', methods=['GET'])
def get_pairs():
    """获取所有成对图片（编辑模式）"""
    return jsonify({
        "success": True,
        "pairs": list(pairs_data.values())
    })


@app.route('/api/pairs/add', methods=['POST'])
def add_pairs():
    """添加成对图片（编辑模式）"""
    try:
        data = request.json or {}
        pairs = data.get('pairs', [])

        added = 0
        for item in pairs:
            left_path = item.get('left_path')
            right_path = item.get('right_path')

            if left_path and not os.path.exists(left_path):
                left_path = None
            if right_path and not os.path.exists(right_path):
                right_path = None

            create_empty = bool(item.get('create_empty'))
            if not left_path and not right_path and not create_empty:
                continue

            if _pair_contains_path(left_path) or _pair_contains_path(right_path):
                continue

            pair_id = str(uuid.uuid4())
            left_side = _build_pair_side_info(left_path) if left_path else None
            right_side = _build_pair_side_info(right_path) if right_path else None
            pair_text = _get_pair_text(left_side, right_side)
            pair_info = {
                "id": pair_id,
                "left": left_side,
                "right": right_side,
                "text": pair_text,
                "status": "success" if pair_text else "idle",
                "selected": False
            }

            pairs_data[pair_id] = pair_info
            added += 1

        return jsonify({
            "success": True,
            "added": added,
            "total": len(pairs_data),
            "pairs": list(pairs_data.values())
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/pairs/<pair_id>', methods=['GET'])
def get_pair(pair_id):
    """获取单组成对图片"""
    if pair_id not in pairs_data:
        return jsonify({"success": False, "message": "成对图片组不存在"}), 404

    return jsonify({
        "success": True,
        "pair": pairs_data[pair_id]
    })


@app.route('/api/pairs/<pair_id>', methods=['PUT'])
def update_pair(pair_id):
    """更新成对图片组（文本/勾选/导出名/左右图）"""
    if pair_id not in pairs_data:
        return jsonify({"success": False, "message": "成对图片组不存在"}), 404

    try:
        data = request.json or {}
        pair = pairs_data[pair_id]

        if 'text' in data:
            pair['text'] = data.get('text', '')
            pair['status'] = 'success'

        if 'selected' in data:
            pair['selected'] = bool(data['selected'])

        if 'export_name' in data:
            pair['export_name'] = data.get('export_name')

        left_path = data.get('left_path')
        right_path = data.get('right_path')

        if left_path is not None:
            if left_path and os.path.exists(left_path) and not _pair_contains_path(left_path, exclude_pair_id=pair_id):
                pair['left'] = _build_pair_side_info(left_path)
            elif not left_path:
                pair['left'] = None

        if right_path is not None:
            if right_path and os.path.exists(right_path) and not _pair_contains_path(right_path, exclude_pair_id=pair_id):
                pair['right'] = _build_pair_side_info(right_path)
            elif not right_path:
                pair['right'] = None

        return jsonify({
            "success": True,
            "pair": pair
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/pairs/<pair_id>', methods=['DELETE'])
def delete_pair(pair_id):
    """删除成对图片组"""
    if pair_id not in pairs_data:
        return jsonify({"success": False, "message": "成对图片组不存在"}), 404

    del pairs_data[pair_id]
    return jsonify({"success": True, "message": "删除成功"})


@app.route('/api/pairs/<pair_id>/upload-image', methods=['POST'])
def upload_pair_image(pair_id):
    """通过拖拽上传图片到成对图片组"""
    if pair_id not in pairs_data:
        return jsonify({"success": False, "message": "成对图片组不存在"}), 404
    
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "message": "未找到上传文件"}), 400
        
        file = request.files['file']
        side = request.form.get('side', 'left')
        
        if file.filename == '':
            return jsonify({"success": False, "message": "未选择文件"}), 400
        
        # 检查文件类型
        allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
        _, ext = os.path.splitext(file.filename)
        if ext.lower() not in allowed_extensions:
            return jsonify({"success": False, "message": "不支持的图片格式"}), 400
        
        # 保存文件到临时目录
        import tempfile
        temp_dir = tempfile.gettempdir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_filename = f"pair_upload_{timestamp}{ext}"
        save_path = os.path.join(temp_dir, safe_filename)
        file.save(save_path)
        
        # 更新pair数据
        pair = pairs_data[pair_id]
        side_info = _build_pair_side_info(save_path)
        
        if side == 'left':
            pair['left'] = side_info
        else:
            pair['right'] = side_info
        
        return jsonify({
            "success": True,
            "message": "上传成功",
            "pair": pair
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


def _copy_to_input_folder(src_path):
    """将图片复制到本地 input_datas_image 目录，返回新路径"""
    if not src_path or not os.path.exists(src_path):
        return None
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_folder = os.path.join(base_dir, 'training_datas', 'input_datas_image')
    os.makedirs(input_folder, exist_ok=True)
    
    filename = os.path.basename(src_path)
    dest_path = os.path.join(input_folder, filename)
    
    # 如果目标文件已存在且不是同一个文件，添加唯一后缀
    if os.path.exists(dest_path) and os.path.normpath(src_path) != os.path.normpath(dest_path):
        name, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(dest_path):
            dest_path = os.path.join(input_folder, f"{name}_{counter}{ext}")
            counter += 1
    
    # 如果源文件和目标文件不同，则复制
    if os.path.normpath(src_path) != os.path.normpath(dest_path):
        shutil.copy2(src_path, dest_path)
    
    return dest_path


@app.route('/api/pairs/import-folder', methods=['POST'])
def import_pairs_from_folder():
    """从文件夹批量导入并自动配对，同时复制图片到本地目录"""
    try:
        data = request.json or {}
        folder_path = data.get('path', '')
        import_mode = data.get('mode', 'default')  # 'default' 或 'match'
        left_suffix = data.get('left_suffix', 'r').strip().lower()
        right_suffix = data.get('right_suffix', 't').strip().lower()
        txt_follows = data.get('txt_follows', 'right')  # txt跟随哪边

        if not os.path.exists(folder_path):
            return jsonify({"success": False, "message": "文件夹不存在"}), 400

        # 收集所有图片和txt文件
        image_files = []
        txt_files = {}
        for root, _, files in os.walk(folder_path):
            for filename in files:
                filepath = os.path.join(root, filename)
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    image_files.append(filepath)
                elif filename.lower().endswith('.txt'):
                    stem = os.path.splitext(filename)[0].lower()
                    txt_files[stem] = filepath

        image_files.sort()
        
        # 复制所有图片到本地目录，建立映射
        copied_files = {}
        for src_path in image_files:
            dest_path = _copy_to_input_folder(src_path)
            if dest_path:
                copied_files[src_path] = dest_path
        
        print(f"[Import] Copied {len(copied_files)} images to input_datas_image folder")

        added = 0
        
        if import_mode == 'default':
            # 默认模式：按顺序两两配对
            for i in range(0, len(image_files), 2):
                orig_left_path = image_files[i] if i < len(image_files) else None
                orig_right_path = image_files[i + 1] if i + 1 < len(image_files) else None
                
                if not orig_left_path:
                    continue
                
                # 使用复制后的本地路径
                left_path = copied_files.get(orig_left_path, orig_left_path)
                right_path = copied_files.get(orig_right_path, orig_right_path) if orig_right_path else None
                    
                if _pair_contains_path(left_path) or _pair_contains_path(right_path):
                    continue

                pair_id = str(uuid.uuid4())
                left_side = _build_pair_side_info(left_path) if left_path else None
                right_side = _build_pair_side_info(right_path) if right_path else None
                
                # 尝试查找对应的txt文件
                pair_text = ""
                if left_path:
                    left_stem = os.path.splitext(os.path.basename(left_path))[0].lower()
                    if left_stem in txt_files:
                        try:
                            with open(txt_files[left_stem], 'r', encoding='utf-8') as f:
                                pair_text = f.read().strip()
                        except:
                            pass
                if not pair_text and right_path:
                    right_stem = os.path.splitext(os.path.basename(right_path))[0].lower()
                    if right_stem in txt_files:
                        try:
                            with open(txt_files[right_stem], 'r', encoding='utf-8') as f:
                                pair_text = f.read().strip()
                        except:
                            pass
                
                # 如果没找到txt，尝试从图片路径获取
                if not pair_text:
                    pair_text = _get_pair_text(left_side, right_side)
                
                pair_info = {
                    "id": pair_id,
                    "left": left_side,
                    "right": right_side,
                    "text": pair_text,
                    "status": "success" if pair_text else "idle",
                    "selected": False
                }
                pairs_data[pair_id] = pair_info
                added += 1
        else:
            # 规则匹配模式
            grouped = {}
            
            # 构建动态正则匹配规则
            l_pat = re.escape(left_suffix)
            r_pat = re.escape(right_suffix)
            pattern = re.compile(f"^(.*?)(?:[\-_ ]?)({l_pat}|{r_pat})$", re.IGNORECASE)

            for path in image_files:
                stem = os.path.splitext(os.path.basename(path))[0]
                
                m = pattern.match(stem)
                if not m:
                    continue

                base = m.group(1)
                tag = m.group(2).lower()
                
                side = 'left' if tag == left_suffix else 'right'

                if base not in grouped:
                    grouped[base] = {"left": None, "right": None, "base": base}
                grouped[base][side] = path

            for base, lr in grouped.items():
                orig_left_path = lr.get('left')
                orig_right_path = lr.get('right')

                if not orig_left_path and not orig_right_path:
                    continue
                
                # 使用复制后的本地路径
                left_path = copied_files.get(orig_left_path, orig_left_path) if orig_left_path else None
                right_path = copied_files.get(orig_right_path, orig_right_path) if orig_right_path else None
                    
                if _pair_contains_path(left_path) or _pair_contains_path(right_path):
                    continue

                pair_id = str(uuid.uuid4())
                left_side = _build_pair_side_info(left_path) if left_path else None
                right_side = _build_pair_side_info(right_path) if right_path else None
                
                # 根据txt_follows设置查找txt文件
                pair_text = ""
                if txt_follows == 'left' and left_path:
                    txt_stem = os.path.splitext(os.path.basename(left_path))[0].lower()
                    if txt_stem in txt_files:
                        try:
                            with open(txt_files[txt_stem], 'r', encoding='utf-8') as f:
                                pair_text = f.read().strip()
                        except:
                            pass
                elif txt_follows == 'right' and right_path:
                    txt_stem = os.path.splitext(os.path.basename(right_path))[0].lower()
                    if txt_stem in txt_files:
                        try:
                            with open(txt_files[txt_stem], 'r', encoding='utf-8') as f:
                                pair_text = f.read().strip()
                        except:
                            pass
                
                # 如果没找到，尝试用base名查找
                if not pair_text:
                    base_lower = base.lower()
                    # 尝试 base_suffix 格式
                    suffix_to_try = left_suffix if txt_follows == 'left' else right_suffix
                    txt_key = f"{base_lower}_{suffix_to_try}"
                    if txt_key in txt_files:
                        try:
                            with open(txt_files[txt_key], 'r', encoding='utf-8') as f:
                                pair_text = f.read().strip()
                        except:
                            pass
                
                if not pair_text:
                    pair_text = _get_pair_text(left_side, right_side)
                
                pair_info = {
                    "id": pair_id,
                    "left": left_side,
                    "right": right_side,
                    "text": pair_text,
                    "status": "success" if pair_text else "idle",
                    "selected": False
                }
                pairs_data[pair_id] = pair_info
                added += 1

        return jsonify({
            "success": True,
            "added": added,
            "total": len(pairs_data),
            "pairs": list(pairs_data.values())
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/pairs/export', methods=['POST'])
def export_pairs():
    """导出成对图片数据集（训练格式）"""
    try:
        data = request.json or {}
        ids = data.get('ids', [])
        output_dir = data.get('output_dir', '')
        image_format = data.get('image_format', 'png')
        custom_filename = data.get('filename', '').strip()
        # 命名参数
        naming_mode = data.get('naming_mode', 'default')
        suffix_left = data.get('suffix_left', 'R')
        suffix_left2 = data.get('suffix_left2', 'G')
        suffix_right = data.get('suffix_right', 'T')
        txt_follows = data.get('txt_follows', 'right')
        # AIToolkit模式参数
        folder_prefix = data.get('folder_prefix', 'aitoolkit')
        txt_folder_follows = data.get('txt_folder_follows', 'right')
        # 导出类型: 'zip' 或 'folder'
        output_type = data.get('output_type', 'zip')

        print(f"[Export] ids={ids}, output_dir={output_dir}, image_format={image_format}, filename={custom_filename}, naming_mode={naming_mode}, output_type={output_type}")

        if not ids:
            return jsonify({"success": False, "message": "未选择成对图片组"}), 400

        selected_pairs = []
        for pair_id in ids:
            pair = pairs_data.get(pair_id)
            if not pair:
                continue
            left_path = (pair.get('left') or {}).get('path')
            right_path = (pair.get('right') or {}).get('path')
            # T2itrainer和AIToolkit模式允许只有原图1
            if naming_mode in ['t2itrainer', 'aitoolkit']:
                if not left_path or not os.path.exists(left_path):
                    continue
            else:
                if not left_path or not right_path:
                    continue
                if not os.path.exists(left_path) or not os.path.exists(right_path):
                    continue
            selected_pairs.append(pair)
        print(f"[Export] selected_pairs count={len(selected_pairs)}")

        if not selected_pairs:
            return jsonify({"success": False, "message": "没有有效的成对图片组"}), 400

        # 构建输出路径
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if custom_filename:
            # 使用自定义文件名，移除可能的.zip后缀
            if custom_filename.lower().endswith('.zip'):
                custom_filename = custom_filename[:-4]
            base_name = custom_filename
        else:
            base_name = f"training_dataset_{timestamp}"
        
        # 根据命名模式选择导出方法
        naming_config = {
            'mode': naming_mode,
            'suffix_left': suffix_left,
            'suffix_left2': suffix_left2,
            'suffix_right': suffix_right,
            'txt_follows': txt_follows,
            'folder_prefix': folder_prefix,
            'txt_folder_follows': txt_folder_follows
        }
        
        if output_type == 'folder':
            # 导出到文件夹
            if output_dir and os.path.isdir(output_dir):
                folder_path = os.path.join(output_dir, base_name)
            else:
                folder_path = base_name
            print(f"[Export] folder_path={folder_path}")
            result_path = ImageProcessor.export_pairs_to_folder(selected_pairs, folder_path, image_format, naming_config)
        else:
            # 导出到zip
            zip_filename = f"{base_name}.zip"
            if output_dir and os.path.isdir(output_dir):
                zip_path = os.path.join(output_dir, zip_filename)
            else:
                zip_path = zip_filename
            print(f"[Export] zip_path={zip_path}")
            result_path = ImageProcessor.export_pairs_to_zip(selected_pairs, zip_path, image_format, naming_config)

        # 自动备份到 training_datas 文件夹
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            training_folder = os.path.join(base_dir, 'training_datas')
            os.makedirs(training_folder, exist_ok=True)
            
            if output_type == 'folder':
                # 备份文件夹
                backup_folder = os.path.join(training_folder, base_name)
                if os.path.exists(backup_folder):
                    import shutil
                    shutil.rmtree(backup_folder)
                import shutil
                shutil.copytree(result_path, backup_folder)
                print(f"[Export] Backup folder created: {backup_folder}")
            else:
                # 备份zip文件
                backup_zip = os.path.join(training_folder, f"{base_name}.zip")
                import shutil
                shutil.copy2(result_path, backup_zip)
                print(f"[Export] Backup zip created: {backup_zip}")
        except Exception as backup_error:
            print(f"[Export] Backup failed: {backup_error}")

        return jsonify({
            "success": True,
            "message": f"已导出 {len(selected_pairs)} 组图片",
            "file": result_path
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/pairs/tag/<pair_id>', methods=['POST'])
def tag_single_pair(pair_id):
    """单个pair反推提示词"""
    if pair_id not in pairs_data:
        return jsonify({"success": False, "message": "成对图片组不存在"}), 404
    
    try:
        apikey_config = load_apikey_config()
        config = load_config()
        provider = apikey_config['current_provider']
        api_key = apikey_config['providers'][provider]['api_key']
        base_url = apikey_config['providers'][provider]['base_url']
        model = apikey_config.get('model', 'Qwen/Qwen2.5-VL-72B-Instruct')
        
        if not api_key:
            return jsonify({"success": False, "message": "请先配置 API Key"}), 400
        
        pair = pairs_data[pair_id]
        
        # 获取原图和目标图路径
        left_path = pair.get('left', {}).get('path') if pair.get('left') else None
        right_path = pair.get('right', {}).get('path') if pair.get('right') else None
        
        if not left_path and not right_path:
            return jsonify({"success": False, "message": "请先选择图片"}), 400
        
        system_prompt, user_prompt = _get_selected_prompts(config, 'editing')
        
        # 使用原图进行反推（如果有目标图，可以同时发送两张图）
        image_path = left_path or right_path
        
        result = APIHandler.call_vision_api(
            image_path, system_prompt, user_prompt, api_key, base_url, model
        )
        
        pairs_data[pair_id]['text'] = result
        pairs_data[pair_id]['status'] = 'success'
        
        return jsonify({
            "success": True,
            "text": result,
            "pair": pairs_data[pair_id]
        })
    except Exception as e:
        pairs_data[pair_id]['status'] = 'error'
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/pairs/tag', methods=['POST'])
def tag_batch_pairs():
    """批量反推pairs提示词"""
    try:
        data = request.get_json(silent=True) or {}
        ids = data.get('ids', [])
        
        if not ids:
            return jsonify({"success": False, "message": "未选择成对图片组"}), 400
        
        apikey_config = load_apikey_config()
        config = load_config()
        provider = apikey_config['current_provider']
        api_key = apikey_config['providers'][provider]['api_key']
        
        if not api_key:
            return jsonify({"success": False, "message": "请先配置 API Key"}), 400
        
        task_id = str(uuid.uuid4())
        processing_tasks[task_id] = {
            "status": "processing",
            "type": "pairs",
            "total": len(ids),
            "completed": 0,
            "failed": 0,
            "current_index": 0,
            "current_id": None,
            "current_name": "",
            "cancel_requested": False
        }
        
        def process_batch():
            base_url = apikey_config['providers'][provider]['base_url']
            model = apikey_config.get('model', 'Qwen/Qwen2.5-VL-72B-Instruct')
            system_prompt, user_prompt = _get_selected_prompts(config, 'editing')
            
            for idx, pair_id in enumerate(ids, start=1):
                if processing_tasks.get(task_id, {}).get('cancel_requested'):
                    processing_tasks[task_id]['status'] = 'cancelled'
                    break
                if pair_id not in pairs_data:
                    continue
                
                pair = pairs_data[pair_id]
                pairs_data[pair_id]['status'] = 'processing'

                left_name = (pair.get('left') or {}).get('name')
                right_name = (pair.get('right') or {}).get('name')
                display_name = left_name or right_name or pair_id
                processing_tasks[task_id]['current_index'] = idx
                processing_tasks[task_id]['current_id'] = pair_id
                processing_tasks[task_id]['current_name'] = display_name
                
                # 获取图片路径
                left_path = pair.get('left', {}).get('path') if pair.get('left') else None
                right_path = pair.get('right', {}).get('path') if pair.get('right') else None
                image_path = left_path or right_path
                
                if not image_path:
                    processing_tasks[task_id]['failed'] += 1
                    continue
                
                try:
                    result = APIHandler.call_vision_api(
                        image_path, system_prompt, user_prompt, api_key, base_url, model
                    )
                    pairs_data[pair_id]['text'] = result
                    pairs_data[pair_id]['status'] = 'success'
                    processing_tasks[task_id]['completed'] += 1
                except Exception as e:
                    print(f"Failed to process pair {pair_id}: {e}")
                    pairs_data[pair_id]['status'] = 'error'
                    processing_tasks[task_id]['failed'] += 1
            
            processing_tasks[task_id]['status'] = 'completed'
            if processing_tasks[task_id]['cancel_requested']:
                processing_tasks[task_id]['status'] = 'cancelled'
            processing_tasks[task_id]['current_id'] = None
            processing_tasks[task_id]['current_name'] = ""
        
        thread = threading.Thread(target=process_batch, daemon=True)
        thread.start()
        
        return jsonify({
            "success": True,
            "task_id": task_id,
            "message": f"开始处理 {len(ids)} 组图片"
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/translate', methods=['POST'])
def translate_text():
    """翻译文本"""
    try:
        data = request.get_json(silent=True) or {}
        text = data.get('text', '')
        
        if not text:
            return jsonify({"success": False, "message": "请输入要翻译的文本"}), 400
        
        apikey_config = load_apikey_config()
        provider = apikey_config['current_provider']
        api_key = apikey_config['providers'][provider]['api_key']
        base_url = apikey_config['providers'][provider]['base_url']
        model = apikey_config.get('model', 'Qwen/Qwen2.5-VL-72B-Instruct')
        
        if not api_key:
            return jsonify({"success": False, "message": "请先配置 API Key"}), 400
        
        # 使用API进行翻译
        translated = APIHandler.translate_text(text, api_key, base_url, model)
        
        return jsonify({
            "success": True,
            "translated": translated
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/images', methods=['GET'])
def get_images():
    """获取所有图片"""
    return jsonify({
        "success": True,
        "images": list(images_data.values())
    })


@app.route('/api/images/<img_id>', methods=['GET'])
def get_image(img_id):
    """获取单张图片信息"""
    if img_id not in images_data:
        return jsonify({"success": False, "message": "图片不存在"}), 404
    
    return jsonify({
        "success": True,
        "image": images_data[img_id]
    })


@app.route('/api/file/image', methods=['GET'])
def serve_image_file():
    """提供原图文件访问"""
    from flask import send_file
    try:
        file_path = request.args.get('path', '')
        if not file_path or not os.path.exists(file_path):
            return jsonify({"success": False, "message": "文件不存在"}), 404
        
        # 安全检查：只允许访问图片文件
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp']:
            return jsonify({"success": False, "message": "不支持的文件类型"}), 400
        
        return send_file(file_path)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/images/<img_id>', methods=['PUT'])
def update_image(img_id):
    """更新图片信息"""
    if img_id not in images_data:
        return jsonify({"success": False, "message": "图片不存在"}), 404
    
    try:
        data = request.get_json(silent=True) or {}
        if 'text' in data:
            images_data[img_id]['text'] = data['text']
            images_data[img_id]['status'] = 'success'
        if 'selected' in data:
            images_data[img_id]['selected'] = data['selected']
        
        return jsonify({
            "success": True,
            "image": images_data[img_id]
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/images/<img_id>', methods=['DELETE'])
def delete_image(img_id):
    """删除图片"""
    if img_id not in images_data:
        return jsonify({"success": False, "message": "图片不存在"}), 404
    
    del images_data[img_id]
    return jsonify({"success": True, "message": "删除成功"})


@app.route('/api/images/tag/<img_id>', methods=['POST'])
def tag_single_image(img_id):
    """单图打标"""
    if img_id not in images_data:
        return jsonify({"success": False, "message": "图片不存在"}), 404
    
    try:
        apikey_config = load_apikey_config()
        config = load_config()
        data = request.get_json(silent=True) or {}
        
        provider = apikey_config['current_provider']
        api_key = apikey_config['providers'][provider]['api_key']
        base_url = apikey_config['providers'][provider]['base_url']
        model = apikey_config.get('model', 'Qwen/Qwen2.5-VL-72B-Instruct')
        cfg_system, cfg_user = _get_selected_prompts(config, 'tagging')
        system_prompt = data.get('system_prompt', cfg_system)
        user_prompt = data.get('user_prompt', cfg_user)
        
        if not api_key:
            return jsonify({"success": False, "message": "请先配置 API Key"}), 400
        
        image_path = images_data[img_id]['path']
        
        result = APIHandler.call_vision_api(
            image_path, system_prompt, user_prompt, api_key, base_url, model
        )
        
        images_data[img_id]['text'] = result
        images_data[img_id]['status'] = 'success'
        
        return jsonify({
            "success": True,
            "text": result,
            "image": images_data[img_id]
        })
    except Exception as e:
        print(f"tag_single_image failed: {e}")
        print(traceback.format_exc())
        images_data[img_id]['status'] = 'error'
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/images/tag', methods=['POST'])
def tag_batch_images():
    """批量打标"""
    try:
        data = request.get_json(silent=True) or {}
        ids = data.get('ids', [])
        
        if not ids:
            return jsonify({"success": False, "message": "未选择图片"}), 400
        
        apikey_config = load_apikey_config()
        config = load_config()
        provider = apikey_config['current_provider']
        api_key = apikey_config['providers'][provider]['api_key']
        
        if not api_key:
            return jsonify({"success": False, "message": "请先配置 API Key"}), 400
        
        task_id = str(uuid.uuid4())
        processing_tasks[task_id] = {
            "status": "processing",
            "type": "images",
            "total": len(ids),
            "completed": 0,
            "failed": 0,
            "current_index": 0,
            "current_id": None,
            "current_name": "",
            "cancel_requested": False
        }
        
        def process_batch():
            base_url = apikey_config['providers'][provider]['base_url']
            model = apikey_config.get('model', 'Qwen/Qwen2.5-VL-72B-Instruct')
            system_prompt, user_prompt = _get_selected_prompts(config, 'tagging')
            
            for idx, img_id in enumerate(ids, start=1):
                if processing_tasks.get(task_id, {}).get('cancel_requested'):
                    processing_tasks[task_id]['status'] = 'cancelled'
                    break
                if img_id not in images_data:
                    continue
                
                images_data[img_id]['status'] = 'processing'
                processing_tasks[task_id]['current_index'] = idx
                processing_tasks[task_id]['current_id'] = img_id
                processing_tasks[task_id]['current_name'] = images_data[img_id].get('name') or img_id
                
                try:
                    result = APIHandler.call_vision_api(
                        images_data[img_id]['path'],
                        system_prompt, user_prompt, api_key, base_url, model
                    )
                    images_data[img_id]['text'] = result
                    images_data[img_id]['status'] = 'success'
                    processing_tasks[task_id]['completed'] += 1
                except Exception as e:
                    print(f"Failed to process {img_id}: {e}")
                    images_data[img_id]['status'] = 'error'
                    processing_tasks[task_id]['failed'] += 1
            
            if not processing_tasks.get(task_id, {}).get('cancel_requested') and processing_tasks.get(task_id, {}).get('status') != 'cancelled':
                processing_tasks[task_id]['status'] = 'completed'
            processing_tasks[task_id]['current_id'] = None
            processing_tasks[task_id]['current_name'] = ""
        
        thread = threading.Thread(target=process_batch, daemon=True)
        thread.start()
        
        return jsonify({
            "success": True,
            "task_id": task_id,
            "message": f"开始处理 {len(ids)} 张图片"
        })
    except Exception as e:
        print(f"tag_batch_images failed: {e}")
        print(traceback.format_exc())
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """获取任务状态"""
    if task_id not in processing_tasks:
        return jsonify({"success": False, "message": "任务不存在"}), 404
    
    return jsonify({
        "success": True,
        "task": processing_tasks[task_id]
    })


@app.route('/api/tasks/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    """取消任务"""
    if task_id not in processing_tasks:
        return jsonify({"success": False, "message": "任务不存在"}), 404

    task = processing_tasks[task_id]
    if task.get('status') in ('completed', 'cancelled'):
        return jsonify({"success": True, "message": "任务已结束"})

    task['cancel_requested'] = True
    return jsonify({"success": True, "message": "已请求取消"})


@app.route('/api/batch/rename', methods=['POST'])
def batch_rename():
    """批量重命名"""
    try:
        data = request.get_json(silent=True) or {}
        ids = data.get('ids', [])
        prefix = data.get('prefix', 'image')
        
        count = ImageProcessor.batch_rename(images_data, ids, prefix)
        
        return jsonify({
            "success": True,
            "message": f"已重命名 {count} 张图片",
            "count": count
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/batch/add-text', methods=['POST'])
def batch_add_text():
    """批量添加文本"""
    try:
        data = request.get_json(silent=True) or {}
        ids = data.get('ids', [])
        text = data.get('text', '')
        position = data.get('position', 'prefix')
        
        count = ImageProcessor.batch_add_text(images_data, ids, text, position)
        
        return jsonify({
            "success": True,
            "message": f"已为 {count} 张图片添加文本",
            "count": count
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/batch/clear-text', methods=['POST'])
def batch_clear_text():
    """批量清空文本"""
    try:
        data = request.get_json(silent=True) or {}
        ids = data.get('ids', [])
        
        count = ImageProcessor.batch_clear_text(images_data, ids)
        
        return jsonify({
            "success": True,
            "message": f"已清空 {count} 张图片的文本",
            "count": count
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/batch/resize', methods=['POST'])
def batch_resize():
    """批量设置裁切"""
    try:
        data = request.get_json(silent=True) or {}
        ids = data.get('ids', [])
        max_size = data.get('max_size', 1024)
        
        count = ImageProcessor.batch_set_resize(images_data, ids, max_size)
        
        return jsonify({
            "success": True,
            "message": f"已为 {count} 张图片设置裁切",
            "count": count
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/select-folder', methods=['POST'])
def select_folder():
    """选择文件夹并加载图片"""
    try:
        data = request.get_json(silent=True) or {}
        folder_path = data.get('path', '')
        
        if not os.path.exists(folder_path):
            return jsonify({"success": False, "message": "文件夹不存在"}), 400
        
        image_paths = []
        for root, _, files in os.walk(folder_path):
            for filename in files:
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    image_paths.append(os.path.join(root, filename))
        
        added = 0
        for path in image_paths:
            if any(img['path'] == path for img in images_data.values()):
                continue
            
            img_info = ImageProcessor.load_image_with_txt(path)
            if img_info:
                img_id = str(uuid.uuid4())
                img_info['id'] = img_id
                images_data[img_id] = img_info
                added += 1
        
        return jsonify({
            "success": True,
            "added": added,
            "total": len(images_data),
            "images": list(images_data.values())
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/analyzer/parse', methods=['POST'])
def analyze_log():
    """分析训练日志文件"""
    if not TRAINING_ANALYZER_AVAILABLE:
        return jsonify({"success": False, "message": "训练分析器模块未加载"}), 500
    
    try:
        data = request.get_json(silent=True) or {}
        log_path = data.get('path', '')
        
        if not log_path or not os.path.exists(log_path):
            return jsonify({"success": False, "message": "日志文件不存在"}), 400
        
        result = parse_log_file(log_path)
        if not result:
            return jsonify({"success": False, "message": "日志解析失败，请检查文件格式"}), 400
        
        # 检查是否有多次训练
        if result.get('training_sessions'):
            sessions = result['training_sessions']
            if not any(session['val_losses'] for session in sessions):
                return jsonify({"success": False, "message": "日志中未找到有效的val_loss数据"}), 400
            
            # 保存每个训练会话
            saved_ids = []
            for session in sessions:
                if session['val_losses']:
                    session_result = {
                        'val_losses': session['val_losses'],
                        'config': session['config'],
                        'statistics': session['statistics'],
                        'log_file_path': result['log_file_path'],
                    }
                    record_id = save_record(session_result)
                    saved_ids.append(record_id)
            
            return jsonify({
                "success": True,
                "multiple_sessions": True,
                "total_sessions": len(sessions),
                "sessions": sessions,
                "saved_ids": saved_ids,
                "log_file_path": result['log_file_path']
            })
        else:
            if not result.get('val_losses'):
                return jsonify({"success": False, "message": "日志中未找到有效的val_loss数据"}), 400
            
            record_id = save_record(result)
            
            return jsonify({
                "success": True,
                "multiple_sessions": False,
                "val_losses": result['val_losses'],
                "config": result['config'],
                "statistics": result['statistics'],
                "record_id": record_id,
                "log_file_path": result['log_file_path']
            })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/analyzer/records', methods=['GET'])
def get_analyzer_records():
    """获取历史分析记录"""
    if not TRAINING_ANALYZER_AVAILABLE:
        return jsonify({"success": False, "message": "训练分析器模块未加载"}), 500
    
    try:
        summaries = get_records_summary()
        return jsonify({
            "success": True,
            "records": summaries
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/analyzer/records/<record_id>', methods=['GET'])
def get_analyzer_record(record_id):
    """获取单条记录详情"""
    if not TRAINING_ANALYZER_AVAILABLE:
        return jsonify({"success": False, "message": "训练分析器模块未加载"}), 500
    
    try:
        record = get_record_by_id(record_id)
        if not record:
            return jsonify({"success": False, "message": "记录不存在"}), 404
        
        return jsonify({
            "success": True,
            "record": record
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/analyzer/records/<record_id>', methods=['DELETE'])
def delete_analyzer_record(record_id):
    """删除分析记录"""
    if not TRAINING_ANALYZER_AVAILABLE:
        return jsonify({"success": False, "message": "训练分析器模块未加载"}), 500
    
    try:
        if delete_record(record_id):
            return jsonify({"success": True, "message": "记录已删除"})
        else:
            return jsonify({"success": False, "message": "删除失败"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/analyzer/pending-logs', methods=['GET'])
def get_pending_log_files():
    """获取待分析的日志文件列表"""
    if not TRAINING_ANALYZER_AVAILABLE:
        return jsonify({"success": False, "message": "训练分析器模块未加载"}), 500
    
    try:
        logs = get_pending_logs()
        files = []
        for log_path in logs:
            try:
                stat = os.stat(log_path)
                files.append({
                    'path': log_path,
                    'name': os.path.basename(log_path),
                    'size': stat.st_size,
                    'mtime': stat.st_mtime
                })
            except:
                pass
        return jsonify({"success": True, "files": files})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/analyzer/upload', methods=['POST'])
def upload_log_file():
    """上传日志文件到待分析目录"""
    if not TRAINING_ANALYZER_AVAILABLE:
        return jsonify({"success": False, "message": "训练分析器模块未加载"}), 500
    
    try:
        # 支持两种方式：文件上传或路径复制
        if 'file' in request.files:
            file = request.files['file']
            if file.filename:
                from training_analyzer.config import TRAINING_LOG_DIR
                dest_path = os.path.join(TRAINING_LOG_DIR, file.filename)
                file.save(dest_path)
                return jsonify({"success": True, "path": dest_path, "name": file.filename})
        
        data = request.get_json(silent=True) or {}
        source_path = data.get('path', '')
        
        if source_path and os.path.exists(source_path):
            dest_path = copy_to_log_dir(source_path)
            if dest_path:
                return jsonify({"success": True, "path": dest_path, "name": os.path.basename(dest_path)})
            else:
                return jsonify({"success": False, "message": "复制文件失败"}), 400
        
        return jsonify({"success": False, "message": "未提供有效的文件"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/analyzer/analyze-and-move', methods=['POST'])
def analyze_and_move_log():
    """分析日志并移动到历史目录"""
    if not TRAINING_ANALYZER_AVAILABLE:
        return jsonify({"success": False, "message": "训练分析器模块未加载"}), 500
    
    try:
        data = request.get_json(silent=True) or {}
        log_path = data.get('path', '')
        
        if not log_path or not os.path.exists(log_path):
            return jsonify({"success": False, "message": "日志文件不存在"}), 400
        
        # 解析日志
        result = parse_log_file(log_path)
        if not result:
            return jsonify({"success": False, "message": "日志解析失败"}), 400
        
        # 保存记录
        saved_ids = []
        if result.get('training_sessions'):
            for session in result['training_sessions']:
                if session['val_losses']:
                    session_result = {
                        'val_losses': session['val_losses'],
                        'config': session['config'],
                        'statistics': session['statistics'],
                        'log_file_path': log_path,
                    }
                    record_id = save_record(session_result)
                    saved_ids.append(record_id)
        elif result.get('val_losses'):
            record_id = save_record(result)
            saved_ids.append(record_id)
        
        # 移动到历史目录
        history_path = move_to_history(log_path)
        
        return jsonify({
            "success": True,
            "result": result,
            "saved_ids": saved_ids,
            "history_path": history_path
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/analyzer/delete-pending', methods=['POST'])
def delete_pending_log():
    """删除待分析的日志文件"""
    if not TRAINING_ANALYZER_AVAILABLE:
        return jsonify({"success": False, "message": "训练分析器模块未加载"}), 500
    
    try:
        data = request.get_json(silent=True) or {}
        log_path = data.get('path', '')
        
        if log_path and os.path.exists(log_path):
            os.remove(log_path)
            return jsonify({"success": True, "message": "文件已删除"})
        return jsonify({"success": False, "message": "文件不存在"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/system/select-files', methods=['POST'])
def system_select_files():
    """打开系统原生文件选择对话框"""
    try:
        data = request.get_json(silent=True) or {}
        file_type = data.get('type', 'image')  # 'image' or 'log'
        allow_multiple = data.get('multiple', True)
        
        root = get_tk_root()
        if not root:
            return jsonify({"success": False, "message": "无法初始化文件对话框"}), 500
        
        if file_type == 'log':
            filetypes = [('Log Files', '*.log;*.txt;*.json'), ('All Files', '*.*')]
        else:
            filetypes = [('Image Files', '*.jpg;*.jpeg;*.png;*.webp'), ('All Files', '*.*')]
            
        if allow_multiple:
            paths = filedialog.askopenfilenames(
                title='选择文件',
                filetypes=filetypes,
                parent=root
            )
        else:
            path = filedialog.askopenfilename(
                title='选择文件',
                filetypes=filetypes,
                parent=root
            )
            paths = [path] if path else []
            
        root.destroy()
        
        return jsonify({
            "success": True,
            "paths": list(paths) if paths else []
        })
    except Exception as e:
        if 'root' in locals() and root:
            root.destroy()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/system/select-folder', methods=['POST'])
def system_select_folder():
    """打开系统原生文件夹选择对话框"""
    try:
        root = get_tk_root()
        if not root:
            return jsonify({"success": False, "message": "无法初始化文件对话框"}), 500
            
        path = filedialog.askdirectory(
            title='选择文件夹',
            parent=root
        )
        
        root.destroy()
        
        return jsonify({
            "success": True,
            "path": path if path else None
        })
    except Exception as e:
        if 'root' in locals() and root:
            root.destroy()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/system/open-training-folder', methods=['POST'])
def system_open_training_folder():
    """打开training_datas文件夹"""
    try:
        # 获取项目根目录下的training_datas文件夹
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        training_folder = os.path.join(base_dir, 'training_datas')
        
        # 确保文件夹存在
        os.makedirs(training_folder, exist_ok=True)
        
        # 打开文件夹
        os.startfile(training_folder)
        
        return jsonify({"success": True, "path": training_folder})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/system/open-folder', methods=['POST'])
def system_open_folder():
    """打开文件所在文件夹"""
    try:
        data = request.get_json(silent=True) or {}
        file_path = data.get('path', '')
        
        if not file_path:
            return jsonify({"success": False, "message": "未指定文件路径"}), 400
        
        # 获取文件所在目录
        if os.path.isfile(file_path):
            folder_path = os.path.dirname(file_path)
        else:
            folder_path = file_path
        
        if not os.path.exists(folder_path):
            return jsonify({"success": False, "message": "目录不存在"}), 400
        
        # Windows下使用explorer打开文件夹并选中文件
        if os.path.isfile(file_path):
            os.system(f'explorer /select,"{file_path}"')
        else:
            os.startfile(folder_path)
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/system/save-dialog', methods=['POST'])
def system_save_dialog():
    """打开系统原生保存文件对话框"""
    try:
        data = request.get_json(silent=True) or {}
        default_name = data.get('filename', 'config.json')
        
        root = get_tk_root()
        if not root:
            return jsonify({"success": False, "message": "无法初始化文件对话框"}), 500
            
        path = filedialog.asksaveasfilename(
            title='保存文件',
            initialfile=default_name,
            filetypes=[('JSON Files', '*.json'), ('All Files', '*.*')],
            parent=root
        )
        
        root.destroy()
        
        return jsonify({
            "success": True,
            "path": path if path else None
        })
    except Exception as e:
        if 'root' in locals() and root:
            root.destroy()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/system/read-file', methods=['POST'])
def system_read_file():
    """读取文件内容"""
    try:
        data = request.get_json(silent=True) or {}
        path = data.get('path', '')
        
        if not path or not os.path.exists(path):
            return jsonify({"success": False, "message": "文件不存在"}), 400
            
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        return jsonify({
            "success": True,
            "content": content
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/system/write-file', methods=['POST'])
def system_write_file():
    """写入文件内容"""
    try:
        data = request.get_json(silent=True) or {}
        path = data.get('path', '')
        content = data.get('content', '')
        
        if not path:
            return jsonify({"success": False, "message": "路径不能为空"}), 400
            
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return jsonify({
            "success": True,
            "message": "文件保存成功"
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/chat/message', methods=['POST'])
def chat_message():
    """处理聊天消息"""
    try:
        data = request.get_json(silent=True) or {}
        message = data.get('message', '').strip()
        history = data.get('history', [])
        chat_model = data.get('model', '')
        
        if not message:
            return jsonify({"success": False, "message": "消息不能为空"}), 400
        
        # 获取配置
        apikey_config = load_apikey_config()
        current_provider = apikey_config.get('current_provider', 'siliconflow')
        provider_config = apikey_config.get('providers', {}).get(current_provider, {})
        
        api_key = provider_config.get('api_key', '')
        base_url = provider_config.get('base_url', 'https://api.siliconflow.cn/v1')
        
        if not api_key:
            return jsonify({"success": False, "message": "请先配置 API Key"}), 400
        
        # 使用前端传递的模型，如果没有则使用默认文本模型
        text_model = chat_model if chat_model else "Qwen/Qwen2.5-7B-Instruct"
        
        # 构建消息历史
        messages = []
        for msg in history[-10:]:  # 只保留最近10条消息
            messages.append({
                "role": msg.get('role', 'user'),
                "content": msg.get('content', '')
            })
        messages.append({
            "role": "user",
            "content": message
        })
        
        # 调用 API
        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        payload = {
            "model": text_model,
            "messages": messages,
            "max_tokens": 2048,
            "temperature": 0.7
        }
        
        print(f"[Chat] 调用 URL: {url}")
        print(f"[Chat] 模型: {text_model}")
        print(f"[Chat] Provider: {current_provider}")
        
        import requests
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        print(f"[Chat] 响应状态: {resp.status_code}")
        print(f"[Chat] 响应内容: {resp.text[:500] if resp.text else '(empty)'}")
        try:
            resp_json = resp.json()
        except Exception:
            content_type = resp.headers.get('Content-Type', '')
            body_snippet = (resp.text or '')[:800]
            return jsonify({
                "success": False,
                "message": (
                    "上游接口返回非JSON响应，无法解析。"
                    f"HTTP {resp.status_code} | Content-Type: {content_type} | Body: {body_snippet}"
                )
            }), 500
        
        if resp.status_code != 200:
            error_msg = resp_json.get('error', {}).get('message', resp_json.get('message', str(resp_json)))
            return jsonify({"success": False, "message": f"API 错误: {error_msg}"}), 500
        
        if "choices" in resp_json and len(resp_json["choices"]) > 0:
            reply = resp_json["choices"][0]["message"]["content"]
            return jsonify({
                "success": True,
                "reply": reply
            })
        else:
            return jsonify({"success": False, "message": "API 返回格式错误"}), 500
            
    except requests.exceptions.Timeout:
        return jsonify({"success": False, "message": "请求超时，请稍后重试"}), 500
    except Exception as e:
        print(f"Chat error: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/analyzer/ai-analyze', methods=['POST'])
def ai_analyze_training():
    """使用AI分析训练数据并给出优化建议"""
    if not TRAINING_ANALYZER_AVAILABLE:
        return jsonify({"success": False, "message": "训练分析器模块未加载"}), 500
    
    try:
        data = request.get_json(silent=True) or {}
        training_data = data.get('training_data', {})
        api_key = data.get('api_key', '')
        base_url = data.get('base_url', '')
        model = data.get('model', None)
        system_prompt = data.get('system_prompt', None)
        
        if not training_data:
            return jsonify({"success": False, "message": "未提供训练数据"}), 400
        
        if not api_key:
            return jsonify({"success": False, "message": "未提供API密钥，请在设置中配置"}), 400
        
        if not base_url:
            return jsonify({"success": False, "message": "未提供API地址"}), 400
        
        # 调用AI分析
        analysis_result = APIHandler.analyze_training(
            training_data=training_data,
            api_key=api_key,
            base_url=base_url,
            model=model,
            system_prompt=system_prompt
        )
        
        return jsonify({
            "success": True,
            "analysis": analysis_result
        })
    except Exception as e:
        print(f"AI分析错误: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500


# ==================== AI对话历史管理 ====================

CHAT_HISTORY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ai_chat', 'chat_history')
os.makedirs(CHAT_HISTORY_DIR, exist_ok=True)


@app.route('/api/chat/sessions', methods=['GET'])
def get_chat_sessions():
    """获取所有对话会话列表"""
    try:
        sessions = []
        if os.path.exists(CHAT_HISTORY_DIR):
            for filename in os.listdir(CHAT_HISTORY_DIR):
                if filename.endswith('.json'):
                    filepath = os.path.join(CHAT_HISTORY_DIR, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            sessions.append({
                                'id': data.get('id', filename.replace('.json', '')),
                                'title': data.get('title', '未命名对话'),
                                'created_at': data.get('created_at', ''),
                                'updated_at': data.get('updated_at', ''),
                                'message_count': len(data.get('messages', []))
                            })
                    except:
                        pass
        # 按更新时间倒序
        sessions.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
        return jsonify({"success": True, "sessions": sessions})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/chat/session/<session_id>', methods=['GET'])
def get_chat_session(session_id):
    """获取指定会话的完整内容"""
    try:
        filepath = os.path.join(CHAT_HISTORY_DIR, f"{session_id}.json")
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify({"success": True, "session": data})
        return jsonify({"success": False, "message": "会话不存在"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/chat/session', methods=['POST'])
def save_chat_session():
    """保存对话会话"""
    try:
        data = request.get_json(silent=True) or {}
        session_id = data.get('id') or str(uuid.uuid4())[:8]
        messages = data.get('messages', [])
        title = data.get('title', '')
        
        # 自动生成标题（取第一条用户消息的前20个字符）
        if not title and messages:
            for msg in messages:
                if msg.get('role') == 'user':
                    title = msg.get('content', '')[:20]
                    if len(msg.get('content', '')) > 20:
                        title += '...'
                    break
        if not title:
            title = '新对话'
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        session_data = {
            'id': session_id,
            'title': title,
            'messages': messages,
            'created_at': data.get('created_at', now),
            'updated_at': now
        }
        
        filepath = os.path.join(CHAT_HISTORY_DIR, f"{session_id}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({"success": True, "session_id": session_id, "title": title})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/chat/session/<session_id>', methods=['DELETE'])
def delete_chat_session(session_id):
    """删除对话会话"""
    try:
        filepath = os.path.join(CHAT_HISTORY_DIR, f"{session_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
            return jsonify({"success": True})
        return jsonify({"success": False, "message": "会话不存在"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


if __name__ == '__main__':
    print("="*60)
    print("🐼 Pandy AI 工具箱 Web 服务启动中...")
    print("="*60)
    
    # 自动打开浏览器
    def open_browser():
        webbrowser.open('http://localhost:5000')
        
    threading.Timer(1.5, open_browser).start()
    
    print(f"📍 访问地址: http://localhost:5000")
    print(f"📂 前端路径: {app.static_folder}")
    print(f"📊 训练分析器: {'已加载' if TRAINING_ANALYZER_AVAILABLE else '未加载'}")
    print("="*60)
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
