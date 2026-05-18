#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志配置模块

自动生成时间: 2026-02-05 09:31:57

功能：统一配置运行态代码的日志输出
- 控制台输出：INFO级别
- 文件输出：DEBUG级别（包含详细调试信息）
"""

import logging
from pathlib import Path
from datetime import datetime


def setup_logging(log_dir: str = "logs", log_prefix: str = "runtime") -> Path:
    """配置日志系统

    Args:
        log_dir: 日志目录路径（默认：logs）
        log_prefix: 日志文件名前缀（默认：runtime）

    Returns:
        日志文件路径

    配置说明：
        - 控制台：INFO级别，简洁格式
        - 文件：DEBUG级别，详细格式（包含模块名）
    """
    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # 创建日志文件名（带时间戳）
    log_filename = log_path / f"{log_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # 设置为最低级别，由各个handler控制

    # 清除已有的handlers（避免重复配置）
    root_logger.handlers.clear()

    # ========================================================================
    # 控制台处理器（INFO级别）
    # ========================================================================
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # ========================================================================
    # 文件处理器（DEBUG级别）
    # ========================================================================
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # 记录日志配置信息
    logger = logging.getLogger(__name__)
    logger.info(f"日志系统已初始化")
    logger.info(f"日志文件: {log_filename}")
    logger.debug(f"控制台日志级别: INFO")
    logger.debug(f"文件日志级别: DEBUG")

    return log_filename


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的logger

    Args:
        name: logger名称（通常使用 __name__）

    Returns:
        配置好的logger实例
    """
    return logging.getLogger(name)