# utils.py
import csv
import os

def save_diffusion_results(results, output_file, append=False):
    """
    以 CSV 格式保存扩散系数计算结果
    :param results: { 文件名: (D, R²) } 字典
    :param output_file: CSV 文件路径
    :param append: 是否追加到现有文件
    """
    output_dir = os.path.dirname(output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    mode = 'a' if append else 'w'
    with open(output_file, mode, newline='') as f:
        writer = csv.writer(f)
        if not append or os.stat(output_file).st_size == 0:
            writer.writerow(["File Name", "Diffusion Coefficient (m²/s)", "R²"])  # CSV 头部
        for file, (D, r_squared) in results.items():
            writer.writerow([file, f"{D:.6e}", f"{r_squared:.4f}"])

    print(f"扩散系数已保存至: {output_file}")
