import matplotlib.pyplot as plt
import logging
import numpy as np
import os
from matplotlib.ticker import MaxNLocator
import matplotlib.colors as mcolors
from matplotlib import lines as mlines
import config
import colorsys
import itertools

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

    # ========== 新增颜色循环配置 ==========
    color_cycle = itertools.cycle(config.COLORS)  # 定义在函数内部

    plt.figure(figsize=(20, 6))
    ax = plt.gca()

    # 设置全局字体
    plt.rcParams.update({
        'font.family': 'serif',
        'font.serif': ['Times New Roman'],
        'mathtext.fontset': 'stix'  # 数学符号风格
    })
    
    # 初始化变量来存储 time 的最大和最小值
    min_time = float('inf')
    max_time = float('-inf')

    # ========== 新增图例分离逻辑 ==========
    data_handles = []
    data_labels = []
    fit_handles = []
    fit_labels = []

    # ========== 新增颜色生成函数 ==========
    def generate_contrast_color(base_hex, light=0.3, dark=0.7):
        """
        生成同色系高对比颜色对
        :param base_hex: 基础色十六进制
        :param light: 数据线亮度系数 (0-1)
        :param dark: 拟合线亮度系数 (0-1)
        :return: (data_color, fit_color)
        """
        # 转换为HSL空间
        rgb = mcolors.hex2color(base_hex)
        h, l, s = colorsys.rgb_to_hls(rgb[0], rgb[1], rgb[2])
        
        # 生成配色对
        data_color = colorsys.hls_to_rgb(h, light, s)
        fit_color = colorsys.hls_to_rgb(h, dark, min(s*1.5, 1.0))
        return (
            mcolors.to_hex(data_color),
            mcolors.to_hex(fit_color)
        )
    
    # 遍历数据，找到时间的最小值和最大值
    for key, (time, msd) in data_dict.items():
        # 获取基础色并生成对比色
        base_color = next(color_cycle)
        data_color, fit_color = generate_contrast_color(base_color)

        # 更新最小时间和最大时间
        min_time = min(min_time, np.min(time))
        max_time = max(max_time, np.max(time))

        # 处理键名
        ele_name = key.split("-")[-1].replace(".dat", "")
        
        
        # 绘制数据线（浅色+透明度）
        data_line = ax.plot(
            time, msd,
            label=ele_name,
            color=data_color,  # 使用浅色版本
            alpha=0.4,         # 透明度设置
            linestyle=line_style,
            linewidth=line_width,
            zorder=5
        )[0]

        data_handles.append(data_line)
        data_labels.append(ele_name)

        # 判断是否需要绘制拟合线：只对键中包含 target_keyword 的数据绘制拟合线
        if fit_params and key in fit_params:

            # 如果设置了 target_keyword，则检查
            if target_keyword and target_keyword.lower() not in key.lower():
                continue
            slope, intercept = fit_params[key]
            fit_time = np.array(time)
            fit_line = slope * fit_time + intercept

            fit_mask = (fit_time >= fit_start) & (fit_time <= fit_end)
            fit_line_obj, =ax.plot(
                fit_time[fit_mask],
                fit_line[fit_mask],
                color=fit_color,  # 使用深色版本
                linestyle='--',
                linewidth=line_width*1.5,  # 加粗50%
                alpha=1.0,        # 不透明
                zorder=4,         # 在数据线下层
                label=f"{ele_name}_Fit" + r'$\mathregular{y = %.5fx  %+0.4f}$' % (slope, intercept)  # 确保标签唯一性
            )

            fit_handles.append(fit_line_obj)
            fit_labels.append(f"{ele_name} Fit: "+ r'$\mathregular{y = %.5fx  %+0.4f}$' % (slope, intercept))

            # # 绘制拟合线，并捕获句柄
            # fit_line, = plt.plot(
            #     fit_time[fit_mask],
            #     fit_line[fit_mask],
            #     linestyle='--',
            #     linewidth=1,
            #     label=f"Fit_Line_{ele_name}:"  # 确保标签唯一性
            # )
            # fit_legend_entries.append((fit_line, fit_line.get_label() + r'$\mathregular{y = {%.5f}x  %+.4f}$' % (slope, intercept)))  # 存储句柄和标签

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

    # ========== 图例优化 ==========
    # 合并图例项（数据线在上，拟合线在下）
    all_handles = data_handles + fit_handles
    all_labels = data_labels + fit_labels
    
    # 创建不透明图例句柄
    # handles, labels = ax.get_legend_handles_labels()
    # new_handles = []
    # for h in handles:
    #     if isinstance(h, mlines.Line2D):
    #         # 克隆句柄并移除透明度
    #         new_h = mlines.Line2D(
    #             [], [],
    #             color=h.get_color(),
    #             linestyle=h.get_linestyle(),
    #             linewidth=h.get_linewidth(),
    #             marker=h.get_marker(),
    #             markersize=h.get_markersize(),
    #             alpha=1.0  # 强制图例不透明
    #         )
    #         new_handles.append(new_h)
    
    # 应用优化后的图例
    ax.legend(
        handles=all_handles,
        labels=all_labels,
        loc='best',
        frameon=True,
        edgecolor='none',
        framealpha=0,
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

