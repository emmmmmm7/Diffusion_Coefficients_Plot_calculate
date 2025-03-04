import numpy as np
from scipy.stats import linregress
import logging

def compute_diffusion_coefficient(time, msd, fit_start, fit_end):
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
