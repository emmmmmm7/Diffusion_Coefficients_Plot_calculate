import json
import os

# 路径配置单独在 config.py 中管理
def get_data_folder():
    """
    获取数据文件夹路径
    :return: 数据文件夹路径
    """
    return "/Users/rrw/Documents/postgraduate/矿物年代学/扩散系数模拟相关/模拟结果/SnO2_Ti_qudai_2025.3.11"  # 根据实际情况调整路径

def get_output_file():
    """
    获取输出文件路径
    :return: 输出文件路径
    """
    return os.path.join(get_data_folder(), "output/diffusion_coefficients.csv")

CONFIG_FILE_PATH = os.path.join(get_data_folder(),"config.json")  # 配置文件路径

#   # 根据实际情况调整路径

def load_config():
    if os.path.exists(CONFIG_FILE_PATH):
        with open(CONFIG_FILE_PATH, 'r') as f:
            config_data = json.load(f)
    else:
        print("未找到 config.json，动态生成默认配置...")
        data_folder = get_data_folder()
        
        # 动态获取温度组（排除output目录）
        temperature_groups = [
            subdir for subdir in os.listdir(data_folder)
            if os.path.isdir(os.path.join(data_folder, subdir)) 
            and subdir.lower() != "output"
        ]
        
        # 构建默认的fit_ranges（每个温度组默认20000-30000）
        fit_ranges = {
            temp: {"fit_start": 20, "fit_end": 30}
            for temp in temperature_groups
        }
        
        # 完整的默认配置结构
        config_data = {
            "ENABLE_FITTING": 1,
            "target_keyword": "ti",
            "output_dir": "/path/to/output",
            "colors": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", 
                      "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
                      "#bcbd22", "#17becf"],  # 新增颜色配置
            "fit_ranges": fit_ranges,
            "start_time_ps": 20,
            "end_time_ps": 30,
            "data_smooth_method": 0,  # 新增平滑方法配置
            "smooth_params": {
                "window_size": 21,
                "poly_order": 3,
                "cutoff": 0.1,
                "fs": 10,
                "order": 5
                } # 新增平滑参数配置
        }
        
        with open(CONFIG_FILE_PATH, 'w') as f:
            json.dump(config_data, f, indent=4)
    return config_data