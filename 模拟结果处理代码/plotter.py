import matplotlib.pyplot as plt
import logging
import numpy as np
import os
from matplotlib.ticker import MaxNLocator  # <--- 新增导入
import config

def plot_msd(data_dict, fit_params=None, save_path=None, target_keyword=None, fit_start=None, fit_end=None, line_style='-', line_width=1, grid=True):
    """
    绘制 MSD 曲线，并在每条曲线上添加拟合线（如果启用）
    :param data_dict: { unique_key: (time, msd) } 字典
    :param fit_params: { unique_key: (slope, intercept) } 字典（如果为 None，则不绘制拟合线）
    :param save_path: 图片保存路径，如果为 None，则显示图像
    :param target_keyword: 目标关键字，用于筛选拟合线（可选）
    :param fit_start: 拟合起始时间
    :param fit_end: 拟合结束时间
    """
    plt.figure(figsize=(10, 6))

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
                text_x = fit_time[fit_mask][-1]
                text_y = fit_line[fit_mask][-1]
                offset = 0.05 * (plt.ylim()[1] - plt.ylim()[0])
                plt.text(text_x, text_y + offset, f'y={slope:.2e}x+{intercept:.2e}', 
                         fontsize=8, verticalalignment='bottom', horizontalalignment='right')

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

    # # 让 max_time 的标签向左偏移，避免太突兀
    # for label in ax.get_xticklabels():
    #     try:
    #         if np.isclose(float(label.get_text()), max_time, atol=1e-6):  # 允许浮点数误差
    #             label.set_ha('right')  # 让 max_time 的标签靠右，使其视觉上向左偏移
    #     except ValueError:
    #         continue  # 忽略非数字标签，避免错误

    # 标签设置
    plt.xlabel('Time (ps)', fontsize=12)
    plt.ylabel('Total MSD (Å²)', fontsize=12)  # <--- 修正单位符号
    plt.title('Time vs Total MSD', fontsize=14)
    plt.legend(loc='best')
    plt.grid(grid)
    plt.gca().tick_params(direction='in')
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logging.info(f"图像已保存: {save_path}")
        plt.close()
    else:
        plt.show()

