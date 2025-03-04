import os

def safe_read_file(file_path, read_function, *args, **kwargs):
    try:
        return read_function(file_path, *args, **kwargs)
    except FileNotFoundError:
        print(f"文件未找到: {file_path}")
    except Exception as e:
        print(f"读取文件 {file_path} 时出错: {e}")
    return None

def read_data(file_path, start_time_ps=20, end_time_ps=30):
    """
    读取 MSD 数据文件
    :param file_path: .dat 文件路径
    :return: (time, msd) 两个列表
    :param start_time_ps: 起始时间（皮秒）
    :param end_time_ps: 结束时间（皮秒）
    """
    time = []
    tot_msd = []

    # 转换为fs进行比较
    start_fs = start_time_ps * 1000
    end_fs = end_time_ps * 1000

    with open(file_path, 'r') as file:
        for line in file:
            if line.startswith('#') or 'Time(fs)' in line:
                continue
            data = line.split()
            if len(data) < 5:
                continue  # 跳过不完整的行
            time_fs = float(data[0])
            if start_fs <= time_fs <= end_fs:  # 新增过滤条件
                time.append(time_fs / 1000)  # 转换为皮秒
                tot_msd.append(float(data[4]))
    return time, tot_msd

def get_all_data_files(folder_path):
    """
    获取指定文件夹下所有 .dat 文件路径
    :param folder_path: 目录路径
    :return: 文件路径列表
    """
    return [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".dat")]
