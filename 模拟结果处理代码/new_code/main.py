# main.py
"""
主程序入口
根据配置选择处理模式
"""
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
from config import config_manager
from diffusion_processor import DiffusionProcessor
from pressure_processor import PressureProcessor
import time
import os
import matplotlib

class ProcessorBase:
    """处理器基类"""
    def __init__(self):
        self.setup_logging()
        logging.info("程序启动，开始运行数据处理流程。按 Ctrl+C 结束程序。")
        logging.info(f"加载字体")
        self.setup_fonts()
        logging.info(f"字体设置成功")
        try:
            self.config = config_manager.get_config()
            logging.info(f"加载配置文件成功")
            logging.info(f"数据目录: {config_manager.data_folder}")
            logging.info(f"输出目录: {config_manager.output_dir }")
        except Exception as e:
            logging.error(f"处理失败: {str(e)}", exc_info=True)
    
    def ensure_output_dir(self, output_path):
        """
        确保输出目录存在，如果不存在则创建。
        """
        if not os.path.exists(output_path):
            os.makedirs(output_path)

    def setup_logging(self):
        """配置统一日志系统"""
        log_format = "%(asctime)s - %(levelname)s - %(message)s"
        self.ensure_output_dir(config_manager.output_dir)

        # 清空之前可能存在的 root logger 的 handler
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        logging.basicConfig(
            level=config_manager.config["log_level"],
            format=log_format,
            handlers=[
                logging.FileHandler(os.path.join(config_manager.output_dir, "processing.log")),
                logging.StreamHandler()
            ]
        )
        # 直接关闭fontTools的日志
        logging.getLogger('fontTools').setLevel(logging.WARNING)

    def setup_fonts(self):
        """设置全局字体（适用于 matplotlib）"""
        # 示例：使用系统中的思源黑体（或微软雅黑）
        font_paths_to_try = [
            "/System/Library/Fonts/STHeiti Medium.ttc",  # macOS 默认中文字体
            "/System/Library/Fonts/PingFang.ttc",
            "/Library/Fonts/SourceHanSansSC-Regular.otf",  # 思源黑体（Source Han Sans）
            "/Library/Fonts/Microsoft YaHei.ttf"
        ]
        
        for path in font_paths_to_try:
            if os.path.exists(path):
                matplotlib.rcParams['font.sans-serif'] = [matplotlib.font_manager.FontProperties(fname=path).get_name()]
                matplotlib.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
                logging.info(f"中文字体设置为: {matplotlib.rcParams['font.sans-serif'][0]}")
                return

        logging.info("未找到预设字体，使用默认字体。")

    
    def run(self):
        """执行处理流程"""
        if config_manager.current_mode == "diffusion":
            logging.info(f"启动处理模式: {config_manager.current_mode.upper()}")
            MainProcessor = DiffusionProcessor(config_manager)
        elif config_manager.current_mode == "pressure":
            logging.info(f"启动处理模式: {config_manager.current_mode.upper()}")
            MainProcessor = PressureProcessor(config_manager)
        else:
            raise ValueError(f"未知处理模式: {config_manager.current_mode}")
        MainProcessor.run()

def main():
    try:
        pipeline = ProcessorBase()
        pipeline.run()
        last_modified = os.path.getmtime(config_manager.config_path)
        
        # 配置热重载监控
        logging.info("进入配置文件监控模式 (Ctrl+C退出)...")
        while True:
            time.sleep(2)
            current_mtime = os.path.getmtime(config_manager.config_path)
            if current_mtime > last_modified:
                logging.info("检测到配置文件变更，重新加载配置...")
                config_manager.reload_config()
                pipeline = ProcessorBase()
                pipeline.run()
                last_modified = current_mtime
                logging.info("进入配置文件监控模式 (Ctrl+C退出)...")
                
    except KeyboardInterrupt:
        logging.info("用户中断程序执行")
    except Exception as e:
        logging.error(f"程序运行异常: {str(e)}")

if __name__ == "__main__":
    main()