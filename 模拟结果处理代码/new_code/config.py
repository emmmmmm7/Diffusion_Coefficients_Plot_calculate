# config.py
"""
统一配置文件
包含扩散系数分析和压力分析两种模式的配置参数
"""
import os
import json
import re
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self):
        logger.info("初始化配置管理器...")
        self.data_folder = "/Users/rrw/Documents/postgraduate/MineralogicalGeochronology/DiffusionCoefficient/SnO2/SnO2数据整合"
        self.output_dir = os.path.join(self.data_folder, "output")
        self.config_path = os.path.join(self.data_folder, "config.json")
        self.root_folder= self._load_root_folders()
        self.config = self._load_config()
        logger.info("配置管理器初始化完成")
        # 基础配置
    
    def default_config(self):
        """
        默认配置
        :return: 默认配置字典
        """

        diffusion_mode = "pressure"  # 默认值
        # pressure_pattern = r"\d+-(\d+\.\d+)"
        pressure_pattern = r"\d+-\w+-\d+"

        return {
            "processing_mode": "diffusion",  # diffusion/pressure
            "log_level": "INFO",
            "output_dir": "output",
            "color_palette": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"],
            
            # 扩散系数模式配置
            "diffusion": {
                "enable_fitting": True,
                "target_element": "Ti",
                "fit_ranges": self._auto_detect_fit_ranges(diffusion_mode, pressure_pattern),
                "start_time_ps": 20,
                "end_time_ps": 30,
                "data_smooth_method": 0,  # 新增平滑方法配置
                "smooth_params": {
                    "window_size": 21,
                    "poly_order": 3,
                    "cutoff": 0.1,
                    "fs": 10,
                    "order": 5
                    } ,
                "diffusion_mode": "temperature",  # 新增模式开关：temperature/pressure
                "diffusion_direction": "4", # 扩散方向，1-x, 2-y, 3-z, 4-total
                "just_plotDC": "False",  # 仅绘制扩散系数曲线
                "temperature_mode": "multiedition",  # 温度模式：multiedition/constant
                "fixed_temperature": 700,        # 压力模式下的固定温度（K）
                "pressure_pattern": r"\d+-(\d+\.\d+)",  # 压力值提取正则
            },
            
            # 压力分析模式配置
            "pressure": {
                "ignore_dirs": [],
                "verify_dirs": [],
                "expected_pressure": 0.5,
                "all_time": 1,
                "start_time_ps": 0,
                "end_time_ps": 3,
                "plot_model": 1,
                "analyse_model": 3
            },

            # ERR模式配置
            "err_plot": {
                "enabled": True,
                "err_filename": "ERR.csv"
            },

            # MSD模式配置
            "MSD_plot": {
                "target_element": "all",  # 计算所有元素的MSD，或指定元素符号如 "Ti"
                "step_interval_fs": 1.0   # 时间步长，单位为飞秒(fs)
            }
        }

    def _load_root_folders(self):
        """
        加载文件夹配置
        :return: 文件夹各文件信息
        """
        ignore_dirs = {"output", "INCAR"}  # 忽略这些文件夹
        return [
            os.path.join(self.data_folder, subdir)
            for subdir in os.listdir(self.data_folder)
            if os.path.isdir(os.path.join(self.data_folder, subdir)) and subdir not in ignore_dirs
        ]
        
    def _load_config(self):
        """
        加载配置文件
        :return: 配置字典
        """
        config_file_path = os.path.join(self.data_folder, "config.json")
        if os.path.exists(config_file_path):
            with open(config_file_path, 'r') as f:
                return json.load(f)
        else:
            logger.info("未找到 config.json，动态生成默认配置...")
            return self._generate_default_config(config_file_path)
    
    def _generate_default_config(self, config_file_path):
        with open(config_file_path, 'w') as f:
            json.dump(self.default_config(), f, indent=4)
        return self.default_config()

    def _auto_detect_fit_ranges(self, diffusion_mode="temperature", pressure_pattern=None):
        """
        根据模式自动生成拟合范围
        :return: 拟合范围字典
        """
        dirs = [os.path.basename(folder) for folder in self.root_folder] 
        if diffusion_mode == "pressure":
            return {d: (20, 30) for d in dirs if re.match(pressure_pattern, d)}
        else:
            return {d: (20, 30) for d in dirs if d != "output"}
    
    @property
    def current_mode(self):
        return self.config["processing_mode"]
    
    def get_config(self):
        """
        获取指定处理模式的配置
        :param mode: 处理模式（diffusion/pressure）
        :return: 配置字典
        """
        return self.config
    
    def reload_config(self):
        """强制重新加载配置文件"""
        with open(self.config_path, 'r') as f:
            self.config = json.load(f)
    
config_manager = ConfigManager()