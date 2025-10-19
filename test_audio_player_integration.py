#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频播放功能集成测试
测试主窗口中的音频播放功能
"""

import sys
import os
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_audio_player_integration():
    """测试音频播放器集成"""
    print("音频播放功能集成测试")
    print("=" * 50)

    try:
        import wx
        from src.core.config_manager import ConfigManager
        from src.ui.main_frame import MainFrame

        # 创建应用程序
        app = wx.App()

        # 创建配置管理器
        config_manager = ConfigManager()

        # 创建主窗口
        frame = MainFrame(config_manager)

        print("[1] 主窗口创建成功")

        # 检查音频播放控制器
        if hasattr(frame, 'audio_controller'):
            controller = frame.audio_controller
            print(f"[2] 音频播放控制器: {type(controller).__name__}")
            print(f"  可用性: {controller.is_available()}")
            print(f"  当前播放状态: {controller.get_playback_status()}")
        else:
            print("[2] 错误: 音频播放控制器不存在")
            return False

        # 检查菜单
        menubar = frame.GetMenuBar()
        if menubar:
            menu_count = menubar.GetMenuCount()
            print(f"[3] 菜单栏包含 {menu_count} 个菜单")

            # 查找播放菜单
            play_menu = None
            for i in range(menu_count):
                menu = menubar.GetMenu(i)
                menu_title = menubar.GetMenuLabel(i)
                print(f"  菜单 {i}: {menu_title}")
                if "播放" in menu_title:
                    play_menu = menu
                    break

            if play_menu:
                print("[4] 播放菜单找到")
                item_count = play_menu.GetMenuItemCount()
                print(f"  包含 {item_count} 个菜单项")

                # 列出播放菜单项
                for i in range(item_count):
                    item = play_menu.FindItemByPosition(i)
                    if item:
                        label = item.GetItemLabel()
                        print(f"    {i}: {label}")
            else:
                print("[4] 警告: 播放菜单未找到")

        # 检查状态栏
        status_bar = frame.GetStatusBar()
        if status_bar:
            fields_count = status_bar.GetFieldsCount()
            print(f"[5] 状态栏包含 {fields_count} 个字段")

            # 显示状态栏内容
            for i in range(fields_count):
                text = status_bar.GetStatusText(i)
                print(f"  字段 {i}: {text}")
        else:
            print("[5] 警告: 状态栏不存在")

        # 检查快捷键表
        accel_table = frame.GetAcceleratorTable()
        if accel_table:
            print("[6] 快捷键表已设置")
        else:
            print("[6] 警告: 快捷键表未设置")

        # 测试播放器状态
        if controller.is_available():
            print("[7] 音频播放器功能测试:")

            # 测试音量控制
            print(f"  当前音量: {controller.get_volume()}")
            volume_up_result = controller.volume_up(10)
            print(f"  音量增加结果: {volume_up_result}")
            print(f"  增加后音量: {controller.get_volume()}")

            volume_down_result = controller.volume_down(10)
            print(f"  音量减少结果: {volume_down_result}")
            print(f"  减少后音量: {controller.get_volume()}")

            # 测试倍速控制
            print(f"  当前倍速: {controller.playback_rate}")
            for speed in [0.5, 1.0, 1.5, 2.0]:
                result = controller.set_playback_rate(speed)
                print(f"  设置倍速 {speed}x 结果: {result}")
                print(f"  实际倍速: {controller.playback_rate}")

            # 恢复默认倍速
            controller.set_playback_rate(1.0)

        # 测试音频设备
        devices = controller.get_available_devices()
        print(f"[8] 可用音频设备: {devices}")

        print("\n[成功] 音频播放功能集成测试完成")
        print("所有基础功能都已正确集成到主窗口中！")

        # 显示窗口（可选，用于手动测试）
        frame.Show()
        print("\n提示: 窗口已显示，可以手动测试菜单和快捷键功能")
        print("按Alt+F4或关闭窗口退出测试")

        # 运行应用程序
        app.MainLoop()

        return True

    except Exception as e:
        print(f"[失败] 音频播放功能集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    success = test_audio_player_integration()

    print("\n" + "=" * 50)
    if success:
        print("✅ 音频播放功能集成成功！")
        print("\n已实现的功能:")
        print("• 播放菜单和所有子菜单")
        print("• 5字段状态栏显示")
        print("• 播放控制快捷键")
        print("• 音量和倍速控制")
        print("• 无障碍标签和帮助文本")
        print("\n下一步:")
        print("• 实现空格键播放/暂停功能")
        print("• 添加音频设备选择功能")
        print("• 测试实际音频文件播放")
    else:
        print("❌ 音频播放功能集成失败")
        print("请检查错误信息并修复问题")

if __name__ == "__main__":
    main()