# ERR_plot_processor.py
"""
ERR数据绘图模块
处理ERR.csv数据并生成相关图表
"""
import os
import logging
import numpy as np
import matplotlib.pyplot as plt
import csv
import re

class ERRPlotProcessor:
    def __init__(self, config):
        self.config = config
        self.err_config = self.config.get_config().get("err_plot", {})
        self.data_dict = {}

    def _find_err_files(self):
        """
        在所有数据文件夹中查找ERR.csv文件
        :return: ERR.csv文件路径列表
        """
        err_files = []
        for root_folder in self.config.root_folder:
            for dirpath, _, filenames in os.walk(root_folder):
                for filename in filenames:
                    if filename.upper() == "ERR.CSV":
                        err_files.append(os.path.join(dirpath, filename))
        return err_files

    def _read_err_data(self, file_path):
        """
        读取ERR.csv数据文件
        :param file_path: ERR.csv文件路径
        :return: 包含nstep, rmse_energy, rmse_force, rmse_stress的字典
        """
        data = {
            'nstep': [],
            'rmse_energy': [],
            'rmse_force': [],
            'rmse_stress': []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                # 跳过可能的BOM标记
                line = file.readline()
                if line.startswith('\ufeff'):
                    line = line[1:]
                
                # 检查列名
                reader = csv.reader([line] + file.readlines())
                headers = next(reader)
                
                # 查找各列索引
                nstep_idx = -1
                rmse_energy_idx = -1
                rmse_force_idx = -1
                rmse_stress_idx = -1
                
                for i, header in enumerate(headers):
                    header_lower = header.lower()
                    if 'nstep' in header_lower:
                        nstep_idx = i
                    elif 'rmse_energy' in header_lower:
                        rmse_energy_idx = i
                    elif 'rmse_force' in header_lower:
                        rmse_force_idx = i
                    elif 'rmse_stress' in header_lower:
                        rmse_stress_idx = i
                
                # 读取数据
                for row in reader:
                    if len(row) < max(nstep_idx, rmse_energy_idx, rmse_force_idx, rmse_stress_idx) + 1:
                        continue
                    
                    try:
                        nstep_val = float(row[nstep_idx]) if nstep_idx >= 0 else None
                        rmse_energy_val = float(row[rmse_energy_idx]) if rmse_energy_idx >= 0 else None
                        rmse_force_val = float(row[rmse_force_idx]) if rmse_force_idx >= 0 else None
                        rmse_stress_val = float(row[rmse_stress_idx]) if rmse_stress_idx >= 0 else None
                        
                        if nstep_val is not None:
                            data['nstep'].append(nstep_val)
                            data['rmse_energy'].append(rmse_energy_val)
                            data['rmse_force'].append(rmse_force_val)
                            data['rmse_stress'].append(rmse_stress_val)
                    except (ValueError, TypeError):
                        continue
                        
        except Exception as e:
            logging.error(f"读取ERR文件 {file_path} 时出错: {e}")
        
        return data

    def _plot_err_data(self, data, save_path=None, folder_name=""):
        """
        绘制ERR数据曲线
        :param data: 包含nstep和三个rmse值的字典
        :param save_path: 图片保存路径
        :param folder_name: 文件夹名称，用于图例
        """
        if not data['nstep']:
            logging.warning(f"文件夹 {folder_name} 中没有有效数据")
            return
            
        plt.figure(figsize=(12, 8))
        
        # 设置全局字体
        plt.rcParams.update({
            'font.family': 'serif',
            'font.serif': ['Times New Roman'],
            'mathtext.fontset': 'stix'
        })
        
        # 绘制三条曲线
        line_energy, = plt.plot(data['nstep'], data['rmse_energy'], 
                               label='RMSE_Energy', linewidth=2, color='#1f77b4', marker='o', markersize=7)
        line_force, = plt.plot(data['nstep'], data['rmse_force'], 
                              label='RMSE_Force', linewidth=2, color='#ff7f0e', marker='o', markersize=7)
        line_stress, = plt.plot(data['nstep'], data['rmse_stress'], 
                               label='RMSE_Stress', linewidth=2, color='#2ca02c', marker='o', markersize=7)
        
        # 设置坐标轴
        plt.xlabel('Time step', fontsize=14)
        plt.ylabel('RMSE(eV/Å)', fontsize=14)

        # 调整坐标轴
        min_nstep = min(data['nstep'])
        max_nstep = max(data['nstep'])
        plt.xlim(min_nstep-1000, max_nstep+1000)
        plt.ylim(-0.05, 1)

        plt.gca().tick_params(direction='in')
        
        # 设置对数坐标轴（由于数据范围可能很大）
        # plt.xscale('log')
        # plt.yscale('log')
        
        # 添加网格
        # plt.grid(True, which="both", ls="-", alpha=0.2)
        
        # 添加图例
        plt.legend(loc='best', fontsize=12, frameon=True, edgecolor='none', framealpha=0)
        
        # 添加标题
        # plt.title(f'RMSE vs nstep - {folder_name}', fontsize=16)
        
        # 调整布局
        plt.tight_layout()
        
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logging.info(f"ERR图像已保存: {save_path}")
            plt.close()
        else:
            plt.show()

    def run(self):
        """执行ERR数据处理流程"""
        logging.info("开始处理ERR数据")
        
        # 查找所有ERR.csv文件
        err_files = self._find_err_files()
        
        if not err_files:
            logging.warning("未找到任何ERR.csv文件")
            return
            
        logging.info(f"找到 {len(err_files)} 个ERR.csv文件")
        
        # 处理每个ERR文件
        for err_file in err_files:
            # 获取文件夹名称用于保存和标识
            folder_name = os.path.basename(os.path.dirname(err_file))
            logging.info(f"处理ERR文件: {err_file} (文件夹: {folder_name})")
            
            # 读取数据
            data = self._read_err_data(err_file)
            
            if data['nstep']:
                # 绘制图像
                output_img = os.path.join(self.config.output_dir, f"ERR_{folder_name}.png")
                self._plot_err_data(data, output_img, folder_name)
                
                # 保存数据到字典（可选）
                self.data_dict[folder_name] = data
            else:
                logging.warning(f"文件 {err_file} 中没有有效数据")
        
        logging.info("ERR数据处理完成")