#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
版本信息管理
统一管理软件版本号和相关信息
"""

# 版本号 - 采用语义化版本控制 (主版本.次版本.修订版本)
# - 主版本：重大功能更新或不兼容的更改 (1.0.0 -> 2.0.0)
# - 次版本：新功能添加，保持向后兼容 (1.0.0 -> 1.1.0)
# - 修订版本：bug修复和小改进 (1.0.0 -> 1.0.1)
VERSION = "1.2.0"

# 软件信息
SOFTWARE_NAME = "OpenList管理器"
DEVELOPER = "扶苏@glm-4.6"
COMPANY = "梦想天宫"
COPYRIGHT_START_YEAR = 2025
COPYRIGHT_END_YEAR = 2025

def get_version_info():
    """获取版本信息"""
    return {
        "version": VERSION,
        "software_name": SOFTWARE_NAME,
        "developer": DEVELOPER,
        "company": COMPANY,
        "copyright_start": COPYRIGHT_START_YEAR,
        "copyright_end": COPYRIGHT_END_YEAR
    }

def get_about_text():
    """获取关于对话框的文本"""
    version_info = get_version_info()

    about_text = (
        f"软件名称：{version_info['software_name']}\n"
        f"版本: {version_info['version']}\n"
        f"程序开发: {version_info['developer']}\n"
        f"Copyright © {version_info['copyright_start']}-{version_info['copyright_end']} "
        f"{version_info['company']} All Rights Reserved."
    )

    return about_text

def get_copyright_text():
    """获取版权信息"""
    version_info = get_version_info()
    return f"Copyright © {version_info['copyright_start']}-{version_info['copyright_end']} {version_info['company']} All Rights Reserved."

def get_version_parts():
    """获取版本号各部分"""
    version_parts = VERSION.split('.')
    return {
        'major': int(version_parts[0]) if len(version_parts) > 0 else 0,
        'minor': int(version_parts[1]) if len(version_parts) > 1 else 0,
        'patch': int(version_parts[2]) if len(version_parts) > 2 else 0
    }

def bump_version(bump_type='patch'):
    """
    增加版本号

    Args:
        bump_type: 增加类型 ('major', 'minor', 'patch')

    Returns:
        新版本号字符串
    """
    parts = get_version_parts()

    if bump_type == 'major':
        parts['major'] += 1
        parts['minor'] = 0
        parts['patch'] = 0
    elif bump_type == 'minor':
        parts['minor'] += 1
        parts['patch'] = 0
    elif bump_type == 'patch':
        parts['patch'] += 1
    else:
        raise ValueError(f"无效的版本增加类型: {bump_type}")

    return f"{parts['major']}.{parts['minor']}.{parts['patch']}"

def format_version_with_prefix():
    """获取带前缀的版本号（用于显示）"""
    return f"v{VERSION}"