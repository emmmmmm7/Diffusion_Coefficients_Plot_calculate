import csv
import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress

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
        print(f"温度转换错误: {temp_str} -> {e}")
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
                print(f"扩散系数转换错误: {D_str} -> {e}")
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
    # 读取 CSV 文件数据
    raw_data = read_diffusion_csv(csv_file)
    if not raw_data:
        print("未读取到数据！")
        return

    temperatures_used = []
    avg_lnD = []
    err_lnD = []

    # 对每个温度组，过滤掉非正值，并计算 ln(D) 的均值和标准误
    for T in sorted(raw_data.keys()):
        values = np.array(raw_data[T])
        # 过滤掉非正值（<= 0）的扩散系数
        positive_values = values[values > 0]
        if len(positive_values) == 0:
            print(f"温度 {T} 下无正的扩散系数数据，跳过。")
            continue
        # 对正值取自然对数
        ln_values = np.log(positive_values)
        mean_ln = np.mean(ln_values)
        std_ln = np.std(ln_values, ddof=1) if len(ln_values) > 1 else 0.0
        se_ln = std_ln / np.sqrt(len(ln_values))
        temperatures_used.append(1/T)
        avg_lnD.append(mean_ln)
        err_lnD.append(se_ln)

    # 如果没有温度组留下数据，则退出
    if len(temperatures_used) == 0:
        print("所有温度组均无正的扩散系数数据，无法绘图。")
        return

    temperatures_used = np.array(temperatures_used)
    avg_lnD = np.array(avg_lnD)
    err_lnD = np.array(err_lnD)

    # 绘制图形
    plt.figure(figsize=(10, 6))
    ax = plt.gca()  # <--- 新增关键代码：获取坐标轴对象

    # 设置全局字体
    plt.rcParams.update({
        'font.family': 'serif',
        'font.serif': ['Times New Roman'],
        'mathtext.fontset': 'stix'  # 数学符号风格
    })

    # # 使用 errorbar 绘制数据点及误差条，fmt='s-' 表示用方形标记并连接折线
    # plt.errorbar(temperatures_used, avg_lnD, yerr=err_lnD, fmt='s-', markersize=8, capsize=5, label='Data Points')
    # 数据点绘制（修改标记样式和颜色）
    plt.errorbar(temperatures_used, avg_lnD, yerr=err_lnD, 
                fmt='o', markersize=8, markerfacecolor='white',  # 空心圆点
                markeredgewidth=1.5, capsize=5, 
                ecolor='dimgrey', elinewidth=1.2,  # 灰色误差线
                color='steelblue', label='Experimental Data')  # 主色
    
    # 在每个数据点上显示误差值（标准误），使用科学计数法格式
    for x, y, err in zip(temperatures_used, avg_lnD, err_lnD):
        plt.text(x, y + err, f'{err:.2e}', ha='center', va='bottom', fontsize=8)

    # 对平均 ln(D) 数据进行线性回归拟合
    regression_result = linregress(temperatures_used, avg_lnD)
    slope, intercept, r_value, p_value, std_err = regression_result
    # 生成拟合线数据
    fit_line = intercept + slope * temperatures_used

    # plt.plot(temperatures_used, fit_line, 'r--', label=f'Fit: y={slope:.2e}x+{intercept:.2e}\n$R^2$={r_value**2:.4f}')

    # 误差值标注（转换为×10格式）
    for x, y, err in zip(temperatures_used, avg_lnD, err_lnD):
        # err_str = "{:.1f}×10$^{{{}}}$".format(err / 10**np.floor(np.log10(err)), 
        #                 int(np.floor(np.log10(err))))
        # plt.text(x, y + err, err_str, 
        #         ha='center', va='bottom', 
        #         fontsize=9, color='dimgrey')
        if err > 0:
            err_str = "{:.1f}×10$^{{{}}}$".format(err / 10**np.floor(np.log10(err)), 
            int(np.floor(np.log10(err))))
            plt.text(x, y + err, err_str, 
                ha='center', va='bottom', 
                fontsize=9, color='dimgrey')
        else:
            # 对于零或负的误差，显示一个默认值或直接跳过
            plt.text(x, y + err, "N/A", ha='center', va='bottom', fontsize=9, color='dimgrey')
    print(f"拟合结果：slope={slope:.2e}, intercept={intercept:.2e}, R²={r_value**2:.4f}")
    # 拟合线标签（LaTeX渲染）
    fit_label = (
        r'$\ln(D) = {:.2f} \cdot \frac{{1}}{{T}} + {:.2f}$' # 数学公式
        '\n'  # 换行
        r'$R^2 = {:.3f}$'  # 上标
    ).format(slope, intercept, r_value**2)

    from matplotlib.ticker import ScalarFormatter
    ax.xaxis.set_major_formatter(ScalarFormatter(useMathText=True))
    ax.ticklabel_format(axis='x', style='sci', scilimits=(-3,3))

    plt.plot(temperatures_used, fit_line, 
            color='crimson', linestyle='--', linewidth=1.8,
            label=fit_label)
    
    # plt.xlabel('Temperature (K)')
    # 新标签（使用LaTeX格式）
    plt.xlabel(r'$1/T\ (\mathrm{K^{-1}})$', fontsize=12)
    plt.ylabel('ln(D) (ln(m²/s))')
    plt.title('Diffusion Coefficient vs Temperature (ln scale)')
    plt.legend(loc='best')
    plt.grid(True)
    plt.gca().tick_params(direction='in')
    plt.tight_layout()

    # 确保保存目录存在
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=300)
    print(f"Diffusion Coefficient plot saved to: {save_path}")
    plt.close()

    # 计算 D0 = exp(intercept) 并保存拟合结果到文本文件
    D0 = np.exp(intercept)
    fitting_results_file = os.path.join(os.path.dirname(save_path), "fitting_results.txt")
    with open(fitting_results_file, "w") as f:
        f.write("Fitting Results:\n")
        f.write(f"Fitted line: ln(D) = {slope:.2e} * (1/T) + {intercept:.2e}\n")
        f.write(f"R² = {r_value**2:.4f}\n")
        f.write(f"D0 = exp({intercept:.2e}) = {D0:.2e} m²/s\n")
    print(f"Fitting results saved to: {fitting_results_file}")

if __name__ == '__main__':
    # 示例用法（根据实际路径修改）
    csv_file = "output/diffusion_coefficients.csv"  # CSV 文件路径
    save_path = os.path.join("output", "diffusion_coefficient_vs_temperature.png")
    plot_diffusion_coefficients(csv_file, save_path)
