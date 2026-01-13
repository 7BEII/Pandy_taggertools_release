"""
图片处理模块 - 图片加载、缩略图生成、导出 ZIP
"""
import os
import io
import base64
import zipfile
from PIL import Image
from datetime import datetime


class ImageProcessor:
    """图片处理器"""
    
    @staticmethod
    def create_thumbnail(image_path, size=(1024, 1024)):
        """
        生成缩略图并返回 Base64 编码
        保持 PNG 透明通道
        
        Args:
            image_path: 图片路径
            size: 缩略图尺寸（提高到1024x1024以保证清晰度）
        
        Returns:
            str: Base64 编码的缩略图
        """
        try:
            img = Image.open(image_path)
            original_mode = img.mode
            
            # 检查是否有透明通道
            has_alpha = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)
            
            if has_alpha:
                # 保持透明通道，转换为 RGBA
                if img.mode == 'P':
                    img = img.convert('RGBA')
                elif img.mode == 'LA':
                    img = img.convert('RGBA')
                
                # 生成缩略图（使用LANCZOS高质量重采样）
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                # 保存为 PNG 以保持透明
                buffered = io.BytesIO()
                img.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                return f"data:image/png;base64,{img_str}"
            else:
                # 无透明通道，转换为 RGB 保存为 JPEG
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 生成缩略图（使用LANCZOS高质量重采样）
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                # 保存为 JPEG
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG", quality=95)
                img_str = base64.b64encode(buffered.getvalue()).decode()
                return f"data:image/jpeg;base64,{img_str}"
        except Exception as e:
            print(f"❌ Error creating thumbnail for {image_path}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def crop_image(image_path, crop_x, crop_y, crop_width, crop_height, target_width, target_height):
        """
        裁剪图片指定区域并缩放到目标尺寸（覆盖原文件）
        
        Args:
            image_path: 图片路径
            crop_x: 裁剪区域左上角X坐标（相对于原图的比例 0-1）
            crop_y: 裁剪区域左上角Y坐标（相对于原图的比例 0-1）
            crop_width: 裁剪区域宽度（相对于原图的比例 0-1）
            crop_height: 裁剪区域高度（相对于原图的比例 0-1）
            target_width: 目标宽度
            target_height: 目标高度
        
        Returns:
            str: 裁剪后图片的Base64编码（用于预览），失败返回None
        """
        try:
            img = Image.open(image_path)
            width, height = img.size
            
            # 计算实际裁剪坐标
            left = int(crop_x * width)
            top = int(crop_y * height)
            right = int((crop_x + crop_width) * width)
            bottom = int((crop_y + crop_height) * height)
            
            # 确保坐标在有效范围内
            left = max(0, min(left, width))
            top = max(0, min(top, height))
            right = max(left + 1, min(right, width))
            bottom = max(top + 1, min(bottom, height))
            
            # 裁剪图片
            cropped = img.crop((left, top, right, bottom))
            
            # 缩放到目标尺寸
            resized = cropped.resize((target_width, target_height), Image.Resampling.LANCZOS)
            
            # 保存图片（覆盖原文件）
            _, ext = os.path.splitext(image_path)
            ext = ext.lower()
            
            if ext in ['.jpg', '.jpeg']:
                if resized.mode == 'RGBA':
                    background = Image.new('RGB', resized.size, (255, 255, 255))
                    background.paste(resized, mask=resized.split()[3])
                    resized = background
                elif resized.mode != 'RGB':
                    resized = resized.convert('RGB')
                resized.save(image_path, format='JPEG', quality=95)
            elif ext == '.png':
                resized.save(image_path, format='PNG')
            elif ext == '.webp':
                resized.save(image_path, format='WEBP', quality=95)
            else:
                resized.save(image_path)
            
            # 生成预览缩略图
            buffered = io.BytesIO()
            if resized.mode == 'RGBA':
                bg = Image.new('RGB', resized.size, (255, 255, 255))
                bg.paste(resized, mask=resized.split()[3])
                bg.save(buffered, format="JPEG", quality=95)
            else:
                if resized.mode != 'RGB':
                    resized = resized.convert('RGB')
                resized.save(buffered, format="JPEG", quality=95)
            
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            img.close()
            cropped.close()
            resized.close()
            
            print(f"Cropped {image_path}: ({left},{top})-({right},{bottom}) -> {target_width}x{target_height}")
            return f"data:image/jpeg;base64,{img_str}"
        except Exception as e:
            print(f"Error cropping image {image_path}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def crop_image_to_base64(image_path, crop_x, crop_y, crop_width, crop_height, target_width, target_height, fill_background=False, background_color='#FFFFFF', image_scale=1.0, offset_x=0, offset_y=0):
        """
        裁剪图片指定区域并返回Base64（不保存，保留原图）
        
        Args:
            image_path: 图片路径
            crop_x: 裁剪区域左上角X坐标（相对于原图的比例 0-1）
            crop_y: 裁剪区域左上角Y坐标（相对于原图的比例 0-1）
            crop_width: 裁剪区域宽度（相对于原图的比例 0-1）
            crop_height: 裁剪区域高度（相对于原图的比例 0-1）
            target_width: 目标宽度
            target_height: 目标高度
            fill_background: 是否填充透明背景
            background_color: 背景填充颜色（十六进制，如 '#FFFFFF'）
            image_scale: 图片缩放比例（0.5-1.0），小于1时图片会缩小，周围填充背景
            offset_x: 缩小图片时的X偏移（-0.5到0.5）
            offset_y: 缩小图片时的Y偏移（-0.5到0.5）
        
        Returns:
            tuple: (缩略图Base64, 裁剪后图片bytes用于API调用)，失败返回(None, None)
        """
        try:
            img = Image.open(image_path)
            width, height = img.size
            
            # 如果图片被缩小（scale < 1），需要特殊处理
            # 与前端 getScaledImageStyle 方法保持一致
            if image_scale < 1.0:
                img_aspect = width / height
                target_aspect = target_width / target_height
                
                # 计算图片在目标画布中的 contain 尺寸（与前端一致）
                if img_aspect > target_aspect:
                    # 图片更宽，以宽度为基准
                    contain_width = target_width
                    contain_height = target_width / img_aspect
                else:
                    # 图片更高，以高度为基准
                    contain_height = target_height
                    contain_width = target_height * img_aspect
                
                # 按 scale 缩小
                scaled_width = int(contain_width * image_scale)
                scaled_height = int(contain_height * image_scale)
                
                # 确保尺寸至少为1
                scaled_width = max(1, scaled_width)
                scaled_height = max(1, scaled_height)
                
                # 缩放原图
                scaled = img.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
                
                # 计算位置（与前端 getScaledImageStyle 一致）
                # 基础位置（居中）
                base_left = (target_width - scaled_width) / 2
                base_top = (target_height - scaled_height) / 2
                
                # 偏移量计算（与前端一致）
                # 前端: offsetXPercent = (offsetX / maxOffset) * baseLeft
                # 前端: left = baseLeft + offsetXPercent
                max_offset = (1 - image_scale) / 2
                if max_offset > 0:
                    offset_x_pixels = (offset_x / max_offset) * base_left
                    offset_y_pixels = (offset_y / max_offset) * base_top
                else:
                    offset_x_pixels = 0
                    offset_y_pixels = 0
                
                paste_x = int(base_left + offset_x_pixels)
                paste_y = int(base_top + offset_y_pixels)
                
                # 确保不超出画布边界
                paste_x = max(0, min(paste_x, target_width - scaled_width))
                paste_y = max(0, min(paste_y, target_height - scaled_height))
                
                print(f"[crop_scaled] img={width}x{height}, target={target_width}x{target_height}, scale={image_scale}, offset=({offset_x},{offset_y})")
                print(f"[crop_scaled] contain={contain_width:.1f}x{contain_height:.1f}, scaled={scaled_width}x{scaled_height}")
                print(f"[crop_scaled] base=({base_left:.1f},{base_top:.1f}), paste=({paste_x},{paste_y})")
                
                # 解析背景颜色
                bg_color = background_color.lstrip('#')
                rgb = tuple(int(bg_color[i:i+2], 16) for i in (0, 2, 4))
                
                if fill_background or img.mode != 'RGBA':
                    # 填充背景色或非透明图片
                    canvas = Image.new('RGB', (target_width, target_height), rgb)
                    if scaled.mode == 'RGBA':
                        canvas.paste(scaled, (paste_x, paste_y), mask=scaled.split()[3])
                    else:
                        if scaled.mode != 'RGB':
                            scaled = scaled.convert('RGB')
                        canvas.paste(scaled, (paste_x, paste_y))
                    resized = canvas
                    # 保存为 JPEG
                    thumb_buffer = io.BytesIO()
                    resized.save(thumb_buffer, format="JPEG", quality=95)
                    thumb_base64 = f"data:image/jpeg;base64,{base64.b64encode(thumb_buffer.getvalue()).decode()}"
                    api_buffer = io.BytesIO()
                    resized.save(api_buffer, format="JPEG", quality=95)
                    api_bytes = api_buffer.getvalue()
                else:
                    # 保持透明，创建 RGBA 画布
                    canvas = Image.new('RGBA', (target_width, target_height), (0, 0, 0, 0))
                    canvas.paste(scaled, (paste_x, paste_y))
                    resized = canvas
                    # 保存为 PNG
                    thumb_buffer = io.BytesIO()
                    resized.save(thumb_buffer, format="PNG")
                    thumb_base64 = f"data:image/png;base64,{base64.b64encode(thumb_buffer.getvalue()).decode()}"
                    api_buffer = io.BytesIO()
                    resized.save(api_buffer, format="PNG")
                    api_bytes = api_buffer.getvalue()
                
                img.close()
                scaled.close()
                
                print(f"Cropped (scaled) {image_path}: scale={image_scale}, offset=({offset_x}, {offset_y}) -> {target_width}x{target_height}, fill_bg={fill_background}")
                return thumb_base64, api_bytes
            
            # 正常裁剪流程（scale = 1）
            # 计算实际裁剪坐标
            left = int(crop_x * width)
            top = int(crop_y * height)
            right = int((crop_x + crop_width) * width)
            bottom = int((crop_y + crop_height) * height)
            
            # 确保坐标在有效范围内
            left = max(0, min(left, width))
            top = max(0, min(top, height))
            right = max(left + 1, min(right, width))
            bottom = max(top + 1, min(bottom, height))
            
            # 裁剪图片
            cropped = img.crop((left, top, right, bottom))
            
            # 缩放到目标尺寸
            resized = cropped.resize((target_width, target_height), Image.Resampling.LANCZOS)
            
            # 处理透明背景
            if resized.mode == 'RGBA':
                if fill_background:
                    # 填充背景色
                    # 解析十六进制颜色
                    bg_color = background_color.lstrip('#')
                    rgb = tuple(int(bg_color[i:i+2], 16) for i in (0, 2, 4))
                    background = Image.new('RGB', resized.size, rgb)
                    background.paste(resized, mask=resized.split()[3])
                    resized = background
                    # 保存为 JPEG
                    thumb_buffer = io.BytesIO()
                    resized.save(thumb_buffer, format="JPEG", quality=95)
                    thumb_base64 = f"data:image/jpeg;base64,{base64.b64encode(thumb_buffer.getvalue()).decode()}"
                    api_buffer = io.BytesIO()
                    resized.save(api_buffer, format="JPEG", quality=95)
                    api_bytes = api_buffer.getvalue()
                else:
                    # 保持透明，保存为 PNG
                    thumb_buffer = io.BytesIO()
                    resized.save(thumb_buffer, format="PNG")
                    thumb_base64 = f"data:image/png;base64,{base64.b64encode(thumb_buffer.getvalue()).decode()}"
                    api_buffer = io.BytesIO()
                    resized.save(api_buffer, format="PNG")
                    api_bytes = api_buffer.getvalue()
            else:
                # 非透明图片，转换为 RGB 保存为 JPEG
                if resized.mode != 'RGB':
                    resized = resized.convert('RGB')
                thumb_buffer = io.BytesIO()
                resized.save(thumb_buffer, format="JPEG", quality=95)
                thumb_base64 = f"data:image/jpeg;base64,{base64.b64encode(thumb_buffer.getvalue()).decode()}"
                api_buffer = io.BytesIO()
                resized.save(api_buffer, format="JPEG", quality=95)
                api_bytes = api_buffer.getvalue()
            
            img.close()
            cropped.close()
            
            print(f"Cropped (no save) {image_path}: ({left},{top})-({right},{bottom}) -> {target_width}x{target_height}, fill_bg={fill_background}")
            return thumb_base64, api_bytes
        except Exception as e:
            print(f"Error cropping image {image_path}: {e}")
            import traceback
            traceback.print_exc()
            return None, None
    
    @staticmethod
    def get_crop_preview(image_path, crop_x, crop_y, crop_width, crop_height, target_width, target_height):
        """
        获取裁剪预览（不保存，仅返回预览图）
        
        Args:
            image_path: 图片路径
            crop_x: 裁剪区域左上角X坐标（相对于原图的比例 0-1）
            crop_y: 裁剪区域左上角Y坐标（相对于原图的比例 0-1）
            crop_width: 裁剪区域宽度（相对于原图的比例 0-1）
            crop_height: 裁剪区域高度（相对于原图的比例 0-1）
            target_width: 目标宽度
            target_height: 目标高度
        
        Returns:
            str: 裁剪预览图的Base64编码，失败返回None
        """
        try:
            img = Image.open(image_path)
            width, height = img.size
            
            # 计算实际裁剪坐标
            left = int(crop_x * width)
            top = int(crop_y * height)
            right = int((crop_x + crop_width) * width)
            bottom = int((crop_y + crop_height) * height)
            
            # 确保坐标在有效范围内
            left = max(0, min(left, width))
            top = max(0, min(top, height))
            right = max(left + 1, min(right, width))
            bottom = max(top + 1, min(bottom, height))
            
            # 裁剪图片
            cropped = img.crop((left, top, right, bottom))
            
            # 缩放到目标尺寸
            resized = cropped.resize((target_width, target_height), Image.Resampling.LANCZOS)
            
            # 生成预览
            buffered = io.BytesIO()
            if resized.mode == 'RGBA':
                bg = Image.new('RGB', resized.size, (255, 255, 255))
                bg.paste(resized, mask=resized.split()[3])
                bg.save(buffered, format="JPEG", quality=85)
            else:
                if resized.mode != 'RGB':
                    resized = resized.convert('RGB')
                resized.save(buffered, format="JPEG", quality=85)
            
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            img.close()
            cropped.close()
            resized.close()
            
            return f"data:image/jpeg;base64,{img_str}"
        except Exception as e:
            print(f"Error getting crop preview for {image_path}: {e}")
            return None

    @staticmethod
    def resize_image_by_longest_edge(image_path, max_size, allow_upscale=True):
        """
        按最长边缩放图片并保存（覆盖原文件）
        
        Args:
            image_path: 图片路径
            max_size: 最长边目标尺寸
            allow_upscale: 是否允许放大图片
        
        Returns:
            bool: 是否进行了缩放
        """
        try:
            img = Image.open(image_path)
            width, height = img.size
            
            # 如果图片尺寸等于目标尺寸，不需要缩放
            if max(width, height) == max_size:
                img.close()
                return False
            
            # 如果不允许放大且图片尺寸小于目标尺寸，不缩放
            if not allow_upscale and max(width, height) < max_size:
                img.close()
                return False
            
            # 计算缩放比例
            if width >= height:
                new_width = max_size
                new_height = int(height * max_size / width)
            else:
                new_height = max_size
                new_width = int(width * max_size / height)
            
            # 缩放图片
            img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 保存图片（保持原格式）
            _, ext = os.path.splitext(image_path)
            ext = ext.lower()
            
            if ext in ['.jpg', '.jpeg']:
                # 处理RGBA模式
                if img_resized.mode == 'RGBA':
                    background = Image.new('RGB', img_resized.size, (255, 255, 255))
                    background.paste(img_resized, mask=img_resized.split()[3])
                    img_resized = background
                img_resized.save(image_path, format='JPEG', quality=95)
            elif ext == '.png':
                img_resized.save(image_path, format='PNG')
            elif ext == '.webp':
                img_resized.save(image_path, format='WEBP', quality=95)
            else:
                img_resized.save(image_path)
            
            img.close()
            img_resized.close()
            print(f"Resized {image_path}: {width}x{height} -> {new_width}x{new_height}")
            return True
        except Exception as e:
            print(f"Error resizing image {image_path}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def load_image_with_txt(image_path):
        """
        加载图片并检查同名 txt 文件
        
        Args:
            image_path: 图片路径
        
        Returns:
            dict: 图片信息
        """
        try:
            img = Image.open(image_path)
            width, height = img.size
            
            # 检查同名 txt
            txt_path = os.path.splitext(image_path)[0] + ".txt"
            text_content = ""
            status = "idle"
            
            if os.path.exists(txt_path):
                with open(txt_path, "r", encoding="utf-8") as f:
                    text_content = f.read()
                status = "success"
            
            # 生成缩略图
            thumbnail = ImageProcessor.create_thumbnail(image_path)
            
            return {
                "path": image_path,
                "name": os.path.basename(image_path),
                "width": width,
                "height": height,
                "text": text_content,
                "status": status,
                "thumbnail": thumbnail,
                "selected": False
            }
        except Exception as e:
            print(f"Error loading image {image_path}: {e}")
            return None
    
    @staticmethod
    def export_to_zip(images_data, output_path=None):
        """
        导出图片和文本到 ZIP 文件
        
        Args:
            images_data: 图片数据列表
            output_path: 输出路径（可选）
        
        Returns:
            str: ZIP 文件路径
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"dataset_{timestamp}.zip"
        
        try:
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for idx, item in enumerate(images_data):
                    # 确定文件名
                    base_name = item.get("export_name", f"image_{idx:04d}")
                    _, ext = os.path.splitext(item["path"])
                    
                    # 处理图片（如果有 resize 需求）
                    if "resize_target" in item:
                        img = Image.open(item["path"])
                        img.thumbnail((item["resize_target"], item["resize_target"]))
                        img_byte_arr = io.BytesIO()
                        save_fmt = "JPEG" if ext.lower() in ['.jpg', '.jpeg'] else "PNG"
                        img.save(img_byte_arr, format=save_fmt)
                        zf.writestr(f"{base_name}{ext}", img_byte_arr.getvalue())
                    else:
                        # 直接写入原图
                        zf.write(item["path"], f"{base_name}{ext}")
                    
                    # 写入文本
                    if item.get("text"):
                        zf.writestr(f"{base_name}.txt", item["text"])
            
            return output_path
        except Exception as e:
            raise Exception(f"Export failed: {e}")

    @staticmethod
    def export_pairs_to_zip(pairs_data, output_path=None, image_format='png', naming_config=None, include_images=True, include_txt=True):
        """
        导出成对图片为训练格式zip
        
        Args:
            pairs_data: 成对图片数据列表
            output_path: 输出路径（完整zip文件路径）
            image_format: 图片格式 'png' 或 'jpg'
            naming_config: 命名配置 {
                'mode': 'default' 或 't2itrainer',
                'suffix_left': 原图1后缀 (默认'R'),
                'suffix_left2': 原图2后缀 (默认'G'),
                'suffix_right': 目标图后缀 (默认'T'),
                'txt_follows': txt跟随 'left' 或 'right'
            }
        
        Returns:
            str: 导出的zip文件路径
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"editing_pairs_{timestamp}.zip"

        # 确保格式正确
        image_format = image_format.lower()
        if image_format not in ['png', 'jpg', 'jpeg']:
            image_format = 'png'
        if image_format == 'jpeg':
            image_format = 'jpg'

        # 解析命名配置
        if naming_config is None:
            naming_config = {}
        naming_mode = naming_config.get('mode', 'default')
        suffix_left = naming_config.get('suffix_left', 'R')
        suffix_left2 = naming_config.get('suffix_left2', 'G')
        suffix_right = naming_config.get('suffix_right', 'T')
        txt_follows = naming_config.get('txt_follows', 'right')
        prefix_letter = naming_config.get('prefix_letter', False)
        folder_prefix = naming_config.get('folder_prefix', 'aitoolkit')
        unified_file_prefix = naming_config.get('unified_file_prefix', 'T')
        unified_file_prefix = naming_config.get('unified_file_prefix', 'T')
        txt_folder_follows = naming_config.get('txt_folder_follows', 'right')
        runinghub_start = naming_config.get('runinghub_start', 'start')
        runinghub_end = naming_config.get('runinghub_end', 'end')
        prefix_letter = naming_config.get('prefix_letter', False)

        try:
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for idx, pair in enumerate(pairs_data):
                    base_num = idx + 1
                    left = pair.get("left")
                    right = pair.get("right")

                    def _write_image_to_zip(src_path, arc_name):
                        _, src_ext = os.path.splitext(src_path)
                        src_ext = src_ext.lower()
                        target_ext = f'.{image_format}'

                        if not include_images:
                            return
                        if src_ext == target_ext or (image_format == 'jpg' and src_ext in ['.jpg', '.jpeg']):
                            zf.write(src_path, arc_name)
                            return

                        img = Image.open(src_path)
                        if img.mode == 'RGBA' and image_format == 'jpg':
                            img = img.convert('RGB')
                        img_buffer = io.BytesIO()
                        if image_format == 'jpg':
                            img.save(img_buffer, format='JPEG', quality=95)
                        else:
                            img.save(img_buffer, format='PNG')
                        zf.writestr(arc_name, img_buffer.getvalue())

                    left_path = (left or {}).get("path")
                    left2_path = (pair.get("left2") or {}).get("path")  # 原图2（如果有）
                    right_path = (right or {}).get("path")

                    if naming_mode == 't2itrainer':
                        # T2itrainer模式: {num}_{suffix}.{fmt}
                        # 原图1: 1_R.png, 2_R.png ...
                        # 原图2: 1_G.png, 2_G.png ... (如果有)
                        # 目标图: 1_T.png, 2_T.png ...
                        # txt: 跟随原图或目标图命名
                        
                        if left_path and os.path.exists(left_path):
                            name = f"{suffix_left}_{base_num}.{image_format}" if prefix_letter else f"{base_num}_{suffix_left}.{image_format}"
                            _write_image_to_zip(left_path, name)
                        
                        if left2_path and os.path.exists(left2_path):
                            name = f"{suffix_left2}_{base_num}.{image_format}" if prefix_letter else f"{base_num}_{suffix_left2}.{image_format}"
                            _write_image_to_zip(left2_path, name)
                        
                        if right_path and os.path.exists(right_path):
                            name = f"{suffix_right}_{base_num}.{image_format}" if prefix_letter else f"{base_num}_{suffix_right}.{image_format}"
                            _write_image_to_zip(right_path, name)
                        
                        if pair.get("text") and include_txt:
                            if txt_follows == 'left':
                                if prefix_letter:
                                    txt_name = f"{suffix_left}_{base_num}.txt"
                                else:
                                    txt_name = f"{base_num}_{suffix_left}.txt"
                            else:
                                if prefix_letter:
                                    txt_name = f"{suffix_right}_{base_num}.txt"
                                else:
                                    txt_name = f"{base_num}_{suffix_right}.txt"
                            zf.writestr(txt_name, pair["text"])

                    elif naming_mode == 'aitoolkit':
                        # AIToolkit模式: 分文件夹放置
                        # 子文件夹: {suffix_left}, {suffix_left2}, {suffix_right}
                        # 文件命名: {unified_file_prefix}_{num}.{fmt}

                        left_folder = f"{suffix_left}"
                        left2_folder = f"{suffix_left2}"
                        right_folder = f"{suffix_right}"

                        if left_path and os.path.exists(left_path):
                            fname = f"{unified_file_prefix}_{base_num}.{image_format}"
                            _write_image_to_zip(left_path, f"{left_folder}/{fname}")

                        if left2_path and os.path.exists(left2_path):
                            fname = f"{unified_file_prefix}_{base_num}.{image_format}"
                            _write_image_to_zip(left2_path, f"{left2_folder}/{fname}")

                        if right_path and os.path.exists(right_path):
                            fname = f"{unified_file_prefix}_{base_num}.{image_format}"
                            _write_image_to_zip(right_path, f"{right_folder}/{fname}")

                        if pair.get("text") and include_txt:
                            # txt命名跟随（与图片命名同逻辑）
                            txt_filename = f"{unified_file_prefix}_{base_num}.txt"
                            # txt放置文件夹跟随
                            if txt_folder_follows == 'left':
                                txt_folder = left_folder
                            else:
                                txt_folder = right_folder
                            zf.writestr(f"{txt_folder}/{txt_filename}", pair["text"])
                    
                    elif naming_mode == 'runinghub':
                        # RuningHub模式: {num}_{start}.{fmt}, {num}_{end}.{fmt}
                        # 原图: 1_start.png, 2_start.png ...
                        # 目标图: 1_end.png, 2_end.png ...
                        
                        if left_path and os.path.exists(left_path):
                            _write_image_to_zip(left_path, f"{base_num}_{runinghub_start}.{image_format}")
                        
                        if right_path and os.path.exists(right_path):
                            _write_image_to_zip(right_path, f"{base_num}_{runinghub_end}.{image_format}")
                        
                        if pair.get("text") and include_txt:
                            txt_name = f"{base_num}_{runinghub_end}.txt"
                            zf.writestr(txt_name, pair["text"])
                    
                    else:
                        # 默认模式: {num}_0.{fmt}, {num}_1.{fmt}
                        base_name = pair.get("export_name") or str(base_num)
                        
                        if right_path and os.path.exists(right_path):
                            _write_image_to_zip(right_path, f"{base_name}_1.{image_format}")

                        if left_path and os.path.exists(left_path):
                            _write_image_to_zip(left_path, f"{base_name}_0.{image_format}")

                        if pair.get("text") and include_txt:
                            zf.writestr(f"{base_name}_1.txt", pair["text"])

            return output_path
        except Exception as e:
            raise Exception(f"Export failed: {e}")
    
    @staticmethod
    def export_namefilter_to_zip(pairs_data, output_path=None, formats=None, filter_keyword=None):
        """
        按文件名关键字导出，保留原始文件名（可多选 PNG/JPG/TXT）
        Args:
            pairs_data: 成对图片数据列表
            output_path: 输出 zip 路径
            formats: 列表，例如 ['png','jpg','txt']
        Returns:
            str: 输出 zip 路径
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"namefilter_{timestamp}.zip"

        if formats is None:
            formats = ['png', 'txt']

        formats = [f.lower() for f in formats]

        try:
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                written_basenames = set()
                for pair in pairs_data:
                    # 考察左右两侧文件，若文件名包含关键字，按 formats 导出
                    paths = []
                    left_path = (pair.get("left") or {}).get("path")
                    right_path = (pair.get("right") or {}).get("path")
                    if left_path:
                        paths.append(left_path)
                    if right_path:
                        paths.append(right_path)

                    for src_path in paths:
                        # 如果设置了关键字过滤，则仅导出文件名包含关键字的文件
                        if filter_keyword:
                            fk = filter_keyword.lower()
                            if fk not in os.path.basename(src_path).lower():
                                continue
                        if not src_path or not os.path.exists(src_path):
                            continue
                        base_name, src_ext = os.path.splitext(os.path.basename(src_path))
                        src_ext = src_ext.lower()

                        # 按原文件格式输出（不做格式转换），formats 作为允许的格式集合进行筛选
                        fmt_map = {
                            '.png': 'png',
                            '.jpg': 'jpg',
                            '.jpeg': 'jpg',
                            '.webp': 'webp'
                        }
                        src_fmt = fmt_map.get(src_ext, src_ext.lstrip('.'))

                        # 防止同名文件被重复写入（不同扩展），优先保留首次碰到的原始文件
                        if base_name in written_basenames:
                            continue

                        # 只在用户选择的格式集合中包含源文件格式时才导出该图片（保持原始扩展）
                        if src_fmt in formats or not any(f in ['png', 'jpg', 'webp'] for f in formats):
                            # 保留原文件名及扩展
                            zf.write(src_path, f"{base_name}{src_ext}")
                            written_basenames.add(base_name)

                        # TXT 单独处理：如果用户选择了 txt，则导出同名 txt（若存在）
                        if 'txt' in formats:
                            txt_path = os.path.splitext(src_path)[0] + ".txt"
                            if os.path.exists(txt_path):
                                with open(txt_path, "rb") as f:
                                    content = f.read()
                                zf.writestr(f"{base_name}.txt", content)

            return output_path
        except Exception as e:
            raise Exception(f"Namefilter export failed: {e}")

    @staticmethod
    def export_namefilter_to_folder(pairs_data, output_path, formats=None, filter_keyword=None):
        """
        按文件名关键字导出到文件夹，保留原始文件名（可多选 PNG/JPG/TXT）
        """
        from shutil import copy2

        if formats is None:
            formats = ['png', 'txt']
        formats = [f.lower() for f in formats]

        try:
            os.makedirs(output_path, exist_ok=True)

            for pair in pairs_data:
                paths = []
                left_path = (pair.get("left") or {}).get("path")
                right_path = (pair.get("right") or {}).get("path")
                if left_path:
                    paths.append(left_path)
                if right_path:
                    paths.append(right_path)

                written_basenames = set()
                for src_path in paths:
                    # 如果设置了关键字过滤，则仅导出文件名包含关键字的文件
                    if filter_keyword:
                        fk = filter_keyword.lower()
                        if fk not in os.path.basename(src_path).lower():
                            continue
                    if not src_path or not os.path.exists(src_path):
                        continue
                    base_name, src_ext = os.path.splitext(os.path.basename(src_path))
                    src_ext = src_ext.lower()

                    # 按原文件格式输出（不做格式转换），formats 作为允许的格式集合进行筛选
                    fmt_map = {
                        '.png': 'png',
                        '.jpg': 'jpg',
                        '.jpeg': 'jpg',
                        '.webp': 'webp'
                    }
                    src_fmt = fmt_map.get(src_ext, src_ext.lstrip('.'))

                    # 防止同名文件被重复写入（不同扩展），优先保留首次碰到的原始文件
                    if base_name in written_basenames:
                        continue

                    # 只在用户选择的格式集合中包含源文件格式时才导出该图片（保持原始扩展）
                    if src_fmt in formats or not any(f in ['png', 'jpg', 'webp'] for f in formats):
                        dest = os.path.join(output_path, os.path.basename(src_path))
                        copy2(src_path, dest)
                        written_basenames.add(base_name)

                    # TXT
                    if 'txt' in formats:
                        txt_path = os.path.splitext(src_path)[0] + ".txt"
                        if os.path.exists(txt_path):
                            copy2(txt_path, os.path.join(output_path, f"{base_name}.txt"))

            return output_path
        except Exception as e:
            raise Exception(f"Namefilter export to folder failed: {e}")
    
    @staticmethod
    def export_pairs_to_folder(pairs_data, output_path, image_format='png', naming_config=None, include_images=True, include_txt=True):
        """
        导出成对图片为训练格式文件夹
        
        Args:
            pairs_data: 成对图片数据列表
            output_path: 输出文件夹路径
            image_format: 图片格式 'png' 或 'jpg'
            naming_config: 命名配置
        
        Returns:
            str: 导出的文件夹路径
        """
        from shutil import copy2
        
        # 确保格式正确
        image_format = image_format.lower()
        if image_format not in ['png', 'jpg', 'jpeg']:
            image_format = 'png'
        if image_format == 'jpeg':
            image_format = 'jpg'

        # 解析命名配置
        if naming_config is None:
            naming_config = {}
        naming_mode = naming_config.get('mode', 'default')
        suffix_left = naming_config.get('suffix_left', 'R')
        suffix_left2 = naming_config.get('suffix_left2', 'G')
        suffix_right = naming_config.get('suffix_right', 'T')
        txt_follows = naming_config.get('txt_follows', 'right')
        folder_prefix = naming_config.get('folder_prefix', 'aitoolkit')
        unified_file_prefix = naming_config.get('unified_file_prefix', 'T')
        txt_folder_follows = naming_config.get('txt_folder_follows', 'right')
        runinghub_start = naming_config.get('runinghub_start', 'start')
        runinghub_end = naming_config.get('runinghub_end', 'end')
        prefix_letter = naming_config.get('prefix_letter', False)

        try:
            # 创建输出目录
            os.makedirs(output_path, exist_ok=True)
            
            def _write_image_to_folder(src_path, dest_path):
                _, src_ext = os.path.splitext(src_path)
                src_ext = src_ext.lower()
                target_ext = f'.{image_format}'

                if not include_images:
                    return
                if src_ext == target_ext or (image_format == 'jpg' and src_ext in ['.jpg', '.jpeg']):
                    copy2(src_path, dest_path)
                    return

                img = Image.open(src_path)
                if img.mode == 'RGBA' and image_format == 'jpg':
                    img = img.convert('RGB')
                if image_format == 'jpg':
                    img.save(dest_path, format='JPEG', quality=95)
                else:
                    img.save(dest_path, format='PNG')

            for idx, pair in enumerate(pairs_data):
                base_num = idx + 1
                left = pair.get("left")
                right = pair.get("right")

                left_path = (left or {}).get("path")
                left2_path = (pair.get("left2") or {}).get("path")
                right_path = (right or {}).get("path")

                if naming_mode == 't2itrainer':
                    # T2itrainer模式: {num}_{suffix}.{fmt}
                    if left_path and os.path.exists(left_path):
                        fname = f"{suffix_left}_{base_num}.{image_format}" if prefix_letter else f"{base_num}_{suffix_left}.{image_format}"
                        _write_image_to_folder(left_path, os.path.join(output_path, fname))
                    
                    if left2_path and os.path.exists(left2_path):
                        fname = f"{suffix_left2}_{base_num}.{image_format}" if prefix_letter else f"{base_num}_{suffix_left2}.{image_format}"
                        _write_image_to_folder(left2_path, os.path.join(output_path, fname))
                    
                    if right_path and os.path.exists(right_path):
                        fname = f"{suffix_right}_{base_num}.{image_format}" if prefix_letter else f"{base_num}_{suffix_right}.{image_format}"
                        _write_image_to_folder(right_path, os.path.join(output_path, fname))
                    
                    if pair.get("text") and include_txt:
                        if txt_follows == 'left':
                            if prefix_letter:
                                txt_name = f"{suffix_left}_{base_num}.txt"
                            else:
                                txt_name = f"{base_num}_{suffix_left}.txt"
                        else:
                            if prefix_letter:
                                txt_name = f"{suffix_right}_{base_num}.txt"
                            else:
                                txt_name = f"{base_num}_{suffix_right}.txt"
                        with open(os.path.join(output_path, txt_name), 'w', encoding='utf-8') as f:
                            f.write(pair["text"])
                
                elif naming_mode == 'aitoolkit':
                    # AIToolkit模式: 分文件夹放置
                    left_folder = os.path.join(output_path, f"{suffix_left}")
                    left2_folder = os.path.join(output_path, f"{suffix_left2}")
                    right_folder = os.path.join(output_path, f"{suffix_right}")

                    if left_path and os.path.exists(left_path):
                        os.makedirs(left_folder, exist_ok=True)
                        fname = f"{unified_file_prefix}_{base_num}.{image_format}"
                        _write_image_to_folder(left_path, os.path.join(left_folder, fname))

                    if left2_path and os.path.exists(left2_path):
                        os.makedirs(left2_folder, exist_ok=True)
                        fname = f"{unified_file_prefix}_{base_num}.{image_format}"
                        _write_image_to_folder(left2_path, os.path.join(left2_folder, fname))

                    if right_path and os.path.exists(right_path):
                        os.makedirs(right_folder, exist_ok=True)
                        fname = f"{unified_file_prefix}_{base_num}.{image_format}"
                        _write_image_to_folder(right_path, os.path.join(right_folder, fname))

                    if pair.get("text") and include_txt:
                        txt_filename = f"{unified_file_prefix}_{base_num}.txt"
                        if txt_folder_follows == 'left':
                            txt_folder = left_folder
                        else:
                            txt_folder = right_folder
                        os.makedirs(txt_folder, exist_ok=True)
                        with open(os.path.join(txt_folder, txt_filename), 'w', encoding='utf-8') as f:
                            f.write(pair["text"])
                
                elif naming_mode == 'runinghub':
                    # RuningHub模式: {num}_{start}.{fmt}, {num}_{end}.{fmt}
                    # 原图: 1_start.png, 2_start.png ...
                    # 目标图: 1_end.png, 2_end.png ...
                    
                    if left_path and os.path.exists(left_path):
                        _write_image_to_folder(left_path, os.path.join(output_path, f"{base_num}_{runinghub_start}.{image_format}"))
                    
                    if right_path and os.path.exists(right_path):
                        _write_image_to_folder(right_path, os.path.join(output_path, f"{base_num}_{runinghub_end}.{image_format}"))
                    
                    if pair.get("text") and include_txt:
                        with open(os.path.join(output_path, f"{base_num}_{runinghub_end}.txt"), 'w', encoding='utf-8') as f:
                            f.write(pair["text"])
                
                else:
                    # 默认模式: {num}_0.{fmt}, {num}_1.{fmt}
                    base_name = pair.get("export_name") or str(base_num)
                    
                    if right_path and os.path.exists(right_path):
                        _write_image_to_folder(right_path, os.path.join(output_path, f"{base_name}_1.{image_format}"))

                    if left_path and os.path.exists(left_path):
                        _write_image_to_folder(left_path, os.path.join(output_path, f"{base_name}_0.{image_format}"))

                    if pair.get("text") and include_txt:
                        with open(os.path.join(output_path, f"{base_name}_1.txt"), 'w', encoding='utf-8') as f:
                            f.write(pair["text"])

            return output_path
        except Exception as e:
            raise Exception(f"Export to folder failed: {e}")
    
    @staticmethod
    def batch_rename(images_data, selected_ids, prefix):
        """
        批量重命名（仅修改导出名称）
        
        Args:
            images_data: 图片数据字典
            selected_ids: 选中的图片 ID 列表
            prefix: 文件名前缀
        
        Returns:
            int: 重命名数量
        """
        count = 1
        for img_id in selected_ids:
            if img_id in images_data:
                images_data[img_id]["export_name"] = f"{prefix}_{count}"
                count += 1
        return count - 1
    
    @staticmethod
    def batch_add_text(images_data, selected_ids, text, position="prefix"):
        """
        批量添加文本
        
        Args:
            images_data: 图片数据字典
            selected_ids: 选中的图片 ID 列表
            text: 要添加的文本
            position: 添加位置（prefix/suffix）
        
        Returns:
            int: 修改数量
        """
        count = 0
        for img_id in selected_ids:
            if img_id in images_data:
                item = images_data[img_id]
                if text not in item["text"]:
                    if position == "prefix":
                        item["text"] = f"{text}, {item['text']}" if item["text"] else text
                    else:
                        item["text"] = f"{item['text']}, {text}" if item["text"] else text
                    count += 1
        return count
    
    @staticmethod
    def batch_clear_text(images_data, selected_ids):
        """
        批量清空文本
        
        Args:
            images_data: 图片数据字典
            selected_ids: 选中的图片 ID 列表
        
        Returns:
            int: 清空数量
        """
        count = 0
        for img_id in selected_ids:
            if img_id in images_data:
                images_data[img_id]["text"] = ""
                count += 1
        return count
    
    @staticmethod
    def batch_set_resize(images_data, selected_ids, max_size):
        """
        批量设置裁切尺寸
        
        Args:
            images_data: 图片数据字典
            selected_ids: 选中的图片 ID 列表
            max_size: 最大边长
        
        Returns:
            int: 设置数量
        """
        count = 0
        for img_id in selected_ids:
            if img_id in images_data:
                images_data[img_id]["resize_target"] = max_size
                count += 1
        return count
