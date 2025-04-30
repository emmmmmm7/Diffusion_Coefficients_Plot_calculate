# tools.py
"""
核心工具模块
包含：
1. 数据读取与处理
2. 扩散系数计算
3. 可视化绘图
4. 文件IO操作
"""
import os
import logging
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats, signal
from matplotlib import rcParams
import itertools
import config

class DataProcessor:
    """数据处理管道"""
    
    @staticmethod
    def load_msd_data(file_path, time_range):
        """
        读取MSD数据文件
        参数：
            file_path: .dat文件路径
            time_range: (start, end) 单位ps
        返回：
            (time, msd) 归零化后的数据
        """
        try:
            time, msd = [], []
            valid_data_points = 0

            with open(file_path, 'r', encoding='utf-8') as f:
                for line_idx, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):  # 跳过空行和注释行
                        continue
                    
                    parts = line.split()
                    if len(parts) < 5:
                        logging.warning(f"数据列不足: {file_path}")
                        continue
                    
                    try:
                        # 转换时间单位（fs -> ps）
                        t_fs = float(parts[0])
                        t_ps = t_fs / 1000

                        # 检查时间范围
                        if not (time_range[0] <= t_ps <= time_range[1]):
                            continue
                        # 读取总MSD值（第5列）
                        msd_value = float(parts[4])
                        if np.isnan(msd_value):
                            logging.warning(f"第{line_idx}行包含无效值: {file_path}")
                            continue
                        
                        time.append(t_ps)
                        msd.append(msd_value)
                        valid_data_points += 1

                    except ValueError as e:
                        logging.error(f"第{line_idx}行数据格式错误 [{file_path}]: {str(e)}")
                        continue
            
            if valid_data_points < 2:
                logging.warning(f"有效数据不足 ({valid_data_points}点): {file_path}")
                return None, None
            
            # 归零化处理
            time = np.array(time) - time[0]  
            return time, np.array(msd)
        
        except Exception as e:
            logging.error(f"文件读取失败 [{file_path}]: {str(e)}")
            return None, None

    @staticmethod
    def calculate_diffusion(time, msd, fit_range):
        """
        计算扩散系数
        参数：
            time: 时间序列
            msd: MSD值序列
            fit_range: (start, end) 拟合区间
        返回：
            dict包含计算结果或None
        """
        if time is None or msd is None:
            return None
            
        mask = (time >= fit_range[0]) & (time <= fit_range[1])
        if sum(mask) < 2:
            logging.warning("有效数据点不足，无法拟合")
            return None
        
        try:
            slope, intercept, r_val = stats.linregress(time[mask], msd[mask])[:3]
            return {
                "D": slope / 6,  # 3D扩散系数公式
                "slope": slope,
                "intercept": intercept,
                "r_squared": r_val**2,
                "fit_range": fit_range
            }
        except Exception as e:
            logging.error(f"线性回归失败: {str(e)}")
            return None

class Visualizer:
    """可视化工具集"""
    
    @staticmethod
    def init_chinese_font():
        """初始化中文字体支持"""
        try:
            rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'Microsoft YaHei']
            rcParams['axes.unicode_minus'] = False
        except Exception as e:
            logging.warning(f"字体设置失败: {str(e)}")

    @staticmethod
    def plot_msd(ax, time, msd, fit_result=None, color='b'):
        """绘制单条MSD曲线及拟合线"""
        # 绘制原始数据
        if time is not None and msd is not None:
            ax.plot(time, msd, color=color, alpha=0.4, label='原始数据')
        
        # 绘制拟合结果
        if fit_result:
            fit_line = fit_result['slope']*time + fit_result['intercept']
            mask = (time >= fit_result['fit_range'][0]) & (time <= fit_result['fit_range'][1])
            ax.plot(time[mask], fit_line[mask], '--', 
                   color=color, label='线性拟合')
        return ax
    
    @staticmethod
    def plot_temperature_msd(data_dict, fit_params, output_dir, temperature, fit_range):
        """为单个温度组绘制MSD曲线"""
        plt.figure(figsize=(10, 6), dpi=150)
        ax = plt.gca()
        
        # 设置中文字体
        rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
        rcParams['axes.unicode_minus'] = False

        color_cycle = itertools.cycle(config.load_config()["color_palette"])
        
        # 绘制所有样本曲线
        for idx, (sample_id, (time, msd)) in enumerate(data_dict.items()):
            color = next(color_cycle)
            
            # 原始数据
            ax.plot(time, msd, color=color, alpha=0.4, 
                   label=f'{sample_id.split("_")[-1]} 原始数据')
            
            # 拟合曲线
            if fit_params and sample_id in fit_params:
                slope, intercept = fit_params[sample_id]
                fit_line = slope * time + intercept
                mask = (time >= fit_range[0]) & (time <= fit_range[1])
                ax.plot(time[mask], fit_line[mask], '--', 
                       color=color, linewidth=1.5,
                       label=f'{sample_id.split("_")[-1]} 拟合曲线')

        # 图表装饰
        ax.set_title(f"温度组 {temperature} MSD曲线", fontsize=14)
        ax.set_xlabel("时间 (ps)", fontsize=12)
        ax.set_ylabel("MSD (Å²)", fontsize=12)
        ax.grid(alpha=0.3)
        ax.legend(ncol=2, fontsize=9)
        
        # 保存文件
        output_path = os.path.join(output_dir, f"MSD_{temperature}.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        logging.info(f"已生成温度组图表: {output_path}")

    @staticmethod
    def plot_arrhenius(ax, temperatures, D_values):
        """
        绘制阿伦尼乌斯曲线
        参数：
            ax: matplotlib轴对象
            temperatures: 温度列表 (K)
            D_values: 对应扩散系数列表
        """
        if not temperatures or not D_values:
            logging.error("无有效数据可供绘图")
            return ax
            
        x = 1000 / np.array(temperatures)
        y = np.log(D_values)
        
        # 线性回归
        try:
            slope, intercept, r_val = stats.linregress(x, y)[:3]
            reg_line = slope*x + intercept
        except:
            logging.error("回归分析失败")
            return ax
        
        # 绘图元素
        ax.scatter(x, y, edgecolors='k', label='数据点')
        ax.plot(x, reg_line, 'r--', 
               label=f'拟合曲线 (R²={r_val**2:.2f})')
        
        # 图例标注
        eq_text = f"ln(D) = {slope:.2f}/T + {intercept:.2f}\nD₀ = {np.exp(intercept):.1e} m²/s"
        ax.text(0.05, 0.15, eq_text, 
               transform=ax.transAxes, 
               bbox=dict(facecolor='white', alpha=0.8))
        
        ax.set_xlabel("1000/T (K⁻¹)", fontsize=12)
        ax.set_ylabel("ln(D)", fontsize=12)
        ax.legend()
        return ax

class FileManager:
    """文件操作工具"""
    
    @staticmethod
    def save_results(results, output_path):
        """
        保存扩散系数结果到CSV
        参数：
            results: 字典 {sample_id: {D, r_squared, ...}}
            output_path: 输出文件路径
        """
        if not results:
            logging.warning("无有效结果需要保存")
            return

        headers = ["样本ID", "温度", "扩散系数 (m²/s)", "R²", "拟合起点", "拟合终点"]
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(','.join(headers)+'\n')
            for sample_id, data in results.items():
                row = [
                    sample_id,
                    data['temp'],
                    f"{data['D']:.3e}",
                    f"{data['r_squared']:.4f}",
                    str(data['fit_range'][0]),
                    str(data['fit_range'][1])
                ]
                f.write(','.join(row)+'\n')
        logging.info(f"结果已保存至: {output_path}")