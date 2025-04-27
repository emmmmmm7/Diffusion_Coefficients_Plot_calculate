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
            with open(file_path) as f:
                for line in f:
                    if line.startswith('#'): continue
                    parts = line.strip().split()
                    if len(parts) < 5: continue
                    
                    t_ps = float(parts[0])/1000  # fs转ps
                    if time_range[0] <= t_ps <= time_range[1]:
                        time.append(t_ps)
                        msd.append(float(parts[4]))
            
            if not time: return None, None
            # 归零化处理
            time = np.array(time) - time[0]  
            return time, np.array(msd)
        except Exception as e:
            logging.error(f"Error reading {file_path}: {str(e)}")
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
        mask = (time >= fit_range[0]) & (time <= fit_range[1])
        if sum(mask) < 2: return None
        
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
            logging.warning(f"Regression failed: {str(e)}")
            return None

class Visualizer:
    """可视化工具集"""
    
    @staticmethod
    def plot_msd(ax, time, msd, fit_result=None, color='b'):
        """绘制单条MSD曲线及拟合线"""
        # 绘制原始数据
        ax.plot(time, msd, color=color, alpha=0.4, label='Raw Data')
        
        # 绘制拟合结果
        if fit_result:
            fit_line = fit_result['slope']*time + fit_result['intercept']
            mask = (time >= fit_result['fit_range'][0]) & (time <= fit_result['fit_range'][1])
            ax.plot(time[mask], fit_line[mask], '--', 
                   color=color, label='Linear Fit')
        return ax

    @staticmethod
    def plot_arrhenius(ax, temperatures, D_values):
        """
        绘制阿伦尼乌斯曲线
        参数：
            ax: matplotlib轴对象
            temperatures: 温度列表 (K)
            D_values: 对应扩散系数列表
        """
        x = 1000 / np.array(temperatures)
        y = np.log(D_values)
        
        # 线性回归
        slope, intercept, r_val = stats.linregress(x, y)[:3]
        reg_line = slope*x + intercept
        
        # 绘图元素
        ax.scatter(x, y, edgecolors='k', label='Data Points')
        ax.plot(x, reg_line, 'r--', 
               label=f'Fit (R²={r_val**2:.2f})')
        
        # 图例标注
        eq_text = f"ln(D) = {slope:.2f}/T + {intercept:.2f}\nD₀ = {np.exp(intercept):.1e} m²/s"
        ax.text(0.05, 0.15, eq_text, 
               transform=ax.transAxes, 
               bbox=dict(facecolor='white', alpha=0.8))
        
        ax.set_xlabel("1000/T (K⁻¹)")
        ax.set_ylabel("ln(D)")
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
        headers = ["SampleID", "Temperature", "D (m²/s)", "R²", "Fit Start", "Fit End"]
        with open(output_path, 'w') as f:
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
        logging.info(f"Results saved to {output_path}")