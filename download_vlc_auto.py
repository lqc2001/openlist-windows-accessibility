#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VLC便携版自动下载脚本
无需用户交互，自动下载并安装VLC便携版
"""

import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

def progress_callback(progress, status):
    """下载进度回调"""
    bar_length = 50
    filled_length = int(bar_length * progress // 100)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    print(f'\r进度: |{bar}| {progress:.1f}% - {status}', end='', flush=True)

def main():
    """主函数"""
    print("VLC便携版自动下载")
    print("=" * 60)

    try:
        from src.media.vlc_downloader import VLCDownloader

        # 创建下载器
        downloader = VLCDownloader(project_root)

        # 检查当前状态
        info = downloader.get_vlc_info()
        if info['installed']:
            print(f"VLC便携版已安装: {info['version']}")
            print(f"安装路径: {info['path']}")
            return True

        print(f"准备下载VLC便携版...")
        print(f"下载地址: {info['download_url']}")

        if info['download_size']:
            size_mb = info['download_size'] / (1024 * 1024)
            print(f"文件大小: {size_mb:.1f}MB")

        print("\n开始下载...")

        # 自动下载
        def auto_progress_callback(progress, status):
            progress_callback(progress, status)

        success = downloader.download_vlc(auto_progress_callback)

        print()  # 换行

        if success:
            print("✅ VLC便携版下载成功!")

            # 显示安装信息
            new_info = downloader.get_vlc_info()
            print(f"版本: {new_info['version']}")
            print(f"路径: {new_info['path']}")
            print(f"可执行文件: {new_info['exe_path']}")

            # 检查文件
            vlc_exe = Path(new_info['exe_path'])
            if vlc_exe.exists():
                size_mb = vlc_exe.stat().st_size / (1024 * 1024)
                print(f"VLC.exe大小: {size_mb:.1f}MB")

            print("\n🎉 VLC便携版安装完成!")
            print("现在可以使用媒体播放功能了")
            return True
        else:
            print(f"❌ 下载失败: {downloader.download_status}")
            return False

    except Exception as e:
        print(f"❌ 下载过程发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    print("\n" + "=" * 60)
    if success:
        print("状态: 成功完成")
    else:
        print("状态: 下载失败")
    sys.exit(0 if success else 1)