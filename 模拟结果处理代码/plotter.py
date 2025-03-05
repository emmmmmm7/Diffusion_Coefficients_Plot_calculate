import matplotlib.pyplot as plt
import logging
import numpy as np
import os
from matplotlib.ticker import MaxNLocator  # <--- 新增导入
import config

def plot_msd(data_dict, fit_params=None, save_path=None, target_keyword=None, fit_start=None, fit_end=None, line_style='-', line_width=1):
    """
    绘制 MSD 曲线，并在每条曲线上添加拟合线（如果启用）
    :param data_dict: { unique_key: (time, msd) } 字典
    :param fit_params: { unique_key: (slope, intercept) } 字典（如果为 None，则不绘制拟合线）
    :param save_path: 图片保存路径，如果为 None，则显示图像
    :param target_keyword: 目标关键字，用于筛选拟合线（可选）
    :param fit_start: 拟合起始时间
    :param fit_end: 拟合结束时间
    """
    plt.figure(figsize=(20, 6))

    # 设置全局字体
    plt.rcParams.update({
        'font.family': 'serif',
        'font.serif': ['Times New Roman'],
        'mathtext.fontset': 'stix'  # 数学符号风格
    })
    
    # 初始化变量来存储 time 的最大和最小值
    min_time = float('inf')
    max_time = float('-inf')

    # 遍历数据，找到时间的最小值和最大值
    for key, (time, msd) in data_dict.items():
        # 更新最小时间和最大时间
        min_time = min(min_time, np.min(time))
        max_time = max(max_time, np.max(time))
        
        # 绘制数据线
        plt.plot(time, msd, label=key, linestyle=line_style, linewidth=line_width)

        # 判断是否需要绘制拟合线：只对键中包含 target_keyword 的数据绘制拟合线
        if fit_params and key in fit_params:
            # 如果设置了 target_keyword，则检查
            if target_keyword and target_keyword.lower() not in key.lower():
                continue
            slope, intercept = fit_params[key]
            fit_time = np.array(time)
            fit_line = slope * fit_time + intercept

            fit_mask = (fit_time >= fit_start) & (fit_time <= fit_end)
            plt.plot(fit_time[fit_mask], fit_line[fit_mask], linestyle='--', linewidth=1, label=f"{key} (fit)")

            # 显示拟合表达式，避免挡住数据线
            if np.any(fit_mask):
                # 计算最佳位置
                x_pos = np.median(fit_time[fit_mask])  # 使用中位数位置
                y_pos = np.median(fit_line[fit_mask])
                
                # 动态偏移
                y_range = plt.ylim()[1] - plt.ylim()[0]
                offset = y_range * 0.04
                
                # 智能对齐
                ha = 'left' if x_pos < np.median(plt.xlim()) else 'right'
                va = 'bottom' if y_pos < np.median(plt.ylim()) else 'top'
                
                plt.text(
                    x_pos, y_pos + (offset if va == 'bottom' else -offset),
                    r'$\mathregular{y = {%.5f}x  %+.2f}$' % (slope, intercept),  # 添加R²值
                    fontsize=9,
                    verticalalignment=va,
                    horizontalalignment=ha,
                    # bbox=dict(boxstyle="round,pad=0.3", 
                    #         facecolor='white', 
                    #         edgecolor='gray', 
                    #         alpha=0.8),
                    rotation_mode='anchor',
                    rotation=np.clip(np.arctan(slope)*180/np.pi, -45, 45)  # 限制旋转角度
                )
                
    # ==================== 坐标轴优化 ==================== 
    # 动态设置 x 轴的范围：确保 x 轴的起点和终点根据时间数据来确定
    plt.xlim([min_time, max_time])
    # 坐标轴刻度优化
    ax = plt.gca()
    ticks = ax.get_xticks()  # 获取当前自动生成的刻度
    ticks = np.append(ticks, max_time)  # 强制添加 max_time
    ax.set_xticks(ticks)  # 重新设定刻度
    # 确保显示最大刻度（关键修改）
    ax.xaxis.set_major_locator(MaxNLocator(nbins=5, prune=None))  # <--- 防止x轴最低刻度被裁剪
    ax.yaxis.set_major_locator(MaxNLocator(nbins=7, prune=None))  # <--- 防止y轴最低刻度被裁剪

    # 标签设置
    plt.xlabel('Time (ps)', fontsize=12)
    plt.ylabel('MSD (Å²)', fontsize=12)  # <--- 修正单位符号
    ax.legend(
        loc='best',
        frameon=True,
        framealpha=0.9,
        edgecolor='none',
        fontsize=10
    )
    plt.grid(False)
    plt.gca().tick_params(direction='in')
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logging.info(f"图像已保存: {save_path}")
        plt.close()
    else:
        plt.show()

