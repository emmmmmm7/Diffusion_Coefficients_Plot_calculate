# MSD_Processor.py
"""
MSD计算模块 (VASPkit 格式兼容版)
功能：
1. 读取 VASP 的 XDATCAR 轨迹文件
2. 执行周期性边界条件去折叠 (Unwrap) - 自动修复跨边界断裂
3. 计算指定元素的 MSD (Mean Squared Displacement)
4. 输出完全兼容 VASPkit 格式的 .dat 文件
"""
import os
import logging
import numpy as np
import re

class MSDProcessor:
    def __init__(self, config):
        self.config = config
        self.diffusion_config = self.config.get_config()["diffusion"]
        self.output_dir = self.config.output_dir
        
    def _get_element_indices(self, species_line, counts_line, target_element):
        """解析 XDATCAR 头部，获取目标元素的原子索引范围"""
        species = species_line.strip().split()
        try:
            counts = [int(c) for c in counts_line.strip().split()]
        except ValueError:
            logging.error("无法解析原子数量行")
            return None

        if len(species) != len(counts):
            # 处理旧版 VASP 格式（缺少元素行）的情况
            logging.warning("XDATCAR 格式警告：元素名称与数量不匹配")
            if not species: 
                return None

        current_idx = 0
        target_range = None
        
        for sp, count in zip(species, counts):
            if sp.lower() == target_element.lower():
                target_range = (current_idx, current_idx + count)
                break
            current_idx += count
            
        return target_range

    def _parse_xdatcar(self, file_path):
        """解析 XDATCAR 文件，提取晶格和轨迹"""
        target_element = self.diffusion_config.get("target_element", "Li")
        
        with open(file_path, 'r') as f:
            # --- 读取 Header ---
            lines = [f.readline() for _ in range(7)]
            
            scale = float(lines[1])
            
            # 读取晶格矢量
            lat_vec = []
            for i in range(2, 5):
                lat_vec.append([float(x) for x in lines[i].split()])
            lattice_matrix = np.array(lat_vec) * scale
            
            # 解析元素和数量
            species_line = lines[5]
            counts_line = lines[6]
            
            # 简单检查格式
            if re.match(r'^\s*\d+', species_line):
                logging.error("检测到旧版 VASP XDATCAR (缺少元素名)，请检查文件。")
                return None, None

            idx_range = self._get_element_indices(species_line, counts_line, target_element)
            
            if not idx_range:
                logging.error(f"在 XDATCAR 中未找到元素: {target_element}")
                return None, None
            
            start_idx, end_idx = idx_range
            total_atoms_in_box = sum([int(c) for c in counts_line.split()])
            
            # --- 读取轨迹 ---
            # 读取剩余所有行
            all_lines = f.readlines()
            
        # 每一帧占用 (total_atoms + 1) 行 ("Direct configuration=..." + 原子坐标)
        lines_per_frame = total_atoms_in_box + 1
        num_frames = len(all_lines) // lines_per_frame
        
        if num_frames == 0:
            logging.warning("轨迹帧数为 0，请检查 XDATCAR 是否完整")
            return None, None

        logging.info(f"解析 XDATCAR: 提取 {target_element} (Index {start_idx}-{end_idx}), 共 {num_frames} 帧")
        
        trajectory = []
        
        # 循环提取每一帧中目标原子的坐标
        for i in range(num_frames):
            frame_start_line = i * lines_per_frame
            # 目标原子的行范围 (跳过 configuration 头行)
            atom_lines = all_lines[frame_start_line + 1 + start_idx : frame_start_line + 1 + end_idx]
            
            coords = []
            for line in atom_lines:
                coords.append([float(x) for x in line.split()[:3]])
            
            trajectory.append(coords)
            
        return lattice_matrix, np.array(trajectory)

    def _unwrap_trajectory(self, fractional_trajectory):
        """
        处理周期性边界条件 (Unwrap)
        算法：real_delta = diff - round(diff)
        """
        n_steps, n_atoms, dims = fractional_trajectory.shape
        unwrapped = np.zeros_like(fractional_trajectory)
        
        # 第一帧保持不变
        unwrapped[0] = fractional_trajectory[0]
        
        logging.info("正在进行 PBC Unwrap 处理 (去折叠)...")
        
        for t in range(1, n_steps):
            # 计算相邻帧的位移
            diff = fractional_trajectory[t] - fractional_trajectory[t-1]
            
            # 核心修正：如果位移超过 0.5，说明跨越了边界，减去 round(diff) 进行补偿
            # 例如：diff = 0.9 -> round = 1.0 -> real = -0.1 (向左移)
            real_delta = diff - np.round(diff)
            
            # 累积位置
            unwrapped[t] = unwrapped[t-1] + real_delta
            
        return unwrapped

    def _calculate_msd(self, unwrapped_frac, lattice_matrix):
        """计算各方向及总 MSD"""
        # 1. 分数坐标 -> 笛卡尔坐标 (Å)
        cartesian_traj = np.dot(unwrapped_frac, lattice_matrix)
        
        # 2. 计算相对于 t=0 的位移 r(t) - r(0)
        displacement = cartesian_traj - cartesian_traj[0]
        
        # 3. 计算平方位移
        squared_displacement = displacement ** 2
        
        # 4. 对所有同类原子取平均
        msd_xyz = np.mean(squared_displacement, axis=1) # shape (n_steps, 3)
        
        # 5. 计算总 MSD (x+y+z)
        msd_total = np.sum(msd_xyz, axis=1) # shape (n_steps,)
        
        return {
            'x': msd_xyz[:, 0],
            'y': msd_xyz[:, 1],
            'z': msd_xyz[:, 2],
            'total': msd_total
        }

    def _save_msd_file(self, time_array, msd_data, output_path):
        """
        保存为 .dat 文件，格式尽量模仿 VASPkit
        Columns: Time, X, Y, Z, Total, Sqrt(Total)
        """
        # 1. 计算 sqrt(MSD)
        sqrt_msd = np.sqrt(msd_data['total'])

        # 2. 准备 VASPkit 风格的 Header
        # 注意：这里手动加上 # 并设置 savetxt 的 comments=''，以精确控制 Header 格式
        header = "#Time(fs)    x-MSD(A^2)    y-MSD(A^2)    z-MSD(A^2)    tot-MSD(A^2)  sqrt(MSD)(A)"
        
        # 3. 组合数据列
        # 顺序：Time | X | Y | Z | Total | Sqrt
        data = np.column_stack((
            time_array,
            msd_data['x'],
            msd_data['y'],
            msd_data['z'],
            msd_data['total'],
            sqrt_msd
        ))
        
        # 4. 保存
        # fmt='%15.6E'：使用科学计数法，保留6位小数，总宽15字符，保证列对齐
        # 效果类似于: 1.000000E+01   4.500000E-02
        try:
            np.savetxt(output_path, data, header=header, fmt='%15.6E', comments='')
            logging.info(f"MSD 数据已保存 (VASPkit style): {output_path}")
        except Exception as e:
            logging.error(f"保存文件失败: {e}")

    def run(self):
        """执行 MSD 处理主流程"""
        logging.info(">>> 开始运行 MSDProcessor (Unwrap & Calculate) <<<")
        
        target_element = self.diffusion_config.get("target_element")
        if not target_element:
            logging.error("Config Error: 未指定 target_element (目标元素)")
            return

        # 获取时间步长参数
        # 关键：计算真实时间需要 POTIM * NBLOCK
        nblock_dt = self.diffusion_config.get("step_interval_fs", 1.0) 
        logging.info(f"使用时间步长 (POTIM*NBLOCK): {nblock_dt} fs")

        for root_folder in self.config.root_folder:
            xdatcar_path = os.path.join(root_folder, "XDATCAR")
            
            # 如果没有 XDATCAR，尝试查找类似文件 (可选)
            if not os.path.exists(xdatcar_path):
                # logging.warning(f"跳过: {os.path.basename(root_folder)} (未找到 XDATCAR)")
                continue
                
            logging.info(f"处理目录: {os.path.basename(root_folder)}")
            
            try:
                # 1. 解析
                lattice, traj = self._parse_xdatcar(xdatcar_path)
                if lattice is None or traj is None:
                    continue
                
                # 2. Unwrap (去折叠)
                unwrapped_traj = self._unwrap_trajectory(traj)
                
                # 3. 计算 MSD
                msd_results = self._calculate_msd(unwrapped_traj, lattice)
                
                # 4. 生成时间轴
                n_steps = len(unwrapped_traj)
                time_axis = np.arange(n_steps) * nblock_dt
                
                # 5. 保存结果
                output_filename = f"MSD_data_{target_element}.dat"
                output_file_path = os.path.join(root_folder, output_filename)
                
                self._save_msd_file(time_axis, msd_results, output_file_path)
                
            except Exception as e:
                logging.error(f"处理 {root_folder} 时发生错误: {e}", exc_info=True)

        logging.info("所有 MSD 计算完成。请检查生成的 .dat 文件。")