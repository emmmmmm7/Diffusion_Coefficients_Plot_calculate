import numpy as np
import matplotlib.pyplot as plt
import os
from pathlib import Path

lattice_constant = np.array([24.835004368839,24.835004368839,28.097600000006])
initial_coord_file = "../POSCAR_initial"

def load_initial_coordinates():
    with open(initial_coord_file, 'r') as f:
        lines = f.readlines()
    
    # 跳过前8行
    coord_lines = lines[8:2008]
    
    initial_coords = {}
    for idx, line in enumerate(coord_lines, start=1):
        parts = list(map(float, line.strip().split()))
        initial_coords[idx] = np.array(parts[:3])
    
    return initial_coords

initial_coords = load_initial_coordinates()

def adjust_by_initial(raw_data, atom_id):
    """
    基于初始坐标的周期性修正
    参数：
        raw_data: (n_steps, 3) 原始分数坐标数组
        atom_id: 原子序号
    返回：
        修正后的连续分数坐标
    """
    base_coord = initial_coords[atom_id]
    
    processed = raw_data.copy()
    
    # 对每个时间步进行处理
    for i in range(len(processed)):
        delta = processed[i] - base_coord
        
        for dim in range(3):
            if delta[dim] > 0.5:
                processed[i, dim] -= 1.0
            elif delta[dim] < -0.5:
                processed[i, dim] += 1.0
    
    return processed

def process_atom_file(input_file):
    """处理单个原子数据文件"""
    atom_id = int(Path(input_file).stem.split("_")[-1])
    
    raw_data = np.loadtxt(input_file)
    
    if raw_data.size == 0:
        print(f"警告：文件 {input_file} 为空")
        return
    if raw_data.ndim == 1:
        raw_data = raw_data.reshape(1, -1)
    
    adjusted_data = adjust_by_initial(raw_data, atom_id)
    
    real_coords = adjusted_data * lattice_constant
    
    stats = {
        'x': (np.mean(real_coords[:, 0]), np.var(real_coords[:, 0])),
        'y': (np.mean(real_coords[:, 1]), np.var(real_coords[:, 1])),
        'z': (np.mean(real_coords[:, 2]), np.var(real_coords[:, 2]))
    }
    
    avg_msd_dir = Path("calc_avg_msd")
    avg_msd_dir.mkdir(exist_ok=True)
    
    with open(avg_msd_dir / f"avg_msd_{atom_id}.dat", 'w') as f:
        f.write(f"# Atom {atom_id} 坐标统计\n")
        f.write(f"X_Mean\t{stats['x'][0]:.6f}\tX_Var\t{stats['x'][1]:.6f}\n")
        f.write(f"Y_Mean\t{stats['y'][0]:.6f}\tY_Var\t{stats['y'][1]:.6f}\n")
        f.write(f"Z_Mean\t{stats['z'][0]:.6f}\tZ_Var\t{stats['z'][1]:.6f}\n")
    
    image_dir = Path("image")
    image_dir.mkdir(exist_ok=True)
    
    plt.figure(figsize=(10, 6))
    plt.hist(real_coords[:, 0], bins=50, alpha=0.7, 
             label=f'X (μ={stats["x"][0]:.4f}, σ²={stats["x"][1]:.4f})',
             color='blue', edgecolor='navy', histtype='step')
    plt.hist(real_coords[:, 1], bins=50, alpha=0.7,
             label=f'Y (μ={stats["y"][0]:.4f}, σ²={stats["y"][1]:.4f})',
             color='green', edgecolor='darkgreen', histtype='step')
    plt.hist(real_coords[:, 2], bins=50, alpha=0.7,
             label=f'Z (μ={stats["z"][0]:.4f}, σ²={stats["z"][1]:.4f})',
             color='red', edgecolor='maroon', histtype='step')
    
    plt.title(f'Atom {atom_id} Position Distribution (Initial-based Adjustment)')
    plt.xlabel('Position (Å)')
    plt.ylabel('Frequency')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(image_dir / f'atom_positions_{atom_id}.png', dpi=300)
    plt.close()

if __name__ == "__main__":
    input_dir = Path("atom_positions")
    
    if not input_dir.exists():
        raise FileNotFoundError(f"输入目录 {input_dir} 不存在")
    
    # 处理所有数据文件
    for file in input_dir.glob("atom_positions_*.dat"):
        print(f"正在处理: {file.name}")
        try:
            process_atom_file(file)
        except Exception as e:
            print(f"处理 {file.name} 时出错: {str(e)}")
            continue
    
    print("处理完成，结果保存在以下目录:")
    print(f"- 统计结果: {Path('calc_avg_msd').absolute()}")
    print(f"- 直方图: {Path('image').absolute()}")
