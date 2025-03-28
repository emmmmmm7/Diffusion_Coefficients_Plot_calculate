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

# 生成对比色函数
def generate_contrast_color(base_hex, light=0.3, dark=0.7):
    """生成同色系对比色对"""
    rgb = mcolors.hex2color(base_hex)
    h, l, s = colorsys.rgb_to_hls(rgb[0], rgb[1], rgb[2])
    data_color = colorsys.hls_to_rgb(h, light, s)
    fit_color = colorsys.hls_to_rgb(h, dark, min(s*1.5, 1.0))
    return (mcolors.to_hex(data_color), mcolors.to_hex(fit_color))

# 数据读取和处理函数
def process_data_files(root_dir, colors, output_dir, ignore_dirs, verify_dirs, start_ps, end_ps):
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
        data_file = os.path.join(folder_path, "total-pressure.dat")
        
        # 文件夹名解析验证
        try:
            param_part = folder_name.split("-")[-1]
            float(param_part)
        except (ValueError, IndexError):
            logging.warning(f"跳过文件夹 '{folder_name}'：命名不符合规范")
            continue

        # 查找数据文件
        result_dir = os.path.join(folder_path, "results")
        if not os.path.exists(result_dir):
            logging.warning(f"跳过文件夹 {folder_name}：未找到 results 文件夹")
            continue

        found_file = None
        for f in os.listdir(result_dir):
            if f.lower() == "total-pressure.dat":
                found_file = f
                break

        if not found_file:
            logging.warning(f"跳过文件夹 {folder_name}：未找到 total-pressure.dat")
            continue

        data_file = os.path.join(result_dir, found_file)
            
        try:
            # 读取单列压力数据
            pressure = np.loadtxt(data_file)
            n_points = len(pressure)
            
            # 生成时间序列（假设每个数据点间隔1fs）
            time_fs = np.arange(n_points)  # 0, 1, 2,... fs
            time_ps = time_fs / 1000  # 转换为ps
            
            # 应用时间截取
            start_fs = int(start_ps * 1000)
            end_fs = int(end_ps * 1000)
            start_idx = max(0, start_fs)
            end_idx = min(n_points-1, end_fs)
            
            # 截取数据段
            pressure = pressure[start_idx:end_idx+1]
            time_ps = time_ps[start_idx:end_idx+1]
            
            if len(pressure) == 0:
                logging.warning(f"跳过文件夹 {folder_name}：时间范围内无数据")
                continue
                
            avg = np.mean(pressure)
            
            # 存储数据时区分验证集
            if is_verify:
                verify_averages[param_part] = avg
            else:
                averages[param_part] = avg
            
            # 绘制时序图
            base_color = next(color_cycle)
            data_color, _ = generate_contrast_color(base_color)
            
            plt.figure(figsize=(10, 6))

            # 设置全局字体
            plt.rcParams.update({
                'font.family': 'serif',
                'font.serif': ['Times New Roman'],
                'mathtext.fontset': 'stix'  # 数学符号风格
            })

            plt.plot(pressure, color=data_color, alpha=0.6)
            plt.title(f"Pressure Data - {folder_name.split('-')[-1]}")
            plt.xlabel("Time (fs)")
            plt.ylabel("Pressure")
            # plt.xlim(start_ps, end_ps)  # 设置精确范围

            # 添加刻度线设置和范围设置
            ax = plt.gca()
            ax.xaxis.set_major_locator(MaxNLocator(5, integer=True))
            ax.tick_params(direction='in', which='both', top=False, right=False)
            plt.xlim(0, len(pressure)-1)  # 根据数据长度设置x轴范围

            
            plot_path = os.path.join(timeseries_dir, f"{folder_name}_plot.png")
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()
            logging.info(f"时序图已保存到：{plot_path}")
            
        except Exception as e:
            logging.error(f"处理文件夹 {folder_name} 时出错：{str(e)}", exc_info=True)
    
    return averages, verify_averages

# 平均值分析和拟合函数
def analyze_averages(averages, verify_averages, colors, verify_color, expected_pressure, output_dir):
    """分析数据并区分验证集"""
    # 合并数据显示但分开处理
    all_data = {**averages, **verify_averages}
    
    logging.info("\n有效参数-平均值数据：")
    for k in sorted(all_data.keys(), key=float):
        source = "(验证集)" if k in verify_averages else ""
        logging.info(f"参数: {k.ljust(10)} → 平均值: {all_data[k]:.4f} {source}")

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
    x_min = min(x_data_min, target_param)
    x_max = max(x_data_max, target_param)

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
    
    # 修改保存路径到output目录
    analysis_path = os.path.join(output_dir, "average_pressure_analysis.png")
    plt.savefig(analysis_path, dpi=300, bbox_inches='tight')
    plt.close()
    logging.info(f"分析图表已保存到：{analysis_path}")
    
    return coeffs, target_param

# 主执行函数
def main():
    setup_logging()
    logging.info("===== 压力数据分析程序启动 =====")
    
    try:
        # 加载配置
        cfg = config.config_data
        logging.info(f"配置文件加载成功\n"
                    f"数据路径: {cfg['data_path']}\n"
                    f"排除前缀: {cfg.get('ignore_dirs', [])}\n"
                    f"预期压力: {cfg['expected_pressure']}")
        
        # 创建输出目录（在600K目录下）
        output_dir = os.path.join(cfg["data_path"], "output")
        os.makedirs(output_dir, exist_ok=True)
        logging.info(f"输出目录已创建：{output_dir}")
        
        # 获取时间参数（带默认值）
        start_ps = cfg.get("start_time_ps", 0)
        end_ps = cfg.get("end_time_ps", 100)
        
        # 处理数据文件时传入时间参数
        averages, verify_averages = process_data_files(
            cfg["data_path"], 
            cfg["colors"], 
            output_dir,
            cfg.get("ignore_dirs", []),
            cfg.get("verify_dirs", []),
            start_ps,
            end_ps
        )
        logging.info(f"成功处理 {len(averages)} 个有效数据文件")
        
        # 保存结果到output目录（修改后）
        result_path = os.path.join(output_dir, "average_pressures.txt")
        with open(result_path, "w") as f:
            # 合并数据并排序
            all_data = {**averages, **verify_averages}
            sorted_params = sorted(all_data.keys(), key=lambda x: float(x))
            
            for param in sorted_params:
                # 判断是否为验证数据
                is_verify = param in verify_averages
                note = "(验证集)" if is_verify else ""
                f.write(f"{param}\t{all_data[param]:.4f}\t{note}\n")
        
        logging.info(f"平均值结果已保存到：{result_path}（含验证数据标注）")
        
        # 分析数据
        coeffs, target_param = analyze_averages(
                                            averages, 
                                            verify_averages,
                                            cfg["colors"], 
                                            cfg.get("verify_color", "#d62728"),
                                            cfg["expected_pressure"],
                                            output_dir
                                        )
        
        # 输出结果
        logging.info("\n===== 最终分析结果 =====")
        logging.info(f"线性拟合方程: y = {coeffs[0]:.4f}x + {coeffs[1]:.4f}")
        logging.info(f"目标压力值: {cfg['expected_pressure']}")
        logging.info(f"预测参数值: {target_param:.4f}")
        
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