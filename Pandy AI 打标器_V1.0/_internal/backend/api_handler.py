"""
API 调用处理模块 - 支持多个 API 渠道
"""
import requests
import base64
import io
from PIL import Image


class APIHandler:
    """多渠道 Vision API 处理器"""
    
    PROVIDERS = {
        "siliconflow": {
            "name": "SiliconFlow (硅基流动)",
            "base_url": "https://api.siliconflow.cn/v1",
            "models": [
                "Qwen/Qwen3-VL-8B-Instruct",
                "Qwen/Qwen3-VL-32B-Instruct",
                "Qwen/Qwen2.5-VL-32B-Instruct",
                "Qwen/Qwen2.5-VL-7B-Instruct",
                "Qwen/Qwen2.5-VL-72B-Instruct",
                "Qwen/Qwen2-VL-72B-Instruct",
                "Pro/Qwen/Qwen2-VL-7B-Instruct",
            ]
        },
        "modelscope": {
            "name": "ModelScope (魔塔)",
            "base_url": "https://api-inference.modelscope.cn/v1",
            "models": [
                "Qwen/Qwen3-VL-4B-Instruct",
                "Qwen/Qwen3-VL-8B-Instruct",
                "Qwen/Qwen3-VL-32B-Instruct",
            ]
        },
        "tuzi": {
            "name": "Tuzi API",
            "base_url": "https://api.tu-zi.com/v1",
            "models": [
                "gpt-4o",
                "chatgpt-4o-latest",
                "gpt-4o-mini",
                "gpt-4-turbo",
                "gpt-3.5-turbo",
            ]
        }
    }
    
    @staticmethod
    def call_vision_api(image_path, system_prompt, user_prompt, api_key, base_url, model):
        """
        调用多模态 Vision API 进行图片描述生成
        
        Args:
            image_path: 图片文件路径
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            api_key: API 密钥
            base_url: API 基础 URL
            model: 模型名称
        
        Returns:
            str: API 返回的描述文本
        """
        # 1. 图片处理（如果太大则缩放到1024，减少传输时间）
        img = Image.open(image_path)
        if img.width > 1024 or img.height > 1024:
            img.thumbnail((1024, 1024))
        
        # 如果是RGBA模式，转换为RGB（去除透明通道）
        if img.mode == 'RGBA':
            # 创建白色背景
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])  # 使用alpha通道作为mask
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 转换为 Base64
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=95)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        img_base64 = f"data:image/jpeg;base64,{img_str}"

        # 2. 构建请求
        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": img_base64}},
                    {"type": "text", "text": user_prompt}
                ]}
            ],
            "max_tokens": 1024
        }
        
        # 3. 发送请求
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            print(f"API Response Status: {resp.status_code}")
            resp_json = resp.json()
            print(f"API Response: {resp_json}")
            
            if resp.status_code != 200:
                error_msg = resp_json.get('error', {}).get('message', resp_json.get('message', str(resp_json)))
                raise Exception(f"API Error ({resp.status_code}): {error_msg}")
            
            if "choices" in resp_json and len(resp_json["choices"]) > 0:
                return resp_json["choices"][0]["message"]["content"]
            else:
                raise Exception(f"API Error: No choices in response - {resp_json}")
        except requests.exceptions.Timeout:
            raise Exception("API请求超时，请稍后重试")
        except requests.exceptions.RequestException as e:
            raise Exception(f"网络请求错误: {str(e)}")
    
    @staticmethod
    def translate_text(text, api_key, base_url, model):
        """
        使用API翻译文本（中英互译）
        
        Args:
            text: 要翻译的文本
            api_key: API 密钥
            base_url: API 基础 URL
            model: 模型名称
        
        Returns:
            str: 翻译后的文本
        """
        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # 检测语言并翻译
        system_prompt = "You are a professional translator. Translate the given text. If the text is in Chinese, translate it to English. If the text is in English, translate it to Chinese. Only output the translated text, nothing else."
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            "max_tokens": 1024
        }
        
        try:
            # 翻译使用文本模型而非VL模型
            text_model = "Qwen/Qwen2.5-7B-Instruct"
            payload["model"] = text_model
            
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            resp_json = resp.json()
            
            if resp.status_code != 200:
                error_msg = resp_json.get('error', {}).get('message', resp_json.get('message', str(resp_json)))
                raise Exception(f"API Error ({resp.status_code}): {error_msg}")
            
            if "choices" in resp_json and len(resp_json["choices"]) > 0:
                return resp_json["choices"][0]["message"]["content"]
            else:
                raise Exception(f"API Error: No choices in response - {resp_json}")
        except requests.exceptions.Timeout:
            raise Exception("API请求超时，请稍后重试")
        except requests.exceptions.RequestException as e:
            raise Exception(f"网络请求错误: {str(e)}")

    @staticmethod
    def analyze_training(training_data, api_key, base_url, model=None, system_prompt=None):
        """
        使用大语言模型分析训练数据并给出优化建议
        
        Args:
            training_data: 训练数据字典，包含统计信息、配置等
            api_key: API 密钥
            base_url: API 基础 URL
            model: 模型名称（可选，默认使用文本模型）
            system_prompt: 系统提示词（可选，用户自定义）
        
        Returns:
            str: AI分析结果和建议
        """
        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # 使用用户提供的系统提示词，或使用默认提示词
        if not system_prompt:
            system_prompt = """你是一位专业的深度学习训练专家。请根据提供的训练日志数据，分析训练过程并给出专业的优化建议。

分析时请关注以下方面：
1. **训练收敛性分析**：Loss曲线是否平稳下降，是否存在震荡或过拟合迹象
2. **最优Epoch判断**：根据val_loss确定最佳保存点
3. **学习率建议**：根据Loss变化趋势判断学习率是否合适
4. **训练轮数建议**：是否需要更多epoch或提前停止
5. **其他优化建议**：如数据增强、正则化、batch size调整等

请用中文回答，格式清晰，使用Markdown格式输出。"""

        # 格式化训练数据
        stats = training_data.get('statistics', {})
        config = training_data.get('config', {})
        val_losses = training_data.get('val_losses', [])
        
        # 构建用户消息
        user_message = f"""请分析以下训练数据：

## 训练配置
- 模型名称: {config.get('model_name', '未知')}
- 保存名称: {config.get('save_name', '未知')}
- 学习率: {config.get('learning_rate', '未知')}
- 学习率调度器: {config.get('lr_scheduler', '未知')}
- Batch Size: {config.get('batch_size', '未知')}
- 优化器: {config.get('optimizer', '未知')}

## 训练统计
- 总Epoch数: {stats.get('total_epochs', 'N/A')}
- 最小Loss: {stats.get('min_loss', 'N/A')}
- 最大Loss: {stats.get('max_loss', 'N/A')}
- 平均Loss: {stats.get('avg_loss', 'N/A')}
- 最佳Epoch: {stats.get('best_epoch', 'N/A')}

## Top 10 最优Epoch
"""
        top_10 = stats.get('top_10', [])
        for i, item in enumerate(top_10[:10]):
            user_message += f"{i+1}. Epoch {item.get('epoch')}: val_loss = {item.get('val_loss')}\n"
        
        # 添加Loss变化趋势（采样部分数据点）
        if val_losses:
            user_message += "\n## Val Loss 变化趋势（采样）\n"
            sample_size = min(20, len(val_losses))
            step = max(1, len(val_losses) // sample_size)
            for i in range(0, len(val_losses), step):
                item = val_losses[i]
                user_message += f"Epoch {item.get('epoch')}: {item.get('val_loss')}\n"
        
        user_message += "\n请给出详细的分析和优化建议。"
        
        payload = {
            "model": model or "Qwen/Qwen2.5-7B-Instruct",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": 2048,
            "temperature": 0.7
        }
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            resp_json = resp.json()
            
            if resp.status_code != 200:
                error_msg = resp_json.get('error', {}).get('message', resp_json.get('message', str(resp_json)))
                raise Exception(f"API Error ({resp.status_code}): {error_msg}")
            
            if "choices" in resp_json and len(resp_json["choices"]) > 0:
                return resp_json["choices"][0]["message"]["content"]
            else:
                raise Exception(f"API Error: No choices in response - {resp_json}")
        except requests.exceptions.Timeout:
            raise Exception("AI分析请求超时，请稍后重试")
        except requests.exceptions.RequestException as e:
            raise Exception(f"网络请求错误: {str(e)}")
