"""Logging system for boss-hr-recruiter skill."""

import logging
import sys
from datetime import datetime
from pathlib import Path


class SkillLogger:
    """结构化日志系统."""

    def __init__(self, runtime_dir: str, phase: str = "main"):
        """初始化日志系统.

        Args:
            runtime_dir: 运行时目录
            phase: 阶段名称 (main, phase1, phase2, phase3)
        """
        self.runtime_dir = Path(runtime_dir)
        self.phase = phase

        # 创建logs目录
        self.log_dir = self.runtime_dir / "logs"
        self.log_dir.mkdir(exist_ok=True)

        # 配置logger
        self.logger = logging.getLogger(f"boss-hr-recruiter.{phase}")
        self.logger.setLevel(logging.DEBUG)

        # 清空已有的handler
        self.logger.handlers.clear()

        # 文件handler
        log_file = self.log_dir / f"{phase}-{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)

        # 控制台handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        # 格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def debug(self, msg: str, *args, **kwargs):
        """调试日志."""
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        """信息日志."""
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        """警告日志."""
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        """错误日志."""
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        """严重错误日志."""
        self.logger.critical(msg, *args, **kwargs)
