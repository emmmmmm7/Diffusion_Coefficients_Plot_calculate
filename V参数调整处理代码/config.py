import os

config_data = {
    # 生成目录的绝对路径
    "data_path": os.path.expanduser("/Users/rrw/Documents/postgraduate/矿物年代学/扩散系数模拟相关/Ti_qudai_File/2-2023.03.21-V/600K"),  
    
    # 需要忽略的前缀列表（根据文件夹名的第一部分）
    "ignore_dirs": ["4"],  

    # 新增：验证数据集前缀
    "verify_dirs": ["5"],  
    
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
    "expected_pressure": 0.5
}