import csv
import logging
import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress
from matplotlib.ticker import ScalarFormatter

def parse_temperature(temp_str):
    """
    将温度字符串（例如 "600K" 或 "600"）转换为数值。
    """
    try:
        temp_str = temp_str.strip()
        if temp_str.lower().endswith("k"):
            return float(temp_str[:-1])
        else:
            return float(temp_str)
    except Exception as e:
        logging.error(f"温度转换错误: {temp_str} -> {e}")
        return None

def read_diffusion_csv(csv_file):
    """
    读取 CSV 文件，返回按温度分组的扩散系数列表。
    CSV 文件须包含列 "Temperature" 和 "Diffusion Coefficient (m²/s)"。
    
    返回：
        data: dict, 格式 { temperature_value: [D1, D2, ...] }
    """
    data = {}
    with open(csv_file, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            temp_str = row["Temperature"].strip()
            D_str = row["Diffusion Coefficient (m²/s)"].strip()
            T = parse_temperature(temp_str)
            if T is None:
                continue
            try:
                D = float(D_str)
            except Exception as e:
                logging.error(f"扩散系数转换错误: {D_str} -> {e}")
                continue
            if T not in data:
                data[T] = []
            data[T].append(D)
    return data

def plot_diffusion_coefficients(csv_file, save_path):
    """
    从 csv_file 读取扩散系数数据，按温度分组计算 ln(D) 的平均值及标准误，
    仅使用正的扩散系数（大于 0）的数据，
    绘制以温度为 x 轴、ln(D) 为 y 轴的折线图（数据点用方形标记，并标注误差值），
    同时进行线性回归拟合，并将拟合线绘制在图中，
    最后将图保存到 save_path，并将拟合结果写入文本文件保存到 output 文件夹中。
    """
    # ==================== 数据读取与预处理 ==================== 
    raw_data = read_diffusion_csv(csv_file)
    if not raw_data:
        logging.error("未读取到有效数据，请检查 CSV 文件格式")
        return

    # 初始化数据容器
    inverse_temps = []  # x轴: 1/T (K⁻¹)
    lnD_means = []      # y轴: ln(D) 均值

    # 处理每个温度组
    for T in sorted(raw_data.keys(), reverse=True):  # 温度从高到低排序
        D_values = np.array(raw_data[T])
        
        # 过滤非正值
        valid_D = D_values[D_values > 0]
        if len(valid_D) == 0:
            logging.warning(f"温度 {T}K 下无有效扩散系数，已跳过")
            continue
        
        # 计算统计量
        lnD = np.log(valid_D)
        mean_lnD = np.mean(lnD)
        
        inverse_temps.append(1000 / T)  # 转换为 1/T (10³·K⁻¹)
        lnD_means.append(mean_lnD)
        logging.info(f"温度 {T}K: ln(D) = {mean_lnD:.4f}")

    if not inverse_temps:
        logging.error("无有效数据可供绘图")
        return

    # 转换为 numpy array 便于计算
    x = np.array(inverse_temps)
    y = np.array(lnD_means)

    # ==================== 绘图样式配置 ====================
    plt.figure(figsize=(8, 6), dpi=150)
    ax = plt.gca()
    
    # 全局字体设置
    plt.rcParams.update({
        'font.family': 'Times New Roman',
        'mathtext.fontset': 'stix',
        'axes.labelsize': 12,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10
    })

    # 颜色方案
    PRIMARY_COLOR = '#2C5F94'   # 深蓝色
    SECONDARY_COLOR = '#97CC04' # 鲜绿色
    ERROR_COLOR = '#6B6B6B'     # 中性灰

    # ==================== 数据可视化 ====================
    # 主数据点（带误差条）
    ax.errorbar(
        x, y, 
        fmt='o', markersize=4,
        markerfacecolor='white',
        markeredgewidth=1.5,       
        linestyle='',
        color=PRIMARY_COLOR,
        label='Experimental Data'
    )

    # ==================== 线性回归 ====================
    regress = linregress(x, y)
    slope = regress.slope
    intercept = regress.intercept
    r_squared = regress.rvalue**2
    
    # 生成拟合线
    x_fit = np.linspace(x.min(), x.max(), 100)
    y_fit = intercept + slope * x_fit

    # 拟合线绘制
    ax.plot(
        x_fit, y_fit, 
        color=SECONDARY_COLOR, 
        linestyle='--',
        linewidth=2,
        label=(
            r'$\mathregular{\ln(D) = \frac{%.2f}{T}  %+.2f}$' % (slope*1000, intercept) + '\n' + 
            r'$\mathregular{R^2 = %.3f}$' % r_squared
        )
    )

    # ==================== 坐标轴优化 ====================
    # X轴设置
    ax.set_xlabel(
        r'$\mathregular{1000/T\ (K^{-1})}$', 
        fontsize=12, 
        labelpad=8
    )
    ax.xaxis.set_major_formatter(ScalarFormatter(useMathText=True))
    ax.ticklabel_format(axis='x', style='sci', scilimits=(-3,3))
    ax.xaxis.offsetText.set_fontsize(10)

    # Y轴设置
    ax.set_ylabel(
        r'$\mathregular{\ln(D)\ (m^2/s)}$', 
        fontsize=12, 
        labelpad=8
    )
    
    # 网格线
    ax.grid(False)
    
    # 坐标轴刻度朝内
    ax.tick_params(direction='in')
    # ==================== 图例与输出 ====================
    ax.legend(
        loc='best',
        frameon=True,
        framealpha=0.9,
        edgecolor='none',
        fontsize=10
    )

    plt.tight_layout()
    
    # 保存图像
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, bbox_inches='tight', dpi=300)
    plt.close()

    # ==================== 拟合结果输出 ====================
    D0 = np.exp(intercept)
    result_text = f"""Fitting Results:
    - Slope (Ea/R): {slope:.2e} K
    - Intercept (lnD0): {intercept:.2e}
    - R²: {r_squared:.4f}
    - D0: {D0:.2e} m²/s
    """
    
    result_path = os.path.join(os.path.dirname(save_path), "fitting_results.txt")
    with open(result_path, 'w') as f:
        f.write(result_text)
    logging.info(f"拟合结果已保存至 {result_path}")

if __name__ == '__main__':
    # 示例用法（根据实际路径修改）
    csv_file = "output/diffusion_coefficients.csv"  # CSV 文件路径
    save_path = os.path.join("output", "diffusion_coefficient_vs_temperature.png")
    plot_diffusion_coefficients(csv_file, save_path)
