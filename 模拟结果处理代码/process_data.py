import os
import logging
import data_reader
import diffusion_calculator
import plotter

def get_fit_range_for_temperature(config_data, temperature):
    """
    获取指定温度组的拟合范围
    :param config_data: 从 config.json 加载的配置字典
    :param temperature: 当前温度（如 600K）
    :return: (fit_start, fit_end)
    """
    # print(config_data)
    if "fit_ranges" in config_data and temperature in config_data["fit_ranges"]:
        return config_data["fit_ranges"][temperature]["fit_start"], config_data["fit_ranges"][temperature]["fit_end"]
    else:
        raise ValueError(f"没有找到 {temperature} 的拟合范围")

def process_single_file(file_path, diffusion_results, data_dict, fit_params, temperature, fit_start, fit_end, config_data):
    """
    处理单个数据文件，计算扩散系数并保存结果
    :param temperature: 当前温度（用作文件命名）
    :param fit_start: 拟合的起始时间
    :param fit_end: 拟合的结束时间
    :param config_data: 配置字典，用于获取配置项
    """
    file_name = os.path.basename(file_path)
    # 使用温度前缀生成唯一键
    unique_key = f"{temperature}_{file_name}"
    
    result = data_reader.safe_read_file(file_path, data_reader.read_data, config_data["start_time_ps"], config_data["end_time_ps"])
    if result is not None:
        time, msd = result
    else:
        time, msd = [], []  # 避免解包错误
  
    if time and msd:
        # 将数据存入 data_dict 时也使用 unique_key
        data_dict[unique_key] = (time, msd)
        if config_data["ENABLE_FITTING"]:
            result = diffusion_calculator.compute_diffusion_coefficient(time, msd, fit_start, fit_end)
            if result:
                D, slope, intercept, r_squared = result
                # 判断 target_keyword 过滤
                target = config_data.get("target_keyword", "").lower().strip()
                if not target or target in file_name.lower():
                    diffusion_results[unique_key] = (D, r_squared, temperature)  # 将温度与结果一起保存
                    fit_params[unique_key] = (slope, intercept)
                    logging.info(f"{unique_key}: D = {D:.6e} m²/s, R² = {r_squared:.4f}")
                else:
                    logging.debug(f"文件 {file_name} 不包含目标关键字 '{target}'，跳过保存扩散系数。")
            else:
                logging.warning(f"文件 {file_name} 无法计算扩散系数")
    else:
        logging.warning(f"文件 {file_name} 数据为空或无法读取")


def process_temperature_folder(root_folder, output_dir, diffusion_results, fit_params, config_data):
    """
    处理某个温度组文件夹，遍历文件进行计算和绘图
    :param root_folder: 温度组文件夹路径
    :param output_dir: 输出目录
    :param config_data: 从 config.json 加载的配置字典
    """
    temperature = os.path.basename(root_folder)  # 使用文件夹名作为温度标识（如 600K）
    data_dict = {}  # 只包含当前温度的数据
    data_files = data_reader.get_all_data_files(root_folder)
    if not data_files:
        logging.error(f"{root_folder} 文件夹下没有找到 .dat 文件")
        return
    # print(config_data)
    # 获取拟合范围
    try:
        fit_start, fit_end = get_fit_range_for_temperature(config_data, temperature)
    except ValueError as e:
        logging.error(f"温度 {temperature} 的拟合范围加载失败: {e}")
        return

    # 处理每个文件
    for file_path in data_files:
        process_single_file(file_path, diffusion_results, data_dict, fit_params, temperature, fit_start, fit_end, config_data)

    # 确保每个温度的数据绘制在单独的图中
    output_img = os.path.join(output_dir, f"MSD_{temperature}.png")  # 使用温度作为文件名
    plotter.plot_msd(config_data, data_dict, fit_params if config_data["ENABLE_FITTING"] else None, output_img, config_data["target_keyword"], fit_start, fit_end)


def save_diffusion_results(results, output_file, append=False, config_data=None):
    """
    以 CSV 格式保存扩散系数计算结果，保存时根据关键字筛选
    :param results: { unique_key: (D, R², 温度) } 字典
    :param output_file: CSV 文件路径
    :param append: 是否追加到现有文件
    """
    import csv
    import os

    output_dir = os.path.dirname(output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # print(f"Results to save: {results}")

    mode = 'a' if append else 'w'
    with open(output_file, mode, newline='') as f:
        writer = csv.writer(f)
        if not append or os.stat(output_file).st_size == 0:
            writer.writerow(["Temperature", "Diffusion Coefficient (m²/s)", "R²"])  # CSV 头部
        for file, (D, r_squared, temperature) in results.items():
            writer.writerow([temperature, f"{D:.6e}", f"{r_squared:.4f}"])  # 确保数据格式正确
            logging.info(f"{temperature}已经成功写入")
    logging.info(f"扩散系数已保存至: {output_file}")

