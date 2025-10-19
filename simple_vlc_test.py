#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单VLC测试
避免Unicode编码问题的VLC诊断
"""

import os
import sys
import platform
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

def main():
    """主测试函数"""
    print("VLC问题诊断")
    print("=" * 50)

    print("系统信息:")
    print(f"  操作系统: {platform.system()} {platform.release()}")
    print(f"  架构: {platform.machine()}")
    print(f"  Python: {sys.version.split()[0]}")

    # 检查系统VLC
    print("\n系统VLC检查:")
    vlc_path = "C:\\Program Files\\VideoLAN\\VLC"
    if os.path.exists(vlc_path):
        print(f"  [OK] 找到系统VLC: {vlc_path}")

        libvlc = os.path.join(vlc_path, "libvlc.dll")
        if os.path.exists(libvlc):
            size = os.path.getsize(libvlc)
            print(f"  [OK] libvlc.dll: {size:,} bytes ({size/1024/1024:.1f} MB)")
        else:
            print("  [FAIL] libvlc.dll: 不存在")

        libvlccore = os.path.join(vlc_path, "libvlccore.dll")
        if os.path.exists(libvlccore):
            size = os.path.getsize(libvlccore)
            print(f"  [OK] libvlccore.dll: {size:,} bytes ({size/1024/1024:.1f} MB)")
        else:
            print("  [FAIL] libvlccore.dll: 不存在")
    else:
        print("  [FAIL] 系统VLC不存在")

    # 测试python-vlc
    print("\nPython-VLC测试:")
    try:
        import vlc
        print("  [OK] python-vlc导入成功")

        # 获取版本
        try:
            version = vlc.libvlc_get_version()
            if isinstance(version, bytes):
                version = version.decode('utf-8')
            print(f"  [INFO] VLC版本: {version}")
        except:
            print("  [WARN] 无法获取VLC版本")

        # 测试实例创建 - 使用最简单的配置
        print("  [TEST] 创建VLC实例...")
        try:
            instance = vlc.Instance([])
            print("  [OK] VLC实例创建成功")

            # 测试播放器创建
            print("  [TEST] 创建媒体播放器...")
            try:
                player = instance.media_player_new()
                print("  [OK] 媒体播放器创建成功")

                # 测试媒体加载
                print("  [TEST] 加载网络媒体...")
                try:
                    test_url = "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
                    media = instance.media_new(test_url)
                    player.set_media(media)
                    print("  [OK] 网络媒体加载成功")
                    media.release()
                except Exception as e:
                    print(f"  [FAIL] 网络媒体加载失败: {e}")

                player.release()
            except Exception as e:
                print(f"  [FAIL] 媒体播放器创建失败: {e}")

            instance.release()
        except Exception as e:
            print(f"  [FAIL] VLC实例创建失败: {e}")
            print(f"  [ERROR] 错误类型: {type(e).__name__}")

            if "access violation" in str(e).lower():
                print("  [CRITICAL] 检测到内存访问冲突!")
                print("  可能原因:")
                print("    1. python-vlc版本与VLC不匹配")
                print("    2. 32位/64位架构不匹配")
                print("    3. VLC库文件损坏")
                print("    4. 系统权限问题")

    except ImportError as e:
        print(f"  [FAIL] python-vlc导入失败: {e}")
        print("  建议: pip install python-vlc")

    print("\n诊断完成")
    print("\n如果遇到内存访问冲突:")
    print("1. 检查python-vlc版本: pip show python-vlc")
    print("2. 重新安装python-vlc: pip uninstall python-vlc && pip install python-vlc")
    print("3. 确认VLC和Python架构匹配")
    print("4. 尝试使用管理员权限运行")

if __name__ == "__main__":
    main()