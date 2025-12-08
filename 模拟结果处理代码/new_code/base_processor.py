# base_processor.py
"""
处理器基类
包含配置读取、数据加载、绘图和保存的通用功能
"""
import os
import logging
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from scipy.stats import linregress
import csv
from matplotlib.ticker import ScalarFormatter

class BaseProcessor:
    def __init__(self, config_manager):
        """
        初始化基类
        :param config_manager: 配置管理器实例
        """
        self.config = config_manager
        self.results = {}
        self.data_dict = {}
        self._load_config_section()  # 加载具体配置段

    def _load_config_section(self):
        """
        加载子类对应的配置段（需子类实现）
        """
        raise NotImplementedError("子类必须实现 _load_config_section 方法")

    def _get_dataset_name(self, folder_name):
        """
        获取数据集名称（需子类实现）
        """
        raise NotImplementedError("子类必须实现 _get_dataset_name 方法")

    def _read_data_file(self, file_path):
        """
        读取单个数据文件（需子类实现）
        :return: (x_data, y_data) 或 None
        """
        raise NotImplementedError("子类必须实现 _read_data_file 方法")

    def _process_single_file(self, file_path, data_name, *args):
        """
        处理单个文件（需子类实现）
        """
        raise NotImplementedError("子类必须实现 _process_single_file 方法")

    def _plot_data(self, save_path, data_name, *args):
        """
        绘制数据图表（需子类实现）
        """
        raise NotImplementedError("子类必须实现 _plot_data 方法")

    def _save_results(self, output_file):
        """
        保存结果到文件（需子类实现）
        """
        raise NotImplementedError("子类必须实现 _save_results 方法")

    def _get_all_data_files(self, folder_path):
        """
        获取文件夹下所有数据文件路径
        :return: 文件路径列表
        """
        return [
            os.path.join(folder_path, f)
            for f in os.listdir(folder_path)
            if f.endswith(".dat")
        ]

    def _safe_read_file(self, file_path, read_function, *args, **kwargs):
        """
        安全读取文件，处理异常
        """
        try:
            return read_function(file_path, *args, **kwargs)
        except FileNotFoundError:
            logging.info(f"文件未找到: {file_path}")
        except Exception as e:
            logging.error(f"读取文件 {file_path} 时出错: {e}")
        return None

    def _setup_plot_style(self):
        """
        配置全局绘图样式
        """
        plt.rcParams.update({
            'font.family': 'serif',
            'font.serif': ['Times New Roman'],
            'mathtext.fontset': 'stix',
            'axes.labelsize': 12,
            'xtick.labelsize': 10,
            'ytick.labelsize': 10
        })

    def _save_figure(self, save_path, dpi=300):
        """
        保存图表到文件
        """
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=dpi, bbox_inches='tight')
        plt.close()
        logging.info(f"图像已保存: {save_path}")

    def run(self):
        """
        执行处理流程
        """
        logging.info(f"发现 {len(self.config.root_folder)} 个数据组")
        for folder in self.config.root_folder:
            data_name = self._get_dataset_name(folder)
            logging.info(f"开始处理数据组: {data_name}")
            try:
                self._process_folder(folder, data_name)
            except Exception as e:
                logging.error(f"处理失败: {str(e)}", exc_info=True)
        self._save_results(os.path.join(self.config.output_dir, "results.csv"))