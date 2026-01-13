#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
训练分析器模块
"""

from .log_parser import LogParser, parse_log_file

# 延迟导入可视化模块（需要matplotlib）
try:
    from .visualizer import TrainingVisualizer, plot_training_curve, plot_top10_bar_chart
except ImportError:
    TrainingVisualizer = None
    plot_training_curve = None
    plot_top10_bar_chart = None

from .report_manager import (
    ReportManager, 
    save_record, 
    load_records, 
    delete_record, 
    get_record_by_id, 
    get_records_summary
)

from .file_manager import (
    FileManager,
    get_file_manager,
    copy_to_log_dir,
    move_to_history,
    get_pending_logs,
    get_history_logs
)

__all__ = [
    'LogParser',
    'parse_log_file',
    'TrainingVisualizer',
    'plot_training_curve',
    'plot_top10_bar_chart',
    'ReportManager',
    'save_record',
    'load_records',
    'delete_record',
    'get_record_by_id',
    'get_records_summary',
    'FileManager',
    'get_file_manager',
    'copy_to_log_dir',
    'move_to_history',
    'get_pending_logs',
    'get_history_logs',
]
