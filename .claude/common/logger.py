#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用日志模块
"""

import os
import sys
import traceback
from datetime import datetime
from pathlib import Path


def log(message: str, level: str = "INFO"):
    """
    记录日志到文件并输出到控制台

    Args:
        message: 日志消息
        level: 日志级别 (INFO/WARNING/ERROR/DEBUG)
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] [{level}] {message}"

    # 输出到控制台
    print(formatted)

    # 写入日志文件（按年滚动）
    try:
        log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        # 按年生成日志文件名，如 app_2026.log
        year = datetime.now().strftime("%Y")
        log_file = log_dir / f"app_{year}.log"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(formatted + '\n')
    except Exception as e:
        print(f"写入日志失败: {e}", file=sys.stderr)


def info(message: str):
    """记录 INFO 日志"""
    log(message, "INFO")


def warning(message: str):
    """记录 WARNING 日志"""
    log(message, "WARNING")


def error(message: str):
    """记录 ERROR 日志"""
    log(message, "ERROR")


def debug(message: str):
    """记录 DEBUG 日志"""
    log(message, "DEBUG")


if __name__ == "__main__":
    info("测试 INFO 日志")
    warning("测试 WARNING 日志")
    error("测试 ERROR 日志")
    debug("测试 DEBUG 日志")
