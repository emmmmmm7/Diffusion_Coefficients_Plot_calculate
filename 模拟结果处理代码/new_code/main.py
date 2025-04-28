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
        
        # 初始化中文日志
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=[
                logging.FileHandler(os.path.join(self.paths["output_dir"], "运行日志.log")), 
                logging.StreamHandler()
            ]
        )
        logging.info("初始化数据处理管道...")
    
    def process_temperature_group(self, temp_dir):
        """"处理单个温度组"""
        temp = os.path.basename(temp_dir)
        logging.info(f"正在处理温度组: {temp}")
        
        # 获取配置参数
        fit_range = self.config['fit_ranges'].get(temp, (20, 30))
        data_dict = {}  # 当前温度组数据 {sample_id: (time, msd)}
        fit_params = {} if self.config['enable_fitting'] else None

        # 遍历数据文件
        for fname in os.listdir(temp_dir):
            if not fname.endswith(".dat"):
                continue
            
            file_path = os.path.join(temp_dir, fname)
            # 数据读取与处理
            time, msd = DataProcessor.load_msd_data(
                file_path,
                self.config['time_range']
            )
            if time is None or msd is None:
                continue
            
            # 存储原始数据
            sample_id = f"{temp}_{fname.split('.')[0]}"
            data_dict[sample_id] = (time, msd)
            
            # 计算扩散系数
            if self.config['enable_fitting']:
                result = DataProcessor.calculate_diffusion(time, msd, fit_range)
                if result:
                    self.results[sample_id] = {
                        "temp": temp,
                        "D": result["D"],
                        "r_squared": result["r_squared"],
                        "fit_range": fit_range
                    }
                    fit_params[sample_id] = (result["slope"], result["intercept"])

        # 为当前温度组生成图表
        if data_dict:
            Visualizer.plot_temperature_msd(
                data_dict, 
                fit_params,
                self.paths["output_dir"],
                temperature=temp,
                fit_range=fit_range
            )
        else:
            logging.warning(f"温度组 {temp} 无有效数据")
    
    def _generate_plots(self):

        Visualizer.init_chinese_font()  # 初始化中文字体
        
        """生成所有可视化图表"""
        if not self.results:
            logging.warning("无有效数据可供绘图")
            return
            
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
            
            # 绘制MSD曲线示例
            sample_data = next(iter(self.results.values()))
            Visualizer.plot_msd(ax1, sample_data['time'], sample_data['msd'])
            ax1.set_title("MSD曲线示例")
            
            # 绘制阿伦尼乌斯图
            temps = [float(d['temp'].split('-')[0]) for d in self.results.values()]  # 适配温度格式
            D_values = [d['D'] for d in self.results.values()]
            Visualizer.plot_arrhenius(ax2, temps, D_values)
            ax2.set_title("阿伦尼乌斯曲线")
            
            plt.savefig(self.paths["plot_output"], dpi=300, bbox_inches='tight')
            plt.close()
            logging.info("可视化图表已生成")
        except Exception as e:
            logging.error(f"图表生成失败: {str(e)}")

if __name__ == "__main__":
    try:
        pipeline = DiffusionPipeline()
        pipeline.run()
        
        # 配置热重载监控
        logging.info("进入配置文件监控模式 (Ctrl+C退出)...")
        while True:
            time.sleep(10)
            current_mtime = os.path.getmtime(get_paths()["config"])
            if current_mtime > pipeline.config['_last_modified']:
                logging.info("检测到配置文件变更，重新加载配置...")
                pipeline = DiffusionPipeline()
                pipeline.run()
                
    except KeyboardInterrupt:
        logging.info("用户中断程序执行")
    except Exception as e:
        logging.error(f"程序运行异常: {str(e)}")