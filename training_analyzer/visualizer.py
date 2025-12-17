#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
可视化模块 - 绘制训练曲线和柱状图
"""

import matplotlib
matplotlib.use('TkAgg')  # 使用TkAgg后端，适配tkinter
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

from .config import (
    PLOT_DPI, PLOT_FIGURE_SIZE, PLOT_LINE_WIDTH, PLOT_MARKER_SIZE,
    PRIMARY_COLOR, SECONDARY_COLOR, ACCENT_COLOR
)

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']  # 显示中文
plt.rcParams['axes.unicode_minus'] = False  # 显示负号


class TrainingVisualizer:
    """训练可视化类"""
    
    def __init__(self):
        """初始化可视化器"""
        self.figure = None
        self.canvas = None
    
    def plot_training_curve(self, val_losses, statistics, parent=None):
        """
        绘制训练曲线
        
        Args:
            val_losses: list of {'epoch': int, 'val_loss': float}
            statistics: dict 统计信息
            parent: tkinter父容器（可选）
            
        Returns:
            FigureCanvasTkAgg 或 Figure
        """
        # 提取数据
        epochs = [item['epoch'] for item in val_losses]
        losses = [item['val_loss'] for item in val_losses]
        
        # 创建图表
        self.figure = plt.Figure(figsize=PLOT_FIGURE_SIZE, dpi=PLOT_DPI)
        ax = self.figure.add_subplot(111)
        
        # 绘制曲线
        line = ax.plot(epochs, losses, 
                color=PRIMARY_COLOR, 
                linewidth=PLOT_LINE_WIDTH, 
                marker='o', 
                markersize=4,
                label='Val Loss')[0]
        
        # 在每个数据点上显示loss值（如果数据点不太多）
        if len(epochs) <= 50:
            for epoch, loss in zip(epochs, losses):
                ax.annotate(f'{loss:.6f}',
                           xy=(epoch, loss),
                           xytext=(0, 5),
                           textcoords='offset points',
                           fontsize=7,
                           ha='center',
                           alpha=0.6,
                           color=PRIMARY_COLOR)
        else:
            # 如果数据点太多，只显示关键点的值
            for epoch, loss in zip(epochs, losses):
                if epoch % 10 == 0 or epoch == statistics.get('best_epoch'):
                    ax.annotate(f'{loss:.6f}',
                               xy=(epoch, loss),
                               xytext=(0, 5),
                               textcoords='offset points',
                               fontsize=7,
                               ha='center',
                               alpha=0.6,
                               color=PRIMARY_COLOR)
        
        # 标记最佳epoch
        best_epoch = statistics['best_epoch']
        best_loss = statistics['min_loss']
        ax.plot(best_epoch, best_loss, 
                'r*', 
                markersize=PLOT_MARKER_SIZE * 2, 
                label=f'最佳: Epoch {best_epoch}',
                zorder=5)
        
        # 添加最佳点注释
        ax.annotate(f'最佳\nEpoch {best_epoch}\nLoss: {best_loss:.6f}',
                   xy=(best_epoch, best_loss),
                   xytext=(20, 20),
                   textcoords='offset points',
                   bbox=dict(boxstyle='round,pad=0.5', fc=ACCENT_COLOR, alpha=0.7),
                   arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0',
                                 color='red', lw=2),
                   fontsize=9)
        
        # 设置标题和标签
        ax.set_title('训练曲线 - Epoch vs Val Loss', fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('Epoch', fontsize=12)
        ax.set_ylabel('Val Loss', fontsize=12)
        
        # 添加网格
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # 添加图例
        ax.legend(loc='upper right', fontsize=10)
        
        # 调整布局
        self.figure.tight_layout()
        
        # 如果有父容器，创建canvas
        if parent:
            self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
            self.canvas.draw()
            self._add_hover_annotation(ax, epochs, losses, line)
            return self.canvas
        
        self._add_hover_annotation(ax, epochs, losses, line)
        return self.figure
    
    def plot_top10_bar_chart(self, top_10_data, parent=None):
        """
        绘制前10个最优epoch的柱状图
        
        Args:
            top_10_data: list of {'epoch': int, 'val_loss': float}
            parent: tkinter父容器（可选）
            
        Returns:
            FigureCanvasTkAgg 或 Figure
        """
        # 提取数据
        epochs = [f"Epoch {item['epoch']}" for item in top_10_data]
        losses = [item['val_loss'] for item in top_10_data]
        
        # 创建颜色渐变
        colors = self._generate_gradient_colors(len(top_10_data))
        
        # 创建图表
        self.figure = plt.Figure(figsize=PLOT_FIGURE_SIZE, dpi=PLOT_DPI)
        ax = self.figure.add_subplot(111)
        
        # 绘制柱状图
        bars = ax.bar(range(len(epochs)), losses, color=colors, alpha=0.8, edgecolor='black')
        
        # 在柱子上显示数值
        for i, (bar, loss) in enumerate(zip(bars, losses)):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{loss:.6f}',
                   ha='center', va='bottom', fontsize=8, rotation=0)
        
        # 设置x轴标签
        ax.set_xticks(range(len(epochs)))
        ax.set_xticklabels(epochs, rotation=45, ha='right')
        
        # 设置标题和标签
        ax.set_title('前10个最优Epoch分析', fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('Epoch', fontsize=12)
        ax.set_ylabel('Val Loss', fontsize=12)
        
        # 添加网格
        ax.grid(True, alpha=0.3, linestyle='--', axis='y')
        
        # 调整y轴范围
        y_min = min(losses)
        y_max = max(losses)
        y_range = y_max - y_min
        ax.set_ylim(y_min - y_range * 0.1, y_max + y_range * 0.2)
        
        # 调整布局
        self.figure.tight_layout()
        
        # 如果有父容器，创建canvas
        if parent:
            self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
            self.canvas.draw()
            return self.canvas
        
        return self.figure
    
    def _add_hover_annotation(self, ax, epochs, losses, line):
        """添加鼠标悬停显示详细信息的功能"""
        # 创建注释对象（初始隐藏）
        annot = ax.annotate('', xy=(0, 0), xytext=(20, 20),
                           textcoords='offset points',
                           bbox=dict(boxstyle='round', fc='w', alpha=0.8),
                           arrowprops=dict(arrowstyle='->'),
                           fontsize=9)
        annot.set_visible(False)
        
        def update_annot(ind):
            """更新注释内容"""
            epoch_idx = ind['ind'][0]
            epoch = epochs[epoch_idx]
            loss = losses[epoch_idx]
            annot.xy = (epoch, loss)
            text = f'Epoch: {epoch}\nLoss: {loss:.10f}'
            annot.set_text(text)
            annot.get_bbox_patch().set_facecolor(ACCENT_COLOR)
            annot.get_bbox_patch().set_alpha(0.8)
        
        def hover(event):
            """鼠标悬停事件处理"""
            if event.inaxes == ax:
                vis = annot.get_visible()
                cont, ind = line.contains(event)
                if cont:
                    update_annot(ind)
                    annot.set_visible(True)
                    self.figure.canvas.draw_idle()
                else:
                    if vis:
                        annot.set_visible(False)
                        self.figure.canvas.draw_idle()
        
        # 连接鼠标移动事件
        self.figure.canvas.mpl_connect('motion_notify_event', hover)
    
    def _generate_gradient_colors(self, n):
        """生成渐变颜色列表"""
        start_color = (46, 125, 50)    # 深绿色
        end_color = (165, 214, 167)    # 浅绿色
        
        colors = []
        for i in range(n):
            ratio = i / (n - 1) if n > 1 else 0
            r = int(start_color[0] + (end_color[0] - start_color[0]) * ratio)
            g = int(start_color[1] + (end_color[1] - start_color[1]) * ratio)
            b = int(start_color[2] + (end_color[2] - start_color[2]) * ratio)
            color = f'#{r:02x}{g:02x}{b:02x}'
            colors.append(color)
        
        return colors
    
    def save_figure(self, filename):
        """保存图表到文件"""
        if self.figure:
            self.figure.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"图表已保存到: {filename}")
        else:
            print("错误: 没有可保存的图表")


# 便捷函数
def plot_training_curve(val_losses, statistics, parent=None):
    """绘制训练曲线（便捷函数）"""
    visualizer = TrainingVisualizer()
    return visualizer.plot_training_curve(val_losses, statistics, parent)


def plot_top10_bar_chart(top_10_data, parent=None):
    """绘制前10最优柱状图（便捷函数）"""
    visualizer = TrainingVisualizer()
    return visualizer.plot_top10_bar_chart(top_10_data, parent)
