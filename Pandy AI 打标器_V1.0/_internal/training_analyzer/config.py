#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
训练分析器配置文件 - 常量定义
"""

import os
from pathlib import Path

# 获取模块目录
MODULE_DIR = Path(__file__).parent

# 颜色主题 - 绿色系
PRIMARY_COLOR = "#2e7d32"      # 深绿色
SECONDARY_COLOR = "#4caf50"    # 中绿色
ACCENT_COLOR = "#81c784"       # 浅绿色
TEXT_COLOR = "#1b5e20"         # 深绿色文字
BG_COLOR = "#e8f5e9"           # 背景淡绿色
HOVER_COLOR = "#a5d6a7"        # 悬停颜色

# 字体配置
FONT_FAMILY = "Microsoft YaHei UI"  # 微软雅黑
FONT_SIZE_TITLE = 14
FONT_SIZE_NORMAL = 11
FONT_SIZE_SMALL = 9

# 文件路径配置 - 相对于模块目录
RECORDS_FILE = str(MODULE_DIR / "log_record" / "records.json")
LOGS_BACKUP_DIR = str(MODULE_DIR / "log_record" / "logs")

# 训练日志目录配置
TRAINING_LOG_DIR = str(MODULE_DIR / "training_log")
TRAINING_LOG_HISTORY_DIR = str(MODULE_DIR / "training_log_history")

# 日志解析正则表达式
VAL_LOSS_PATTERN = r"{'val_loss': ([0-9.]+), 'epoch': ([0-9]+)}"

# 从日志中提取的配置信息模式
CONFIG_PATTERNS = {
    'pretrained_model': r"pretrained_model_name_or_path='([^']+)'",
    'output_dir': r"output_dir='([^']+)'",
    'save_name': r"save_name='([^']+)'",
    'learning_rate': r"learning_rate=([0-9.eE+-]+)",
    'lr_scheduler': r"lr_scheduler='([^']+)'",
    'num_train_epochs': r"num_train_epochs=([0-9]+)",
    'rank': r"(?:^|,\s)rank=([0-9]+)",
    'train_batch_size': r"train_batch_size=([0-9]+)",
    'repeats': r"(?:^|,\s)repeats=([0-9]+)",
    'save_model_epochs': r"save_model_epochs=([0-9]+)",
    'train_data_dir': r"train_data_dir='([^']+)'",
}

# JSON格式配置提取模式（ai-toolkit等新格式）
JSON_CONFIG_PATTERNS = {
    'job_name': r'Running job:\s*([^\s#\n]+)',                    # 从 "Running job: sh-10.25" 提取模型名称
    'steps': r'"steps":\s*(\d+)',                                  # "steps": 3000
    'learning_rate': r'"lr":\s*([0-9.eE+-]+)',                    # "lr": 0.0002
    'save_every': r'"save_every":\s*(\d+)',                       # "save_every": 400
    'rank': r'"linear":\s*(\d+)',                                  # "linear": 32 (LoRA rank)
    'train_batch_size': r'"batch_size":\s*(\d+)',                 # "batch_size": 2
    'pretrained_model': r'"name_or_path":\s*"([^"]+)"',           # 底模路径
    'dataset_path': r'"folder_path":\s*"([^"]+)"',                # 数据集路径
    'control_path': r'"control_path":\s*"([^"]+)"',               # 控制图路径
    'network_type': r'"type":\s*"(lora|loha|lokr)"',              # 网络类型
    'optimizer': r'"optimizer":\s*"([^"]+)"',                     # 优化器
    'dtype': r'"dtype":\s*"([^"]+)"',                             # 数据类型
    'sample_every': r'"sample_every":\s*(\d+)',                   # 采样间隔
}

# 数据集数量提取模式
DATASET_COUNT_PATTERNS = [
    r'-\s*Found\s+(\d+)\s+images',                                # "- Found 40 images"
    r'Num examples\s*=\s*(\d+)',                                  # "Num examples = 36"
    r'100%\|[█]+\|\s*(\d+)/\d+\s*\[',                             # "100%|██████████| 30/30 [00:02" - 进度条格式
    r'(\d+)\s+files\s*$',                                         # "40 files"
]

# 步骤级别的loss模式（支持多种格式）
STEP_LOSS_PATTERNS = [
    r"step_loss=([0-9.]+)",                                       # Format 1: step_loss=0.0573
    r"loss:\s*([0-9.]+e[+-][0-9]+)",                             # Format 2/3: loss: 6.710e-01
    r"loss:\s*([0-9.]+)",                                         # Format fallback: loss: 0.671
]

# 图表配置
PLOT_DPI = 100
PLOT_FIGURE_SIZE = (10, 5)
PLOT_LINE_WIDTH = 2
PLOT_MARKER_SIZE = 8

# Top N配置
TOP_N_EPOCHS = 10

# 表格列配置
TABLE_COLUMNS = {
    'model_name': '模型名称',
    'analysis_date': '训练时间',
    'best_val_loss': '最佳Loss',
    'lr_scheduler': '学习率调度器',
    'num_epochs': 'Epoch数',
    'best_epoch': '最佳Epoch',
}

# 列宽配置
TABLE_COLUMN_WIDTHS = {
    'model_name': 200,
    'analysis_date': 150,
    'best_val_loss': 120,
    'lr_scheduler': 150,
    'num_epochs': 100,
    'best_epoch': 100,
}
