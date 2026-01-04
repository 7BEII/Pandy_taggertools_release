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
import subprocess
import webbrowser
import tkinter as tk
from tkinter import filedialog
from datetime import datetime
import traceback
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from PIL import Image
from api_handler import APIHandler
from image_processor import ImageProcessor
from path_utils import (
    BASE_PATH, RESOURCE_PATH, CONFIG_DIR, CONFIG_FILE, APIKEY_FILE, 
    TEMPLATES_DIR, FRONTEND_DIR, TRAINING_DATA_DIR,
    TRAINING_EDIT_TMP_DIR, ensure_user_dirs, copy_default_configs
)

# 初始化用户目录和默认配置
ensure_user_dirs()
copy_default_configs()

# 添加资源路径，以便导入 training_analyzer
sys.path.insert(0, RESOURCE_PATH)

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

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
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

# 路径常量已从 path_utils 导入
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
                            "file_path": filepath,  # 添加完整文件路径
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
        left2 = (pair.get('left2') or {}).get('path')
        if left == path or right == path or left2 == path:
            return True
    return False


def _get_unique_path(base_path, is_zip=False):
    """
    获取唯一的文件/文件夹路径，如果已存在则添加 _1, _2 等后缀
    
    Args:
        base_path: 基础路径
        is_zip: 是否是zip文件
    
    Returns:
        str: 唯一的路径
    """
    if not os.path.exists(base_path):
        return base_path
    
    # 分离目录、文件名和扩展名
    if is_zip:
        dir_name = os.path.dirname(base_path)
        base_name = os.path.basename(base_path)
        if base_name.lower().endswith('.zip'):
            name_without_ext = base_name[:-4]
            ext = '.zip'
        else:
            name_without_ext = base_name
            ext = ''
    else:
        dir_name = os.path.dirname(base_path)
        name_without_ext = os.path.basename(base_path)
        ext = ''
    
    # 尝试添加后缀直到找到不存在的路径
    counter = 1
    while True:
        new_name = f"{name_without_ext}_{counter}{ext}"
        new_path = os.path.join(dir_name, new_name) if dir_name else new_name
        if not os.path.exists(new_path):
            return new_path


def get_cpu_uuid():
    """尝试跨平台读取机器的 CPU / 产品 UUID"""
    try:
        if sys.platform.startswith('win'):
            # Windows: wmic csproduct get uuid
            try:
                out = subprocess.check_output(['wmic', 'csproduct', 'get', 'uuid'], stderr=subprocess.DEVNULL)
                lines = [l.strip() for l in out.decode(errors='ignore').splitlines() if l.strip()]
                for line in lines:
                    if line.lower() != 'uuid':
                        return line
            except Exception:
                pass
        elif sys.platform.startswith('linux'):
            # Linux: try /sys/class/dmi/id/product_uuid
            try:
                path = '/sys/class/dmi/id/product_uuid'
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        return f.read().strip()
            except Exception:
                pass
            # fallback to machine-id
            try:
                path = '/etc/machine-id'
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        return f.read().strip()
            except Exception:
                pass
        elif sys.platform.startswith('darwin'):
            # macOS
            try:
                out = subprocess.check_output(['ioreg', '-rd1', '-c', 'IOPlatformExpertDevice'], stderr=subprocess.DEVNULL)
                for line in out.decode(errors='ignore').splitlines():
                    if 'IOPlatformUUID' in line:
                        import re
                        m = re.search(r'\"IOPlatformUUID\" = \"(.+)\"', line)
                        if m:
                            return m.group(1)
            except Exception:
                pass

        # 最后回退到 uuid.getnode()
        try:
            return str(uuid.getnode())
        except Exception:
            return None
    except Exception:
        return None
        counter += 1
        # 防止无限循环
        if counter > 1000:
            raise Exception("无法找到唯一的文件名")


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


@app.route('/api/analyzer/count-files', methods=['POST'])
def analyzer_count_files():
    """统计指定目录下的图片/样本数量（用于训练集数量显示）"""
    try:
        data = request.get_json(silent=True) or {}
        path = data.get('path') or data.get('dir') or ''
        if not path:
            return jsonify({"success": False, "message": "未提供路径"}), 400
        if not os.path.exists(path):
            return jsonify({"success": True, "count": 0, "message": "路径不存在"}), 200

        # 统计图片/样本文件（常见扩展名）
        exts = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.txt'}
        count = 0
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for fn in files:
                    if os.path.splitext(fn)[1].lower() in exts:
                        count += 1
        else:
            # 如果给的是单个文件，返回1或0
            if os.path.splitext(path)[1].lower() in exts:
                count = 1

        return jsonify({"success": True, "count": count})
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "count": 0}), 500


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


@app.route('/api/template-file/save', methods=['POST'])
def save_template_file():
    """保存模板文件（通过file_path）"""
    try:
        data = request.get_json(silent=True) or {}
        file_path = data.get('file_path', '')
        system_prompt = data.get('system_prompt', '')
        user_prompt = data.get('user_prompt', '')
        
        if not file_path:
            return jsonify({"success": False, "message": "缺少文件路径"}), 400
        
        # 确保文件路径在配置目录内
        if not os.path.exists(file_path):
            return jsonify({"success": False, "message": "模板文件不存在"}), 404
        
        # 读取现有模板
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                template_data = json.load(f)
        except:
            template_data = {}
        
        # 更新提示词
        template_data['system_prompt'] = system_prompt
        template_data['user_prompt'] = user_prompt
        
        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(template_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({"success": True, "message": "模板已保存"})
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


@app.route('/api/images/upload-drop', methods=['POST'])
def upload_images_drop():
    """处理拖拽上传的图片和文本文件"""
    try:
        # 获取上传的图片文件
        image_files = request.files.getlist('images')
        text_files = request.files.getlist('texts')
        text_matches = request.form.getlist('text_matches')
        
        if not image_files:
            return jsonify({"success": False, "message": "未找到图片文件"}), 400
        
        # 使用 training_datas/input_datas_image 目录保存上传的文件
        upload_dir = os.path.join(TRAINING_DATA_DIR, 'input_datas_image')
        os.makedirs(upload_dir, exist_ok=True)
        
        # 构建文本文件映射 (baseName -> content)
        text_content_map = {}
        for i, txt_file in enumerate(text_files):
            if i < len(text_matches):
                base_name = text_matches[i].lower()
                text_content_map[base_name] = txt_file.read().decode('utf-8', errors='ignore')
        
        added = 0
        matched = 0
        
        for img_file in image_files:
            # 保存图片到上传目录
            img_filename = img_file.filename
            img_path = os.path.join(upload_dir, img_filename)
            
            # 如果文件已存在，直接覆盖（以最新导入为主）
            # 同时清理内存中对应的旧数据
            if os.path.exists(img_path):
                # 查找并删除内存中的旧记录
                old_ids = [img_id for img_id, img in images_data.items() if img['path'] == img_path]
                for old_id in old_ids:
                    del images_data[old_id]
            
            img_file.save(img_path)
            
            # 加载图片信息
            img_info = ImageProcessor.load_image_with_txt(img_path)
            if img_info:
                img_id = str(uuid.uuid4())
                img_info['id'] = img_id
                
                # 检查是否有匹配的文本
                base_name = os.path.splitext(img_file.filename)[0].lower()
                if base_name in text_content_map:
                    img_info['text'] = text_content_map[base_name]
                    img_info['status'] = 'success'
                    matched += 1
                
                images_data[img_id] = img_info
                added += 1
        
        return jsonify({
            "success": True,
            "added": added,
            "matched": matched,
            "total": len(images_data),
            "images": list(images_data.values())
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
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
        left2_path = data.get('left2_path')
        right_path = data.get('right_path')

        if left_path is not None:
            if left_path and os.path.exists(left_path) and not _pair_contains_path(left_path, exclude_pair_id=pair_id):
                pair['left'] = _build_pair_side_info(left_path)
            elif not left_path:
                pair['left'] = None

        if left2_path is not None:
            if left2_path and os.path.exists(left2_path) and not _pair_contains_path(left2_path, exclude_pair_id=pair_id):
                pair['left2'] = _build_pair_side_info(left2_path)
            elif not left2_path:
                pair['left2'] = None

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
        elif side == 'left2':
            pair['left2'] = side_info
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
        left2_suffix = data.get('left2_suffix', 'g').strip().lower()
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
        elif False:  # 旧的match模式已废弃，保留代码以备参考
            # 规则匹配模式
            grouped = {}
            
            # 构建动态正则匹配规则
            l_pat = re.escape(left_suffix)
            r_pat = re.escape(right_suffix)
            pattern = re.compile(f"^(.*?)(?:[-_ ]?)({l_pat}|{r_pat})$", re.IGNORECASE)

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

        elif import_mode == 'manual':
            # 手动导入模式：将文件夹中每张图片作为单独组，放到指定的一侧（left/left2/right）
            manual_side = (data.get('manual_side') or 'left').lower()

            for orig_path in image_files:
                left_path = None
                left2_path = None
                right_path = None

                copied = copied_files.get(orig_path, orig_path)
                if manual_side == 'left':
                    left_path = copied
                elif manual_side == 'left2':
                    left2_path = copied
                else:
                    right_path = copied

                if _pair_contains_path(left_path) or _pair_contains_path(left2_path) or _pair_contains_path(right_path):
                    continue

                pair_id = str(uuid.uuid4())
                left_side = _build_pair_side_info(left_path) if left_path else None
                # left2 stored as separate key in pair dict if present
                left2_side = _build_pair_side_info(left2_path) if left2_path else None
                right_side = _build_pair_side_info(right_path) if right_path else None

                # 尝试查找同名txt（优先使用对应侧的同名txt）
                pair_text = ""
                if manual_side == 'left' and left_path:
                    stem = os.path.splitext(os.path.basename(left_path))[0].lower()
                    if stem in txt_files:
                        try:
                            with open(txt_files[stem], 'r', encoding='utf-8') as f:
                                pair_text = f.read().strip()
                        except:
                            pass
                elif manual_side == 'left2' and left2_path:
                    stem = os.path.splitext(os.path.basename(left2_path))[0].lower()
                    if stem in txt_files:
                        try:
                            with open(txt_files[stem], 'r', encoding='utf-8') as f:
                                pair_text = f.read().strip()
                        except:
                            pass
                elif manual_side == 'right' and right_path:
                    stem = os.path.splitext(os.path.basename(right_path))[0].lower()
                    if stem in txt_files:
                        try:
                            with open(txt_files[stem], 'r', encoding='utf-8') as f:
                                pair_text = f.read().strip()
                        except:
                            pass

                if not pair_text:
                    pair_text = _get_pair_text(left_side, right_side)

                pair_info = {
                    "id": pair_id,
                    "left": left_side,
                    "left2": left2_side,
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

        # 原来的 match 分支继续在这里（保留）
        else:
            # 规则匹配模式
            grouped = {}
            
            # 构建动态正则匹配规则（支持 left / left2 / right 三个标识，前缀或后缀）
            l_pat = re.escape(left_suffix)
            l2_pat = re.escape(left2_suffix)
            r_pat = re.escape(right_suffix)
            pattern = re.compile(f"^(.*?)(?:[-_ ]?)({l_pat}|{l2_pat}|{r_pat})$", re.IGNORECASE)

            for path in image_files:
                stem = os.path.splitext(os.path.basename(path))[0]
                
                m = pattern.match(stem)
                if not m:
                    continue

                base = m.group(1)
                tag = m.group(2).lower()

                # 识别是 left / left2 / right
                if tag == left_suffix:
                    side = 'left'
                elif tag == left2_suffix:
                    side = 'left2'
                else:
                    side = 'right'

                if base not in grouped:
                    grouped[base] = {"left": None, "left2": None, "right": None, "base": base}
                grouped[base][side] = path

            for base, lr in grouped.items():
                orig_left_path = lr.get('left')
                orig_left2_path = lr.get('left2')
                orig_right_path = lr.get('right')

                if not orig_left_path and not orig_left2_path and not orig_right_path:
                    continue

                # 使用复制后的本地路径
                left_path = copied_files.get(orig_left_path, orig_left_path) if orig_left_path else None
                left2_path = copied_files.get(orig_left2_path, orig_left2_path) if orig_left2_path else None
                right_path = copied_files.get(orig_right_path, orig_right_path) if orig_right_path else None

                if _pair_contains_path(left_path) or _pair_contains_path(left2_path) or _pair_contains_path(right_path):
                    continue

                pair_id = str(uuid.uuid4())
                left_side = _build_pair_side_info(left_path) if left_path else None
                left2_side = _build_pair_side_info(left2_path) if left2_path else None
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
                
                # 如果没找到，尝试用base名查找（尝试 left/left2/right 后缀）
                if not pair_text:
                    base_lower = base.lower()
                    for try_suffix in [left_suffix, left2_suffix, right_suffix]:
                        if not try_suffix:
                            continue
                        txt_key = f"{base_lower}_{try_suffix}"
                        if txt_key in txt_files:
                            try:
                                with open(txt_files[txt_key], 'r', encoding='utf-8') as f:
                                    pair_text = f.read().strip()
                                break
                            except:
                                pass
                
                if not pair_text:
                    pair_text = _get_pair_text(left_side, right_side)
                
                pair_info = {
                    "id": pair_id,
                    "left": left_side,
                    "left2": left2_side,
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
        # RuningHub模式参数
        runinghub_start = data.get('runinghub_start', 'start')
        runinghub_end = data.get('runinghub_end', 'end')
        # 导出类型: 'zip' 或 'folder'
        output_type = data.get('output_type', 'zip')
        # 过滤导出（可选）：关键字与文件类型 ('png','txt','both')
        filter_keyword = (data.get('filter_keyword') or '').strip()
        filter_file_type = data.get('filter_file_type', 'both')  # 'png' | 'txt' | 'both'

        print(f"[Export] ids={ids}, output_dir={output_dir}, image_format={image_format}, filename={custom_filename}, naming_mode={naming_mode}, output_type={output_type}")

        if not ids:
            return jsonify({"success": False, "message": "未选择成对图片组"}), 400

        selected_pairs = []
        for pair_id in ids:
            pair = pairs_data.get(pair_id)
            if not pair:
                continue
            left_path = (pair.get('left') or {}).get('path')
            left2_path = (pair.get('left2') or {}).get('path')
            right_path = (pair.get('right') or {}).get('path')

            exists_left = bool(left_path and os.path.exists(left_path))
            exists_left2 = bool(left2_path and os.path.exists(left2_path))
            exists_right = bool(right_path and os.path.exists(right_path))

            # 宽松策略：只要有任意一张存在就认为有效组，针对特定命名模式可以有额外要求
            if naming_mode in ['t2itrainer', 'aitoolkit']:
                # T2itrainer/AIToolkit 允许只有原图存在，接受 left 或 left2 或 right 中任意存在
                if not (exists_left or exists_left2 or exists_right):
                    continue
            elif naming_mode == 'runinghub':
                # RuningHub 需要至少有一张原图或目标图
                if not (exists_left or exists_right or exists_left2):
                    continue
            else:
                # 默认模式：至少包含一张图片（兼容只有 left2 的情况）
                if not (exists_left or exists_left2 or exists_right):
                    continue

            selected_pairs.append(pair)
        print(f"[Export] selected_pairs count={len(selected_pairs)}")
        # Debug: 打印每个被选中 pair 的路径信息，帮助定位导出为空的问题
        try:
            print("[Export] Selected pairs detail:")
            for pair in selected_pairs:
                pid = pair.get("id")
                l = (pair.get('left') or {}).get('path')
                l2 = (pair.get('left2') or {}).get('path')
                r = (pair.get('right') or {}).get('path')
                print(f"  - pair_id={pid}")
                print(f"    left:  {l}  exists={os.path.exists(l) if l else False}")
                print(f"    left2: {l2}  exists={os.path.exists(l2) if l2 else False}")
                print(f"    right: {r}  exists={os.path.exists(r) if r else False}")
        except Exception as dbg_e:
            print(f"[Export] detail print error: {dbg_e}")

        # 如果指定了过滤关键字，按文件名过滤（不区分大小写）
        if filter_keyword:
            fk_lower = filter_keyword.lower()
            filtered = []
            for pair in selected_pairs:
                left_path = (pair.get('left') or {}).get('path') or ''
                right_path = (pair.get('right') or {}).get('path') or ''
                if fk_lower in os.path.basename(left_path).lower() or fk_lower in os.path.basename(right_path).lower():
                    filtered.append(pair)
            selected_pairs = filtered

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
            'txt_folder_follows': txt_folder_follows,
            'unified_file_prefix': data.get('unified_file_prefix', 'T'),
            'runinghub_start': runinghub_start,
            'runinghub_end': runinghub_end,
            'prefix_letter': bool(data.get('prefix_letter', False))
        }
        
        # 根据 filter_file_type 决定是否包含图片/文本（兼容旧参数）
        include_images = filter_file_type in ['png', 'both']
        include_txt = filter_file_type in ['txt', 'both']

        # namefilter 模式支持保留原始文件名并按多选 formats 导出
        filter_formats = data.get('filter_formats') or []
        if naming_mode == 'namefilter':
            formats = []
            for f in filter_formats:
                if isinstance(f, str):
                    ff = f.lower()
                    if ff in ['png', 'jpg', 'txt']:
                        formats.append(ff)
            if not formats:
                formats = ['png', 'txt']

            if output_type == 'folder':
                if output_dir and os.path.isdir(output_dir):
                    folder_path = os.path.join(output_dir, base_name)
                else:
                    folder_path = base_name
                
                # 自动处理重复名称（添加 _1, _2 后缀）
                if os.path.exists(folder_path):
                    folder_path = _get_unique_path(folder_path, is_zip=False)
                
                print(f"[Export] namefilter folder_path={folder_path}, formats={formats}, filter_keyword={filter_keyword}")
                result_path = ImageProcessor.export_namefilter_to_folder(selected_pairs, folder_path, formats=formats, filter_keyword=filter_keyword)
            else:
                zip_filename = f"{base_name}.zip"
                if output_dir and os.path.isdir(output_dir):
                    zip_path = os.path.join(output_dir, zip_filename)
                else:
                    zip_path = zip_filename
                
                # 自动处理重复名称（添加 _1, _2 后缀）
                if os.path.exists(zip_path):
                    zip_path = _get_unique_path(zip_path, is_zip=True)
                
                print(f"[Export] namefilter zip_path={zip_path}, formats={formats}, filter_keyword={filter_keyword}")
                result_path = ImageProcessor.export_namefilter_to_zip(selected_pairs, zip_path, formats=formats, filter_keyword=filter_keyword)
        else:
            # 常规模式导出（保留向后兼容）
            if output_type == 'folder':
                # 导出到文件夹
                if output_dir and os.path.isdir(output_dir):
                    folder_path = os.path.join(output_dir, base_name)
                else:
                    folder_path = base_name
                print(f"[Export] folder_path={folder_path}")
                
                # 自动处理重复名称（添加 _1, _2 后缀）
                if os.path.exists(folder_path):
                    folder_path = _get_unique_path(folder_path, is_zip=False)
                
                result_path = ImageProcessor.export_pairs_to_folder(selected_pairs, folder_path, image_format, naming_config, include_images=include_images, include_txt=include_txt)
            else:
                # 导出到zip
                zip_filename = f"{base_name}.zip"
                if output_dir and os.path.isdir(output_dir):
                    zip_path = os.path.join(output_dir, zip_filename)
                else:
                    zip_path = zip_filename
                print(f"[Export] zip_path={zip_path}")
                
                # 自动处理重复名称（添加 _1, _2 后缀）
                if os.path.exists(zip_path):
                    zip_path = _get_unique_path(zip_path, is_zip=True)
                
                result_path = ImageProcessor.export_pairs_to_zip(selected_pairs, zip_path, image_format, naming_config, include_images=include_images, include_txt=include_txt)

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


@app.route('/api/pairs/resize', methods=['POST'])
def resize_pairs():
    """批量裁切pairs图片（按最长边缩放）"""
    try:
        data = request.get_json(silent=True) or {}
        ids = data.get('ids', [])
        max_size = data.get('max_size', 1536)
        
        if not ids:
            return jsonify({"success": False, "message": "未选择成对图片组"}), 400
        
        count = 0
        for pair_id in ids:
            if pair_id not in pairs_data:
                continue
            pair = pairs_data[pair_id]
            
            # 处理左侧图片
            left_path = (pair.get('left') or {}).get('path')
            if left_path and os.path.exists(left_path):
                if ImageProcessor.resize_image_by_longest_edge(left_path, max_size):
                    # 更新缩略图
                    thumb = ImageProcessor.create_thumbnail(left_path)
                    pairs_data[pair_id]['left']['thumbnail'] = thumb
                    # 更新尺寸信息
                    img = Image.open(left_path)
                    pairs_data[pair_id]['left']['width'] = img.width
                    pairs_data[pair_id]['left']['height'] = img.height
                    img.close()
            
            # 处理右侧图片
            right_path = (pair.get('right') or {}).get('path')
            if right_path and os.path.exists(right_path):
                if ImageProcessor.resize_image_by_longest_edge(right_path, max_size):
                    # 更新缩略图
                    thumb = ImageProcessor.create_thumbnail(right_path)
                    pairs_data[pair_id]['right']['thumbnail'] = thumb
                    # 更新尺寸信息
                    img = Image.open(right_path)
                    pairs_data[pair_id]['right']['width'] = img.width
                    pairs_data[pair_id]['right']['height'] = img.height
                    img.close()
            
            count += 1
        
        return jsonify({
            "success": True,
            "message": f"已裁切 {count} 组图片",
            "count": count
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
        target_lang = data.get('target_lang', None)  # 'en' 或 'zh'
        
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
        translated = APIHandler.translate_text(text, api_key, base_url, model, target_lang)
        
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


@app.route('/api/export', methods=['POST'])
def export_images():
    """导出单图数据集"""
    try:
        data = request.get_json(silent=True) or {}
        ids = data.get('ids', [])
        image_format = data.get('format', 'png').lower()
        output_type = data.get('output_type', 'zip')
        output_path = data.get('output_path', '').strip()
        
        if not ids:
            return jsonify({"success": False, "message": "请选择要导出的图片"}), 400
        
        # 确保格式正确
        if image_format not in ['png', 'jpg', 'jpeg']:
            image_format = 'png'
        if image_format == 'jpeg':
            image_format = 'jpg'
        
        # 准备导出数据
        export_data = []
        for img_id in ids:
            if img_id in images_data:
                img = images_data[img_id]
                export_data.append({
                    'path': img['path'],
                    'text': img.get('text', ''),
                    'name': img.get('name', '')
                })
        
        if not export_data:
            return jsonify({"success": False, "message": "没有找到要导出的图片"}), 400
        
        # 生成输出路径
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 记录用户选择的目录（用于返回给前端打开文件夹）
        export_folder = output_path if output_path else TRAINING_DATA_DIR
        
        if output_type == 'zip':
            # 导出为ZIP
            if not output_path:
                # 未指定路径，使用默认目录
                export_folder = TRAINING_DATA_DIR
                zip_path = os.path.join(TRAINING_DATA_DIR, f"data_{timestamp}.zip")
            elif output_path.endswith('.zip'):
                # 用户指定了完整的 zip 文件路径
                zip_path = output_path
                export_folder = os.path.dirname(output_path) or TRAINING_DATA_DIR
            else:
                # 用户指定的是目录，在该目录下生成 zip 文件
                export_folder = output_path
                zip_path = os.path.join(output_path, f"data_{timestamp}.zip")
            
            # 确保目录存在
            os.makedirs(export_folder, exist_ok=True)
            
            # 调用导出函数
            import zipfile
            import io
            from PIL import Image
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for idx, item in enumerate(export_data):
                    src_path = item['path']
                    base_name = os.path.splitext(item['name'])[0]
                    
                    # 处理图片格式转换
                    _, src_ext = os.path.splitext(src_path)
                    src_ext = src_ext.lower()
                    target_ext = f'.{image_format}'
                    
                    if src_ext == target_ext or (image_format == 'jpg' and src_ext in ['.jpg', '.jpeg']):
                        # 格式相同，直接复制
                        zf.write(src_path, f"{base_name}{target_ext}")
                    else:
                        # 需要转换格式
                        img = Image.open(src_path)
                        if img.mode == 'RGBA' and image_format == 'jpg':
                            background = Image.new('RGB', img.size, (255, 255, 255))
                            background.paste(img, mask=img.split()[3])
                            img = background
                        elif img.mode != 'RGB' and image_format == 'jpg':
                            img = img.convert('RGB')
                        
                        img_buffer = io.BytesIO()
                        if image_format == 'jpg':
                            img.save(img_buffer, format='JPEG', quality=95)
                        else:
                            img.save(img_buffer, format='PNG')
                        zf.writestr(f"{base_name}{target_ext}", img_buffer.getvalue())
                    
                    # 导出文本文件
                    if item.get('text'):
                        zf.writestr(f"{base_name}.txt", item['text'])
            
            result_path = zip_path
            
        else:
            # 导出为文件夹
            if not output_path:
                output_path = os.path.join(TRAINING_DATA_DIR, f"dataset_{timestamp}")
            
            export_folder = output_path  # 设置文件夹导出的目录
            os.makedirs(output_path, exist_ok=True)
            
            from shutil import copy2
            from PIL import Image
            
            for idx, item in enumerate(export_data):
                src_path = item['path']
                base_name = os.path.splitext(item['name'])[0]
                
                # 处理图片格式转换
                _, src_ext = os.path.splitext(src_path)
                src_ext = src_ext.lower()
                target_ext = f'.{image_format}'
                dest_path = os.path.join(output_path, f"{base_name}{target_ext}")
                
                if src_ext == target_ext or (image_format == 'jpg' and src_ext in ['.jpg', '.jpeg']):
                    # 格式相同，直接复制
                    copy2(src_path, dest_path)
                else:
                    # 需要转换格式
                    img = Image.open(src_path)
                    if img.mode == 'RGBA' and image_format == 'jpg':
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[3])
                        img = background
                    elif img.mode != 'RGB' and image_format == 'jpg':
                        img = img.convert('RGB')
                    
                    if image_format == 'jpg':
                        img.save(dest_path, format='JPEG', quality=95)
                    else:
                        img.save(dest_path, format='PNG')
                
                # 导出文本文件
                if item.get('text'):
                    txt_path = os.path.join(output_path, f"{base_name}.txt")
                    with open(txt_path, 'w', encoding='utf-8') as f:
                        f.write(item['text'])
            
            result_path = output_path
            export_folder = output_path
        
        return jsonify({
            "success": True,
            "message": f"成功导出 {len(export_data)} 张图片",
            "file": result_path,
            "folder": export_folder,
            "count": len(export_data)
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
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


@app.route('/api/analyzer/refresh-record/<record_id>', methods=['POST'])
def refresh_analyzer_record(record_id):
    """重新解析记录对应的日志文件，更新记录中的训练参数（pretrained_model_name_or_path、training_time、steps）"""
    if not TRAINING_ANALYZER_AVAILABLE:
        return jsonify({"success": False, "message": "训练分析器模块未加载"}), 500
    try:
        from training_analyzer import report_manager
        manager = report_manager.get_manager()
        record = manager.get_record_by_id(record_id)
        if not record:
            return jsonify({"success": False, "message": "记录不存在"}), 404

        log_path = record.get('log_file_path')
        if not log_path or not os.path.exists(log_path):
            return jsonify({"success": False, "message": "日志文件不存在，无法刷新"}), 400

        # 解析日志但不重复保存为新记录
        from training_analyzer.log_parser import parse_log_file
        parsed = parse_log_file(log_path)
        if not parsed:
            return jsonify({"success": False, "message": "日志解析失败"}), 500

        # 获取 config 优先级：如果 multiple sessions, take first session config
        config = None
        if parsed.get('training_sessions'):
            config = parsed['training_sessions'][0].get('config', {})
        else:
            config = parsed.get('config', {})

        # 更新字段
        if config:
            record['pretrained_model_name_or_path'] = config.get('pretrained_model_name_or_path') or config.get('pretrained_model')
            record['training_time'] = config.get('training_time')
            record['steps'] = config.get('steps')

            # 保存回 records.json
            all_records = manager.load_records()
            for idx, r in enumerate(all_records.get('records', [])):
                if r.get('id') == record_id:
                    all_records['records'][idx] = record
                    break
            manager._save_to_file(all_records)

            return jsonify({"success": True, "record": record})
        else:
            return jsonify({"success": False, "message": "未在解析结果中找到配置"}), 500
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


@app.route('/api/analyzer/export-markdown', methods=['POST'])
def export_analyzer_markdown():
    """接收前端发送的 Markdown 内容并写入 training_excel.md"""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if content is None:
            return jsonify({"success": False, "message": "没有提供内容"}), 400

        target_dir = os.path.join(RESOURCE_PATH, 'training_analyzer', 'training_excel')
        os.makedirs(target_dir, exist_ok=True)
        target_file = os.path.join(target_dir, 'training_excel.md')

        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(content)
        # 另外，将每条历史记录也写入单独的 Markdown 作为备份
        try:
            from training_analyzer import report_manager
            records_data = report_manager.load_records()
            # 创建备份目录
            backup_dir = os.path.join(RESOURCE_PATH, 'training_analyzer', 'log_record', 'markdowns')
            os.makedirs(backup_dir, exist_ok=True)

            # Markdown 表头
            header = '| 横轴分类 - 模型名称|训练集数量|epoch|repeat|save epoch|rank|steps|训练底模|学习率|训练时间|\n|---|---|---|---|---|---|---|---|---|---|\n'

            for rec in records_data.get('records', []):
                model_name = rec.get('model_name', 'N/A')
                train_data = (rec.get('train_data_dir') or 'N/A').split('/')[-1].split('\\')[-1]
                epoch = rec.get('num_epochs') or rec.get('total_trained_epochs') or 'N/A'
                repeat = rec.get('repeats', 'N/A')
                save_epoch = rec.get('save_model_epochs', 'N/A')
                rank = rec.get('rank', 'N/A')
                steps = rec.get('steps', 'N/A')
                base_model = (rec.get('pretrained_model_name_or_path') or rec.get('pretrained_model') or '').split('/')[-1].split('\\')[-1] or 'N/A'
                lr = rec.get('learning_rate', 'N/A')
                training_time = rec.get('training_time', 'N/A')

                row = f'| {model_name} | {train_data} | {epoch} | {repeat} | {save_epoch} | {rank} | {steps} | {base_model} | {lr} | {training_time} |\n'

                rec_file = os.path.join(backup_dir, f'{rec.get("id")}.md')
                with open(rec_file, 'w', encoding='utf-8') as rf:
                    rf.write(header + row)
        except Exception as e:
            # 备份失败不影响主保存，记录错误
            print("Warning: per-record markdown backup failed:", e)

        return jsonify({"success": True, "path": target_file})
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
        user_prompt = data.get('user_prompt', '')  # 添加用户提示词支持
        
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


@app.route('/api/analyzer/settings', methods=['GET'])
def get_analyzer_settings():
    """获取训练分析器设置"""
    try:
        settings_file = os.path.join(CONFIG_DIR, "analyzer_settings.json")
        
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        else:
            # 返回默认设置
            settings = {
                "system_prompt": "",
                "user_prompt": ""
            }
        
        return jsonify({"success": True, "settings": settings})
    except Exception as e:
        print(f"加载训练分析器设置错误: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/analyzer/settings', methods=['POST'])
def save_analyzer_settings():
    """保存训练分析器设置"""
    try:
        data = request.get_json(silent=True) or {}
        system_prompt = data.get('system_prompt', '')
        user_prompt = data.get('user_prompt', '')
        
        settings = {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt
        }
        
        settings_file = os.path.join(CONFIG_DIR, "analyzer_settings.json")
        os.makedirs(os.path.dirname(settings_file), exist_ok=True)
        
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        
        return jsonify({"success": True, "message": "设置已保存"})
    except Exception as e:
        print(f"保存训练分析器设置错误: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


# ==================== AI对话历史管理 ====================

CHAT_HISTORY_DIR = os.path.join(BASE_PATH, 'ai_chat', 'chat_history')
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

@app.route('/api/cache/save', methods=['POST'])
def save_cache():
    """保存当前编辑状态到缓存"""
    try:
        import json
        from datetime import datetime
        
        data = request.json or {}
        cache_name = data.get('name', '').strip()
        
        if not cache_name:
            return jsonify({"success": False, "message": "请输入缓存名称"}), 400

        if any(sep in cache_name for sep in ['/', '\\']) or cache_name in ['.', '..'] or '..' in cache_name:
            return jsonify({"success": False, "message": "缓存名称不合法"}), 400
        
        # 创建缓存目录
        cache_dir = os.path.join(TRAINING_EDIT_TMP_DIR, '__temp_cache__')
        os.makedirs(cache_dir, exist_ok=True)
        
        # 创建缓存文件夹
        cache_folder = os.path.join(cache_dir, cache_name)
        # 不允许覆盖已存在的缓存
        if os.path.exists(cache_folder):
            return jsonify({"success": False, "message": "缓存名称已存在"}), 400
        
        os.makedirs(cache_folder)

        # 保存pairs数据（优先使用请求中提供的 pairs，如果没有则回退到服务端 pairs_data）
        pairs_snapshot = []
        request_pairs = data.get('pairs')
        if isinstance(request_pairs, list):
            for p in request_pairs:
                # 支持多种前端传递格式：可能是 { left: { path: ... }, left_path: "...", left: "..." }
                left_path = None
                right_path = None
                try:
                    left = p.get('left')
                    if isinstance(left, dict):
                        left_path = left.get('path')
                    else:
                        left_path = p.get('left_path') or left
                except Exception:
                    left_path = p.get('left_path') or None

                try:
                    right = p.get('right')
                    if isinstance(right, dict):
                        right_path = right.get('path')
                    else:
                        right_path = p.get('right_path') or right
                except Exception:
                    right_path = p.get('right_path') or None
                
                # left2 支持
                left2_path = None
                try:
                    left2 = p.get('left2')
                    if isinstance(left2, dict):
                        left2_path = left2.get('path')
                    else:
                        left2_path = p.get('left2_path') or left2
                except Exception:
                    left2_path = p.get('left2_path') or None

                pairs_snapshot.append({
                    'id': p.get('id'),
                    'left_path': left_path,
                    'left2_path': left2_path,
                    'right_path': right_path,
                    'text': p.get('text', ''),
                    'status': p.get('status', 'idle'),
                    'selected': bool(p.get('selected', False)),
                    'export_name': p.get('export_name')
                })
        else:
            for p in pairs_data.values():
                left_path = ((p.get('left') or {}).get('path'))
                left2_path = ((p.get('left2') or {}).get('path'))
                right_path = ((p.get('right') or {}).get('path'))
                pairs_snapshot.append({
                    'id': p.get('id'),
                    'left_path': left_path,
                    'left2_path': left2_path,
                    'right_path': right_path,
                    'text': p.get('text', ''),
                    'status': p.get('status', 'idle'),
                    'selected': bool(p.get('selected', False)),
                    'export_name': p.get('export_name')
                })

        cache_data = {
            'pairs': pairs_snapshot,
            'timestamp': datetime.now().isoformat(),
            'version': '1.0'
        }
        
        # 保存到JSON文件
        with open(os.path.join(cache_folder, 'cache_data.json'), 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({"success": True, "message": f"缓存已保存: {cache_name}"})
        
    except Exception as e:
        print(f"保存缓存失败: {e}")
        return jsonify({"success": False, "message": f"保存失败: {str(e)}"}), 500


@app.route('/api/cache/list', methods=['GET'])
def list_cache():
    """列出所有可用的缓存"""
    try:
        import json
        from datetime import datetime
        
        cache_dir = os.path.join(TRAINING_EDIT_TMP_DIR, '__temp_cache__')
        if not os.path.exists(cache_dir):
            return jsonify({"success": True, "caches": []})
        
        caches = []
        for item in os.listdir(cache_dir):
            cache_path = os.path.join(cache_dir, item)
            if os.path.isdir(cache_path):
                cache_file = os.path.join(cache_path, 'cache_data.json')
                if os.path.exists(cache_file):
                    try:
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            cache_data = json.load(f)
                        
                        # 计算文件夹大小
                        total_size = 0
                        for root, dirs, files in os.walk(cache_path):
                            for file in files:
                                total_size += os.path.getsize(os.path.join(root, file))
                        
                        # 格式化大小
                        if total_size < 1024:
                            size_str = f"{total_size} B"
                        elif total_size < 1024 * 1024:
                            size_str = f"{total_size / 1024:.1f} KB"
                        else:
                            size_str = f"{total_size / (1024 * 1024):.1f} MB"
                        
                        # 格式化时间
                        timestamp = cache_data.get('timestamp', '')
                        try:
                            dt = datetime.fromisoformat(timestamp)
                            created_at = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            created_at = timestamp
                        
                        caches.append({
                            'name': item,
                            'display_name': item,
                            'timestamp': timestamp,
                            'created_at': created_at,
                            'pair_count': len(cache_data.get('pairs', [])),
                            'size': size_str,
                            'version': cache_data.get('version', '1.0')
                        })
                    except Exception as e:
                        print(f"读取缓存 {item} 失败: {e}")
                        continue
        
        # 按时间戳排序
        caches.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({"success": True, "caches": caches})
        
    except Exception as e:
        print(f"列出缓存失败: {e}")
        return jsonify({"success": False, "message": f"获取缓存列表失败: {str(e)}"}), 500


@app.route('/api/cache/load', methods=['POST'])
def load_cache():
    """加载指定的缓存"""
    try:
        import json
        
        data = request.json or {}
        cache_name = data.get('name', '').strip()
        
        if not cache_name:
            return jsonify({"success": False, "message": "请选择要加载的缓存"}), 400
        
        cache_dir = os.path.join(TRAINING_EDIT_TMP_DIR, '__temp_cache__')
        cache_path = os.path.join(cache_dir, cache_name)
        
        if not os.path.exists(cache_path):
            return jsonify({"success": False, "message": "缓存不存在"}), 404
        
        cache_file = os.path.join(cache_path, 'cache_data.json')
        if not os.path.exists(cache_file):
            return jsonify({"success": False, "message": "缓存数据文件不存在"}), 404
        
        # 读取缓存数据
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        # 清空当前pairs数据
        pairs_data.clear()

        # 加载缓存数据并重建图片信息（缩略图/尺寸等）
        missing_files = []
        for item in cache_data.get('pairs', []):
            pair_id = item.get('id')
            if not pair_id:
                continue

            left_path = item.get('left_path')
            left2_path = item.get('left2_path')
            right_path = item.get('right_path')

            # 构建图片信息，如果文件存在则加载完整信息，否则保留路径但标记为缺失
            left_info = None
            left2_info = None
            right_info = None
            
            if left_path:
                if os.path.exists(left_path):
                    left_info = _build_pair_side_info(left_path)
                else:
                    missing_files.append(left_path)
                    left_info = {
                        "path": left_path,
                        "name": os.path.basename(left_path),
                        "width": 0,
                        "height": 0,
                        "thumbnail": None,
                        "text": "",
                        "status": "missing"
                    }
            
            if left2_path:
                if os.path.exists(left2_path):
                    left2_info = _build_pair_side_info(left2_path)
                else:
                    missing_files.append(left2_path)
                    left2_info = {
                        "path": left2_path,
                        "name": os.path.basename(left2_path),
                        "width": 0,
                        "height": 0,
                        "thumbnail": None,
                        "text": "",
                        "status": "missing"
                    }
            
            if right_path:
                if os.path.exists(right_path):
                    right_info = _build_pair_side_info(right_path)
                else:
                    missing_files.append(right_path)
                    right_info = {
                        "path": right_path,
                        "name": os.path.basename(right_path),
                        "width": 0,
                        "height": 0,
                        "thumbnail": None,
                        "text": "",
                        "status": "missing"
                    }

            pair_info = {
                'id': pair_id,
                'left': left_info,
                'left2': left2_info,
                'right': right_info,
                'text': item.get('text', ''),
                'status': item.get('status', 'idle'),
                'selected': bool(item.get('selected', False)),
                'export_name': item.get('export_name')
            }
            pairs_data[pair_id] = pair_info
        
        message = f"缓存已加载: {cache_name}"
        if missing_files:
            message += f" (警告: {len(missing_files)} 个文件不存在)"
        
        return jsonify({
            "success": True, 
            "message": message,
            "pairs": list(pairs_data.values()),
            "missing_files": len(missing_files)
        })
        
    except Exception as e:
        print(f"加载缓存失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"加载失败: {str(e)}"}), 500


@app.route('/api/cache/delete', methods=['POST'])
def delete_cache():
    """删除指定的缓存"""
    try:
        data = request.json or {}
        cache_name = data.get('name', '').strip()
        
        if not cache_name:
            return jsonify({"success": False, "message": "请选择要删除的缓存"}), 400
        
        cache_dir = os.path.join(TRAINING_EDIT_TMP_DIR, '__temp_cache__')
        cache_path = os.path.join(cache_dir, cache_name)
        
        if not os.path.exists(cache_path):
            return jsonify({"success": False, "message": "缓存不存在"}), 404
        
        # 删除整个缓存文件夹
        shutil.rmtree(cache_path)
        
        return jsonify({"success": True, "message": f"缓存已删除: {cache_name}"})
        
    except Exception as e:
        print(f"删除缓存失败: {e}")
        return jsonify({"success": False, "message": f"删除失败: {str(e)}"}), 500


@app.route('/api/cache/export', methods=['POST'])
def export_cache():
    """导出指定的缓存为ZIP文件"""
    try:
        import zipfile
        
        data = request.json or {}
        cache_name = data.get('name', '').strip()
        
        if not cache_name:
            return jsonify({"success": False, "message": "请选择要导出的缓存"}), 400
        
        cache_dir = os.path.join(TRAINING_EDIT_TMP_DIR, '__temp_cache__')
        cache_path = os.path.join(cache_dir, cache_name)
        
        if not os.path.exists(cache_path):
            return jsonify({"success": False, "message": "缓存不存在"}), 404
        
        # 创建导出目录
        export_dir = TRAINING_EDIT_TMP_DIR
        os.makedirs(export_dir, exist_ok=True)
        
        # 生成ZIP文件路径
        zip_path = os.path.join(export_dir, f"{cache_name}.zip")
        
        # 如果ZIP已存在，添加后缀
        if os.path.exists(zip_path):
            zip_path = _get_unique_path(zip_path, is_zip=True)
        
        # 创建ZIP文件
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(cache_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, cache_path)
                    zipf.write(file_path, arcname)
        
        return jsonify({
            "success": True, 
            "message": f"缓存已导出: {os.path.basename(zip_path)}",
            "file": zip_path
        })
        
    except Exception as e:
        print(f"导出缓存失败: {e}")
        return jsonify({"success": False, "message": f"导出失败: {str(e)}"}), 500


@app.route('/api/cache/select-import', methods=['POST'])
def select_cache_for_import():
    """选择要导入的缓存ZIP文件"""
    try:
        root = get_tk_root()
        if not root:
            return jsonify({"success": False, "message": "无法打开文件选择对话框"}), 500
        
        file_path = filedialog.askopenfilename(
            parent=root,
            title="选择缓存文件",
            filetypes=[("ZIP文件", "*.zip"), ("所有文件", "*.*")]
        )
        
        root.destroy()
        
        if not file_path:
            return jsonify({"success": False, "message": "未选择文件"}), 400
        
        return jsonify({"success": True, "file": file_path})
        
    except Exception as e:
        print(f"选择导入文件失败: {e}")
        return jsonify({"success": False, "message": f"选择文件失败: {str(e)}"}), 500


@app.route('/api/cache/import', methods=['POST'])
def import_cache():
    """导入缓存ZIP文件"""
    try:
        import zipfile
        
        data = request.json or {}
        file_path = data.get('file', '').strip()
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({"success": False, "message": "文件不存在"}), 400
        
        if not file_path.lower().endswith('.zip'):
            return jsonify({"success": False, "message": "只支持ZIP文件"}), 400
        
        # 获取缓存名称（从ZIP文件名）
        cache_name = os.path.splitext(os.path.basename(file_path))[0]
        
        # 确保缓存名称合法
        if any(sep in cache_name for sep in ['/', '\\']) or cache_name in ['.', '..']:
            cache_name = f"imported_cache_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        cache_dir = os.path.join(TRAINING_EDIT_TMP_DIR, '__temp_cache__')
        os.makedirs(cache_dir, exist_ok=True)
        
        cache_path = os.path.join(cache_dir, cache_name)
        
        # 如果缓存已存在，添加后缀
        if os.path.exists(cache_path):
            counter = 1
            while os.path.exists(f"{cache_path}_{counter}"):
                counter += 1
            cache_path = f"{cache_path}_{counter}"
            cache_name = f"{cache_name}_{counter}"
        
        # 解压ZIP文件
        with zipfile.ZipFile(file_path, 'r') as zipf:
            zipf.extractall(cache_path)
        
        return jsonify({
            "success": True, 
            "message": f"缓存已导入: {cache_name}",
            "name": cache_name
        })
        
    except Exception as e:
        print(f"导入缓存失败: {e}")
        return jsonify({"success": False, "message": f"导入失败: {str(e)}"}), 500


@app.route('/api/cache/clear-all', methods=['POST'])
def clear_all_cache():
    """一键清空所有缓存"""
    try:
        # print("[DEBUG] clear_all_cache called")
        cache_dir = os.path.join(TRAINING_EDIT_TMP_DIR, '__temp_cache__')
        # print(f"[DEBUG] cache_dir: {cache_dir}")
        
        if not os.path.exists(cache_dir):
            # print("[DEBUG] cache_dir does not exist")
            return jsonify({"success": True, "message": "缓存目录不存在，无需清空", "deleted_count": 0})
        
        deleted_count = 0
        items = os.listdir(cache_dir)
        # print(f"[DEBUG] items in cache_dir: {items}")
        
        for item in items:
            item_path = os.path.join(cache_dir, item)
            if os.path.isdir(item_path):
                try:
                    shutil.rmtree(item_path)
                    deleted_count += 1
                    # print(f"[DEBUG] deleted: {item}")
                except Exception as e:
                    print(f"删除缓存 {item} 失败: {e}")
        
        # print(f"[DEBUG] deleted_count: {deleted_count}")
        return jsonify({
            "success": True, 
            "message": f"已清空 {deleted_count} 个缓存",
            "deleted_count": deleted_count
        })
        
    except Exception as e:
        print(f"清空缓存失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"清空失败: {str(e)}"}), 500


@app.route('/api/cache/export-all', methods=['POST'])
def export_all_cache():
    """一键导出所有缓存为ZIP文件"""
    try:
        import zipfile
        from datetime import datetime
        
        data = request.json or {}
        export_path = data.get('path', '').strip()
        
        cache_dir = os.path.join(TRAINING_EDIT_TMP_DIR, '__temp_cache__')
        
        if not os.path.exists(cache_dir):
            return jsonify({"success": False, "message": "缓存目录不存在"}), 400
        
        # 检查是否有缓存
        cache_folders = [d for d in os.listdir(cache_dir) if os.path.isdir(os.path.join(cache_dir, d))]
        
        if not cache_folders:
            return jsonify({"success": False, "message": "没有可导出的缓存"}), 400
        
        # 如果没有指定路径，弹出文件选择对话框
        if not export_path:
            root = get_tk_root()
            if not root:
                return jsonify({"success": False, "message": "无法打开文件选择对话框"}), 500
            
            default_name = f"cache_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            try:
                export_path = filedialog.asksaveasfilename(
                    parent=root,
                    title="选择导出位置",
                    defaultextension=".zip",
                    initialfile=default_name,
                    filetypes=[("ZIP文件", "*.zip"), ("所有文件", "*.*")]
                )
            except Exception as dialog_error:
                root.destroy()
                return jsonify({"success": False, "message": f"文件对话框错误: {str(dialog_error)}"}), 500
            finally:
                try:
                    root.destroy()
                except:
                    pass
            
            if not export_path:
                return jsonify({"success": False, "message": "未选择导出位置"}), 400
        
        # 创建ZIP文件
        with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for cache_folder in cache_folders:
                cache_path = os.path.join(cache_dir, cache_folder)
                for root_dir, dirs, files in os.walk(cache_path):
                    for file in files:
                        file_path = os.path.join(root_dir, file)
                        # 保持目录结构：cache_folder/file
                        arcname = os.path.join(cache_folder, os.path.relpath(file_path, cache_path))
                        zipf.write(file_path, arcname)
        
        return jsonify({
            "success": True, 
            "message": f"已导出 {len(cache_folders)} 个缓存",
            "file": export_path,
            "count": len(cache_folders)
        })
        
    except Exception as e:
        print(f"导出所有缓存失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"导出失败: {str(e)}"}), 500


@app.route('/api/cache/import-all', methods=['POST'])
def import_all_cache():
    """一键导入缓存ZIP文件（支持多个缓存的打包文件）"""
    try:
        import zipfile
        import json
        
        data = request.json or {}
        file_path = data.get('file', '').strip()
        
        # 如果没有指定文件，弹出文件选择对话框
        if not file_path:
            root = get_tk_root()
            if not root:
                return jsonify({"success": False, "message": "无法打开文件选择对话框"}), 500
            
            file_path = filedialog.askopenfilename(
                parent=root,
                title="选择要导入的缓存文件",
                filetypes=[("ZIP文件", "*.zip"), ("所有文件", "*.*")]
            )
            root.destroy()
            
            if not file_path:
                return jsonify({"success": False, "message": "未选择文件"}), 400
        
        if not os.path.exists(file_path):
            return jsonify({"success": False, "message": "文件不存在"}), 400
        
        if not file_path.lower().endswith('.zip'):
            return jsonify({"success": False, "message": "只支持ZIP文件"}), 400
        
        cache_dir = os.path.join(TRAINING_EDIT_TMP_DIR, '__temp_cache__')
        os.makedirs(cache_dir, exist_ok=True)
        
        imported_count = 0
        
        with zipfile.ZipFile(file_path, 'r') as zipf:
            # 获取ZIP中的所有文件
            namelist = zipf.namelist()
            
            # 检查是否是多缓存打包格式（包含多个文件夹）
            top_level_dirs = set()
            for name in namelist:
                parts = name.split('/')
                if len(parts) > 1 and parts[0]:
                    top_level_dirs.add(parts[0])
            
            if top_level_dirs:
                # 多缓存打包格式：每个顶级目录是一个缓存
                for cache_name in top_level_dirs:
                    # 检查是否包含cache_data.json
                    cache_data_path = f"{cache_name}/cache_data.json"
                    if cache_data_path in namelist:
                        target_path = os.path.join(cache_dir, cache_name)
                        
                        # 如果缓存已存在，添加后缀
                        if os.path.exists(target_path):
                            counter = 1
                            while os.path.exists(f"{target_path}_{counter}"):
                                counter += 1
                            target_path = f"{target_path}_{counter}"
                        
                        os.makedirs(target_path, exist_ok=True)
                        
                        # 解压该缓存的所有文件
                        for name in namelist:
                            if name.startswith(f"{cache_name}/") and not name.endswith('/'):
                                # 获取相对路径
                                rel_path = name[len(cache_name)+1:]
                                if rel_path:
                                    target_file = os.path.join(target_path, rel_path)
                                    os.makedirs(os.path.dirname(target_file), exist_ok=True)
                                    with zipf.open(name) as src, open(target_file, 'wb') as dst:
                                        dst.write(src.read())
                        
                        imported_count += 1
            else:
                # 单缓存格式：直接解压到新文件夹
                cache_name = os.path.splitext(os.path.basename(file_path))[0]
                target_path = os.path.join(cache_dir, cache_name)
                
                if os.path.exists(target_path):
                    counter = 1
                    while os.path.exists(f"{target_path}_{counter}"):
                        counter += 1
                    target_path = f"{target_path}_{counter}"
                
                zipf.extractall(target_path)
                imported_count = 1
        
        return jsonify({
            "success": True, 
            "message": f"已导入 {imported_count} 个缓存",
            "count": imported_count
        })
        
    except Exception as e:
        print(f"导入缓存失败: {e}")
        return jsonify({"success": False, "message": f"导入失败: {str(e)}"}), 500


# ================ 授权 / 激活 接口 =================
@app.route('/api/license/get_cpu_uuid', methods=['GET'])
def api_get_cpu_uuid():
    try:
        cpu = get_cpu_uuid()
        cpu_hex = cpu.encode('utf-8').hex() if cpu else ''
        return jsonify({"success": True, "cpu_uuid": cpu, "cpu_hex": cpu_hex})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/license/get_saved_code', methods=['GET'])
def api_get_saved_license_code():
    """从apikey.json读取预存的激活码"""
    try:
        config = load_apikey_config()
        code = config.get('license_code', '')
        return jsonify({"success": True, "license_code": code})
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "license_code": ""})


@app.route('/api/license/save_code', methods=['POST'])
def api_save_license_code():
    """保存激活码到apikey.json"""
    try:
        data = request.get_json(silent=True) or {}
        license_code = (data.get('license_code') or '').strip()
        
        # 读取现有配置
        config = load_apikey_config()
        config['license_code'] = license_code
        save_apikey_config(config)
        
        return jsonify({"success": True, "message": "激活码已保存"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/license/activate', methods=['POST'])
def api_license_activate():
    """
    激活接口：验证激活码是否匹配本机，匹配才保存
    激活码格式：20位字符（UUID前16位十六进制 + PDYY后缀）
    必须与本机UUID完全匹配才能激活成功
    """
    try:
        import re
        data = request.get_json(silent=True) or {}
        license_code = (data.get('license_code') or '').strip()
        if not license_code:
            return jsonify({"success": False, "message": "未提供激活码"}), 400
        
        # 规范化激活码：去掉短横线/空白，转大写
        cleaned = re.sub(r'[\-\s]', '', license_code).upper()
        
        # 严格校验格式：必须是20位，且以PDYY结尾
        if len(cleaned) != 20:
            return jsonify({"success": False, "message": "激活码格式不正确，应为20位"}), 400
        
        if not cleaned.endswith('PDYY'):
            return jsonify({"success": False, "message": "激活码格式不正确"}), 400
        
        # 获取本机UUID，计算期望的激活码
        cpu = get_cpu_uuid()
        if not cpu:
            return jsonify({"success": False, "message": "无法获取本机UUID"}), 500
        
        # 使用 SHA256 哈希生成激活码（数字和字母混合）
        import hashlib
        hash_obj = hashlib.sha256(cpu.encode('utf-8'))
        cpu_hex_full = hash_obj.hexdigest().upper()
        cpu_hex_16 = cpu_hex_full[:16]
        expected = cpu_hex_16 + 'PDYY'
        
        # print(f"[DEBUG] 原始CPU UUID: {cpu}")
        # print(f"[DEBUG] SHA256哈希: {cpu_hex_full}")
        # print(f"[DEBUG] 期望激活码: {expected}")
        # print(f"[DEBUG] 用户输入(清理后): {cleaned}")
        
        # 验证激活码是否与本机匹配
        if cleaned != expected:
            return jsonify({"success": False, "message": f"激活码与本机不匹配"}), 400

        # 验证通过，保存激活码到apikey.json
        config = load_apikey_config()
        config['license_code'] = cleaned
        save_apikey_config(config)

        return jsonify({"success": True, "message": "激活成功"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/license/verify', methods=['GET'])
def api_license_verify():
    """
    验证激活码逻辑：
    激活码 = SHA256(CPU_UUID)的前16位(大写) + "PDYY"
    必须完全匹配，长度必须是20位
    """
    try:
        import re
        import hashlib
        cpu = get_cpu_uuid()
        if not cpu:
            return jsonify({"success": False, "message": "无法获取本机UUID"}), 200
        
        # 使用 SHA256 哈希
        hash_obj = hashlib.sha256(cpu.encode('utf-8'))
        cpu_hex_full = hash_obj.hexdigest().upper()
        cpu_hex_16 = cpu_hex_full[:16]
        
        # 期望的激活码：SHA256前16位 + PDYY，总长度20位
        expected = cpu_hex_16 + 'PDYY'
        
        # 从apikey.json读取激活码
        config = load_apikey_config()
        content_raw = config.get('license_code', '').strip()
        
        if not content_raw:
            return jsonify({"success": False, "message": "未找到授权信息"}), 200

        # 去除短横线/空白，转大写
        content = re.sub(r'[\-\s]', '', content_raw).upper()
        
        # 严格校验：长度必须是20位，内容必须完全匹配
        if len(content) != 20:
            return jsonify({"success": False, "message": "激活码格式不正确"}), 200
        
        if content == expected:
            return jsonify({"success": True, "message": "授权校验通过"})
        else:
            return jsonify({"success": False, "message": "授权不匹配"}), 200
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
