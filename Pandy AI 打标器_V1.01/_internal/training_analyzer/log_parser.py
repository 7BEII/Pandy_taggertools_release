#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
日志解析模块 - 解析训练日志，提取数据
"""

import re
import os
from datetime import datetime
from pathlib import Path

from .config import VAL_LOSS_PATTERN, CONFIG_PATTERNS, STEP_LOSS_PATTERNS, JSON_CONFIG_PATTERNS, DATASET_COUNT_PATTERNS


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
        self.step_losses = []  # 存储步骤级别的loss
        self.config_info = {}
        self.training_sessions = []  # 存储多次训练的结果
        self.completeness_threshold = 0.8  # 80%的epoch数认为基本完成
        
    def parse(self, filter_incomplete=True):
        """
        解析日志文件
        
        Args:
            filter_incomplete: 是否过滤不完整的训练
            
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
            # 提取配置信息（先提取，因为后续需要用到）
            self._extract_config_info()
            
            # 提取val_loss数据
            self._extract_val_losses()
            
            # 提取步骤级别的loss数据
            self._extract_step_losses()
            
            # 如果没有val_loss但有step_loss，则从step_loss计算epoch平均值
            if not self.val_losses and self.step_losses:
                self.val_losses = self._calculate_epoch_losses_from_steps()
            
            # 计算统计信息
            stats = self._calculate_statistics()
            
            # 检查训练完整性
            completeness = self._check_training_completeness(self.val_losses, self.config_info)
            
            result = {
                'val_losses': self.val_losses,
                'config': self.config_info,
                'statistics': stats,
                'log_file_path': self.log_file_path,
                'training_sessions': [],  # 空列表表示单次训练
                'completeness': completeness,
                'is_complete': completeness.get('is_complete', False),
            }
            
            return result
        
        # 过滤不完整的训练
        if filter_incomplete:
            self._filter_incomplete_trainings()
        
        # 如果过滤后没有完整的训练，选择最完整的
        if not self.training_sessions:
            self._select_most_complete_training()
        
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
        """识别并解析多次训练（基于epoch重置和配置重置检测）"""
        # 首先提取所有val_loss数据
        all_matches = re.findall(VAL_LOSS_PATTERN, self.content)
        
        if not all_matches:
            return  # 没有找到val_loss数据
        
        # 转换为列表
        all_losses = [
            {'val_loss': float(val_loss), 'epoch': int(epoch)}
            for val_loss, epoch in all_matches
        ]
        
        # 查找所有配置行和保存标记的位置
        config_positions = []
        save_positions = []
        
        for i, line in enumerate(self.lines):
            if 'Using config:' in line:
                config_positions.append(i)
            elif 'Saved to' in line:
                save_positions.append(i)
        
        # 通过多种方式检测多个训练任务
        training_sessions_data = []
        current_session = []
        prev_epoch = -1
        
        # 方法1：基于epoch重置
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
        
        # 方法2：如果只有一个任务，尝试根据配置和保存标记分割
        if len(training_sessions_data) <= 1 and (len(config_positions) > 1 or len(save_positions) > 1):
            # 使用配置位置作为分割点
            training_sessions_data = []
            session_boundaries = []
            
            # 找到所有可能的训练开始位置
            if config_positions:
                session_boundaries = config_positions
            elif save_positions:
                session_boundaries = save_positions
            
            # 根据边界分割val_loss数据
            for idx, boundary in enumerate(session_boundaries):
                # 找到这个边界后的第一个val_loss
                session_losses = []
                boundary_line_num = boundary
                
                # 查找下一个边界或文件末尾
                next_boundary = session_boundaries[idx + 1] if idx + 1 < len(session_boundaries) else len(self.lines)
                
                # 在这个范围内查找val_loss
                for i in range(boundary_line_num, next_boundary):
                    match = re.search(VAL_LOSS_PATTERN, self.lines[i])
                    if match:
                        val_loss, epoch = match.groups()
                        session_losses.append({
                            'val_loss': float(val_loss),
                            'epoch': int(epoch)
                        })
                
                if session_losses:
                    training_sessions_data.append(session_losses)
        
        # 如果仍然只有一个任务，不需要多任务处理
        if len(training_sessions_data) <= 1:
            return
        
        # 查找配置信息的位置
        config_positions = []
        for i, line in enumerate(self.lines):
            if 'Using config:' in line:
                config_positions.append(i)
        
        # 查找每个训练段的结束位置
        segment_end_positions = self._find_training_segment_ends(training_sessions_data)
        
        # 为每次训练提取数据
        for idx, session_losses in enumerate(training_sessions_data):
            # 提取该训练段的配置
            config_info = {}
            if idx < len(config_positions):
                config_line = self.lines[config_positions[idx]]
                config_info = self._extract_config_from_line(config_line)
            
            # 计算统计信息
            stats = self._calculate_statistics_from_losses(session_losses)
            
            # 检查训练完整性
            completeness = self._check_training_completeness(session_losses, config_info)
            
            # 保存训练会话信息
            self.training_sessions.append({
                'session_index': idx + 1,  # 从1开始编号
                'config': config_info,
                'val_losses': session_losses,
                'statistics': stats,
                'completeness': completeness,
                'is_complete': completeness.get('is_complete', False),
                'completion_ratio': completeness.get('completion_ratio', 0),
                'end_position': segment_end_positions.get(idx, len(self.lines)),
            })
    
    def _find_training_segment_ends(self, training_sessions_data):
        """查找每个训练段的结束位置"""
        segment_ends = {}
        
        # 为每个训练段查找最后一个val_loss的位置
        for idx, session_losses in enumerate(training_sessions_data):
            if not session_losses:
                continue
                
            # 获取该段的最后一个epoch
            last_epoch = session_losses[-1]['epoch']
            
            # 在日志中查找这个epoch最后出现的位置
            for i in range(len(self.lines) - 1, -1, -1):
                if f"'epoch': {last_epoch}" in self.lines[i] and "val_loss" in self.lines[i]:
                    segment_ends[idx] = i
                    break
        
        return segment_ends
    
    def _check_training_completeness(self, val_losses, config):
        """检查训练是否完整"""
        if not val_losses:
            return {
                'is_complete': False,
                'completion_ratio': 0,
                'reason': 'No training data found'
            }
        
        # 获取配置的epoch数
        target_epochs = config.get('num_train_epochs', 0) or 0
        if target_epochs == 0:
            # 如果没有配置信息，根据实际训练情况判断
            actual_epochs = len(val_losses)
            # 检查是否有保存标记
            has_save_marker = self._has_save_marker(val_losses[-1]['epoch'] if val_losses else 0)
            # 如果有保存标记，认为是正常结束的训练
            return {
                'is_complete': has_save_marker,
                'completion_ratio': 1.0 if has_save_marker else 0.5,
                'actual_epochs': actual_epochs,
                'target_epochs': actual_epochs,
                'has_save_marker': has_save_marker,
                'reason': 'Training completed normally' if has_save_marker else 'Training interrupted'
            }
        
        # 计算完成的epoch数
        actual_epochs = len(val_losses)
        completion_ratio = actual_epochs / target_epochs if target_epochs > 0 else 0
        
        # 检查是否有保存模型的标记
        has_save_marker = self._has_save_marker(val_losses[-1]['epoch'] if val_losses else 0)
        
        # 判断是否完整 - 如果有保存标记且训练正常结束，认为是完整的
        is_complete = (
            has_save_marker and  # 有保存标记
            actual_epochs > 0 and  # 至少训练了一个epoch
            not self._is_training_interrupted()  # 训练没有被中断
        )
        
        # 基本完成的判断（达到80%或者有保存标记）
        is_substantially_complete = (
            completion_ratio >= self.completeness_threshold or 
            (has_save_marker and completion_ratio >= 0.5)  # 有保存标记且达到50%
        )
        
        # 特殊情况：如果最后一个epoch很高（比如79），且有保存标记，认为是完整训练
        if actual_epochs >= 50 and has_save_marker:
            is_complete = True
            is_substantially_complete = True
        
        return {
            'is_complete': is_complete,
            'is_substantially_complete': is_substantially_complete,
            'completion_ratio': completion_ratio,
            'actual_epochs': actual_epochs,
            'target_epochs': target_epochs,
            'has_save_marker': has_save_marker,
            'reason': (
                'Complete' if is_complete else
                'Substantially complete' if is_substantially_complete else
                'Incomplete'
            )
        }
    
    def _has_save_marker(self, last_epoch):
        """检查是否有保存模型的标记"""
        # 查找"Saved to"标记
        save_patterns = [
            r"Saved to",
            r"保存到",
            r"checkpoint saved",
            r"model saved",
        ]
        
        # 检查最后几行是否有保存标记
        for pattern in save_patterns:
            for line in self.lines[-20:]:  # 检查最后20行
                if re.search(pattern, line, re.IGNORECASE):
                    return True
        
        return False
    
    def _is_training_interrupted(self):
        """检查训练是否被中断"""
        # 检查最后几行是否有中断标记
        interrupt_patterns = [
            r"KeyboardInterrupt",
            r"Traceback",
            r"Error:",
            r"Exception:",
            r"训练被中断",
            r"训练异常退出",
        ]
        
        # 检查最后20行
        for line in self.lines[-20:]:
            for pattern in interrupt_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    return True
        
        # 检查是否在训练过程中突然结束（没有保存标记但有训练进度）
        has_training_progress = False
        for line in self.lines[-10:]:
            if "Steps:" in line and "%" in line:
                has_training_progress = True
                break
        
        # 如果有训练进度但没有保存标记，可能是被中断
        if has_training_progress and not self._has_save_marker(0):
            return True
        
        return False
    
    def _filter_incomplete_trainings(self):
        """过滤掉不完整的训练"""
        # 保留完整或基本完整的训练
        filtered_sessions = []
        
        for session in self.training_sessions:
            completeness = session.get('completeness', {})
            
            # 优先选择完全完成的训练
            if completeness.get('is_complete', False):
                filtered_sessions.append(session)
            # 如果没有完全完成的，保留基本完成的
            elif completeness.get('is_substantially_complete', False) and not any(
                s.get('completeness', {}).get('is_complete', False) 
                for s in self.training_sessions
            ):
                filtered_sessions.append(session)
        
        # 如果有多个完整的训练，选择最后一个
        if filtered_sessions:
            # 按结束位置排序，选择最后完成的
            filtered_sessions.sort(key=lambda x: x.get('end_position', 0))
            self.training_sessions = [filtered_sessions[-1]]
        else:
            self.training_sessions = filtered_sessions
    
    def _select_most_complete_training(self):
        """选择最完整的训练"""
        if not self.training_sessions:
            return
        
        # 按完成度排序
        def get_completeness_score(session):
            completeness = session.get('completeness', {})
            score = 0
            
            # 完成度比例权重
            score += completeness.get('completion_ratio', 0) * 100
            
            # 是否有保存标记
            if completeness.get('has_save_marker', False):
                score += 20
            
            # 实际epoch数
            score += completeness.get('actual_epochs', 0) * 0.1
            
            return score
        
        # 选择得分最高的训练
        best_session = max(self.training_sessions, key=get_completeness_score)
        self.training_sessions = [best_session]
    
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
            # 不打印警告，因为可能使用step_loss
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
    
    def _extract_step_losses(self):
        """提取所有步骤级别的loss数据"""
        self.step_losses = []
        
        # 尝试所有的loss模式
        for pattern in STEP_LOSS_PATTERNS:
            matches = re.findall(pattern, self.content)
            if matches:
                # 转换为浮点数
                for loss_str in matches:
                    try:
                        loss_value = float(loss_str)
                        self.step_losses.append(loss_value)
                    except ValueError:
                        continue
                break  # 找到匹配的模式就停止
        
        if not self.step_losses:
            print("提示: 日志文件中未找到步骤级别的loss数据")
    
    def _calculate_epoch_losses_from_steps(self):
        """从步骤级别的loss计算每个epoch的平均loss"""
        if not self.step_losses:
            return []
        
        # 获取总步数
        total_steps = self.config_info.get('steps')
        
        # 尝试从进度条中提取总步数
        if not total_steps:
            try:
                # 匹配形如 "sh-10.25:   0%|          | 0/3000"
                progress_matches = re.findall(r":\s+\d+%\|[^|]*\|\s*\d+/(\d+)", self.content)
                if progress_matches:
                    total_steps = max(int(s) for s in progress_matches)
                    self.config_info['steps'] = total_steps
            except Exception:
                pass
        
        # 优先使用save_every作为每个epoch的步数
        save_every = self.config_info.get('save_every')
        steps_per_epoch = None
        num_epochs = None
        
        if save_every and save_every > 0:
            # 使用save_every作为每个epoch的步数
            steps_per_epoch = save_every
            if total_steps:
                num_epochs = total_steps // save_every
            else:
                # 根据实际收集的loss数量估算
                num_epochs = len(self.step_losses) // save_every
            print(f"提示: 使用save_every={save_every}作为每个epoch的步数，共{num_epochs}个epoch")
        else:
            # 回退到原来的逻辑
            num_epochs = self.config_info.get('num_train_epochs')
            
            if not num_epochs and total_steps:
                # 假设每个epoch至少有10步，最多推断100个epoch
                estimated_epochs = min(max(total_steps // 30, 1), 100)
                num_epochs = estimated_epochs
                print(f"提示: 未找到epoch配置，根据总步数{total_steps}推断为{num_epochs}个epoch")
            
            if total_steps and num_epochs:
                steps_per_epoch = total_steps // num_epochs
        
        if not steps_per_epoch or steps_per_epoch == 0:
            print("警告: 无法确定每个epoch的步数")
            return []
        
        if not num_epochs:
            num_epochs = len(self.step_losses) // steps_per_epoch
        
        epoch_losses = []
        
        # 按epoch分组计算平均loss
        for epoch_idx in range(num_epochs):
            start_step = epoch_idx * steps_per_epoch
            end_step = min((epoch_idx + 1) * steps_per_epoch, len(self.step_losses))
            
            # 如果超出实际记录的步数，停止
            if start_step >= len(self.step_losses):
                break
            
            # 计算该epoch的平均loss
            epoch_step_losses = self.step_losses[start_step:end_step]
            if epoch_step_losses:
                avg_loss = sum(epoch_step_losses) / len(epoch_step_losses)
                epoch_losses.append({
                    'epoch': epoch_idx + 1,  # epoch从1开始
                    'val_loss': avg_loss,
                    'step_range': f"{start_step + 1}-{end_step}",  # 记录步数范围
                    'step_count': len(epoch_step_losses)  # 记录该epoch的实际步数
                })
        
        # 更新配置中的epoch数
        if epoch_losses:
            self.config_info['num_train_epochs'] = len(epoch_losses)
        
        print(f"成功从{len(self.step_losses)}个步骤loss计算出{len(epoch_losses)}个epoch的平均loss")
        return epoch_losses
    
    def _extract_config_info(self):
        """从日志中提取配置信息"""
        # 首先尝试传统格式
        for key, pattern in CONFIG_PATTERNS.items():
            match = re.search(pattern, self.content)
            if match:
                value = match.group(1)
                # 尝试转换为数字
                try:
                    if '.' in value or 'e' in value.lower():
                        value = float(value)
                    else:
                        value = int(value)
                except ValueError:
                    pass  # 保持字符串
                self.config_info[key] = value
            else:
                self.config_info[key] = None
        
        # 然后尝试JSON格式配置（ai-toolkit等新格式）
        self._extract_json_config()
        
        # 提取模型名称：优先使用job_name，然后是save_name
        if self.config_info.get('job_name'):
            self.config_info['model_name'] = self.config_info['job_name']
        elif self.config_info.get('save_name'):
            self.config_info['model_name'] = self.config_info['save_name']
        elif self.config_info.get('output_dir'):
            output_dir = self.config_info['output_dir']
            model_name = os.path.basename(output_dir.rstrip('/\\'))
            self.config_info['model_name'] = model_name
        else:
            self.config_info['model_name'] = os.path.splitext(
                os.path.basename(self.log_file_path)
            )[0]
        
        # 兼容性处理：将可能的 pretrained_model 字段统一为 pretrained_model_name_or_path
        if self.config_info.get('pretrained_model') and not self.config_info.get('pretrained_model_name_or_path'):
            self.config_info['pretrained_model_name_or_path'] = self.config_info.get('pretrained_model')

        # 从日志中提取 Steps
        if not self.config_info.get('steps'):
            try:
                # 匹配形如 "Steps:   0%|          | 2280/2280"
                steps_matches = re.findall(r"Steps:.*?(\d+)/(\d+)", self.content)
                if steps_matches:
                    last_match = steps_matches[-1]
                    self.config_info['steps'] = int(last_match[1])
            except Exception:
                pass
        
        # 尝试从进度条中提取总步数（支持不同格式）
        if not self.config_info.get('steps'):
            try:
                # 匹配形如 "sh-10.25:   0%|          | 0/3000"
                progress_matches = re.findall(r":\s+\d+%\|[^|]*\|\s*\d+/(\d+)", self.content)
                if progress_matches:
                    self.config_info['steps'] = max(int(s) for s in progress_matches)
            except Exception:
                pass

        # 从日志中提取训练时长
        try:
            time_matches = re.findall(r"\[([0-9]{1,2}:[0-9]{2}:[0-9]{2})<", self.content)
            if time_matches:
                elapsed = time_matches[-1]
                parts = elapsed.split(':')
                hours = int(parts[0]) if len(parts) >= 1 else 0
                self.config_info['training_time'] = f"{hours}h"
            else:
                self.config_info['training_time'] = None
        except Exception:
            self.config_info['training_time'] = None

        # 额外从日志中提取训练集大小及步数信息
        try:
            mm = re.search(r"max_train_steps\s*=\s*([0-9]+)", self.content, re.IGNORECASE)
            if mm and not self.config_info.get('steps'):
                self.config_info['steps'] = int(mm.group(1))

            mu = re.search(r"num_update_steps_per_epoch\s*=\s*([0-9]+)", self.content, re.IGNORECASE)
            if mu and not self.config_info.get('steps'):
                per_epoch = int(mu.group(1))
                epochs = int(self.config_info.get('num_train_epochs') or 0)
                if epochs > 0:
                    self.config_info['steps'] = per_epoch * epochs
        except Exception:
            pass
        
        # 最后：如果dataset_count为0或未提取到，尝试通过公式计算
        if not self.config_info.get('dataset_count') or self.config_info.get('dataset_count') == 0:
            self._calculate_dataset_count_from_formula()
    
    def _extract_json_config(self):
        """从JSON格式的配置中提取信息（ai-toolkit等新格式）"""
        # 提取JSON配置模式
        for key, pattern in JSON_CONFIG_PATTERNS.items():
            if self.config_info.get(key):  # 如果已经有值，跳过
                continue
            match = re.search(pattern, self.content)
            if match:
                value = match.group(1)
                # 尝试转换为数字
                try:
                    if '.' in value or 'e' in value.lower():
                        value = float(value)
                    else:
                        value = int(value)
                except ValueError:
                    pass  # 保持字符串
                self.config_info[key] = value
        
        # 提取数据集数量
        if not self.config_info.get('dataset_count'):
            for pattern in DATASET_COUNT_PATTERNS:
                matches = re.findall(pattern, self.content, re.MULTILINE)
                if matches:
                    try:
                        self.config_info['dataset_count'] = max(int(m) for m in matches)
                    except ValueError:
                        pass
                    break
        
        # 从底模路径提取底模名称
        if self.config_info.get('pretrained_model'):
            pretrained = self.config_info['pretrained_model']
            base_model_name = os.path.basename(pretrained.rstrip('/\\'))
            self.config_info['base_model_name'] = base_model_name
        
        # 将save_every映射到save_model_epochs（兼容性）
        if self.config_info.get('save_every') and not self.config_info.get('save_model_epochs'):
            self.config_info['save_model_epochs'] = self.config_info['save_every']
    
    def _calculate_dataset_count_from_formula(self):
        """通过公式计算训练集数量：训练集数量 = 总steps / (epoch * repeat)"""
        steps = self.config_info.get('steps')
        epochs = self.config_info.get('num_train_epochs')
        repeats = self.config_info.get('repeats')
        
        # 如果有steps和epochs，尝试计算
        if steps and epochs and epochs > 0:
            # 如果有repeat，使用公式：dataset_count = steps / (epoch * repeat)
            if repeats and repeats > 0:
                dataset_count = steps / (epochs * repeats)
                if dataset_count > 0:
                    self.config_info['dataset_count'] = int(dataset_count)
                    print(f"提示: 通过公式计算训练集数量: {steps} / ({epochs} * {repeats}) = {int(dataset_count)}")
            else:
                # 如果没有repeat，假设repeat=1：dataset_count = steps / epoch
                dataset_count = steps / epochs
                if dataset_count > 0:
                    self.config_info['dataset_count'] = int(dataset_count)
                    print(f"提示: 通过公式计算训练集数量: {steps} / {epochs} = {int(dataset_count)}")
    
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


def parse_log_file(log_file_path, filter_incomplete=True):
    """
    便捷函数：解析日志文件
    
    Args:
        log_file_path: 日志文件路径
        filter_incomplete: 是否过滤不完整的训练
        
    Returns:
        dict: 解析结果，失败返回None
    """
    parser = LogParser(log_file_path)
    return parser.parse(filter_incomplete=filter_incomplete)
