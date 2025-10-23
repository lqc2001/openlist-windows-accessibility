#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志系统模块
默认关闭日志输出，只有设置环境变量 OPENLIST_LOG_LEVEL=on 才启用完整日志记录
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler


def _parse_level(env_value: str, default_level: int) -> int:
    """将环境变量解析为日志等级；支持 OFF 关闭日志。"""
    if not env_value:
        return default_level

    value = env_value.strip().upper()
    if value in {"OFF", "NONE", "DISABLE", "DISABLED"}:
        return logging.NOTSET

    # 特殊处理：当设置为 ON 时启用完整日志（DEBUG级别）
    if value == "ON":
        return logging.DEBUG

    return getattr(logging, value, default_level)


def setup_logger():
    """设置日志系统"""
    logger = logging.getLogger("OpenListManager")

    # 如果已经有处理器，就沿用之前的配置
    if logger.handlers:
        return logger

    log_level_env = os.getenv("OPENLIST_LOG_LEVEL")
    console_level_env = os.getenv("OPENLIST_CONSOLE_LEVEL")

    # 默认完全关闭日志（NOTSET），只有设置 OPENLIST_LOG_LEVEL=on 才启用
    file_level = _parse_level(log_level_env, logging.NOTSET)
    console_level = _parse_level(console_level_env, logging.NOTSET)

    # 如果日志被完全禁用，直接禁用整个日志系统
    if file_level == logging.NOTSET and console_level == logging.NOTSET:
        logging.disable(logging.CRITICAL)
        return logger

    logger.setLevel(min(level for level in [file_level, console_level] if level != logging.NOTSET) or logging.DEBUG)

    # 确保日志目录存在（仅当文件日志启用时）
    if file_level != logging.NOTSET:
        os.makedirs("logs", exist_ok=True)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    if file_level != logging.NOTSET:
        log_file = f"logs/debug_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if console_level != logging.NOTSET:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if logger.isEnabledFor(logging.INFO):
        logger.info("日志系统初始化完成")

    return logger


def get_logger():
    """获取日志记录器实例"""
    return logging.getLogger("OpenListManager")
