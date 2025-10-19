#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VLC库快速设置脚本
简化VLC内置库的配置过程
"""

import os
import sys
import shutil
from pathlib import Path

def find_vlc_installation():
    """查找系统VLC安装"""
    vlc_paths = [
        os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files'), 'VideoLAN', 'VLC'),
        os.path.join(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)'), 'VideoLAN', 'VLC'),
        'C:\\Program Files\\VideoLAN\\VLC',
        'C:\\Program Files (x86)\\VideoLAN\\VLC',
    ]

    for path in vlc_paths:
        if os.path.exists(path):
            libvlc_path = os.path.join(path, 'libvlc.dll')
            if os.path.exists(libvlc_path):
                return path

    return None

def copy_vlc_libraries(vlc_source, vlc_target):
    """复制VLC库文件"""
    try:
        # 确保目标目录存在
        os.makedirs(vlc_target, exist_ok=True)
        lib_dir = os.path.join(vlc_target, 'lib')
        plugins_dir = os.path.join(lib_dir, 'plugins')
        os.makedirs(lib_dir, exist_ok=True)
        os.makedirs(plugins_dir, exist_ok=True)

        # 复制核心库文件
        core_files = ['libvlc.dll', 'libvlccore.dll']
        for file in core_files:
            src_file = os.path.join(vlc_source, file)
            if os.path.exists(src_file):
                shutil.copy2(src_file, lib_dir)
                print(f"复制: {file}")

        # 复制插件目录
        src_plugins = os.path.join(vlc_source, 'plugins')
        if os.path.exists(src_plugins):
            for item in os.listdir(src_plugins):
                src_item = os.path.join(src_plugins, item)
                dst_item = os.path.join(plugins_dir, item)
                if os.path.isfile(src_item) and src_item.lower().endswith('.dll'):
                    shutil.copy2(src_item, dst_item)

            plugin_count = len(os.listdir(plugins_dir))
            print(f"复制插件: {plugin_count}个文件")

        return True

    except Exception as e:
        print(f"复制失败: {e}")
        return False

def main():
    """主函数"""
    print("VLC库快速设置工具")
    print("=" * 30)

    # 确定目标目录
    script_dir = Path(__file__).parent.parent
    vlc_target_dir = script_dir / "src" / "media" / "vlc_runtime"

    print(f"目标目录: {vlc_target_dir}")

    # 查找VLC安装
    vlc_source = find_vlc_installation()
    if not vlc_source:
        print("❌ 未找到VLC安装")
        print("请先安装VLC媒体播放器: https://www.videolan.org/")
        return False

    print(f"找到VLC安装: {vlc_source}")

    # 复制文件
    print("正在复制VLC库文件...")
    success = copy_vlc_libraries(vlc_source, str(vlc_target_dir))

    if success:
        print("VLC库设置完成!")
        print("现在可以运行 test_embedded_vlc.py 测试")
        return True
    else:
        print("VLC库设置失败")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)