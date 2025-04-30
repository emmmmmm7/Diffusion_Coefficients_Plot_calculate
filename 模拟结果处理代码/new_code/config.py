# config.py
"""
统一配置文件
包含扩散系数分析和压力分析两种模式的配置参数
"""
import os
import json

class ConfigManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """加载基础配置并动态生成必要参数"""
        self.data_root = os.path.expanduser(
            "/Users/rrw/Documents/postgraduate/矿物年代学/扩散系数模拟相关/Ti_qudai_File/nVT方案/3-Ptest-2025.4.24"
        )
        self.output_dir = os.path.join(self.data_root, "output")
        
        # 基础配置
        self.config = {
            "processing_mode": "diffusion",  # diffusion/pressure
            "log_level": "INFO",
            
            # 扩散系数模式配置
            "diffusion": {
                "enable_fitting": True,
                "target_element": "Ti",
                "color_palette": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"],
                "fit_ranges": self._auto_detect_fit_ranges(),
                "time_range": (20, 30),
                "smoothing": {
                    "method": "lowpass",
                    "window_size": 21,
                    "cutoff_freq": 0.1
                }
            },
            
            # 压力分析模式配置
            "pressure": {
                "ignore_dirs": [],
                "verify_dirs": [],
                "colors": ["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd"],
                "expected_pressure": 0.5,
                "all_time": 1,
                "start_time_ps": 0,
                "end_time_ps": 3,
                "plot_model": 1,
                "analyse_model": 3
            }
        }
        
    def _auto_detect_fit_ranges(self):
        """自动生成扩散模式的拟合范围"""
        temp_dirs = [d for d in os.listdir(self.data_root) 
                    if os.path.isdir(os.path.join(self.data_root, d))]
        return {temp: (20, 30) for temp in temp_dirs if temp != "output"}
    
    @property
    def current_mode(self):
        return self.config["processing_mode"]
    
    def get_config(self, mode=None):
        mode = mode or self.current_mode
        return {
            "data_root": self.data_root,
            "output_dir": self.output_dir,
            **self.config[mode]
        }

config_manager = ConfigManager()