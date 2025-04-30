# pressure_processor.py
"""
压力/温度分析模块
处理压力/温度数据并生成分析图表
"""
import os
import logging
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams

class PressureProcessor:
    def __init__(self, config):
        self.config = config
        # 初始化中文字体
        rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
        rcParams['axes.unicode_minus'] = False

    def _process_file(self, file_path):
        """处理单个数据文件"""
        try:
            data = np.loadtxt(file_path)
            time_ps = np.arange(len(data)) / 1000
            return time_ps, data
        except Exception as e:
            logging.error(f"处理文件失败 {file_path}: {str(e)}")
            return None, None

    def _generate_timeseries_plot(self, folder_name, time_ps, data):
        """生成时间序列图"""
        plt.figure(figsize=(10, 6))
        plt.plot(time_ps, data, alpha=0.6)
        plt.title(folder_name)
        plt.xlabel("时间 (ps)")
        plt.ylabel("压力" if self.config["plot_model"] == 1 else "温度 (K)")
        plot_path = os.path.join(self.config["output_dir"], "timeseries", f"{folder_name}.png")
        os.makedirs(os.path.dirname(plot_path), exist_ok=True)
        plt.savefig(plot_path)
        plt.close()

    def run(self):
        """执行处理流程"""
        os.makedirs(self.config["output_dir"], exist_ok=True)
        averages = {}
        
        for folder in os.listdir(self.config["data_root"]):
            dir_path = os.path.join(self.config["data_root"], folder)
            if not os.path.isdir(dir_path) or folder == "output":
                continue
                
            file_path = os.path.join(dir_path, 
                "total-pressure.dat" if self.config["plot_model"] == 1 else "T-E.dat"
            )
            
            time_ps, data = self._process_file(file_path)
            if data is None:
                continue
                
            avg = np.mean(data)
            averages[folder] = avg
            self._generate_timeseries_plot(folder, time_ps, data)

        # 生成平均压力分析图
        if averages:
            params = sorted(averages.keys(), key=lambda x: float(x.split('-')[-1]))
            values = [averages[p] for p in params]
            
            plt.figure(figsize=(12, 6))
            plt.scatter(params, values)
            plt.title("平均压力分析")
            plt.xlabel("参数")
            plt.ylabel("平均压力")
            plt.savefig(os.path.join(self.config["output_dir"], "pressure_analysis.png"))
            plt.close()
            
            logging.info(f"处理完成，共分析 {len(averages)} 个样本")