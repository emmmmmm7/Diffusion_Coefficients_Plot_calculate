import matplotlib.pyplot as plt
import os

def read_data(file_path):
    """Reads time and total MSD data from a .dat file."""
    time = []
    tot_msd = []
    try:
        with open(file_path, 'r') as file:
            for line in file:
                if line.startswith('#') or 'Time(fs)' in line:
                    continue
                data = line.split()
                if len(data) < 5:
                    continue  # Skip lines that don't have enough data
                time.append(float(data[0]))
                tot_msd.append(float(data[4]))
    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except Exception as e:
        print(f"An error occurred while reading {file_path}: {e}")
    return time, tot_msd

def plot_data(data_dict):
    """Plots data from multiple .dat files on the same figure."""
    plt.figure(figsize=(10, 6))
    
    for file_name, (time, tot_msd) in data_dict.items():
        plt.plot(time, tot_msd, linestyle='-', linewidth=1, label=file_name)
    
    plt.xlabel('Time (fs)')
    plt.ylabel('Total MSD (A^2)')
    plt.legend(loc='best')
    plt.title('Time vs Total MSD')
    plt.grid(True)
    plt.gca().tick_params(direction='in')
    plt.show()

def main():
    folder_path = '/Users/rrw/Documents/postgraduate/矿物年代学/扩散系数模拟相关/扩散/取代位/Ti/600K/'  # Update this path
    
    data_dict = {}
    
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.dat'):
            file_path = os.path.join(folder_path, file_name)
            time, tot_msd = read_data(file_path)
            if time and tot_msd:
                data_dict[file_name] = (time, tot_msd)
    
    if data_dict:
        plot_data(data_dict)
    else:
        print("No valid .dat files found in the specified directory.")

if __name__ == "__main__":
    main()
