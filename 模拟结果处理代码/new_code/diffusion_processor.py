# diffusion_processor.py
"""
扩散系数分析模块
处理MSD数据计算扩散系数并生成相关图表
"""
import os
import logging
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats, signal
from matplotlib import rcParams

class DiffusionProcessor:
    def __init__(self, config):
        self.config = config
        self.results = {}
        
        # 初始化中文字体
        rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
        rcParams['axes.unicode_minus'] = False

    def _load_msd_data(self, file_path):
        """加载MSD数据文件"""
        try:
            time, msd = [], []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('#') or not line.strip():
                        continue
                    parts = line.split()
                    if len(parts) < 5:
                        continue
                    
                    t_fs = float(parts[0])
                    t_ps = t_fs / 1000
                    if self.config["time_range"][0] <= t_ps <= self.config["time_range"][1]:
                        time.append(t_ps)
                        msd.append(float(parts[4]))
            
            if len(time) < 2:
                return None, None
            
            # 归零化处理
            time = np.array(time) - time[0]
            return time, np.array(msd)
        except Exception as e:
            logging.error(f"读取文件失败 {file_path}: {str(e)}")
            return None, None

    def _calculate_diffusion(self, time, msd, fit_range):
        """计算扩散系数"""
        mask = (time >= fit_range[0]) & (time <= fit_range[1])
        if sum(mask) < 2:
            return None
        
        try:
            slope, intercept, r_val = stats.linregress(time[mask], msd[mask])[:3]
            return {
                "D": slope / 6,
                "slope": slope,
                "intercept": intercept,
                "r_squared": r_val**2
            }
        except Exception as e:
            logging.error(f"线性回归失败: {str(e)}")
            return None

    def _plot_temperature_msd(self, temp_dir, data_dict, fit_params):
        """生成温度组MSD图表"""
        temp = os.path.basename(temp_dir)
        plt.figure(figsize=(10, 6))
        
        for sample_id, (time, msd) in data_dict.items():
            color = plt.cm.tab10(np.linspace(0, 1, len(data_dict)))
            plt.plot(time, msd, color=color, alpha=0.4)
            
            if sample_id in fit_params:
                slope, intercept = fit_params[sample_id]
                fit_line = slope * time + intercept
                plt.plot(time, fit_line, '--', color=color)

        plt.title(f"温度组 {temp} MSD曲线")
        plt.xlabel("时间 (ps)")
        plt.ylabel("MSD (Å²)")
        plt.savefig(os.path.join(self.config["output_dir"], f"MSD_{temp}.png"))
        plt.close()

    def process_temperature_group(self, temp_dir):
        """处理单个温度组"""
        temp = os.path.basename(temp_dir)
        data_dict = {}
        fit_params = {}
        fit_range = self.config["fit_ranges"].get(temp, (20, 30))

        for fname in os.listdir(temp_dir):
            if not fname.endswith(".dat"):
                continue
            
            file_path = os.path.join(temp_dir, fname)
            time, msd = self._load_msd_data(file_path)
            if time is None:
                continue
            
            sample_id = f"{temp}_{fname.split('.')[0]}"
            data_dict[sample_id] = (time, msd)
            
            result = self._calculate_diffusion(time, msd, fit_range)
            if result:
                self.results[sample_id] = {
                    "temp": temp,
                    "D": result["D"],
                    "r_squared": result["r_squared"]
                }
                fit_params[sample_id] = (result["slope"], result["intercept"])

        if data_dict:
            self._plot_temperature_msd(temp_dir, data_dict, fit_params)
        return len(data_dict)

    def run(self):
        """执行处理流程"""
        os.makedirs(self.config["output_dir"], exist_ok=True)
        valid_groups = 0
        
        for item in os.listdir(self.config["data_root"]):
            dir_path = os.path.join(self.config["data_root"], item)
            if os.path.isdir(dir_path) and item != "output":
                valid_groups += self.process_temperature_group(dir_path)

        if valid_groups == 0:
            raise ValueError("未找到有效温度组")
            
        # 保存结果
        if self.results:
            output_path = os.path.join(self.config["output_dir"], "扩散系数结果.csv")
            with open(output_path, 'w') as f:
                f.write("样本ID,温度,扩散系数(m²/s),R²\n")
                for sample_id, data in self.results.items():
                    f.write(f"{sample_id},{data['temp']},{data['D']:.3e},{data['r_squared']:.4f}\n")
            logging.info(f"结果已保存至 {output_path}")