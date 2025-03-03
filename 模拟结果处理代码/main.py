import logging
import os
import time
import config
import process_data
import plot_diffusion

def run_pipeline():
    """
    执行一次完整的处理流程：
      - 加载配置
      - 处理各温度组数据，保存扩散系数 CSV
      - 根据 CSV 绘制 Diffusion Coefficient 图
    """
    # 从 config.json 加载配置
    config_data = config.load_config()

    # 获取路径配置
    data_folder = config.get_data_folder()
    output_file = config.get_output_file()  # CSV 文件路径

    # 创建输出目录
    output_dir = os.path.join(data_folder, "output")
    os.makedirs(output_dir, exist_ok=True)

    # 初始化结果存储字典
    diffusion_results = {}
    fit_params = {}

    # 获取所有温度组目录，排除 output 文件夹
    root_folders = [
        os.path.join(data_folder, subdir)
        for subdir in os.listdir(data_folder)
        if os.path.isdir(os.path.join(data_folder, subdir)) and subdir.lower() != "output"
    ]

    logging.info(f"发现 {len(root_folders)} 个温度组: {', '.join([os.path.basename(folder) for folder in root_folders])}")

    # 处理每个温度组
    for root_folder in root_folders:
        temperature = os.path.basename(root_folder)
        logging.info(f"开始处理温度组: {temperature}")
        try:
            process_data.process_temperature_folder(root_folder, output_dir, diffusion_results, fit_params, config_data)
            logging.info(f"处理完成: {temperature}")
        except Exception as e:
            logging.error(f"处理温度组 {temperature} 时发生错误: {e}")

    # 保存扩散系数结果到 CSV 文件
    try:
        process_data.save_diffusion_results(diffusion_results, output_file, config_data=config_data)
        logging.info(f"扩散系数结果已保存至 {output_file}")
    except Exception as e:
        logging.error(f"保存扩散系数结果时发生错误: {e}")

    # 自动生成 Diffusion Coefficient 图（纵轴为 log(D) 或 log₁₀(D)；这里假设使用 log(D) 的话 D0 = exp(intercept)，
    # 如果使用 log₁₀(D) 则 D0 = 10^(intercept)；请根据实际需要选择）
    target_keyword = config_data.get("target_keyword", "").strip()
    if target_keyword:
        image_filename = f"diffusion_coefficient_vs_{target_keyword}.png"
    else:
        image_filename = "diffusion_coefficient_vs_temperature.png"
    plot_image_path = os.path.join(output_dir, image_filename)

    try:
        plot_diffusion.plot_diffusion_coefficients(output_file, plot_image_path)
        logging.info(f"扩散系数图已保存至 {plot_image_path}")
    except Exception as e:
        logging.error(f"生成扩散系数图时发生错误: {e}")

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    # 通过 config.py 获取 config.json 的路径（转换为绝对路径）
    config_file = os.path.abspath(config.CONFIG_FILE_PATH)
    logging.info(f"使用配置文件: {config_file}")
    
    # 获取 config.json 文件的最后修改时间
    last_mtime = os.path.getmtime(config_file) if os.path.exists(config_file) else None

    logging.info("程序启动，开始运行数据处理流程。按 Ctrl+C 结束程序。")
    
    # 初次执行数据处理流程
    run_pipeline()

    check_interval = 10  # 每隔10秒检查一次配置文件是否修改
    while True:
        try:
            time.sleep(check_interval)
            if os.path.exists(config_file):
                current_mtime = os.path.getmtime(config_file)
                logging.debug(f"当前 config.json 修改时间: {current_mtime}, 上次记录: {last_mtime}")
                if last_mtime is None or current_mtime > last_mtime:
                    logging.info("检测到 config.json 文件修改，重新运行数据处理流程...")
                    run_pipeline()
                    last_mtime = current_mtime
                else:
                    logging.debug("未检测到 config.json 修改。")
            else:
                logging.warning("config.json 文件不存在。")
        except KeyboardInterrupt:
            logging.info("收到退出信号，程序终止。")
            break
        except Exception as e:
            logging.error(f"监测过程中发生错误: {e}")

if __name__ == "__main__":
    main()
