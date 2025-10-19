#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频设备切换功能测试脚本
用于验证VLC音频设备枚举和切换功能
"""

import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_audio_device_enumeration():
    """测试音频设备枚举功能"""
    print("=== 音频设备枚举功能测试 ===\n")

    try:
        from src.media.media_player_core import MediaPlayerCore

        # 创建媒体播放器核心实例
        player_core = MediaPlayerCore()

        print("1. 初始化播放器核心...")
        if player_core.vlc_instance:
            print("   ✓ VLC实例创建成功")
        else:
            print("   ✗ VLC实例创建失败")
            return False

        print("\n2. 枚举音频设备...")
        devices = player_core.get_available_audio_devices()

        if devices:
            print(f"   ✓ 发现 {len(devices)} 个音频设备:")
            for i, device in enumerate(devices, 1):
                print(f"     {i}. {device['name']} - {device['description']}")
        else:
            print("   ✗ 未发现音频设备")
            return False

        print("\n3. 测试设备切换...")
        if len(devices) > 0:
            # 尝试切换到第一个设备
            first_device = devices[0]['name']
            success = player_core.set_audio_device(first_device)

            if success:
                print(f"   ✓ 成功切换到设备: {first_device}")

                # 检查当前设备
                current = player_core.get_current_audio_device()
                print(f"   ✓ 当前设备: {current}")
            else:
                print(f"   ✗ 切换到设备失败: {first_device}")
                return False

        print("\n4. 测试设备缓存...")
        # 再次获取设备列表（应该使用缓存）
        devices_cached = player_core.get_available_audio_devices()
        if len(devices_cached) == len(devices):
            print("   ✓ 设备缓存工作正常")
        else:
            print("   ✗ 设备缓存异常")

        print("\n5. 测试设备刷新...")
        devices_refreshed = player_core.refresh_audio_devices()
        if len(devices_refreshed) >= len(devices):
            print("   ✓ 设备刷新工作正常")
        else:
            print("   ✗ 设备刷新异常")

        # 清理资源
        player_core.cleanup()
        print("\n=== 测试完成 ===")
        return True

    except Exception as e:
        print(f"   ✗ 测试过程中发生错误: {e}")
        return False

def test_audio_player_controller():
    """测试音频播放控制器的设备功能"""
    print("\n=== 音频播放控制器设备功能测试 ===\n")

    try:
        import wx
        from src.ui.audio_player_controller import AudioPlayerController

        # 创建一个简单的wx应用（不显示窗口）
        app = wx.App()
        frame = wx.Frame(None, title="测试窗口")

        print("1. 初始化音频播放控制器...")
        controller = AudioPlayerController(frame)

        if controller.is_initialized:
            print("   ✓ 音频播放控制器初始化成功")
        else:
            print("   ✗ 音频播放控制器初始化失败")
            return False

        print("\n2. 测试设备列表获取...")
        devices = controller.get_available_devices()

        if devices:
            print(f"   ✓ 获取到 {len(devices)} 个设备:")
            for i, device in enumerate(devices, 1):
                print(f"     {i}. {device['name']} - {device['description']}")
        else:
            print("   ✗ 未获取到设备列表")
            return False

        print("\n3. 测试当前设备获取...")
        current_device = controller.get_current_device()
        print(f"   ✓ 当前设备: {current_device}")

        print("\n4. 测试设备切换...")
        if len(devices) > 1:
            # 尝试切换到不同的设备
            test_device = devices[1]['name'] if devices[0]['name'] == current_device else devices[0]['name']
            success = controller.set_audio_device(test_device)

            if success:
                print(f"   ✓ 成功切换到设备: {test_device}")
            else:
                print(f"   ✗ 切换到设备失败: {test_device}")

        # 清理资源
        controller.cleanup()
        frame.Destroy()
        app.Destroy()

        print("\n=== 控制器测试完成 ===")
        return True

    except Exception as e:
        print(f"   ✗ 控制器测试过程中发生错误: {e}")
        return False

def test_vlc_availability():
    """测试VLC库可用性"""
    print("=== VLC库可用性测试 ===\n")

    try:
        from src.media.vlc_loader import VLCLoader

        print("1. 测试VLC库加载...")
        loader = VLCLoader()

        if loader.is_vlc_available():
            print("   ✓ VLC库加载成功")
            print(f"   版本: {loader.get_vlc_version()}")
            print(f"   来源: {loader.get_load_info()['load_source']}")
        else:
            print("   ✗ VLC库加载失败")
            return False

        print("\n2. 测试VLC实例...")
        instance = loader.get_vlc_instance()
        if instance:
            print("   ✓ VLC实例创建成功")
        else:
            print("   ✗ VLC实例创建失败")
            return False

        # 清理资源
        loader.cleanup()
        print("\n=== VLC测试完成 ===")
        return True

    except Exception as e:
        print(f"   ✗ VLC测试过程中发生错误: {e}")
        return False

def main():
    """主测试函数"""
    print("OpenList Windows 音频设备切换功能测试")
    print("=" * 50)

    test_results = []

    # 1. 测试VLC可用性
    test_results.append(("VLC库可用性", test_vlc_availability()))

    # 2. 测试音频设备枚举
    test_results.append(("音频设备枚举", test_audio_device_enumeration()))

    # 3. 测试音频播放控制器
    test_results.append(("音频播放控制器", test_audio_player_controller()))

    # 显示测试结果总结
    print("\n" + "=" * 50)
    print("测试结果总结:")
    print("=" * 50)

    all_passed = True
    for test_name, result in test_results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name:20} : {status}")
        if not result:
            all_passed = False

    print("=" * 50)
    if all_passed:
        print("🎉 所有测试通过！音频设备切换功能正常工作。")
    else:
        print("⚠️  部分测试失败，请检查相关功能。")

    return all_passed

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n测试过程中发生未预期的错误: {e}")
        sys.exit(1)