import json
import os

# 路径配置单独在 config.py 中管理
def get_data_folder():
    """
    获取数据文件夹路径
    :return: 数据文件夹路径
    """
    return "/Users/rrw/Documents/postgraduate/矿物年代学/扩散系数模拟相关/模拟结果/间隙位/Pb/100ps/4-PbO-2"  # 根据实际情况调整路径

def get_output_file():
    """
    获取输出文件路径
    :return: 输出文件路径
    """
    return os.path.join(get_data_folder(), "output/diffusion_coefficients.csv")

# # 默认配置（路径配置移除，其他参数保留）
# DEFAULT_CONFIG = {
#     "ENABLE_FITTING": 1,  # 1: 启用拟合
#     "fit_start": 20000,  # 拟合起始时间
#     "fit_end": 30000,    # 拟合结束时间
#     "target_keyword": "ti",  # 默认目标关键字
# }

CONFIG_FILE_PATH = os.path.join(get_data_folder(),"config.json")  # 配置文件路径

# def load_config():
#     """
#     加载 config.json 文件，如果不存在，则使用默认配置并生成 config.json。
#     :return: 配置字典
#     """
#     if os.path.exists(CONFIG_FILE_PATH):
#         # 如果 config.json 存在，则加载配置
#         with open(CONFIG_FILE_PATH, 'r') as f:
#             config_data = json.load(f)
#     else:
#         # 如果 config.json 不存在，则使用默认配置并写入文件
#         print("未找到 config.json，使用默认配置生成 config.json")
#         config_data = DEFAULT_CONFIG
#         with open(CONFIG_FILE_PATH, 'w') as f:
#             json.dump(config_data, f, indent=4)
#         print(f"默认配置已保存至 {CONFIG_FILE_PATH}")

#     return config_data

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
            "fit_ranges": fit_ranges,
            "start_time_ps": 20,  # 新增：读取起始时间（皮秒）
            "end_time_ps": 30     # 新增：读取结束时间（皮秒）
        }
        
        with open(CONFIG_FILE_PATH, 'w') as f:
            json.dump(config_data, f, indent=4)
    return config_data