#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度VLC问题诊断
详细分析VLC加载和播放问题
"""

import os
import sys
import platform
import ctypes
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

def check_system_info():
    """检查系统信息"""
    print("=== 系统信息 ===")
    print(f"操作系统: {platform.system()} {platform.release()}")
    print(f"架构: {platform.machine()}")
    print(f"Python版本: {sys.version}")
    print(f"Python架构: {platform.architecture()[0]}")

    # 检查系统架构和Python架构匹配
    is_64bit_os = platform.machine().endswith('64')
    is_64bit_python = sys.maxsize > 2**32
    print(f"64位系统: {is_64bit_os}")
    print(f"64位Python: {is_64bit_python}")

    if is_64bit_os and not is_64bit_python:
        print("⚠️ 警告: 64位系统上运行32位Python，可能导致兼容性问题")

    print()

def check_vlc_installation():
    """检查VLC安装情况"""
    print("=== VLC安装检查 ===")

    # 检查系统VLC
    system_vlc_paths = [
        "C:\\Program Files\\VideoLAN\\VLC",
        "C:\\Program Files (x86)\\VideoLAN\\VLC"
    ]

    for path in system_vlc_paths:
        if os.path.exists(path):
            print(f"✅ 找到系统VLC: {path}")

            # 检查关键文件
            libvlc = os.path.join(path, "libvlc.dll")
            libvlccore = os.path.join(path, "libvlccore.dll")

            if os.path.exists(libvlc):
                size = os.path.getsize(libvlc)
                print(f"   libvlc.dll: {size:,} bytes ({size/1024/1024:.1f} MB)")
            else:
                print("   ❌ libvlc.dll: 不存在")

            if os.path.exists(libvlccore):
                size = os.path.getsize(libvlccore)
                print(f"   libvlccore.dll: {size:,} bytes ({size/1024/1024:.1f} MB)")
            else:
                print("   ❌ libvlccore.dll: 不存在")

            # 检查插件目录
            plugins_dir = os.path.join(path, "plugins")
            if os.path.exists(plugins_dir):
                plugin_count = len(list(Path(plugins_dir).rglob("*.dll")))
                print(f"   插件数量: {plugin_count}")
            else:
                print("   ❌ 插件目录: 不存在")
        else:
            print(f"❌ 系统VLC不存在: {path}")

    # 检查便携版VLC
    portable_vlc = project_root / "vlc_portable"
    if portable_vlc.exists():
        print(f"✅ 找到便携版VLC: {portable_vlc}")

        libvlc = portable_vlc / "libvlc.dll"
        if libvlc.exists():
            size = libvlc.stat().st_size
            print(f"   便携版 libvlc.dll: {size:,} bytes ({size/1024/1024:.1f} MB)")
    else:
        print("❌ 便携版VLC不存在")

    print()

def check_python_vlc():
    """检查python-vlc绑定"""
    print("=== Python-VLC绑定检查 ===")

    try:
        import vlc
        print("✅ python-vlc模块导入成功")

        # 获取VLC版本
        try:
            version = vlc.libvlc_get_version()
            if isinstance(version, bytes):
                version = version.decode('utf-8')
            print(f"VLC版本: {version}")
        except Exception as e:
            print(f"❌ 获取VLC版本失败: {e}")

        # 检查VLC编译信息
        try:
            compiler = vlc.libvlc_get_compiler()
            if isinstance(compiler, bytes):
                compiler = compiler.decode('utf-8')
            print(f"VLC编译器: {compiler}")
        except Exception as e:
            print(f"❌ 获取VLC编译器失败: {e}")

    except ImportError as e:
        print(f"❌ python-vlc模块导入失败: {e}")
        print("建议: pip install python-vlc")

    print()

def test_vlc_instance_creation():
    """测试VLC实例创建"""
    print("=== VLC实例创建测试 ===")

    try:
        import vlc

        # 测试不同的参数组合
        test_configs = [
            {
                "name": "默认配置",
                "args": []
            },
            {
                "name": "静默配置",
                "args": ["--quiet"]
            },
            {
                "name": "最小配置",
                "args": ["--quiet", "--no-stats", "--no-video-title-show"]
            },
            {
                "name": "Windows音频配置",
                "args": ["--quiet", "--aout=directsound"]
            }
        ]

        for config in test_configs:
            print(f"测试配置: {config['name']}")
            print(f"参数: {config['args']}")

            try:
                instance = vlc.Instance(config['args'])
                print("✅ VLC实例创建成功")

                # 尝试创建播放器
                try:
                    player = instance.media_player_new()
                    print("✅ 媒体播放器创建成功")
                    player.release()
                except Exception as e:
                    print(f"❌ 媒体播放器创建失败: {e}")

                instance.release()

            except Exception as e:
                print(f"❌ VLC实例创建失败: {e}")
                print(f"错误类型: {type(e).__name__}")

                # 如果是内存访问冲突，显示详细信息
                if "access violation" in str(e).lower():
                    print("🔍 检测到内存访问冲突，可能原因:")
                    print("   - VLC版本与python-vlc绑定不匹配")
                    print("   - 32位/64位架构不匹配")
                    print("   - 系统权限问题")
                    print("   - VLC库文件损坏")

            print()

    except ImportError:
        print("❌ python-vlc未安装，跳过实例创建测试")
        print()

def test_media_loading():
    """测试媒体加载"""
    print("=== 媒体加载测试 ===")

    try:
        import vlc

        # 使用最简单的配置
        instance = vlc.Instance(["--quiet"])
        player = instance.media_player_new()

        # 测试本地文件
        test_files = []

        # 查找测试音频文件
        for ext in ['.mp3', '.wav', '.m4a']:
            for root, dirs, files in os.walk("C:\\Windows\\Media"):
                for file in files:
                    if file.lower().endswith(ext):
                        test_files.append(os.path.join(root, file))
                        break
                if test_files:
                    break

        print("测试本地文件加载:")
        if test_files:
            test_file = test_files[0]
            print(f"文件: {test_file}")

            try:
                media = instance.media_new(test_file)
                player.set_media(media)
                print("✅ 本地文件加载成功")
                media.release()
            except Exception as e:
                print(f"❌ 本地文件加载失败: {e}")
        else:
            print("❌ 未找到测试音频文件")

        print()

        # 测试网络URL
        print("测试网络URL加载:")
        test_url = "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
        print(f"URL: {test_url}")

        try:
            media = instance.media_new(test_url)
            player.set_media(media)
            print("✅ 网络URL加载成功")
            media.release()
        except Exception as e:
            print(f"❌ 网络URL加载失败: {e}")

        # 清理
        player.release()
        instance.release()

    except ImportError:
        print("❌ python-vlc未安装，跳过媒体加载测试")
    except Exception as e:
        print(f"❌ 媒体加载测试失败: {e}")

    print()

def main():
    """主诊断函数"""
    print("VLC深度问题诊断")
    print("=" * 60)

    check_system_info()
    check_vlc_installation()
    check_python_vlc()
    test_vlc_instance_creation()
    test_media_loading()

    print("=" * 60)
    print("诊断完成")
    print()
    print("如果看到内存访问冲突错误，建议:")
    print("1. 确认python-vlc版本与VLC版本匹配")
    print("2. 尝试重新安装python-vlc: pip uninstall python-vlc && pip install python-vlc")
    print("3. 确认VLC和Python都是相同架构(32位或64位)")
    print("4. 以管理员权限运行程序")

if __name__ == "__main__":
    main()