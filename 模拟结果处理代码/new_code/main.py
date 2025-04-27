# main.py
"""
主执行模块
包含：
1. 数据处理流程控制
2. 配置热重载
3. 日志管理
"""
import time
import logging
import os
import matplotlib.pyplot as plt
from config import get_paths, load_config
from tools import DataProcessor, Visualizer, FileManager

class DiffusionPipeline:
    """主处理管道"""
    
    def __init__(self):
        self.config = load_config()
        self.paths = get_paths()
        self.results = {}
        
        # 初始化日志
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.FileHandler(os.path.join(self.paths["output_dir"], "process.log")),
                logging.StreamHandler()
            ]
        )
    
    def process_temperature_group(self, temp_dir):
        """处理单个温度组"""
        temp = os.path.basename(temp_dir)
        logging.info(f"Processing {temp}...")
        
        # 获取拟合范围
        fit_range = self.config['fit_ranges'].get(temp, (20, 30))
        
        # 遍历数据文件
        for fname in os.listdir(temp_dir):
            if not fname.endswith(".dat"): continue
            
            # 数据读取与处理
            time, msd = DataProcessor.load_msd_data(
                os.path.join(temp_dir, fname),
                self.config['time_range']
            )
            if time is None: continue
            
            # 计算扩散系数
            result = DataProcessor.calculate_diffusion(time, msd, fit_range)
            if not result: continue
            
            # 存储结果
            sample_id = f"{temp}_{fname.split('.')[0]}"
            self.results[sample_id] = {
                "temp": temp,
                "D": result["D"],
                "r_squared": result["r_squared"],
                "fit_range": fit_range
            }
            
    def run(self):
        """执行完整流程"""
        # 创建输出目录
        os.makedirs(self.paths["output_dir"], exist_ok=True)
        
        # 遍历温度组
        data_root = self.paths["data_root"]
        for item in os.listdir(data_root):
            dir_path = os.path.join(data_root, item)
            if os.path.isdir(dir_path) and item != "output":
                self.process_temperature_group(dir_path)
        
        # 保存结果
        FileManager.save_results(self.results, self.paths["coefficients_csv"])
        
        # 绘制综合图表
        self._generate_plots()
    
    def _generate_plots(self):
        """生成所有可视化图表"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # 绘制MSD曲线示例
        sample_data = next(iter(self.results.values()))
        Visualizer.plot_msd(ax1, sample_data['time'], sample_data['msd'])
        
        # 绘制阿伦尼乌斯图
        temps = [float(d['temp'].strip('K')) for d in self.results.values()]
        D_values = [d['D'] for d in self.results.values()]
        Visualizer.plot_arrhenius(ax2, temps, D_values)
        
        plt.savefig(self.paths["plot_output"], dpi=300, bbox_inches='tight')
        plt.close()

if __name__ == "__main__":
    pipeline = DiffusionPipeline()
    
    try:
        # 初始运行
        pipeline.run()
        
        # 配置热重载监控
        while True:
            time.sleep(10)
            if os.path.getmtime(get_paths()["config"]) > pipeline.config['_last_modified']:
                logging.info("Configuration updated, reloading...")
                pipeline = DiffusionPipeline()
                pipeline.run()
    except KeyboardInterrupt:
        logging.info("Process terminated by user")