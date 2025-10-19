#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VLC问题诊断脚本
诊断VLC播放器的问题并提供解决方案
"""

import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

def diagnose_vlc():
    """诊断VLC问题"""
    print("VLC问题诊断")
    print("=" * 50)

    try:
        # 检查VLC便携版
        vlc_portable = project_root / "vlc_portable"
        print(f"[1] 检查VLC便携版目录: {vlc_portable}")

        if vlc_portable.exists():
            print("   [存在] VLC便携版目录存在")

            # 检查关键文件
            libvlc = vlc_portable / "libvlc.dll"
            libvlccore = vlc_portable / "libvlccore.dll"
            plugins = vlc_portable / "plugins"

            print(f"   检查 {libvlc.name}: {'存在' if libvlc.exists() else '不存在'}")
            print(f"   检查 {libvlccore.name}: {'存在' if libvlccore.exists() else '不存在'}")
            print(f"   检查 plugins目录: {'存在' if plugins.exists() else '不存在'}")

            if plugins.exists():
                # 检查插件数量
                plugin_files = list(plugins.rglob("*.dll"))
                print(f"   插件文件数量: {len(plugin_files)}")

                if len(plugin_files) < 50:
                    print("   [警告] 插件文件数量可能不足")
                else:
                    print("   [正常] 插件文件数量充足")

            # 检查文件大小
            if libvlc.exists():
                size_mb = libvlc.stat().st_size / 1024 / 1024
                print(f"   libvlc.dll大小: {size_mb:.1f} MB")
                if size_mb < 1:
                    print("   [警告] libvlc.dll文件过小，可能损坏")

            if libvlccore.exists():
                size_mb = libvlccore.stat().st_size / 1024 / 1024
                print(f"   libvlccore.dll大小: {size_mb:.1f} MB")
                if size_mb < 1:
                    print("   [警告] libvlccore.dll文件过小，可能损坏")
        else:
            print("   [不存在] VLC便携版目录不存在")

            # 检查传统runtime目录
            vlc_runtime = project_root / "src" / "media" / "vlc_runtime"
            print(f"[2] 检查传统VLC runtime目录: {vlc_runtime}")

            if vlc_runtime.exists():
                print("   [存在] 传统VLC runtime目录存在")
            else:
                print("   [不存在] 传统VLC runtime目录也不存在")
                print("   [建议] 需要下载VLC便携版")

        # 测试VLC加载器
        print("\n[3] 测试VLC加载器...")
        try:
            from src.media.vlc_loader import VLCLoader

            loader = VLCLoader()
            print("   [成功] VLC加载器创建成功")

            # 尝试获取VLC实例
            vlc_instance = loader.get_vlc_instance()
            if vlc_instance:
                print("   [成功] VLC实例创建成功")
            else:
                print("   [失败] VLC实例创建失败")

        except Exception as e:
            print(f"   [失败] VLC加载器测试失败: {e}")

        # 测试媒体播放器核心
        print("\n[4] 测试媒体播放器核心...")
        try:
            from src.media.media_player_core import MediaPlayerCore

            core = MediaPlayerCore()
            print("   [成功] 媒体播放器核心创建成功")

            # 清理
            core.cleanup()
            print("   [成功] 媒体播放器核心清理成功")

        except Exception as e:
            print(f"   [失败] 媒体播放器核心测试失败: {e}")

        # 测试简单媒体播放
        print("\n[5] 测试简单媒体播放...")
        try:
            from src.media.audio_player import AudioPlayer

            player = AudioPlayer()
            print("   [成功] 音频播放器创建成功")

            # 清理
            player.cleanup()
            print("   [成功] 音频播放器清理成功")

        except Exception as e:
            print(f"   [失败] 音频播放器测试失败: {e}")

        return True

    except Exception as e:
        print(f"[失败] 诊断过程失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def provide_solution():
    """提供解决方案"""
    print("\n" + "=" * 50)
    print("解决方案建议")
    print("-" * 50)

    print("根据诊断结果，可能的解决方案：")
    print()
    print("1. 如果VLC文件损坏或过小：")
    print("   python download_vlc_auto.py")
    print()
    print("2. 如果插件不足：")
    print("   删除vlc_portable目录，重新下载")
    print()
    print("3. 如果仍有问题：")
    print("   检查系统是否安装了VLC")
    print("   尝试使用系统VLC库")
    print()
    print("4. 内存访问问题通常由于：")
    print("   - VLC库文件不完整")
    print("   - 插件缺失")
    print("   - 版本不兼容")

def main():
    """主函数"""
    print("OpenList VLC问题诊断工具")
    print("=" * 60)

    diagnose_vlc()
    provide_solution()

if __name__ == "__main__":
    main()