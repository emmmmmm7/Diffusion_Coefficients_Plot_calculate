# config.py
"""
配置管理模块
功能：
1. 管理所有路径配置
2. 加载/生成配置文件
3. 提供全局配置访问接口
"""
import os
import json

# 基础路径配置
_DATA_FOLDER = "/Users/rrw/Documents/postgraduate/矿物年代学/扩散系数模拟相关/Ti_qudai_File/nVT方案/3-Ptest-2025.4.24"
_CONFIG_PATH = os.path.join(_DATA_FOLDER, "config.json")
_OUTPUT_DIR = os.path.join(_DATA_FOLDER, "output")

def get_paths():
    """获取所有关键路径"""
    return {
        "data_root": _DATA_FOLDER,
        "config": _CONFIG_PATH,
        "output_dir": _OUTPUT_DIR,
        "coefficients_csv": os.path.join(_OUTPUT_DIR, "扩散系数结果.csv"),
        "plot_output": os.path.join(_OUTPUT_DIR, "扩散系数曲线图.png")
    }

def load_config():
    """
    加载或生成配置文件
    返回包含所有配置参数的字典
    """
    paths = get_paths()
    if os.path.exists(paths["config"]):
        with open(paths["config"], 'r', encoding='utf-8') as f:
            config = json.load(f)
            config['_last_modified'] = os.path.getmtime(paths["config"])  # 记录最后修改时间
            return config
    
    # 生成默认配置
    print("正在生成默认配置文件...")
    default_config = {
        "enable_fitting": True,
        "target_element": "Ti",
        "color_palette": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"],
        "fit_ranges": _auto_detect_fit_ranges(),
        "time_range": (20, 30),  # 单位：皮秒
        "smoothing": {
            "method": "lowpass",  # none/lowpass/moving_avg
            "window_size": 21,
            "cutoff_freq": 0.1
        },
        "_last_modified": 0  # 初始化时间戳
    }
    
    with open(paths["config"], 'w', encoding='utf-8') as f:
        json.dump(default_config, f, indent=4, ensure_ascii=False)
    
    # 增强字体配置
    try:
        import matplotlib.pyplot as plt
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
    except ImportError:
        pass
    
    return default_config

def _auto_detect_fit_ranges():
    """自动检测温度组并生成默认拟合范围"""
    temp_dirs = [d for d in os.listdir(get_paths()["data_root"]) 
                if os.path.isdir(os.path.join(get_paths()["data_root"], d))]
    return {temp: (20, 30) for temp in temp_dirs if temp != "output"}