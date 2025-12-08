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
import itertools

class PressureProcessor:
    def __init__(self, config):
        self.config = config
        self.output_dir = self.config.output_dir
        self.data_folder = self.config.data_folder
        self.pressure_config = self.config.get_config()["pressure"]
        self.ignore_dirs = self.pressure_config.get("ignore_dirs", [])
        self.verify_dirs = self.pressure_config.get("verify_dirs", [])
        self.exprected_pressure = self.pressure_config.get("expected_pressure", 0.5)
        self.all_time = self.pressure_config.get("all_time", 1)
        self.start_time_ps = self.pressure_config.get("start_time_ps", 0)
        self.end_time_ps = self.pressure_config.get("end_time_ps", 6)
        self.plot_model = self.pressure_config.get("plot_model", 1)
        self.analyse_model = self.pressure_config.get("analyse_model", 1)
        self.root_folder = self.config.root_folder
        self.all_time= self.pressure_config.get["all_time", 1]        
        self.results = {}
        self.diffusion_results = {}
        self.fit_params = {}
        self.data_dict = {}
        # 初始化中文字体
        rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
        rcParams['axes.unicode_minus'] = False
        logging.info(f"配置文件加载成功\n"
                    f"数据路径: {self.config.data_folder}\n"
                    f"排除前缀: {self.ignore_dirs}\n"
                    f"预期压力: {self.exprected_pressure}\n")
    
    def _process_data_files(self):
        averages = {}
        verify_averages = {}
        color_cycle = itertools.cycle(self.config.get_config()["colors"])

        # 创建输出子目录
        timeseries_dir = os.path.join(self.output_dir, "timeseries_plots")
        os.makedirs(timeseries_dir, exist_ok=True)

        # 验证根目录
        if not os.path.exists(self.data_folder):
            raise FileExistsError(f"配置的根目录不存在: {self.data_folder}")
        
        if not self.root_folder:
            raise ValueError(f"在指定目录 {self.data_folder} 中未找到任何子文件夹")
        
        logging.info(f"开始处理{len(self.root_folder)}...")

        for folder_name in self.root_folder:
            # 忽略指定前缀的文件夹
            prefix = folder_name.split("-")[0]

            if prefix in self.ignore_dirs:
                logging.info(f"跳过文件夹: {folder_name}")
                continue

            # 标记验证目录
            is_verify = prefix in self.verify_dirs

            # 忽略output文件夹
            if folder_name == "output":
                continue

            folder_path = os.path.join(self.data_folder, folder_name)

            if self.plot_model == 1:
                data_file_name = "total_pressure.txt"
                data_columns = (None, 0) # 单列数据
                y_label = "Pressure (Kbar)"
            elif self.plot_model == 2:
                data_file_name = "T-E.dat"
                data_columns = (0, 1)
                y_label = "Temperature (K)"
            else:
                raise ValueError("无效的绘图模式: {self.plot_model}")
            
            data_file =os.path.join(folder_path, "results", data_file_name)

            # 文件夹名解析验证
            try:
                param_part = folder_name.split("-")[-1]
                float(param_part)
            except (ValueError, IndexError):
                logging.warning(f"跳过文件夹 '{folder_name}'：命名不符合规范")
                continue

            if not os.path.exists(data_file):
                logging.warning(f"跳过文件夹 '{folder_name}'：数据文件不存在")
                continue

            try:
                if self.plot_model == 1:
                    # 模式1:单列压力数据
                    data = np.loadtxt(data_file)
                    n_points = len(data)
                    time_fs = np.arange(n_points)
                    time_ps = time_fs * 0.001
                elif self.plot_model == 2:
                    # 模式2:多列数据，提取指定列
                    try:
                        # 使用更稳健的方法读取数据
                        full_data = np.genfromtxt(data_file, invalid_raise=False)

                        # 检验并处理包含NaN的行
                        nan_mask = np.isnan(full_data).any(axis=1)
                        if np.any(nan_mask):
                            nan_count = np.sum(nan_mask)
                            valid_data = full_data[~nan_mask]
                            logging.warning(
                                f"在文件夹 {folder_name} 中发现 {nan_count} 行包含NaN值 "
                                f"(总行数：{len(full_data)})，已自动过滤"
                            )

                            # 如果过滤后无有效数据则跳过
                            if len(valid_data) == 0:
                                logging.warning(f"在文件夹 {folder_name}的{data_file_name}中没有有效数据，跳过该文件")
                                continue
                            
                            full_data = valid_data
                        
                        # 提取时间和温度数据
                        time_fs = full_data[:, data_columns[0]].astype(float)
                        data = full_data[:, data_columns[1]].astype(float)

                        # 时间归零处理（从第一个有效数据点开始）
                        time_fs -= time_fs[0]

                        n_points = len(data)
                        time_ps = time_fs * 0.001
                    
                    except Exception as e:
                        logging.error(f"加载 {data_file_name} 失败：{str(e)}")
                        continue
                else:
                    raise ValueError(f"无效的绘图模式: {self.plot_model}")
                
                # 添加安全校验
                if "time_ps" not in locals():
                    raise ValueError("时间序列生成失败，请检查数据文件格式")
                
                # 时间截取逻辑修改
                if self.all_time == 1:
                    start_idx = 0
                    end_idx = n_points - 1
                    used_start_ps = 0.0
                    used_end_ps = time_ps[-1]
                else:
                    # 精确查找索引（避免fs转换误差）
                    tart_idx = np.searchsorted(time_ps, self.start_time_ps, side='left')
                    end_idx = np.searchsorted(time_ps, self.end_time_ps, side='right') - 1
                    end_idx = min(end_idx, n_points-1)  # 安全保护
                    used_start_ps = self.start_time_ps
                    used_end_ps = self.end_time_ps

                # 截取数据段
                data = data[start_idx:end_idx+1]
                time_ps = time_ps[start_idx:end_idx+1]

                # 新增：确保时间序列连续（处理可能的索引错误）
                if len(time_ps) == 0:
                    logging.warning(f"跳过文件夹 {folder_name}：时间范围内无数据")
                    continue

                # 添加调试日志
                logging.debug(
                    f"时间范围 - {folder_name}: "
                    f"配置all_time={self.all_time} "
                    f"实际使用范围=[{used_start_ps:.2f}ps, {used_end_ps:.2f}ps] "
                    f"数据点数={len(data)}"
                )
                        
            except Exception as e:
                logging.error(f"处理文件夹 {folder_name} 时出错: {str(e)}")
                continue

    def run(self):
        averages, verrify_averages = self._process_data_files()
        pass

    