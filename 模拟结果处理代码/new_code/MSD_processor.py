# MSD_Processor.py
"""
MSD计算模块 (VASPkit 格式兼容版 + 批量处理模式)
功能：
1. 读取 VASP 的 XDATCAR 轨迹文件
2. 自动解析元素列表
3. 若 target_element="all"，则分别计算每种元素的 MSD 并输出独立文件
4. 执行 PBC Unwrap (去折叠)
5. 输出完全兼容 VASPkit 格式的 .dat 文件
"""
import os
import logging
import numpy as np
import re

class MSDProcessor:
    def __init__(self, config):
        self.config = config
        self.MSD_config = self.config.get_config()["MSD_plot"]
        self.output_dir = self.config.output_dir
        
    def _parse_xdatcar_metadata(self, lines):
        """
        解析 XDATCAR 头部信息
        :param lines: 文件的所有行
        :return: (lattice_matrix, element_ranges, total_atoms)
        """
        # 1. 读取晶格常数 (Lines 2-5)
        scale = float(lines[1])
        lat_vec = []
        for i in range(2, 5):
            lat_vec.append([float(x) for x in lines[i].split()])
        lattice_matrix = np.array(lat_vec) * scale
        
        # 2. 读取元素和数量 (Lines 6-7)
        species_line = lines[5]
        counts_line = lines[6]
        
        species = species_line.strip().split()
        try:
            counts = [int(c) for c in counts_line.strip().split()]
        except ValueError:
            # 尝试处理旧版 VASP (没有元素名行)
            if re.match(r'^\s*\d+', species_line):
                logging.error("检测到旧版 VASP 格式（缺失元素名行），无法自动支持 'all' 模式。")
                return None, None, None
            raise ValueError("无法解析原子数量")

        if len(species) != len(counts):
            logging.error(f"XDATCAR 格式错误：元素种类({len(species)})与数量({len(counts)})不匹配")
            return None, None, None

        # 3. 构建元素索引范围字典
        # 格式: {'Li': (0, 10), 'P': (10, 16), ...}
        element_ranges = {}
        current_idx = 0
        for sp, count in zip(species, counts):
            element_ranges[sp] = (current_idx, current_idx + count)
            current_idx += count
            
        total_atoms = current_idx
        return lattice_matrix, element_ranges, total_atoms

    def _extract_trajectory(self, all_lines, start_idx, end_idx, total_atoms):
        """
        从内存中的所有行提取特定原子的轨迹
        """
        # 每一帧占用行数 = "Direct config..." + 所有原子坐标
        lines_per_frame = total_atoms + 1
        num_frames = len(all_lines) // lines_per_frame
        
        if num_frames == 0:
            return None

        trajectory = []
        
        # 循环提取每一帧
        for i in range(num_frames):
            frame_start_line = i * lines_per_frame
            # 计算目标原子在当前帧内的绝对行号
            # frame_start (Header) + 1 (Skip Header) + start_idx
            lines_slice = all_lines[frame_start_line + 1 + start_idx : frame_start_line + 1 + end_idx]
            
            coords = []
            for line in lines_slice:
                coords.append([float(x) for x in line.split()[:3]])
            trajectory.append(coords)
            
        return np.array(trajectory)

    def _unwrap_trajectory(self, fractional_trajectory):
        """
        处理周期性边界条件 (Unwrap)
        算法：real_delta = diff - round(diff)
        """
        n_steps, n_atoms, dims = fractional_trajectory.shape
        unwrapped = np.zeros_like(fractional_trajectory)
        unwrapped[0] = fractional_trajectory[0]
        
        # logging.debug("正在进行 PBC Unwrap 处理...")
        
        for t in range(1, n_steps):
            diff = fractional_trajectory[t] - fractional_trajectory[t-1]
            real_delta = diff - np.round(diff)
            unwrapped[t] = unwrapped[t-1] + real_delta
            
        return unwrapped

    def _calculate_msd(self, unwrapped_frac, lattice_matrix):
        """计算各方向及总 MSD"""
        # 1. 转换坐标 (Fractional -> Cartesian)
        cartesian_traj = np.dot(unwrapped_frac, lattice_matrix)
        
        # 2. 计算位移 r(t) - r(0)
        displacement = cartesian_traj - cartesian_traj[0]
        
        # 3. 平方
        squared_displacement = displacement ** 2
        
        # 4. 对原子求平均
        msd_xyz = np.mean(squared_displacement, axis=1) # (steps, 3)
        
        # 5. 求和
        msd_total = np.sum(msd_xyz, axis=1) # (steps,)
        
        return {
            'x': msd_xyz[:, 0],
            'y': msd_xyz[:, 1],
            'z': msd_xyz[:, 2],
            'total': msd_total
        }

    def _save_msd_file(self, time_array, msd_data, output_path):
        """保存为 VASPkit 兼容格式"""
        sqrt_msd = np.sqrt(msd_data['total'])
        header = "#Time(fs)    x-MSD(A^2)    y-MSD(A^2)    z-MSD(A^2)    tot-MSD(A^2)  sqrt(MSD)(A)"
        
        data = np.column_stack((
            time_array,
            msd_data['x'],
            msd_data['y'],
            msd_data['z'],
            msd_data['total'],
            sqrt_msd
        ))
        
        try:
            np.savetxt(output_path, data, header=header, fmt='%15.6E', comments='')
            logging.info(f"  -> 已保存: {os.path.basename(output_path)}")
        except Exception as e:
            logging.error(f"保存失败: {e}")

    def run(self):
        """主流程"""
        logging.info(">>> 开始运行 MSDProcessor (批量元素处理模式) <<<")
        
        target_config = self.MSD_config.get("target_element", "all").strip()
        nblock_dt = self.MSD_config.get("step_interval_fs", 1.0)
        logging.info(f"时间步长设置: {nblock_dt} fs")

        for root_folder in self.config.root_folder:
            xdatcar_path = os.path.join(root_folder, "XDATCAR")
            
            if not os.path.exists(xdatcar_path):
                logging.warning(f"未找到 XDATCAR 文件: {xdatcar_path}，跳过该文件夹。")
                continue
                
            logging.info(f"读取文件: {os.path.join(os.path.basename(root_folder), 'XDATCAR')}")
            
            try:
                # 1. 一次性读取文件所有行（避免重复IO）
                with open(xdatcar_path, 'r') as f:
                    # 先读 header 部分用于解析
                    header_lines = [f.readline() for _ in range(7)]
                    # 读剩余所有内容
                    body_lines = f.readlines()
                    
                # 组合所有行用于后续处理 (虽然这里内存占用稍微多一点，但处理方便)
                all_lines = header_lines + body_lines
                
                # 2. 解析元数据
                lattice, element_ranges, total_atoms = self._parse_xdatcar_metadata(all_lines)
                if lattice is None:
                    continue

                # 3. 确定要处理的元素列表
                elements_to_process = []
                
                if target_config.lower() == "all":
                    # 处理所有存在的元素
                    elements_to_process = list(element_ranges.keys())
                    logging.info(f"检测到元素: {', '.join(elements_to_process)}，将分别进行处理。")
                else:
                    # 处理指定元素
                    # 简单的模糊匹配查找 (忽略大小写)
                    found = False
                    for key in element_ranges.keys():
                        if key.lower() == target_config.lower():
                            elements_to_process = [key]
                            found = True
                            break
                    if not found:
                        logging.warning(f"元素 {target_config} 不在 XDATCAR 中 ({list(element_ranges.keys())})")
                        continue

                # 4. 循环处理每种元素
                for element in elements_to_process:
                    start_idx, end_idx = element_ranges[element]
                    atom_count = end_idx - start_idx
                    
                    logging.info(f"正在处理元素: {element} (原子数: {atom_count})")
                    
                    # 4.1 提取
                    traj = self._extract_trajectory(body_lines, start_idx, end_idx, total_atoms)
                    if traj is None:
                        continue
                        
                    # 4.2 Unwrap
                    unwrapped_traj = self._unwrap_trajectory(traj)
                    
                    # 4.3 MSD 计算
                    msd_results = self._calculate_msd(unwrapped_traj, lattice)
                    
                    # 4.4 生成时间轴
                    n_steps = len(unwrapped_traj)
                    time_axis = np.arange(n_steps) * nblock_dt
                    
                    # 4.5 保存 (文件名: MSD-元素名.dat)
                    output_filename = f"MSD-{element}.dat"
                    output_file_path = os.path.join(root_folder, output_filename)
                    
                    self._save_msd_file(time_axis, msd_results, output_file_path)
                    
            except Exception as e:
                logging.error(f"处理 {root_folder} 时发生错误: {e}", exc_info=True)

        logging.info("所有 MSD 处理任务完成。")