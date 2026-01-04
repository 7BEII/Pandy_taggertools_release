"""
路径工具模块 - 兼容 PyInstaller 打包环境
"""
import sys
import os


def get_base_path():
    """
    获取基础路径
    - 开发环境: 返回项目根目录
    - 打包环境: 返回 exe 所在目录（用于存放用户数据）
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，返回 exe 所在目录
        return os.path.dirname(sys.executable)
    # 开发环境，返回 backend 的父目录（项目根目录）
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_resource_path():
    """
    获取资源路径（打包的静态资源）
    - 开发环境: 返回项目根目录
    - 打包环境: 返回 _MEIPASS 临时目录
    """
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# 基础路径（用户数据目录）
BASE_PATH = get_base_path()

# 资源路径（打包的静态资源）
RESOURCE_PATH = get_resource_path()

# 配置文件路径（用户可修改的配置，放在 exe 同级目录）
CONFIG_DIR = os.path.join(BASE_PATH, 'apikey_config')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
APIKEY_FILE = os.path.join(CONFIG_DIR, 'apikey.json')
# 注意：激活码现在统一存储在 apikey.json 的 license_code 字段中

# 模板目录（默认模板从资源目录读取，用户模板存放在用户目录）
TEMPLATES_DIR = CONFIG_DIR

# 前端静态文件路径（从资源目录读取）
FRONTEND_DIR = os.path.join(RESOURCE_PATH, 'frontend')

# 训练数据目录（用户数据，放在 exe 同级目录）
TRAINING_DATA_DIR = os.path.join(BASE_PATH, 'training_datas')
TRAINING_EDIT_TMP_DIR = os.path.join(BASE_PATH, 'training_edit_tmp')
TRAINING_PROMPT_TMP_DIR = os.path.join(BASE_PATH, 'training_prompt_tmp')


def ensure_user_dirs():
    """确保用户数据目录存在"""
    dirs = [
        CONFIG_DIR,
        TRAINING_DATA_DIR,
        TRAINING_EDIT_TMP_DIR,
        TRAINING_PROMPT_TMP_DIR,
        os.path.join(TRAINING_DATA_DIR, 'input_datas_image'),
        os.path.join(TRAINING_EDIT_TMP_DIR, '__temp_cache__'),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def copy_default_configs():
    """如果用户配置不存在，从资源目录复制默认配置"""
    import shutil
    
    ensure_user_dirs()
    
    # 默认配置文件列表（用于首次运行时复制）
    default_files = [
        '默认单图反推.json',
        '默认编辑模型.json',
    ]
    
    resource_config_dir = os.path.join(RESOURCE_PATH, 'apikey_config')
    
    for filename in default_files:
        src = os.path.join(resource_config_dir, filename)
        dst = os.path.join(CONFIG_DIR, filename)
        if os.path.exists(src) and not os.path.exists(dst):
            try:
                shutil.copy2(src, dst)
            except Exception:
                pass
