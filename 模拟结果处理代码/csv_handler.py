import csv
import logging

def load_diffusion_results(csv_file):
    """
    从 CSV 文件读取扩散系数数据
    :param csv_file: CSV 文件路径
    :return: { 文件名: (D, R²) } 字典
    """
    results = {}
    try:
        with open(csv_file, "r") as f:
            reader = csv.reader(f)
            next(reader)  # 跳过头部
            for row in reader:
                file_name, D, r_squared = row
                results[file_name] = (float(D), float(r_squared))
    except FileNotFoundError:
        logging.error(f"文件 {csv_file} 未找到")
    except Exception as e:
        logging.error(f"读取 CSV 文件 {csv_file} 时发生错误: {e}")
    
    return results
