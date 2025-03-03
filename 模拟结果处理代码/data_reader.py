import os

def safe_read_file(file_path, read_function, *args, **kwargs):
    try:
        return read_function(file_path, *args, **kwargs)
    except FileNotFoundError:
        print(f"文件未找到: {file_path}")
    except Exception as e:
        print(f"读取文件 {file_path} 时出错: {e}")
    return None

def read_data(file_path):
    """
    读取 MSD 数据文件
    :param file_path: .dat 文件路径
    :return: (time, msd) 两个列表
    """
    time = []
    tot_msd = []
    with open(file_path, 'r') as file:
        for line in file:
            if line.startswith('#') or 'Time(fs)' in line:
                continue
            data = line.split()
            if len(data) < 5:
                continue  # 跳过不完整的行
            time.append(float(data[0]))
            tot_msd.append(float(data[4]))
    return time, tot_msd

def get_all_data_files(folder_path):
    """
    获取指定文件夹下所有 .dat 文件路径
    :param folder_path: 目录路径
    :return: 文件路径列表
    """
    return [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".dat")]
