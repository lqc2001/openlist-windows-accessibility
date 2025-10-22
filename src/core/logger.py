#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志系统模块
提供调试级别的详细日志记录功能
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler


def setup_logger():
    """设置日志系统"""
    # 检查环境变量是否开启日志（默认关闭）
    log_level = os.environ.get('OPENLIST_LOG_LEVEL', '').upper()

    # 创建日志记录器
    logger = logging.getLogger("OpenListManager")

    # 清除现有处理器以避免重复添加和缓存问题
    logger.handlers.clear()

    if log_level != 'ON':
        # 默认创建空的日志记录器，不输出任何日志
        logger.setLevel(logging.CRITICAL + 1)  # 设置比最高级别还高的级别，确保不输出任何日志
        # 添加空的处理器，防止日志系统警告
        logger.addHandler(logging.NullHandler())
        return logger

    # 确保日志目录存在
    os.makedirs("logs", exist_ok=True)

    logger.setLevel(logging.DEBUG)  # 调试级别，记录详细信息

    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 创建按日期滚动的文件处理器
    log_file = f"logs/debug_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # 创建控制台处理器（仅在开发环境显示）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # 控制台只显示警告和错误
    console_handler.setFormatter(formatter)

    # 添加处理器到日志记录器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info("日志系统初始化完成")
    return logger


def get_logger():
    """获取日志记录器实例"""
    return logging.getLogger("OpenListManager")