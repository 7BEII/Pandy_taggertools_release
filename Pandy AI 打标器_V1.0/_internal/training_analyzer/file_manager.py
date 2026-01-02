#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件管理模块 - 处理训练日志文件的上传、移动和管理
"""

import os
import shutil
from datetime import datetime
from pathlib import Path

from .config import TRAINING_LOG_DIR, TRAINING_LOG_HISTORY_DIR


class FileManager:
    """训练日志文件管理器"""
    
    def __init__(self):
        """初始化文件管理器"""
        self.log_dir = Path(TRAINING_LOG_DIR)
        self.history_dir = Path(TRAINING_LOG_HISTORY_DIR)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)
    
    def copy_to_log_dir(self, source_path):
        """
        复制文件到训练日志目录
        
        Args:
            source_path: 源文件路径
            
        Returns:
            str: 目标文件路径，失败返回None
        """
        source = Path(source_path)
        if not source.exists():
            print(f"错误: 源文件不存在 - {source_path}")
            return None
        
        # 生成唯一文件名（避免覆盖）
        dest_name = source.name
        dest_path = self.log_dir / dest_name
        
        # 如果文件已存在，添加时间戳
        if dest_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            stem = source.stem
            suffix = source.suffix
            dest_name = f"{stem}_{timestamp}{suffix}"
            dest_path = self.log_dir / dest_name
        
        try:
            shutil.copy2(source, dest_path)
            return str(dest_path)
        except Exception as e:
            print(f"错误: 复制文件失败 - {e}")
            return None
    
    def move_to_history(self, log_path):
        """
        将分析完成的日志移动到历史目录
        
        Args:
            log_path: 日志文件路径
            
        Returns:
            str: 移动后的文件路径，失败返回None
        """
        source = Path(log_path)
        if not source.exists():
            print(f"错误: 文件不存在 - {log_path}")
            return None
        
        # 生成带时间戳的文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = source.stem
        suffix = source.suffix
        dest_name = f"{stem}_{timestamp}{suffix}"
        dest_path = self.history_dir / dest_name
        
        # 复制并确认后删除原文件：先复制到历史目录，校验后删除源文件以避免占用双份空间长留
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                shutil.copy2(str(source), str(dest_path))
                # 校验文件大小一致以确认复制成功
                src_size = source.stat().st_size
                dst_size = dest_path.stat().st_size
                if src_size == dst_size:
                    try:
                        source.unlink()  # 删除原文件
                    except Exception as e_del:
                        # 如果删除失败，移除历史副本以避免不一致状态并继续重试
                        try:
                            dest_path.unlink()
                        except Exception:
                            pass
                        print(f"警告: 删除原文件失败（尝试{attempt}） - {e_del}")
                        # 如果不是最后一次尝试，继续重试
                        if attempt < max_attempts:
                            continue
                        else:
                            return None
                    return str(dest_path)
                else:
                    # 大小不一致，删除目标并重试
                    try:
                        dest_path.unlink()
                    except Exception:
                        pass
                    print(f"警告: 复制校验失败（尝试{attempt}），源 {src_size} != 目标 {dst_size}")
            except Exception as e:
                print(f"错误: 复制到历史目录失败（尝试{attempt}） - {e}")
            # 如果未在最后一次尝试成功，继续重试
        # 所有尝试均失败
        return None
    
    def get_pending_logs(self):
        """
        获取待分析的日志文件列表
        
        Returns:
            list: 日志文件路径列表
        """
        logs = []
        for ext in ['.txt', '.log']:
            logs.extend(self.log_dir.glob(f'*{ext}'))
        return [str(p) for p in sorted(logs)]
    
    def get_history_logs(self):
        """
        获取历史日志文件列表
        
        Returns:
            list: 历史日志文件路径列表
        """
        logs = []
        for ext in ['.txt', '.log']:
            logs.extend(self.history_dir.glob(f'*{ext}'))
        return [str(p) for p in sorted(logs, reverse=True)]
    
    def delete_log(self, log_path):
        """
        删除日志文件
        
        Args:
            log_path: 日志文件路径
            
        Returns:
            bool: 是否删除成功
        """
        try:
            path = Path(log_path)
            if path.exists():
                path.unlink()
                return True
            return False
        except Exception as e:
            print(f"错误: 删除文件失败 - {e}")
            return False


# 全局实例
_file_manager = None


def get_file_manager():
    """获取全局文件管理器实例"""
    global _file_manager
    if _file_manager is None:
        _file_manager = FileManager()
    return _file_manager


def copy_to_log_dir(source_path):
    """复制文件到日志目录（便捷函数）"""
    return get_file_manager().copy_to_log_dir(source_path)


def move_to_history(log_path):
    """移动到历史目录（便捷函数）"""
    return get_file_manager().move_to_history(log_path)


def get_pending_logs():
    """获取待分析日志（便捷函数）"""
    return get_file_manager().get_pending_logs()


def get_history_logs():
    """获取历史日志（便捷函数）"""
    return get_file_manager().get_history_logs()
