import os
import numpy as np
import matplotlib.pyplot as plt
import itertools
import colorsys
import matplotlib.colors as mcolors
from matplotlib.ticker import MaxNLocator, ScalarFormatter
import config
import logging
from logging.handlers import RotatingFileHandler

# 配置日志系统
def setup_logging():
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            RotatingFileHandler(
                "pressure_analysis.log",
                maxBytes=1024*1024,
                backupCount=3
            ),
            logging.StreamHandler()
        ]
    )
    # 直接关闭fontTools的日志
    logging.getLogger('fontTools').setLevel(logging.WARNING)

# 生成对比色函数
def generate_contrast_color(base_hex, light=0.3, dark=0.7):
    """生成同色系对比色对"""
    rgb = mcolors.hex2color(base_hex)
    h, l, s = colorsys.rgb_to_hls(rgb[0], rgb[1], rgb[2])
    data_color = colorsys.hls_to_rgb(h, light, s)
    fit_color = colorsys.hls_to_rgb(h, dark, min(s*1.5, 1.0))
    return (mcolors.to_hex(data_color), mcolors.to_hex(fit_color))

# 数据读取和处理函数
def process_data_files(root_dir, colors, output_dir, ignore_dirs, verify_dirs, start_ps, end_ps, plot_model, all_time):
    """处理数据并区分验证集"""
    averages = {}
    verify_averages = {}  # 新增：存储验证数据
    color_cycle = itertools.cycle(colors)
    
    # 创建输出子目录
    timeseries_dir = os.path.join(output_dir, "timeseries_plots")
    os.makedirs(timeseries_dir, exist_ok=True)
    
    # 验证根目录
    if not os.path.exists(root_dir):
        raise FileNotFoundError(f"配置的根目录不存在：{root_dir}")
    
    folders = [f for f in os.listdir(root_dir) 
              if os.path.isdir(os.path.join(root_dir, f))]
    if not folders:
        raise ValueError(f"在指定目录 {root_dir} 中未找到任何子文件夹")
    
    logging.info(f"开始处理 {len(folders)} 个文件夹...")
    
    for folder_name in sorted(folders):
        # 忽略指定前缀的文件夹
        prefix = folder_name.split("-")[0]

        # 处理忽略目录
        if prefix in ignore_dirs:
            logging.info(f"忽略文件夹 '{folder_name}'（配置排除）")
            continue
        
        # 标记验证目录
        is_verify = prefix in verify_dirs

        # 忽略output文件夹
        if folder_name == "output":
            continue
            
        folder_path = os.path.join(root_dir, folder_name)

        # 根据绘图模式选择数据文件
        if plot_model == 1:
            data_file_name = "total-pressure.dat"
            data_columns = (None, 0)  # 单列数据
            y_label = "Pressure"
        elif plot_model == 2:
            data_file_name = "T-E.dat"
            data_columns = (0, 1)     # 时间列和温度列
            y_label = "Temperature (K)"
        else:
            raise ValueError(f"无效的绘图模式: {plot_model}")
        
        data_file = os.path.join(folder_path, "results", data_file_name)
        
        # 文件夹名解析验证
        try:
            param_part = folder_name.split("-")[-1]
            float(param_part)
        except (ValueError, IndexError):
            logging.warning(f"跳过文件夹 '{folder_name}'：命名不符合规范")
            continue

        if not os.path.exists(data_file):
            logging.warning(f"跳过文件夹 {folder_name}：未找到 {data_file_name}")
            continue
            
        try:
            # 通用数据加载逻辑
            if plot_model == 1:
                # 模式1：单列压力数据
                data = np.loadtxt(data_file)
                n_points = len(data)
                time_fs = np.arange(n_points)
                time_ps = time_fs / 1000  # 确保time_ps在此定义
            elif plot_model == 2:
                # 模式2：多列数据，提取指定列
                try:
                    # 使用更稳健的genfromtxt加载数据
                    full_data = np.genfromtxt(data_file, invalid_raise=False)
                    
                    # 检测并处理包含NaN的行
                    nan_mask = np.isnan(full_data).any(axis=1)
                    if np.any(nan_mask):
                        nan_count = np.sum(nan_mask)
                        valid_data = full_data[~nan_mask]
                        logging.warning(
                            f"在文件夹 {folder_name} 中发现 {nan_count} 行包含NaN值 "
                            f"(总行数：{len(full_data)})，已自动过滤"
                        )
                        
                        # 如果过滤后无有效数据则跳过
                        if len(valid_data) == 0:
                            logging.warning(f"文件夹 {folder_name} 的 {data_file_name} 无有效数据")
                            continue
                            
                        full_data = valid_data
                        
                    # 提取时间和温度数据
                    time_fs = full_data[:, data_columns[0]].astype(float)
                    data = full_data[:, data_columns[1]].astype(float)
                    
                    # 时间归零处理（从第一个有效数据点开始）
                    time_fs -= time_fs[0]  # 使时间从0开始
                    
                    n_points = len(data)
                    time_ps = time_fs / 1000  # 转换为ps
                    
                except Exception as e:
                    logging.error(f"加载 {data_file_name} 失败：{str(e)}")
                    continue
            else:
                raise ValueError(f"无效的绘图模式: {plot_model}")
            
            # 添加安全校验
            if 'time_ps' not in locals():
                raise ValueError("时间序列生成失败，请检查数据文件格式")


            # 时间截取逻辑修改
            if all_time == 1:
                start_idx = 0
                end_idx = n_points - 1
                used_start_ps = 0.0
                used_end_ps = time_ps[-1]
            else:
                # 精确查找索引（避免fs转换误差）
                start_idx = np.searchsorted(time_ps, start_ps, side='left')
                end_idx = np.searchsorted(time_ps, end_ps, side='right') - 1
                end_idx = min(end_idx, n_points-1)  # 安全保护
                used_start_ps = start_ps
                used_end_ps = end_ps

             # 截取数据段
            data = data[start_idx:end_idx+1]
            time_ps = time_ps[start_idx:end_idx+1]

            # 新增：确保时间序列连续（处理可能的索引错误）
            if len(time_ps) == 0:
                logging.warning(f"跳过文件夹 {folder_name}：时间范围内无数据")
                continue
                        
            # 添加调试日志
            logging.debug(
                f"时间范围 - {folder_name}: "
                f"配置all_time={all_time} "
                f"实际使用范围=[{used_start_ps:.2f}ps, {used_end_ps:.2f}ps] "
                f"数据点数={len(data)}"
            )

            # 通用时间处理
            time_ps = time_fs / 1000  # 统一转换为ps
            
            # 应用时间截取
            start_fs = int(start_ps * 1000)
            end_fs = int(end_ps * 1000)
            start_idx = max(0, start_fs)
            end_idx = min(n_points-1, end_fs)
            
            data = data[start_idx:end_idx+1]
            time_ps = time_ps[start_idx:end_idx+1]
            
            if len(data) == 0:
                logging.warning(f"跳过文件夹 {folder_name}：时间范围内无数据")
                continue
                
            avg = np.mean(data)
            
            # 存储数据
            target_dict = verify_averages if is_verify else averages
            target_dict[param_part] = avg
            
            # 绘图部分
            base_color = next(color_cycle)
            data_color, _ = generate_contrast_color(base_color)
            
            plt.figure(figsize=(10, 6))
            plt.rcParams.update({
                'font.family': 'serif',
                'font.serif': ['Times New Roman'],
                'mathtext.fontset': 'stix'
            })

            plt.plot(time_ps, data, color=data_color, alpha=0.6)
            plt.title(f"{y_label.split(' ')[0]} Data - {param_part}")
            plt.xlabel("Time (ps)")
            plt.ylabel(y_label)
            
            ax = plt.gca()
            ax.xaxis.set_major_locator(MaxNLocator(5))
            ax.xaxis.set_major_formatter(ScalarFormatter(useOffset=False))
            ax.tick_params(direction='in', which='both', top=False, right=False)
            plt.xlim(time_ps[0], time_ps[-1])

            # 设置pdf字体嵌入
            plt.rcParams['pdf.fonttype'] = 42  # 嵌入 TrueType 字体
            plt.rcParams['ps.fonttype'] = 42   # 兼容 PostScript

            plot_path = os.path.join(timeseries_dir, f"{folder_name}_plot.pdf")
            plt.savefig(plot_path, format='pdf', bbox_inches='tight')
            plt.close()
            logging.info(f"时序图已保存到：{plot_path}")
            
        except Exception as e:
            logging.error(f"处理文件夹 {folder_name} 时出错：{str(e)}", exc_info=True)
    
    return averages, verify_averages

# 平均值分析和拟合函数
def analyze_averages(averages, verify_averages, colors, verify_color, expected_pressure, output_dir, analyse_model):
    """分析数据并区分验证集"""

    # 参数有效性检查更新
    if analyse_model not in (0,1,2,3):
        raise ValueError("analyse_model参数必须为0、1、2或3")
    
    """根据分析模式执行不同操作"""
    if analyse_model == 0:
        logging.info("分析模式0: 跳过所有分析")
        return None, None
    
    # 合并数据显示但分开处理
    all_data = {**averages, **verify_averages}
    
    logging.info("有效参数-平均值数据：")
    for k in sorted(all_data.keys(), key=float):
        source = "(验证集)" if k in verify_averages else ""
        logging.info(f"参数: {k.ljust(10)} → 平均值: {all_data[k]:.4f} {source}")

    if analyse_model == 1:
        logging.info("分析模式1: 仅输出平均值")
        return None, None

    # 参数转换（仅使用非验证数据）
    params = []
    valid_keys = []
    for key in averages.keys():
        try:
            params.append(float(key))
            valid_keys.append(key)
        except ValueError:
            logging.warning(f"跳过无效参数 '{key}'")
            continue
    
    if not params:
        raise ValueError("没有有效的数值型参数")
    
    if len(params) < 2:
        raise ValueError(f"有效数据点不足（当前{len(params)}个），至少需要2个点")
    
    # 数据排序
    values = np.array([averages[k] for k in valid_keys])
    sort_idx = np.argsort(params)
    x = np.array(params)[sort_idx]
    y = values[sort_idx]
    
    # 线性拟合
    coeffs = np.polyfit(x, y, 1)
    fit_fn = np.poly1d(coeffs)
    target_param = (expected_pressure - coeffs[1]) / coeffs[0]
    
    # 绘图设置
    plt.figure(figsize=(12, 7))

    # 设置全局字体
    plt.rcParams.update({
        'font.family': 'serif',
        'font.serif': ['Times New Roman'],
        'mathtext.fontset': 'stix'  # 数学符号风格
    })

    ax = plt.gca()
    base_color = colors[0]
    data_color, fit_color = generate_contrast_color(base_color)
    
    # 刻度设置
    ax.tick_params(direction='in', which='both', top=False, right=False)
    ax.xaxis.set_major_formatter(ScalarFormatter(useOffset=False, useMathText=True))
    ax.yaxis.set_major_formatter(ScalarFormatter(useOffset=False, useMathText=True))
    
    # 绘制散点图
    ax.scatter(x, y, color=data_color, s=80, edgecolor='w', linewidth=1, zorder=3, label="Average Values")

    # 绘制验证数据
    if verify_averages:
        verify_params = [float(k) for k in verify_averages.keys()]
        verify_values = [verify_averages[k] for k in verify_averages.keys()]
        ax.scatter(verify_params, verify_values, color=verify_color, s=80, 
                  edgecolor='w', marker='s', zorder=4, label="Validation Data")

    # 1) 计算出实际数据范围 + 目标参数
    x_data_min = x.min()
    x_data_max = x.max()
    if analyse_model == 2:
        x_min = min(x_data_min, target_param)
        x_max = max(x_data_max, target_param)
    else:
        x_min = x_data_min
        x_max = x_data_max

    # 2) 给一点边距（如 5%）
    margin = (x_max - x_min) * 0.05
    x_min_plot = x_min - margin
    x_max_plot = x_max + margin

    # 3) 在 [x_min_plot, x_max_plot] 之间生成更多点来画拟合曲线
    x_fit = np.linspace(x_min_plot, x_max_plot, 500)
    y_fit = fit_fn(x_fit)
    # 生成平滑拟合曲线
    y_fit = fit_fn(x_fit)
    ax.plot(x_fit, y_fit, '--', 
            color=fit_color,
            linewidth=2.5,
            alpha=0.8,
            zorder=2,
            label = f"Fit: " + r'$\mathregular{y = %.5fx %+0.4f}$' % (coeffs[0], coeffs[1])
    )

    # 目标线设置
    if analyse_model == 2:
        ax.axhline(expected_pressure, color='#2c3e50', linestyle='-.', 
                linewidth=1.5, alpha=0.7, zorder=1,
                label=f'Target Pressure: {expected_pressure}')
        ax.axvline(target_param, color='#2c3e50', linestyle='-.',
                linewidth=1.5, alpha=0.7, zorder=1,
                label=f'Predicted Parameter: {target_param:.8f}')

    # 坐标轴设置
    ax.set_xlabel("Parameter Value", fontsize=13, labelpad=8)
    ax.set_ylabel("Average Pressure", fontsize=13, labelpad=8)
    
    # 刻度优化
    ax.xaxis.set_major_locator(MaxNLocator(prune=None, steps=[1, 2, 5], nbins=8))
    ax.yaxis.set_major_locator(MaxNLocator(prune=None, steps=[1, 2, 5], nbins=8))
    
    # 网格线设置
    ax.grid(True, which='major', linestyle='--', linewidth=0.5, alpha=0.5)
    
    # 图例美化
    legend = ax.legend(loc='best', frameon=True, framealpha=0,
                      edgecolor='#2c3e50', fontsize=10)
    legend.get_frame().set_facecolor('#f8f9fa')
    
    # 自动调整范围
    ax.set_xlim(left=x_fit[0], right=x_fit[-1])

    # 设置pdf字体嵌入
    plt.rcParams['pdf.fonttype'] = 42  # 嵌入 TrueType 字体
    plt.rcParams['ps.fonttype'] = 42   # 兼容 PostScript
    
    # 修改保存路径到output目录
    analysis_path = os.path.join(output_dir, "average_pressure_analysis.pdf")
    plt.savefig(analysis_path, format='pdf', bbox_inches='tight')
    plt.close()
    logging.info(f"分析图表已保存到：{analysis_path}")
    
    return coeffs, target_param

# 主执行函数
def main():
    setup_logging()
    logging.info("===== nPT/nVT绘图分析程序启动 =====")
    
    try:
        # 加载配置
        cfg = config.config_data

        # 参数验证
        if cfg.get("analyse_model", 2) not in (0,1,2,3):
            raise ValueError("analyse_model参数必须为0、1或2")
        if cfg.get("all_time", 0) not in (0,1):
            raise ValueError("all_time参数必须为0或1")
        
        logging.info(f"配置文件加载成功\n"
                    f"数据路径: {cfg['data_path']}\n"
                    f"排除前缀: {cfg.get('ignore_dirs', [])}\n"
                    f"预期压力: {cfg['expected_pressure']}")
        
        # 创建输出目录（在600K目录下）
        output_dir = os.path.join(cfg["data_path"], "output")
        os.makedirs(output_dir, exist_ok=True)
        logging.info(f"输出目录已创建：{output_dir}")
        
        # 处理数据文件时传入新参数
        averages, verify_averages = process_data_files(
            cfg["data_path"], 
            cfg["colors"], 
            output_dir,
            cfg.get("ignore_dirs", []),
            cfg.get("verify_dirs", []),
            cfg.get("start_time_ps", 0),
            cfg.get("end_time_ps", 100),
            cfg.get("plot_model", 1),
            cfg.get("all_time", 0)
        )
        logging.info(f"成功处理 {len(averages)} 个有效数据文件")
        
        # 保存结果到output目录（修改后）
        result_path = os.path.join(output_dir, "average_pressures.txt")
        with open(result_path, "w") as f:
            all_data = {**averages, **verify_averages}
            # 计算列宽
            max_param_len = max(len(k) for k in all_data.keys())
            col_width = max(max_param_len, 10)  # 最小列宽10字符

            # 写入表头
            header = (f"{'Parameter':>{col_width}}    {'Average':^12}    Notes")
            separator = "-" * (col_width + 12 + 10)  # 动态分隔线长度
            f.write(f"{header}\n{separator}\n")

            # 合并数据并排序（按数值排序但保留原始字符串）
            sorted_params = sorted(all_data.keys(), key=lambda x: float(x))
            
            for param in sorted_params:
                # 原始参数字符串
                param_str = param.rjust(col_width)
                
                # 格式化平均值（固定4位小数）
                avg_str = f"{all_data[param]:12.4f}"
                
                # 验证集标注
                note = "[Validation]" if param in verify_averages else ""
                
                f.write(f"{param_str}    {avg_str}    {note}\n")
        
        logging.info(f"平均值结果已保存到：{result_path}（含验证数据标注）")
        
         # 分析模式控制
        analyse_mode = cfg.get("analyse_model", 2)
        if analyse_mode == 0:
            logging.info("分析模式0: 跳过所有分析步骤")
        else:
            coeffs, target_param = analyze_averages(
                averages, 
                verify_averages,
                cfg["colors"], 
                cfg.get("verify_color", "#d62728"),
                cfg["expected_pressure"],
                output_dir,
                analyse_mode
            )

            # 根据模式输出结果
            if analyse_mode == 2:
                logging.info("===== 最终分析结果 =====")
                logging.info(f"线性拟合方程: y = {coeffs[0]:.4f}x + {coeffs[1]:.4f}")
                logging.info(f"目标压力值: {cfg['expected_pressure']}")
                logging.info(f"预测参数值: {target_param:.4f}")
            elif analyse_mode == 1:
                logging.info("===== 基础分析完成 =====")
        
    except Exception as e:
        logging.error("\n!!!!! 程序执行出错 !!!!!", exc_info=True)
        logging.error("故障排除建议：")
        logging.error("1. 检查 config.py 中的 data_path 是否存在")
        logging.error("2. 确认每个文件夹包含 total-pressure.dat 文件")
        logging.error("3. 验证文件夹名称均为数值格式（如 1.0001）")
        logging.error("4. 确保至少有两个有效数据文件夹")
    finally:
        logging.info("===== 程序执行结束 =====")

if __name__ == "__main__":
    main()