"""
API 调用处理模块 - 支持多个 API 渠道
"""
import requests
import base64
import io
import time
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
                "Qwen/Qwen2.5-VL-72B-Instruct",
                "Qwen/Qwen2-VL-72B-Instruct",
            ]
        },
        "modelscope": {
            "name": "ModelScope (魔塔)",
            "base_url": "https://api-inference.modelscope.cn/v1",
            "models": [
                "Qwen/Qwen3-VL-8B-Instruct",
                "Qwen/Qwen3-VL-30B-A3B-Instruct",
                "Qwen/Qwen2.5-VL-7B-Instruct",
                "Qwen/Qwen2.5-VL-32B-Instruct",
                "Qwen/Qwen2.5-VL-72B-Instruct",
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
    def call_vision_api(image_path, system_prompt, user_prompt, api_key, base_url, model, crop_params=None):
        """
        调用多模态 Vision API 进行图片描述生成
        
        Args:
            image_path: 图片文件路径
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            api_key: API 密钥
            base_url: API 基础 URL
            model: 模型名称
            crop_params: 裁剪参数 (可选) {'crop_x', 'crop_y', 'crop_width', 'crop_height', 'target_width', 'target_height'}
        
        Returns:
            str: API 返回的描述文本
        """
        total_start_time = time.time()
        
        # 1. 图片处理（如果太大则缩放到1024，减少传输时间）
        print(f"[图片处理] 开始处理图片: {image_path}")
        img_start_time = time.time()
        
        img = Image.open(image_path)
        original_size = f"{img.width}x{img.height}"
        
        # 如果有裁剪参数，先进行裁剪
        if crop_params:
            crop_x = crop_params.get('crop_x', 0)
            crop_y = crop_params.get('crop_y', 0)
            crop_width = crop_params.get('crop_width', 1)
            crop_height = crop_params.get('crop_height', 1)
            target_width = crop_params.get('target_width', 1024)
            target_height = crop_params.get('target_height', 1024)
            
            # 计算实际裁剪坐标
            width, height = img.size
            left = int(crop_x * width)
            top = int(crop_y * height)
            right = int((crop_x + crop_width) * width)
            bottom = int((crop_y + crop_height) * height)
            
            # 确保坐标在有效范围内
            left = max(0, min(left, width))
            top = max(0, min(top, height))
            right = max(left + 1, min(right, width))
            bottom = max(top + 1, min(bottom, height))
            
            # 裁剪并缩放
            img = img.crop((left, top, right, bottom))
            img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            print(f"[图片处理] 已裁剪: ({left},{top})-({right},{bottom}) -> {target_width}x{target_height}")
        elif img.width > 1024 or img.height > 1024:
            img.thumbnail((1024, 1024))
            print(f"[图片处理] 图片已缩放: {original_size} -> {img.width}x{img.height}")
        
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
        img_bytes = buffered.getvalue()
        img_size_kb = len(img_bytes) / 1024
        img_str = base64.b64encode(img_bytes).decode()
        img_base64 = f"data:image/jpeg;base64,{img_str}"
        
        img_elapsed = time.time() - img_start_time
        print(f"[图片处理] 完成 | 尺寸: {img.width}x{img.height} | 大小: {img_size_kb:.1f}KB | 耗时: {img_elapsed:.2f}s")

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
        print(f"[API请求] 开始请求 | 模型: {model} | URL: {url}")
        api_start_time = time.time()
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            api_elapsed = time.time() - api_start_time
            total_elapsed = time.time() - total_start_time
            
            print(f"[API响应] 状态码: {resp.status_code} | API耗时: {api_elapsed:.2f}s | 总耗时: {total_elapsed:.2f}s")
            
            resp_json = resp.json()
            
            if resp.status_code != 200:
                error_msg = resp_json.get('error', {}).get('message', 
                            resp_json.get('errors', {}).get('message',
                            resp_json.get('message', str(resp_json))))
                print(f"[API错误] 状态码: {resp.status_code} | 错误: {error_msg}")
                raise Exception(f"API Error ({resp.status_code}): {error_msg}")
            
            if "choices" in resp_json and len(resp_json["choices"]) > 0:
                result = resp_json["choices"][0]["message"]["content"]
                print(f"[API成功] 返回内容长度: {len(result)} 字符 | 总耗时: {total_elapsed:.2f}s")
                return result
            else:
                print(f"[API错误] 响应中无 choices: {resp_json}")
                raise Exception(f"API Error: No choices in response - {resp_json}")
                
        except requests.exceptions.Timeout:
            api_elapsed = time.time() - api_start_time
            total_elapsed = time.time() - total_start_time
            print(f"[超时错误] ⏱️ API请求超时 | 已等待: {api_elapsed:.2f}s | 超时限制: 120s")
            raise Exception(f"API请求超时 (已等待 {api_elapsed:.1f}s)，请检查网络或稍后重试")
            
        except requests.exceptions.ProxyError as e:
            api_elapsed = time.time() - api_start_time
            print(f"[代理错误] 🔌 代理连接失败 | 已等待: {api_elapsed:.2f}s | 错误: {str(e)[:100]}")
            raise Exception(f"代理连接失败 (耗时 {api_elapsed:.1f}s)，请检查代理设置或关闭代理后重试")
            
        except requests.exceptions.ConnectionError as e:
            api_elapsed = time.time() - api_start_time
            print(f"[连接错误] 🔌 网络连接失败 | 已等待: {api_elapsed:.2f}s | 错误: {str(e)[:100]}")
            raise Exception(f"网络连接失败 (耗时 {api_elapsed:.1f}s)，请检查网络连接")
            
        except requests.exceptions.RequestException as e:
            api_elapsed = time.time() - api_start_time
            print(f"[网络错误] 🔌 请求异常 | 已等待: {api_elapsed:.2f}s | 错误: {str(e)[:100]}")
            raise Exception(f"网络请求错误 (耗时 {api_elapsed:.1f}s): {str(e)}")
    
    @staticmethod
    def translate_text(text, api_key, base_url, model, target_lang=None):
        """
        使用API翻译文本（中英互译）
        
        Args:
            text: 要翻译的文本
            api_key: API 密钥
            base_url: API 基础 URL
            model: 模型名称
            target_lang: 目标语言 ('en' 或 'zh')，如果不指定则自动检测
        
        Returns:
            str: 翻译后的文本
        """
        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # 根据目标语言设置提示词 - 使用 / 作为句子分隔符
        if target_lang == 'en':
            system_prompt = """You are a professional translator. Translate the given Chinese text to English.
IMPORTANT: The input text uses "/" as sentence separator. Keep the same "/" separator in your translation to mark sentence boundaries.
Only output the translated English text, nothing else."""
        elif target_lang == 'zh':
            system_prompt = """你是一个专业翻译。将给定的英文文本翻译成中文。
重要规则：
1. 输入文本中的每个英文句子（通常以句号结尾）需要单独翻译
2. 每翻译完一个完整的英文句子，在对应的中文翻译后面加上"/"作为分隔符
3. 最后一句翻译后也要加"/"
4. 只输出翻译后的中文文本，不要输出其他内容

示例：
输入：A girl with long hair. She is running. The sky is blue.
输出：一个长发女孩。/ 她正在奔跑。/ 天空是蓝色的。/"""
        else:
            # 自动检测语言并翻译
            system_prompt = """You are a professional translator. Translate the given text.
If the text is in Chinese, translate it to English. If the text is in English, translate it to Chinese.
IMPORTANT: Use "/" as sentence separator in your translation to mark sentence boundaries.
Only output the translated text, nothing else."""
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            "max_tokens": 1024
        }
        
        # Qwen3 模型需要禁用 thinking 模式
        if 'Qwen3' in model or 'qwen3' in model.lower():
            payload["enable_thinking"] = False
        
        print(f"[翻译请求] 开始翻译 | 文本长度: {len(text)} | 模型: {model} | 目标语言: {target_lang or '自动'}")
        start_time = time.time()
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            elapsed = time.time() - start_time
            
            print(f"[翻译响应] 状态码: {resp.status_code} | 耗时: {elapsed:.2f}s")
            resp_json = resp.json()
            
            if resp.status_code != 200:
                error_msg = resp_json.get('error', {}).get('message', 
                            resp_json.get('errors', {}).get('message',
                            resp_json.get('message', str(resp_json))))
                print(f"[翻译错误] 状态码: {resp.status_code} | 错误: {error_msg}")
                raise Exception(f"API Error ({resp.status_code}): {error_msg}")
            
            if "choices" in resp_json and len(resp_json["choices"]) > 0:
                result = resp_json["choices"][0]["message"]["content"]
                print(f"[翻译成功] 结果长度: {len(result)} | 耗时: {elapsed:.2f}s")
                return result
            else:
                print(f"[翻译错误] 响应中无 choices: {resp_json}")
                raise Exception(f"API Error: No choices in response - {resp_json}")
                
        except requests.exceptions.Timeout:
            elapsed = time.time() - start_time
            print(f"[超时错误] ⏱️ 翻译请求超时 | 已等待: {elapsed:.2f}s | 超时限制: 60s")
            raise Exception(f"翻译请求超时 (已等待 {elapsed:.1f}s)")
            
        except requests.exceptions.ProxyError as e:
            elapsed = time.time() - start_time
            print(f"[代理错误] 🔌 代理连接失败 | 已等待: {elapsed:.2f}s")
            raise Exception(f"代理连接失败，请检查代理设置")
            
        except requests.exceptions.ConnectionError as e:
            elapsed = time.time() - start_time
            print(f"[连接错误] 🔌 网络连接失败 | 已等待: {elapsed:.2f}s")
            raise Exception(f"网络连接失败，请检查网络")
            
        except requests.exceptions.RequestException as e:
            elapsed = time.time() - start_time
            print(f"[网络错误] 🔌 请求异常 | 已等待: {elapsed:.2f}s | 错误: {str(e)[:80]}")
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
        
        print(f"[AI分析] 开始分析训练数据 | 模型: {payload['model']}")
        start_time = time.time()
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            elapsed = time.time() - start_time
            
            print(f"[AI分析响应] 状态码: {resp.status_code} | 耗时: {elapsed:.2f}s")
            resp_json = resp.json()
            
            if resp.status_code != 200:
                error_msg = resp_json.get('error', {}).get('message', 
                            resp_json.get('errors', {}).get('message',
                            resp_json.get('message', str(resp_json))))
                print(f"[AI分析错误] 状态码: {resp.status_code} | 错误: {error_msg}")
                raise Exception(f"API Error ({resp.status_code}): {error_msg}")
            
            if "choices" in resp_json and len(resp_json["choices"]) > 0:
                result = resp_json["choices"][0]["message"]["content"]
                print(f"[AI分析成功] 结果长度: {len(result)} | 耗时: {elapsed:.2f}s")
                return result
            else:
                print(f"[AI分析错误] 响应中无 choices: {resp_json}")
                raise Exception(f"API Error: No choices in response - {resp_json}")
                
        except requests.exceptions.Timeout:
            elapsed = time.time() - start_time
            print(f"[超时错误] ⏱️ AI分析请求超时 | 已等待: {elapsed:.2f}s | 超时限制: 120s")
            raise Exception(f"AI分析请求超时 (已等待 {elapsed:.1f}s)，请稍后重试")
            
        except requests.exceptions.ProxyError as e:
            elapsed = time.time() - start_time
            print(f"[代理错误] 🔌 代理连接失败 | 已等待: {elapsed:.2f}s")
            raise Exception(f"代理连接失败，请检查代理设置")
            
        except requests.exceptions.ConnectionError as e:
            elapsed = time.time() - start_time
            print(f"[连接错误] 🔌 网络连接失败 | 已等待: {elapsed:.2f}s")
            raise Exception(f"网络连接失败，请检查网络")
            
        except requests.exceptions.RequestException as e:
            elapsed = time.time() - start_time
            print(f"[网络错误] 🔌 请求异常 | 已等待: {elapsed:.2f}s | 错误: {str(e)[:80]}")
            raise Exception(f"网络请求错误: {str(e)}")
