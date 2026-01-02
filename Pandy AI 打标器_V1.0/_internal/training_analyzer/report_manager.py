#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
训练报告管理模块 - 保存、读取、删除历史记录
"""

import json
import os
from datetime import datetime
from pathlib import Path

from .config import RECORDS_FILE, LOGS_BACKUP_DIR


class ReportManager:
    """训练报告管理器类"""
    
    def __init__(self):
        """初始化报告管理器"""
        self.records_file = RECORDS_FILE
        self.logs_backup_dir = LOGS_BACKUP_DIR
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        # 确保records.json所在目录存在
        records_dir = os.path.dirname(self.records_file)
        if records_dir and not os.path.exists(records_dir):
            os.makedirs(records_dir, exist_ok=True)
        
        # 确保日志备份目录存在
        if not os.path.exists(self.logs_backup_dir):
            os.makedirs(self.logs_backup_dir, exist_ok=True)
    
    def save_record(self, parse_result):
        """
        保存分析记录
        
        Args:
            parse_result: 日志解析结果字典
            
        Returns:
            str: 记录ID
        """
        # 加载现有记录
        records = self.load_records()
        
        # 生成记录ID（时间戳）
        record_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        
        # 处理多次训练的情况
        if parse_result.get('training_sessions'):
            # 如果有多次训练，只保存第一个（过滤后的）
            session = parse_result['training_sessions'][0]
            config = session['config']
            statistics = session['statistics']
            val_losses = session['val_losses']
            completeness = session.get('completeness', {})
        else:
            # 单次训练
            config = parse_result['config']
            statistics = parse_result['statistics']
            val_losses = parse_result['val_losses']
            completeness = parse_result.get('completeness', {})
        
        # 创建记录
        record = {
            'id': record_id,
            'model_name': config.get('model_name', 'Unknown'),
            'analysis_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'log_file_path': parse_result.get('log_file_path', ''),
            
            # 训练配置
            'num_epochs': config.get('num_train_epochs'),
            'repeats': config.get('repeats', 1),
            'save_model_epochs': config.get('save_model_epochs'),
            'rank': config.get('rank'),
            'train_batch_size': config.get('train_batch_size'),
            'learning_rate': config.get('learning_rate'),
            'lr_scheduler': config.get('lr_scheduler', 'Unknown'),
            'train_data_dir': config.get('train_data_dir'),
            # 兼容字段：预训练模型路径 / 训练时长 / 总步数
            'pretrained_model_name_or_path': config.get('pretrained_model_name_or_path') or config.get('pretrained_model'),
            'training_time': config.get('training_time'),
            'steps': config.get('steps'),
            
            # 统计信息
            'total_trained_epochs': statistics['total_epochs'],
            'best_epoch': statistics['best_epoch'],
            'best_val_loss': statistics['min_loss'],
            'worst_val_loss': statistics['max_loss'],
            'avg_val_loss': statistics['avg_loss'],
            
            # 完整性信息
            'is_complete': completeness.get('is_complete', False),
            'completion_ratio': completeness.get('completion_ratio', 0),
            'actual_epochs': completeness.get('actual_epochs', 0),
            'target_epochs': completeness.get('target_epochs', 0),
            'completeness_reason': completeness.get('reason', 'Unknown'),
            
            # 完整数据
            'all_val_losses': val_losses,
            'top_10': statistics['top_10']
        }
        
        # 添加到记录列表
        records['records'].append(record)
        
        # 保存到文件
        self._save_to_file(records)
        
        return record_id
    
    def load_records(self):
        """
        加载所有历史记录
        
        Returns:
            dict: {'records': [record1, record2, ...]}
        """
        if not os.path.exists(self.records_file):
            return {'records': []}
        
        try:
            with open(self.records_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'records' not in data:
                    data = {'records': []}
                return data
        except json.JSONDecodeError:
            print("警告: 记录文件格式错误，创建新文件")
            return {'records': []}
        except Exception as e:
            print(f"错误: 读取记录文件失败 - {e}")
            return {'records': []}
    
    def delete_record(self, record_id):
        """
        删除指定记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            bool: 是否删除成功
        """
        records = self.load_records()
        
        original_count = len(records['records'])
        records['records'] = [
            r for r in records['records'] if r['id'] != record_id
        ]
        
        if len(records['records']) < original_count:
            self._save_to_file(records)
            return True
        
        return False
    
    def get_record_by_id(self, record_id):
        """
        根据ID获取记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            dict: 记录数据，未找到返回None
        """
        records = self.load_records()
        
        for record in records['records']:
            if record['id'] == record_id:
                return record
        
        return None
    
    def _save_to_file(self, data):
        """
        保存数据到文件
        
        Args:
            data: 要保存的数据
        """
        try:
            with open(self.records_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"错误: 保存记录文件失败 - {e}")
    
    def get_records_summary(self):
        """
        获取记录摘要（用于表格显示）
        
        Returns:
            list: 记录摘要列表
        """
        records = self.load_records()
        
        summaries = []
        for record in records['records']:
            # 生成完整性状态文本
            completion_status = "✓ 完整" if record.get('is_complete', False) else "✗ 不完整"
            if record.get('completion_ratio', 0) >= 0.8 and not record.get('is_complete', False):
                completion_status = "◐ 基本完整"
            
            summary = {
                'id': record['id'],
                'model_name': record['model_name'],
                'analysis_date': record['analysis_date'],
                'best_val_loss': record['best_val_loss'],
                'lr_scheduler': record.get('lr_scheduler', 'Unknown'),
                'num_epochs': f"{record.get('actual_epochs', 'N/A')}/{record.get('target_epochs', 'N/A')}",
                'best_epoch': record['best_epoch'],
                'completion_status': completion_status,
                'completion_ratio': record.get('completion_ratio', 0),
            }
            summaries.append(summary)
        
        # 按分析日期降序排序（最新的在前）
        summaries.sort(key=lambda x: x['analysis_date'], reverse=True)
        
        return summaries


# 便捷函数
_manager = None

def get_manager():
    """获取全局报告管理器实例"""
    global _manager
    if _manager is None:
        _manager = ReportManager()
    return _manager


def save_record(parse_result):
    """保存记录（便捷函数）"""
    return get_manager().save_record(parse_result)


def load_records():
    """加载记录（便捷函数）"""
    return get_manager().load_records()


def delete_record(record_id):
    """删除记录（便捷函数）"""
    return get_manager().delete_record(record_id)


def get_record_by_id(record_id):
    """获取记录（便捷函数）"""
    return get_manager().get_record_by_id(record_id)


def get_records_summary():
    """获取记录摘要（便捷函数）"""
    return get_manager().get_records_summary()
