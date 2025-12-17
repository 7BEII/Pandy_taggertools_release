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
    def create_thumbnail(image_path, size=(240, 240)):
        """
        生成缩略图并返回 Base64 编码
        
        Args:
            image_path: 图片路径
            size: 缩略图尺寸
        
        Returns:
            str: Base64 编码的缩略图
        """
        try:
            img = Image.open(image_path)
            
            # 转换 RGBA 到 RGB（处理 PNG 透明背景）
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 生成缩略图
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # 保存为 Base64
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            return f"data:image/jpeg;base64,{img_str}"
        except Exception as e:
            print(f"❌ Error creating thumbnail for {image_path}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
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
    def export_pairs_to_zip(pairs_data, output_path=None, image_format='png', naming_config=None):
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
        folder_prefix = naming_config.get('folder_prefix', 'aitoolkit')
        txt_folder_follows = naming_config.get('txt_folder_follows', 'right')

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
                            _write_image_to_zip(left_path, f"{base_num}_{suffix_left}.{image_format}")
                        
                        if left2_path and os.path.exists(left2_path):
                            _write_image_to_zip(left2_path, f"{base_num}_{suffix_left2}.{image_format}")
                        
                        if right_path and os.path.exists(right_path):
                            _write_image_to_zip(right_path, f"{base_num}_{suffix_right}.{image_format}")
                        
                        if pair.get("text"):
                            if txt_follows == 'left':
                                txt_name = f"{base_num}_{suffix_left}.txt"
                            else:
                                txt_name = f"{base_num}_{suffix_right}.txt"
                            zf.writestr(txt_name, pair["text"])
                    
                    elif naming_mode == 'aitoolkit':
                        # AIToolkit模式: 分文件夹放置
                        # 原图文件夹: {folder_prefix}_{suffix_left}/
                        # 目标图文件夹: {folder_prefix}_{suffix_right}/
                        # 文件命名: {num}_{suffix}.{fmt}
                        
                        left_folder = f"{folder_prefix}_{suffix_left}"
                        left2_folder = f"{folder_prefix}_{suffix_left2}"
                        right_folder = f"{folder_prefix}_{suffix_right}"
                        
                        if left_path and os.path.exists(left_path):
                            _write_image_to_zip(left_path, f"{left_folder}/{base_num}_{suffix_left}.{image_format}")
                        
                        if left2_path and os.path.exists(left2_path):
                            _write_image_to_zip(left2_path, f"{left2_folder}/{base_num}_{suffix_left2}.{image_format}")
                        
                        if right_path and os.path.exists(right_path):
                            _write_image_to_zip(right_path, f"{right_folder}/{base_num}_{suffix_right}.{image_format}")
                        
                        if pair.get("text"):
                            # txt命名跟随
                            if txt_follows == 'left':
                                txt_filename = f"{base_num}_{suffix_left}.txt"
                            else:
                                txt_filename = f"{base_num}_{suffix_right}.txt"
                            # txt放置文件夹跟随
                            if txt_folder_follows == 'left':
                                txt_folder = left_folder
                            else:
                                txt_folder = right_folder
                            zf.writestr(f"{txt_folder}/{txt_filename}", pair["text"])
                    
                    else:
                        # 默认模式: {num}_0.{fmt}, {num}_1.{fmt}
                        base_name = pair.get("export_name") or str(base_num)
                        
                        if right_path and os.path.exists(right_path):
                            _write_image_to_zip(right_path, f"{base_name}_1.{image_format}")

                        if left_path and os.path.exists(left_path):
                            _write_image_to_zip(left_path, f"{base_name}_0.{image_format}")

                        if pair.get("text"):
                            zf.writestr(f"{base_name}_1.txt", pair["text"])

            return output_path
        except Exception as e:
            raise Exception(f"Export failed: {e}")
    
    @staticmethod
    def export_pairs_to_folder(pairs_data, output_path, image_format='png', naming_config=None):
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
        txt_folder_follows = naming_config.get('txt_folder_follows', 'right')

        try:
            # 创建输出目录
            os.makedirs(output_path, exist_ok=True)
            
            def _write_image_to_folder(src_path, dest_path):
                _, src_ext = os.path.splitext(src_path)
                src_ext = src_ext.lower()
                target_ext = f'.{image_format}'

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
                        _write_image_to_folder(left_path, os.path.join(output_path, f"{base_num}_{suffix_left}.{image_format}"))
                    
                    if left2_path and os.path.exists(left2_path):
                        _write_image_to_folder(left2_path, os.path.join(output_path, f"{base_num}_{suffix_left2}.{image_format}"))
                    
                    if right_path and os.path.exists(right_path):
                        _write_image_to_folder(right_path, os.path.join(output_path, f"{base_num}_{suffix_right}.{image_format}"))
                    
                    if pair.get("text"):
                        if txt_follows == 'left':
                            txt_name = f"{base_num}_{suffix_left}.txt"
                        else:
                            txt_name = f"{base_num}_{suffix_right}.txt"
                        with open(os.path.join(output_path, txt_name), 'w', encoding='utf-8') as f:
                            f.write(pair["text"])
                
                elif naming_mode == 'aitoolkit':
                    # AIToolkit模式: 分文件夹放置
                    left_folder = os.path.join(output_path, f"{folder_prefix}_{suffix_left}")
                    left2_folder = os.path.join(output_path, f"{folder_prefix}_{suffix_left2}")
                    right_folder = os.path.join(output_path, f"{folder_prefix}_{suffix_right}")
                    
                    if left_path and os.path.exists(left_path):
                        os.makedirs(left_folder, exist_ok=True)
                        _write_image_to_folder(left_path, os.path.join(left_folder, f"{base_num}_{suffix_left}.{image_format}"))
                    
                    if left2_path and os.path.exists(left2_path):
                        os.makedirs(left2_folder, exist_ok=True)
                        _write_image_to_folder(left2_path, os.path.join(left2_folder, f"{base_num}_{suffix_left2}.{image_format}"))
                    
                    if right_path and os.path.exists(right_path):
                        os.makedirs(right_folder, exist_ok=True)
                        _write_image_to_folder(right_path, os.path.join(right_folder, f"{base_num}_{suffix_right}.{image_format}"))
                    
                    if pair.get("text"):
                        if txt_follows == 'left':
                            txt_filename = f"{base_num}_{suffix_left}.txt"
                        else:
                            txt_filename = f"{base_num}_{suffix_right}.txt"
                        if txt_folder_follows == 'left':
                            txt_folder = left_folder
                        else:
                            txt_folder = right_folder
                        os.makedirs(txt_folder, exist_ok=True)
                        with open(os.path.join(txt_folder, txt_filename), 'w', encoding='utf-8') as f:
                            f.write(pair["text"])
                
                else:
                    # 默认模式: {num}_0.{fmt}, {num}_1.{fmt}
                    base_name = pair.get("export_name") or str(base_num)
                    
                    if right_path and os.path.exists(right_path):
                        _write_image_to_folder(right_path, os.path.join(output_path, f"{base_name}_1.{image_format}"))

                    if left_path and os.path.exists(left_path):
                        _write_image_to_folder(left_path, os.path.join(output_path, f"{base_name}_0.{image_format}"))

                    if pair.get("text"):
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
                images_data[img_id]["export_name"] = f"{prefix}_{count:03d}"
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
