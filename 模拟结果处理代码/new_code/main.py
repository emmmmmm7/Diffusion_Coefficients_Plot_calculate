# main.py
"""
主程序入口
根据配置选择处理模式
"""
import logging
from config import config_manager
from diffusion_processor import DiffusionProcessor
from pressure_processor import PressureProcessor
import os

def setup_logging():
    """配置统一日志系统"""
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    logging.basicConfig(
        level=config_manager.config["log_level"],
        format=log_format,
        handlers=[
            logging.FileHandler(os.path.join(config_manager.output_dir, "processing.log")),
            logging.StreamHandler()
        ]
    )

def main():
    setup_logging()
    
    try:
        config = config_manager.get_config()
        logging.info(f"启动处理模式: {config_manager.current_mode.upper()}")

        if config_manager.current_mode == "diffusion":
            processor = DiffusionProcessor(config)
        elif config_manager.current_mode == "pressure":
            processor = PressureProcessor(config)
        else:
            raise ValueError(f"未知处理模式: {config_manager.current_mode}")

        processor.run()
        logging.info("处理完成")

    except Exception as e:
        logging.error(f"处理失败: {str(e)}", exc_info=True)
    finally:
        logging.info("===== 程序结束 =====")

if __name__ == "__main__":
    main()