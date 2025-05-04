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
        self.fit_range = self.config["diffusion"].get("fit_ranges", {})
        self.results = {}

    def _get_dataset_name(self, folder_name):
        """
        获取数据集名称
        :param folder_path: 目录路径
        :return: 数据集名称
        """
        if self.config.current_mode == "pressure":
            return os.path.basename(folder_name).split("-")[1]
        elif self.config.current_mode == "diffusion":
            return os.path.basename(folder_name)
        else:
            raise ValueError("未知的处理模式")
    
    def _get_all_data_files(self, folder_path):
        """
        获取指定文件夹下所有 .dat 文件路径
        :param folder_path: 目录路径
        :return: 文件路径列表
        """
        return [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".dat")]
    
    def _safe_read_file(file_path, read_function, *args, **kwargs):
        try:
            return read_function(file_path, *args, **kwargs)
        except FileNotFoundError:
            logging.info(f"文件未找到: {file_path}")
        except Exception as e:
            logging.error(f"读取文件 {file_path} 时出错: {e}")
        return None
    
    def _read_MSD_data(file_path, start_time_ps=20, end_time_ps=30):
        """
        读取 MSD 数据文件
        :param file_path: .dat 文件路径
        :return: (time, msd) 两个列表
        :param start_time_ps: 起始时间（皮秒）
        :param end_time_ps: 结束时间（皮秒）
        """
        time_original = []  # 存储原始时间
        tot_msd = []

        # 转换为fs进行比较
        start_fs = start_time_ps * 1000
        end_fs = end_time_ps * 1000

        with open(file_path, 'r') as file:
            for line in file:
                if line.startswith('#') or 'Time(fs)' in line:
                    continue
                data = line.split()
                if len(data) < 5:
                    continue  # 跳过不完整的行
                time_fs = float(data[0])
                if start_fs <= time_fs <= end_fs:  # 新增过滤条件
                    time_original.append(time_fs / 1000)  # 转换为皮秒
                    tot_msd.append(float(data[4]))
        # 归零化处理（关键修改点）
        if time_original:
            start_ps = time_original[0]  # 获取实际起始时间
            time = [t - start_ps for t in time_original]  # 归零化
        else:
            time = []
        
        # logging.info(f"时间归零化完成，新范围: [{min(time, default=0):.1f}, {max(time, default=0):.1f}] ps")
        return time, tot_msd
    
    def _process_single_file(self, file_path, data_name, diffusion_results, data_dict, fit_params, rootfolder, fit_start, fit_end, config_data):
        """
        处理单个数据文件，计算扩散系数并保存结果
        :param file_path: 数据文件路径
        :param data_name: 数据集名称
        :param fit_start: 拟合的起始时间
        :param fit_end: 拟合的结束时间
        :param config_data: 配置字典，用于获取配置项
        """
        file_name = os.path.basename(file_path)
        # 使用温度前缀生成唯一键
        unique_key = f"{data_name}_{file_name}"

        result = self._safe_read_file(file_path, self.read_data, self.config["start_time_ps"], config_data["end_time_ps"])

    

    def process_temperature_folder(self, root_folder, data_name, output_dir, diffusion_results, fit_params, config_data):
        """
        处理每个温度组的文件夹
        :param root_folder: 温度组文件夹路径
        :param data_name: 数据集名称
        :param output_dir: 输出目录
        :param diffusion_results: 扩散系数结果字典
        :param fit_params: 拟合参数字典
        :param config_data: 配置数据
        """
        # 读取数据文件，进行扩散系数计算和拟合

        # 这里假设有一个函数 process_data_file 来处理单个数据文件
        # 具体实现根据实际数据格式和需求进行调整
        data_dict = {}
        data_files = self._get_all_data_files(root_folder)
        if not data_files:
            logging.error(f"{root_folder} 文件夹下没有找到 .dat 文件")
            return
        
        # 获取拟合范围
        try:
            fit_range = self.config["diffusion"].get("fit_ranges", {})
            fit_start, fit_end = fit_range[root_folder]
        except ValueError as e:
            logging.error(f"温度 {root_folder} 的拟合范围加载失败: {e}")
            return
        logging.info(f"拟合范围: {fit_start} - {fit_end} fs")

        # 处理每个文件
        for file_path in data_files:
            self._process_single_file(file_path, data_name, diffusion_results, data_dict, fit_params, root_folder, fit_start, fit_end, config_data)

        # 确保每个温度的数据绘制在单独的图中
        output_img = os.path.join(output_dir, f"MSD_{temperature}.png")  # 使用温度作为文件名
        plotter.plot_msd(config_data, data_dict, fit_params if config_data["ENABLE_FITTING"] else None, output_img, config_data["target_keyword"], fit_start, fit_end)


    

    def run(self):
        """执行处理流程"""

        logging.info(f"发现 {len(self.config.root_folder)} 个数据组: {', '.join([os.path.basename(folder) for folder in self.config.root_folder])}")

        # 处理每个温度组
        for root_folder in self.config.root_folder:
            data_name = self._get_dataset_name(root_folder)
            logging.info(f"开始处理数据组: {data_name}")
            try:
                self.process_temperature_folder(root_folder, data_name, output_dir, diffusion_results, fit_params, config_data)
                logging.info(f"处理完成: {data_name}")
            except Exception as e:
                logging.error(f"处理数据组 {data_name} 时发生错误: {e}")
        
        # 保存扩散系数结果到 CSV 文件
        try:
            self.save_diffusion_results(diffusion_results, output_file, config_data=config_data)
            logging.info(f"扩散系数结果已保存至 {output_file}")
        except Exception as e:
            logging.error(f"保存扩散系数结果时发生错误: {e}")

        # 自动生成 Diffusion Coefficient 图（纵轴为 log(D) 或 log₁₀(D)；这里假设使用 log(D) 的话 D0 = exp(intercept)，  
        # 如果使用 log₁₀(D) 则 D0 = 10^(intercept)；请根据实际需要选择）
        target_keyword = config_data.get("target_keyword", "").strip()
        if target_keyword:
            image_filename = f"diffusion_coefficient_vs_{target_keyword}.png"
        else:
            image_filename = "diffusion_coefficient_vs_temperature.png"
        plot_image_path = os.path.join(output_dir, image_filename)

        try:
            plot_diffusion.plot_diffusion_coefficients(output_file, plot_image_path)
            logging.info(f"扩散系数图已保存至 {plot_image_path}")
        except Exception as e:
            logging.error(f"生成扩散系数图时发生错误: {e}")