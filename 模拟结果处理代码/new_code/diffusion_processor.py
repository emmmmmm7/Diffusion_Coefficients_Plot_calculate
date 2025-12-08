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
from scipy.stats import linregress
from matplotlib import rcParams
from scipy.signal import butter, filtfilt
import itertools
import colorsys
import matplotlib.colors as mcolors
from matplotlib.ticker import MaxNLocator
import csv
from matplotlib.ticker import ScalarFormatter
import re

class DiffusionProcessor:
    def __init__(self, config):
        self.config = config
        self.diffusion_config = self.config.get_config()["diffusion"]
        self.fit_range = self.config.get_config()["diffusion"].get("fit_ranges", {})
        self.results = {}
        self.diffusion_results = {}
        self.fit_params = {}
        self.data_dict = {}

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
    
    def _safe_read_file(self,file_path, read_function, *args, **kwargs):
        try:
            return read_function(file_path, *args, **kwargs)
        except FileNotFoundError:
            logging.info(f"文件未找到: {file_path}")
        except Exception as e:
            logging.error(f"读取文件 {file_path} 时出错: {e}")
        return None
    
    def _read_MSD_data(self, file_path, start_time_ps=20, end_time_ps=30):
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
                    tot_msd.append(float(data[int(self.diffusion_config["diffusion_direction"])]))
                    # tot_msd.append(float(data[1]))
        # 归零化处理（关键修改点）
        if time_original:
            start_ps = time_original[0]  # 获取实际起始时间
            time = [t - start_ps for t in time_original]  # 归零化
        else:
            time = []
        
        # logging.info(f"时间归零化完成，新范围: [{min(time, default=0):.1f}, {max(time, default=0):.1f}] ps")
        return time, tot_msd
    
    def _smooth_data(self, y, method=0, window_size=50):
        """
        数据平滑处理
        :param method: 0-原始数据 1-移动平均 2-低通滤波
        :param window_size: 移动平均窗口大小
        """
        try:
            if method == 0:
                return y
            elif method == 1:
                return self._moving_average(y, window_size)
            elif method == 2:
                return self._lowpass_filter(y)
            else:
                raise ValueError("未知的平滑方法")
        except Exception as e:
            logging.warning(f"数据平滑失败: {e}")
            return y
    
    def _moving_average(self, y, window_size):
        window = np.ones(int(window_size))/float(window_size)
        return np.convolve(y, window, 'same')

    def _lowpass_filter(self, y, cutoff=0.1, fs=10, order=5):
        nyq = 0.5 * fs
        normal_cutoff = cutoff / nyq
        b, a = butter(order, normal_cutoff, btype='low', analog=False)
        return filtfilt(b, a, y)
    
    def _compute_diffusion_coefficient(self, time, msd, fit_start, fit_end):
        """
        计算扩散系数 D
        :param time: 时间数据列表
        :param msd: MSD 数据列表
        :param fit_start: 拟合起始时间
        :param fit_end: 拟合结束时间
        :return: (D, slope, intercept, r_squared) 或 None
        """
        # 选择拟合区域
        fit_indices = [i for i, t in enumerate(time) if fit_start <= t <= fit_end]
        if len(fit_indices) < 2:
            logging.warning("拟合区域数据点不足，无法计算 D")
            return None

        fit_time = np.array([time[i] for i in fit_indices])
        fit_msd = np.array([msd[i] for i in fit_indices])

        # 线性拟合 MSD
        slope, intercept, r_value, _, _ = linregress(fit_time, fit_msd)

        # 计算扩散系数 D（适用于三维扩散）
        D = slope / 6  
        return D, slope, intercept, r_value**2
    
    def _process_single_file(self, file_path, data_name, fit_start, fit_end):
        """
        处理单个数据文件，计算扩散系数并保存结果
        :param file_path: 数据文件路径
        :param data_name: 数据集名称
        :param fit_start: 拟合的起始时间
        :param fit_end: 拟合的结束时间
        """
        file_name = os.path.basename(file_path)
        # 使用温度前缀生成唯一键
        unique_key = f"{data_name}_{file_name}"

        result = self._safe_read_file(file_path, self._read_MSD_data, self.diffusion_config["start_time_ps"], self.diffusion_config["end_time_ps"])

        if result is not None:
            time, msd = result
        else:
            time, msd = [], []  # 避免解包错误

        # 获取平滑配置
        smooth_method = self.diffusion_config.get("data_smooth_method", 0)
        window_size = self.diffusion_config.get("smooth_params", {}).get("smooth_window_size", 10)

        if time and msd:
            # 应用平滑
            msd_smoothed = self._smooth_data(msd, method=smooth_method, window_size=window_size)
            # 应用平滑后的数据保存到字典
            self.data_dict[unique_key] = (time, msd_smoothed)
            if self.diffusion_config["enable_fitting"]:
                logging.info(f"拟合模式：{self.diffusion_config["enable_fitting"]}")
                # 计算扩散系数
                result = self._compute_diffusion_coefficient(time, msd_smoothed, fit_start, fit_end)
                if result:
                    D, slope, intercept, r_squared = result
                    # 判断 target_keyword 过滤
                    target = self.diffusion_config.get("target_element", "").lower().strip()
                    if not target or target in file_name.lower():
                        self.diffusion_results[unique_key] = (D, r_squared, data_name)  # 将温度与结果一起保存
                        self.fit_params[unique_key] = (slope, intercept)
                        logging.info(f"{unique_key}: D = {D:.6e} m²/s, R² = {r_squared:.4f}")
                    else:
                        logging.debug(f"文件 {file_name} 不包含目标关键字 '{target}'，跳过保存扩散系数。")
                else:
                    logging.warning(f"文件 {file_name} 无法计算扩散系数")
        else:
            logging.warning(f"文件 {file_name} 数据为空或无法读取")
        
    def _plot_msd(self, save_path=None, fit_start=None, fit_end=None, data_name=None, line_style='-', line_width=1):
        """
        绘制 MSD 曲线，并在每条曲线上添加拟合线（如果启用）
        :param save_path: 图片保存路径，如果为 None，则显示图像
        :param fit_start: 拟合起始时间
        :param fit_end: 拟合结束时间
        """

        # ========== 新增颜色循环配置 ==========
        color_cycle = itertools.cycle(self.config.get_config()["color_palette"])  # 定义在函数内部

        plt.figure(figsize=(20, 6))
        ax = plt.gca()

        # 设置全局字体
        plt.rcParams.update({
            'font.family': 'serif',
            'font.serif': ['Times New Roman'],
            'mathtext.fontset': 'stix'  # 数学符号风格
        })
        
        # 初始化变量来存储 time 的最大和最小值
        min_time = float('inf')
        max_time = float('-inf')

        # ========== 新增图例分离逻辑 ==========
        data_handles = []
        data_labels = []
        fit_handles = []
        fit_labels = []

        # ========== 新增颜色生成函数 ==========
        def generate_contrast_color(base_hex, light=0.3, dark=0.7):
            """
            生成同色系高对比颜色对
            :param base_hex: 基础色十六进制
            :param light: 数据线亮度系数 (0-1)
            :param dark: 拟合线亮度系数 (0-1)
            :return: (data_color, fit_color)
            """
            # 转换为HSL空间
            rgb = mcolors.hex2color(base_hex)
            h, l, s = colorsys.rgb_to_hls(rgb[0], rgb[1], rgb[2])
            
            # 生成配色对
            data_color = colorsys.hls_to_rgb(h, light, s)
            fit_color = colorsys.hls_to_rgb(h, dark, min(s*1.5, 1.0))
            return (
                mcolors.to_hex(data_color),
                mcolors.to_hex(fit_color)
            )
        
        # 遍历数据，找到时间的最小值和最大值
        for key, (time, msd) in list(self.data_dict.items()):
            if not key.startswith(data_name):
                continue
            time, msd = self.data_dict[key]
            # 获取基础色并生成对比色
            base_color = next(color_cycle)
            data_color, fit_color = generate_contrast_color(base_color)

            # 更新最小时间和最大时间
            min_time = min(min_time, np.min(time))
            max_time = max(max_time, np.max(time))

            # 处理键名
            ele_name = key.split("-")[-1].replace(".dat", "")
            
            
            # 绘制数据线（浅色+透明度）
            data_line = ax.plot(
                time, msd,
                label=ele_name,
                color=data_color,  # 使用浅色版本
                alpha=0.4,         # 透明度设置
                linestyle=line_style,
                linewidth=line_width,
                zorder=5
            )[0]

            data_handles.append(data_line)
            data_labels.append(ele_name)

            # 判断是否需要绘制拟合线：只对键中包含 target_keyword 的数据绘制拟合线
            if self.diffusion_config["enable_fitting"] and self.fit_params and key in self.fit_params:

                # 如果设置了 target_keyword，则检查
                target_element = self.diffusion_config["target_element"]
                if target_element and target_element.lower() not in key.lower():
                    continue
                slope, intercept = self.fit_params[key]
                fit_time = np.array(time)
                fit_line = slope * fit_time + intercept

                fit_mask = (fit_time >= fit_start) & (fit_time <= fit_end)
                fit_line_obj, =ax.plot(
                    fit_time[fit_mask],
                    fit_line[fit_mask],
                    color=fit_color,  # 使用深色版本
                    linestyle='--',
                    linewidth=line_width*1.5,  # 加粗50%
                    alpha=1.0,        # 不透明
                    zorder=4,         # 在数据线下层
                    label=f"{ele_name}_Fit" + r'$\mathregular{y = %.5fx  %+0.4f}$' % (slope, intercept)  # 确保标签唯一性
                )

                fit_handles.append(fit_line_obj)
                fit_labels.append(f"{ele_name} Fit: "+ r'$\mathregular{y = %.5fx  %+0.4f}$' % (slope, intercept))

        # ==================== 坐标轴优化 ==================== 
        # 动态设置 x 轴的范围：确保 x 轴的起点和终点根据时间数据来确定
        plt.xlim([min_time, max_time])
        # 坐标轴刻度优化
        ax = plt.gca()
        ticks = ax.get_xticks()  # 获取当前自动生成的刻度
        ticks = np.append(ticks, max_time)  # 强制添加 max_time
        ax.set_xticks(ticks)  # 重新设定刻度
        # 确保显示最大刻度（关键修改）
        ax.xaxis.set_major_locator(MaxNLocator(nbins=5, prune=None))  # <--- 防止x轴最低刻度被裁剪
        ax.yaxis.set_major_locator(MaxNLocator(nbins=7, prune=None))  # <--- 防止y轴最低刻度被裁剪

        # 标签设置
        plt.xlabel('Time (ps)', fontsize=12)
        plt.ylabel('MSD (Å²)', fontsize=12)  # <--- 修正单位符号

        # ========== 图例优化 ==========
        # 合并图例项（数据线在上，拟合线在下）
        all_handles = data_handles + fit_handles
        all_labels = data_labels + fit_labels
        
        # 应用优化后的图例
        ax.legend(
            handles=all_handles,
            labels=all_labels,
            loc='best',
            frameon=True,
            edgecolor='none',
            framealpha=0,
            fontsize=10
        )
        
        plt.grid(False)
        plt.gca().tick_params(direction='in')
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logging.info(f"图像已保存: {save_path}")
            plt.close()
        else:
            plt.show()

    def _process_data_folder(self, root_folder, data_name):
        """
        处理每个温度组的文件夹
        :param root_folder: 温度组文件夹路径
        :param data_name: 数据集名称
        """
        # 读取数据文件，进行扩散系数计算和拟合

        # 这里假设有一个函数 process_data_file 来处理单个数据文件
        # 具体实现根据实际数据格式和需求进行调整
        data_files = self._get_all_data_files(root_folder)
        folder_name = os.path.basename(root_folder)
        if not data_files:
            logging.error(f"{root_folder} 文件夹下没有找到 .dat 文件")
            return
        
        # 获取拟合范围
        try:
            fit_range = self.config.get_config()["diffusion"].get("fit_ranges", {})
            if self.diffusion_config["temperature_mode"] == "multiedition":
                folder_name = folder_name.split("-")[0]
                # logging.info({folder_name})  # 处理多版本温度数据
            # fit_start, fit_end = fit_range[folder_name]
            # 正确提取嵌套字典中的数值
            fit_start = fit_range[folder_name]["fit_start"]
            fit_end = fit_range[folder_name]["fit_end"]
        except ValueError as e:
            logging.error(f"温度 {folder_name} 的拟合范围加载失败: {e}")
            return
        logging.info(f"拟合范围: {fit_start} - {fit_end} fs")

        # 处理每个文件
        for file_path in data_files:
            self._process_single_file(file_path, data_name, fit_start, fit_end)

        # 确保每个温度的数据绘制在单独的图中
        output_img = os.path.join(self.config.output_dir, f"MSD_{data_name}.png")  # 使用温度作为文件名
        self._plot_msd(output_img, fit_start, fit_end, data_name)

    def _save_diffusion_results(self, output_file, append=False):
        """
        以 CSV 格式保存扩散系数计算结果，保存时根据关键字筛选
        :param results: { unique_key: (D, R², 温度) } 字典
        :param output_file: CSV 文件路径
        :param append: 是否追加到现有文件
        """
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # print(f"Results to save: {results}")

        mode = 'a' if append else 'w'
        with open(output_file, mode, newline='') as f:
            writer = csv.writer(f)
            if not append or os.stat(output_file).st_size == 0:
                writer.writerow(["dataset", "Diffusion Coefficient (m²/s)", "R²"])  # CSV 头部
            for file, (D, r_squared, data_name) in self.diffusion_results.items():
                writer.writerow([data_name, f"{D:.6e}", f"{r_squared:.4f}"])  # 确保数据格式正确
                logging.info(f"{data_name}已经成功写入")
        logging.info(f"扩散系数已保存至: {output_file}")

    def _parse_dataset(slef, temp_str):
        """
        将温度字符串（例如 "600K" 或 "600"）转换为数值。
        """
        try:
            temp_str = temp_str.strip()
            if temp_str.lower().endswith("k"):
                return float(temp_str[:-1])
            else:
                return float(temp_str)
        except Exception as e:
            logging.error(f"温度转换错误: {temp_str} -> {e}")
            return None
        
    def _read_diffusion_csv(self, csv_file):
        """
        读取 CSV 文件，返回按温度分组的扩散系数列表。
        CSV 文件须包含列 "dataset" 和 "Diffusion Coefficient (m²/s)"。
        
        返回：
            data: dict, 格式 { dataset_value: [D1, D2, ...] }
        """
        data = {}
        with open(csv_file, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                temp_str = row["dataset"].strip()
                D_str = row["Diffusion Coefficient (m²/s)"].strip()
                
                if self.diffusion_config["diffusion_mode"] == "pressure":
                    # 处理压力数据集名称
                    temp_str = temp_str.split("-")[1]
                    logging.info(f"处理压力数据集: {temp_str}")
                    T = self._parse_dataset(temp_str)
                elif self.diffusion_config["diffusion_mode"] == "temperature":
                    # if self.diffusion_config["temperature_mode"] == "multiedition":
                    #     # 使用正则表达式提取温度
                    #     temp_str = temp_str.split("-")[0]  # 假设温度在第一个部分
                    T = temp_str
                else:
                    logging.error(f"未知的扩散模式: {self.diffusion_config['diffusion_mode']}")
                    continue

                if T is None:
                    continue
                try:
                    D = float(D_str)
                except Exception as e:
                    logging.error(f"扩散系数转换错误: {D_str} -> {e}")
                    continue
                if T not in data:
                    data[T] = []
                data[T].append(D)
        return data
    
    def _plot_diffusion_coefficients(self, csv_file, save_path):
        """
        从 csv_file 读取扩散系数数据，按版本区分数据点，
        仅使用正的扩散系数（大于 0）的数据，
        绘制以温度为 x 轴、ln(D) 为 y 轴的散点图，
        同时进行线性回归拟合，并将拟合线绘制在图中，
        最后将图保存到 save_path，并将拟合结果写入文本文件保存到 output 文件夹中。
        
        参数:
            csv_file: CSV 文件路径
            save_path: 图像保存路径
            params: 参数字典，包含 temperature_mode 等设置
        """
        
        # ==================== 数据读取与预处理 ==================== 
        raw_data = self._read_diffusion_csv(csv_file)
        if not raw_data:
            logging.error("未读取到有效数据，请检查 CSV 文件格式")
            return

        # 判断是否为多版本模式
        is_multiedition = self.diffusion_config.get("temperature_mode") == "multiedition"
        
        # 初始化数据容器
        all_x = []  # 所有数据点的 x 坐标 (1000/T)
        all_y = []  # 所有数据点的 y 坐标 (ln(D))
        version_data = {}  # 按版本分组的数据
        
        # 处理每个温度组
        if is_multiedition:
            # 多版本温度模式处理
            logging.info("使用多版本温度模式处理数据")
            
            # 按版本分组数据
            for full_temp_name, D_values in raw_data.items():
                # 提取版本信息
                if '-' in full_temp_name:
                    parts = full_temp_name.split('-')
                    base_temp = parts[0]
                    version = parts[1] if len(parts) > 1 else "v1"
                else:
                    base_temp = full_temp_name
                    version = "v1"
                
                # 计算温度值
                try:
                    temp_value = int(base_temp.rstrip('K'))
                    x_value = 1000 / temp_value
                except ValueError:
                    logging.warning(f"无法解析温度值: {base_temp}")
                    continue
                
                # 过滤非正值并计算ln(D)
                for D in D_values:
                    if D > 0:
                        y_value = np.log(D)
                        all_x.append(x_value)
                        all_y.append(y_value)
                        
                        # 按版本分组
                        if version not in version_data:
                            version_data[version] = {'x': [], 'y': []}
                        version_data[version]['x'].append(x_value)
                        version_data[version]['y'].append(y_value)
            
            logging.info(f"共处理 {len(all_x)} 个数据点，来自 {len(version_data)} 个版本")
        else:
            # 原有处理模式
            for T, D_values in raw_data.items():
                try:
                    temp_value = int(T.rstrip('K'))
                    x_value = 1000 / temp_value
                except ValueError:
                    logging.warning(f"无法解析温度值: {T}")
                    continue
                
                # 过滤非正值并计算ln(D)
                for D in D_values:
                    if D > 0:
                        y_value = np.log(D)
                        all_x.append(x_value)
                        all_y.append(y_value)
            
            # 将所有数据标记为默认版本
            version_data["default"] = {'x': all_x, 'y': all_y}
            logging.info(f"共处理 {len(all_x)} 个数据点")

        if not all_x:
            logging.error("无有效数据可供绘图")
            return

        # ==================== 绘图样式配置 ====================
        plt.figure(figsize=(8, 6), dpi=150)
        ax = plt.gca()
        
        # 设置全局字体
        plt.rcParams.update({
            'font.family': 'serif',
            'font.serif': ['Times New Roman'],
            'mathtext.fontset': 'stix'  # 数学符号风格
        })

        # 颜色方案
        VERSION_COLORS = {
            'v1': '#2C5F94',   # 深蓝色
            'v2': '#97CC04',   # 鲜绿色
            'v3': '#F4364C',   # 红色
            'v4': '#FFB300',   # 橙色
            'v5': '#804FB3',   # 紫色
            'default': '#2C5F94'  # 默认颜色
        }
        
        VERSION_MARKERS = {
            'v1': 'o',  # 圆形
            'v2': 's',  # 方形
            'v3': '^',  # 三角形
            'v4': 'D',  # 菱形
            'v5': 'v',  # 倒三角形
            'default': 'o'  # 默认标记
        }

        # ==================== 数据可视化 ====================
        # 为每个版本绘制数据点
        for version, data in version_data.items():
            color = VERSION_COLORS.get(version, VERSION_COLORS['default'])
            marker = VERSION_MARKERS.get(version, VERSION_MARKERS['default'])
            
            ax.scatter(
                data['x'], data['y'],
                marker=marker,
                color=color,
                s=60,
                edgecolors='white',
                linewidth=1,
                label=f"{version}" if is_multiedition else "Experimental Data"
            )

        # ==================== 线性回归 ====================
        # 使用所有数据点进行拟合
        if all_x and all_y:
            regress = linregress(all_x, all_y)
            slope = regress.slope
            intercept = regress.intercept
            r_squared = regress.rvalue**2
            
            # 生成拟合线
            x_fit = np.linspace(min(all_x), max(all_x), 100)
            y_fit = intercept + slope * x_fit

            # 拟合线绘制
            ax.plot(
                x_fit, y_fit, 
                color='#97CC04', 
                linestyle='--',
                linewidth=2,
                label=(
                    r'$\mathregular{\ln(D) = \frac{%.2f}{T}  %+.2f}$' % (slope*1000, intercept) + '\n' + 
                    r'$\mathregular{R^2 = %.3f}$' % r_squared
                )
            )
        else:
            logging.error("无有效数据进行线性回归")
            slope, intercept, r_squared = 0, 0, 0

        # ==================== 坐标轴优化 ====================
        # X轴设置
        ax.set_xlabel(
            r'$\mathregular{1000/T\ (K^{-1})}$', 
            fontsize=12, 
            labelpad=8
        )
        ax.xaxis.set_major_formatter(ScalarFormatter(useMathText=True))
        ax.ticklabel_format(axis='x', style='sci', scilimits=(-3,3))
        ax.xaxis.offsetText.set_fontsize(10)

        # Y轴设置
        ax.set_ylabel(
            r'$\mathregular{\ln(D)\ (m^2/s)}$', 
            fontsize=12, 
            labelpad=8
        )
        
        # 网格线
        ax.grid(False)
        
        # 坐标轴刻度朝内
        ax.tick_params(direction='in')
        
        # ==================== 图例与输出 ====================
        ax.legend(
            loc='best',
            frameon=True,
            framealpha=0.9,
            edgecolor='none',
            fontsize=10
        )

        plt.tight_layout()
        
        # 保存图像
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, bbox_inches='tight', dpi=300)
        plt.close()

        # ==================== 拟合结果输出 ====================
        D0 = np.exp(intercept)
        result_text = f"""Fitting Results:
        - Slope (Ea/R): {slope:.2e} K
        - Intercept (lnD0): {intercept:.2e}
        - R²: {r_squared:.4f}
        - D0: {D0:.2e} m²/s
        - Number of data points: {len(all_x)}
        """
        
        # 添加多版本模式下的额外信息
        if is_multiedition:
            result_text += "\nData points by version:\n"
            for version, data in version_data.items():
                result_text += f"  - Version {version}: {len(data['x'])} data points\n"
        
        result_path = os.path.join(os.path.dirname(save_path), "fitting_results.txt")
        with open(result_path, 'w') as f:
            f.write(result_text)
        logging.info(f"拟合结果已保存至 {result_path}")

    def run(self):
        """执行处理流程"""

        logging.info(f"发现 {len(self.config.root_folder)} 个数据组: {', '.join([os.path.basename(folder) for folder in self.config.root_folder])}")

        logging.info(f"是否绘制扩散系数图: {self.diffusion_config.get('just_plotDC', "false")}")
        if self.diffusion_config.get("just_plotDC", "false").lower() == "true": 
            # 处理每个温度组
            for root_folder in self.config.root_folder:
                data_name = self._get_dataset_name(root_folder)
                logging.info(f"开始处理数据组: {data_name}")
                try:
                    self._process_data_folder(root_folder, data_name)
                    logging.info(f"处理完成: {data_name}")
                except Exception as e:
                    logging.error(f"处理数据组 {data_name} 时发生错误: {e}", exc_info=True)
            
            # 保存扩散系数结果到 CSV 文件
            try:
                output_csv_file = os.path.join(self.config.output_dir, "diffusion_coefficients.csv")
                self._save_diffusion_results(output_csv_file)
                logging.info(f"扩散系数结果已保存至 {output_csv_file}")
            except Exception as e:
                logging.error(f"保存扩散系数结果时发生错误: {e}")
        else:
            logging.info("仅绘制扩散系数图，不进行数据处理")
            output_csv_file = os.path.join(self.config.output_dir, "diffusion_coefficients.csv")
            if not os.path.exists(output_csv_file):
                logging.error(f"未找到扩散系数 CSV 文件: {output_csv_file}")
                return

        # 自动生成 Diffusion Coefficient 图（纵轴为 log(D) 或 log₁₀(D)；这里假设使用 log(D) 的话 D0 = exp(intercept)，  
        # 如果使用 log₁₀(D) 则 D0 = 10^(intercept)；请根据实际需要选择）
        target_element = self.diffusion_config.get("target_element", "").strip()
        if target_element:
            image_filename = f"diffusion_coefficient_vs_{target_element}.png"
        else:
            image_filename = "diffusion_coefficient_vs_dataset.png"
        plot_image_path = os.path.join(self.config.output_dir, image_filename)

        try:
            self._plot_diffusion_coefficients(output_csv_file, plot_image_path)
            logging.info(f"扩散系数图已保存至 {plot_image_path}")
        except Exception as e:
            logging.error(f"生成扩散系数图时发生错误: {e}")