#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
日志解析模块 - 解析训练日志，提取数据
"""

import re
import os
from datetime import datetime
from pathlib import Path

from .config import VAL_LOSS_PATTERN, CONFIG_PATTERNS


class LogParser:
    """日志解析器类"""
    
    def __init__(self, log_file_path):
        """
        初始化日志解析器
        
        Args:
            log_file_path: 日志文件路径
        """
        self.log_file_path = log_file_path
        self.content = ""
        self.lines = []
        self.val_losses = []
        self.config_info = {}
        self.training_sessions = []  # 存储多次训练的结果
        
    def parse(self):
        """
        解析日志文件
        
        Returns:
            dict: 解析结果
        """
        # 读取文件
        if not self._read_file():
            return None
        
        # 识别多次训练并分别解析
        self._parse_multiple_trainings()
        
        # 如果没有识别到多次训练，使用原来的方法（向后兼容）
        if not self.training_sessions:
            # 提取val_loss数据
            self._extract_val_losses()
            
            # 提取配置信息
            self._extract_config_info()
            
            # 计算统计信息
            stats = self._calculate_statistics()
            
            return {
                'val_losses': self.val_losses,
                'config': self.config_info,
                'statistics': stats,
                'log_file_path': self.log_file_path,
                'training_sessions': [],  # 空列表表示单次训练
            }
        
        # 返回多次训练的结果
        return {
            'training_sessions': self.training_sessions,
            'log_file_path': self.log_file_path,
            'total_sessions': len(self.training_sessions),
        }
    
    def _read_file(self):
        """读取日志文件"""
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                self.content = f.read()
                self.lines = self.content.split('\n')
            return True
        except FileNotFoundError:
            print(f"错误: 找不到文件 {self.log_file_path}")
            return False
        except Exception as e:
            print(f"错误: 读取文件时出错 - {e}")
            return False
    
    def _parse_multiple_trainings(self):
        """识别并解析多次训练（基于epoch重置检测）"""
        # 首先提取所有val_loss数据
        all_matches = re.findall(VAL_LOSS_PATTERN, self.content)
        
        if not all_matches:
            return  # 没有找到val_loss数据
        
        # 转换为列表
        all_losses = [
            {'val_loss': float(val_loss), 'epoch': int(epoch)}
            for val_loss, epoch in all_matches
        ]
        
        # 通过epoch重置检测多个训练任务
        # 当epoch值小于等于前一个epoch时，说明开始了新的训练任务
        training_sessions_data = []
        current_session = []
        prev_epoch = -1
        
        for item in all_losses:
            if item['epoch'] <= prev_epoch and current_session:
                # 新训练任务开始
                training_sessions_data.append(current_session)
                current_session = []
            current_session.append(item)
            prev_epoch = item['epoch']
        
        # 添加最后一个任务
        if current_session:
            training_sessions_data.append(current_session)
        
        # 如果只有一个任务，不需要多任务处理
        if len(training_sessions_data) <= 1:
            return
        
        # 查找配置信息的位置
        config_positions = []
        for i, line in enumerate(self.lines):
            if 'Using config:' in line:
                config_positions.append(i)
        
        # 为每次训练提取数据
        for idx, session_losses in enumerate(training_sessions_data):
            # 提取该训练段的配置
            config_info = {}
            if idx < len(config_positions):
                config_line = self.lines[config_positions[idx]]
                config_info = self._extract_config_from_line(config_line)
            
            # 计算统计信息
            stats = self._calculate_statistics_from_losses(session_losses)
            
            # 保存训练会话信息
            self.training_sessions.append({
                'session_index': idx + 1,  # 从1开始编号
                'config': config_info,
                'val_losses': session_losses,
                'statistics': stats,
            })
    
    def _extract_config_from_line(self, config_line):
        """从配置行中提取配置信息"""
        config_info = {}
        for key, pattern in CONFIG_PATTERNS.items():
            match = re.search(pattern, config_line)
            if match:
                value = match.group(1)
                # 尝试转换为数字
                try:
                    if '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                except ValueError:
                    pass  # 保持字符串
                config_info[key] = value
            else:
                config_info[key] = None
        
        # 提取模型名称：优先使用save_name作为模型显示名称
        if config_info.get('save_name'):
            config_info['model_name'] = config_info['save_name']
        elif config_info.get('output_dir'):
            output_dir = config_info['output_dir']
            model_name = os.path.basename(output_dir.rstrip('/\\'))
            config_info['model_name'] = model_name
        else:
            config_info['model_name'] = os.path.splitext(
                os.path.basename(self.log_file_path)
            )[0]
        
        return config_info
    
    def _extract_val_losses_from_content(self, content):
        """从内容中提取val_loss数据"""
        matches = re.findall(VAL_LOSS_PATTERN, content)
        
        if not matches:
            return []
        
        # 转换为字典列表
        val_losses = [
            {
                'epoch': int(epoch),
                'val_loss': float(val_loss)
            }
            for val_loss, epoch in matches
        ]
        
        # 按epoch排序
        val_losses.sort(key=lambda x: x['epoch'])
        
        return val_losses
    
    def _calculate_statistics_from_losses(self, val_losses):
        """根据val_losses计算统计信息"""
        if not val_losses:
            return {
                'total_epochs': 0,
                'min_loss': None,
                'max_loss': None,
                'avg_loss': None,
                'best_epoch': None,
                'worst_epoch': None,
                'top_10': []
            }
        
        # 提取所有loss值
        loss_values = [item['val_loss'] for item in val_losses]
        
        # 找到最小loss及其epoch
        min_loss_item = min(val_losses, key=lambda x: x['val_loss'])
        max_loss_item = max(val_losses, key=lambda x: x['val_loss'])
        
        # 计算平均loss
        avg_loss = sum(loss_values) / len(loss_values)
        
        # 找到前10个最低loss
        sorted_losses = sorted(val_losses, key=lambda x: x['val_loss'])
        top_10 = sorted_losses[:10]
        
        return {
            'total_epochs': len(val_losses),
            'min_loss': min_loss_item['val_loss'],
            'max_loss': max_loss_item['val_loss'],
            'avg_loss': avg_loss,
            'best_epoch': min_loss_item['epoch'],
            'worst_epoch': max_loss_item['epoch'],
            'top_10': top_10
        }
    
    def _extract_val_losses(self):
        """提取所有val_loss和epoch数据"""
        matches = re.findall(VAL_LOSS_PATTERN, self.content)
        
        if not matches:
            print("警告: 日志文件中未找到val_loss数据")
            self.val_losses = []
            return
        
        # 转换为字典列表
        self.val_losses = [
            {
                'epoch': int(epoch),
                'val_loss': float(val_loss)
            }
            for val_loss, epoch in matches
        ]
        
        # 按epoch排序
        self.val_losses.sort(key=lambda x: x['epoch'])
    
    def _extract_config_info(self):
        """从日志中提取配置信息"""
        for key, pattern in CONFIG_PATTERNS.items():
            match = re.search(pattern, self.content)
            if match:
                value = match.group(1)
                # 尝试转换为数字
                try:
                    if '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                except ValueError:
                    pass  # 保持字符串
                self.config_info[key] = value
            else:
                self.config_info[key] = None
        
        # 提取模型名称：优先使用save_name作为模型显示名称
        if self.config_info.get('save_name'):
            self.config_info['model_name'] = self.config_info['save_name']
        elif self.config_info.get('output_dir'):
            output_dir = self.config_info['output_dir']
            model_name = os.path.basename(output_dir.rstrip('/\\'))
            self.config_info['model_name'] = model_name
        else:
            self.config_info['model_name'] = os.path.splitext(
                os.path.basename(self.log_file_path)
            )[0]
    
    def _calculate_statistics(self):
        """计算统计信息"""
        if not self.val_losses:
            return {
                'total_epochs': 0,
                'min_loss': None,
                'max_loss': None,
                'avg_loss': None,
                'best_epoch': None,
                'top_10': []
            }
        
        # 提取所有loss值
        loss_values = [item['val_loss'] for item in self.val_losses]
        
        # 找到最小loss及其epoch
        min_loss_item = min(self.val_losses, key=lambda x: x['val_loss'])
        max_loss_item = max(self.val_losses, key=lambda x: x['val_loss'])
        
        # 计算平均loss
        avg_loss = sum(loss_values) / len(loss_values)
        
        # 找到前10个最低loss
        sorted_losses = sorted(self.val_losses, key=lambda x: x['val_loss'])
        top_10 = sorted_losses[:10]
        
        return {
            'total_epochs': len(self.val_losses),
            'min_loss': min_loss_item['val_loss'],
            'max_loss': max_loss_item['val_loss'],
            'avg_loss': avg_loss,
            'best_epoch': min_loss_item['epoch'],
            'worst_epoch': max_loss_item['epoch'],
            'top_10': top_10
        }


def parse_log_file(log_file_path):
    """
    便捷函数：解析日志文件
    
    Args:
        log_file_path: 日志文件路径
        
    Returns:
        dict: 解析结果，失败返回None
    """
    parser = LogParser(log_file_path)
    return parser.parse()
