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
def process_data_files(root_dir, colors, output_dir, ignore_dirs):
    """处理所有文件夹中的数据文件"""
    averages = {}
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
        if prefix in ignore_dirs:
            logging.info(f"忽略文件夹 '{folder_name}'（配置排除）")
            continue
        
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
            # 读取数据
            data = np.loadtxt(data_file)
            if data.size == 0:
                logging.warning(f"跳过文件夹 {folder_name}：数据文件为空")
                continue
                
            avg = np.mean(data)
            averages[param_part] = avg
            
            # 绘制时序图
            base_color = next(color_cycle)
            data_color, _ = generate_contrast_color(base_color)
            
            plt.figure(figsize=(10, 6))
            plt.plot(data, color=data_color, alpha=0.6)
            plt.title(f"Pressure Data - {folder_name}")
            plt.xlabel("Data Index")
            plt.ylabel("Pressure")

            # 添加刻度线设置和范围设置
            ax = plt.gca()
            ax.xaxis.set_major_locator(MaxNLocator(5, integer=True))
            ax.tick_params(direction='in', which='both', top=False, right=False)
            plt.xlim(0, len(data)-1)  # 根据数据长度设置x轴范围

            
            plot_path = os.path.join(timeseries_dir, f"{folder_name}_plot.png")
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()
            logging.info(f"时序图已保存到：{plot_path}")
            
        except Exception as e:
            logging.error(f"处理文件夹 {folder_name} 时出错：{str(e)}", exc_info=True)
    
    return averages

# 平均值分析和拟合函数
def analyze_averages(averages, colors, expected_pressure, output_dir):
    """分析平均值并进行曲线拟合"""
    # 数据验证
    if not averages:
        raise ValueError("未找到有效的平均值数据")
    
    logging.info("\n有效参数-平均值数据：")
    for k, v in averages.items():
        logging.info(f"参数: {k.ljust(10)} → 平均值: {v:.4f}")
    
    # 参数转换
    params = []
    valid_keys = []
    for key in averages.keys():
        try:
            param = float(key.split("-")[-1])  # 提取参数值
            params.append(param)
            valid_keys.append(key)
        except ValueError:
            logging.warning(f"跳过无效参数文件夹 '{key}'")
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
    ax = plt.gca()
    base_color = colors[0]
    data_color, fit_color = generate_contrast_color(base_color)
    
    # 刻度设置
    ax.tick_params(direction='in', which='both', top=False, right=False)
    ax.xaxis.set_major_formatter(ScalarFormatter(useOffset=False, useMathText=True))
    ax.yaxis.set_major_formatter(ScalarFormatter(useOffset=False, useMathText=True))
    
    # 绘制散点图
    ax.scatter(x, y, color=data_color, s=80, edgecolor='w', linewidth=1, zorder=3, label="Average Values")

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
            label=f"Fit: y = {coeffs[0]:.4f}x + {coeffs[1]:.4f}")

    # 目标线设置
    ax.axhline(expected_pressure, color='#2c3e50', linestyle='-.', 
              linewidth=1.5, alpha=0.7, zorder=1,
              label=f'Target Pressure: {expected_pressure}')
    ax.axvline(target_param, color='#2c3e50', linestyle='-.',
              linewidth=1.5, alpha=0.7, zorder=1,
              label=f'Predicted Parameter: {target_param:.4f}')

    # 坐标轴设置
    ax.set_xlabel("Parameter Value", fontsize=13, labelpad=8)
    ax.set_ylabel("Average Pressure", fontsize=13, labelpad=8)
    
    # 刻度优化
    ax.xaxis.set_major_locator(MaxNLocator(prune=None, steps=[1, 2, 5], nbins=8))
    ax.yaxis.set_major_locator(MaxNLocator(prune=None, steps=[1, 2, 5], nbins=8))
    
    # 网格线设置
    ax.grid(True, which='major', linestyle='--', linewidth=0.5, alpha=0.5)
    
    # 图例美化
    legend = ax.legend(loc='best', frameon=True, framealpha=0.95,
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
        
        # 处理数据文件
        averages = process_data_files(
            cfg["data_path"], 
            cfg["colors"], 
            output_dir,
            cfg.get("ignore_dirs", [])
        )
        logging.info(f"成功处理 {len(averages)} 个有效数据文件")
        
        # 保存结果到output目录
        result_path = os.path.join(output_dir, "average_pressures.txt")
        with open(result_path, "w") as f:
            for param in sorted(averages.keys(), key=lambda x: float(x.split("-")[-1])):
                f.write(f"{param}\t{averages[param]:.4f}\n")
        logging.info(f"平均值结果已保存到：{result_path}")
        
        # 分析数据
        coeffs, target_param = analyze_averages(
            averages, 
            cfg["colors"], 
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