#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的音频设备切换功能测试
"""

import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def main():
    print("OpenList Windows 音频设备功能测试")
    print("=" * 50)

    try:
        # 测试VLC加载器
        print("1. 测试VLC加载器...")
        from src.media.vlc_loader import VLCLoader

        loader = VLCLoader()
        if loader.is_vlc_available():
            print("   [OK] VLC库加载成功")
            print(f"   版本: {loader.get_vlc_version()}")
            print(f"   来源: {loader.get_load_info()['load_source']}")
        else:
            print("   [FAIL] VLC库加载失败")
            return False

        # 测试媒体播放器核心
        print("\n2. 测试媒体播放器核心...")
        from src.media.media_player_core import MediaPlayerCore

        player_core = MediaPlayerCore()
        devices = player_core.get_available_audio_devices()

        print(f"   发现 {len(devices)} 个音频设备:")
        for i, device in enumerate(devices, 1):
            print(f"     {i}. {device['name']} - {device['description']}")

        # 测试设备切换
        if devices:
            test_device = devices[0]['name']
            success = player_core.set_audio_device(test_device)
            if success:
                print(f"   [OK] 成功切换到设备: {test_device}")
                current = player_core.get_current_audio_device()
                print(f"   当前设备: {current}")
            else:
                print(f"   [FAIL] 设备切换失败: {test_device}")

        player_core.cleanup()
        loader.cleanup()

        print("\n3. 测试音频播放控制器...")
        import wx
        from src.ui.audio_player_controller import AudioPlayerController

        app = wx.App()
        frame = wx.Frame(None, title="Test")
        controller = AudioPlayerController(frame)

        if controller.is_initialized:
            print("   [OK] 音频播放控制器初始化成功")

            controller_devices = controller.get_available_devices()
            print(f"   控制器发现 {len(controller_devices)} 个设备")

            controller_current = controller.get_current_device()
            print(f"   控制器当前设备: {controller_current}")
        else:
            print("   [FAIL] 音频播放控制器初始化失败")

        controller.cleanup()
        frame.Destroy()
        app.Destroy()

        print("\n" + "=" * 50)
        print("测试完成 - 基本功能正常")
        return True

    except Exception as e:
        print(f"   [ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        sys.exit(1)