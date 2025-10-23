#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志系统开关演示脚本
展示如何使用环境变量控制日志输出
"""

import os
import sys

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    print("=" * 60)
    print("OpenList 日志系统演示")
    print("=" * 60)

    # 显示当前环境变量状态
    log_level = os.getenv('OPENLIST_LOG_LEVEL')
    console_level = os.getenv('OPENLIST_CONSOLE_LEVEL')

    print(f"当前环境变量:")
    print(f"  OPENLIST_LOG_LEVEL = {log_level or '未设置'}")
    print(f"  OPENLIST_CONSOLE_LEVEL = {console_level or '未设置'}")
    print()

    # 导入并设置日志系统
    from core.logger import setup_logger, get_logger
    logger = setup_logger()

    # 检查日志系统状态
    print("日志系统状态:")
    print(f"  DEBUG 模式: {'启用' if logger.isEnabledFor(10) else '禁用'}")
    print(f"  INFO 模式: {'启用' if logger.isEnabledFor(20) else '禁用'}")
    print(f"  WARNING 模式: {'启用' if logger.isEnabledFor(30) else '禁用'}")
    print(f"  ERROR 模式: {'启用' if logger.isEnabledFor(40) else '禁用'}")
    print()

    # 尝试记录各种级别的日志
    print("尝试记录日志:")
    logger.debug("这是一条 DEBUG 级别的日志 - 详细调试信息")
    logger.info("这是一条 INFO 级别的日志 - 一般信息")
    logger.warning("这是一条 WARNING 级别的日志 - 警告信息")
    logger.error("这是一条 ERROR 级别的日志 - 错误信息")
    logger.critical("这是一条 CRITICAL 级别的日志 - 严重错误信息")
    print()

    print("=" * 60)
    print("使用说明:")
    print()
    print("1. 默认状态（不设置环境变量）:")
    print("   - 所有日志输出都被禁用")
    print("   - 应用程序安静运行，不产生日志文件")
    print()
    print("2. 启用完整日志:")
    print("   setx OPENLIST_LOG_LEVEL on")
    print("   setx OPENLIST_CONSOLE_LEVEL DEBUG")
    print("   - 重启命令行或应用程序后生效")
    print("   - 输出 DEBUG 级别及以上的所有日志到文件")
    print("   - 在控制台显示 DEBUG 级别及以上的日志")
    print()
    print("3. 关闭日志:")
    print("   setx OPENLIST_LOG_LEVEL off")
    print("   - 或直接删除环境变量")
    print()
    print("4. 自定义日志级别:")
    print("   setx OPENLIST_LOG_LEVEL WARNING    # 只记录 WARNING 及以上")
    print("   setx OPENLIST_LOG_LEVEL ERROR      # 只记录 ERROR 及以上")
    print("   setx OPENLIST_CONSOLE_LEVEL INFO   # 控制台显示 INFO 及以上")
    print()
    print("日志文件位置: logs/debug_YYYYMMDD.log")
    print("=" * 60)

if __name__ == "__main__":
    main()