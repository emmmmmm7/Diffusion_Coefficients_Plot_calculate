import os

config_data = {
    # 生成目录的绝对路径
    "data_path": os.path.expanduser("/Users/rrw/Documents/postgraduate/矿物年代学/扩散系数模拟相关/Ti_qudai_File/nPT方案/1-test-700K-2025.03.28"),  
    
    # 需要忽略的前缀列表（根据文件夹名的第一部分）
    "ignore_dirs": [],  

    # 新增：验证数据集前缀
    "verify_dirs": [],  
    
    # 颜色配置
    "colors": ["#1f77b4",
                "#ff7f0e",
                "#2ca02c",
                "#d62728",
                "#9467bd",
                "#8c564b",
                "#e377c2",
                "#7f7f7f",
                "#bcbd22",
                "#17becf"
        ], 
    
    # 目标压力值
    "expected_pressure": 0.5,

    
    # 新增：是否绘制所有时间点的图像
    # 0: 不忽略时间截取参数； 1: 忽略时间截取参数
     "all_time": 1,

    # 新增时间截取参数
    "start_time_ps": 0,  
    "end_time_ps": 3,

    # 新增绘图模式：1、nVT方案中用于求解体积参数；2、nPT方案中绘制温度图片
    "plot_model": 2,

    # 新增：分析模式选择，0：不分析；1：仅平均值分析；2：平均值分析+拟合+对应目标值
    "analyse_model": 1,
}