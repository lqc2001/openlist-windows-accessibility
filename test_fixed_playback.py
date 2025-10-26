#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复后的播放逻辑测试脚本
验证停止后播放最后选择文件的功能
"""

import os
import subprocess
import sys

def main():
    print("=" * 60)
    print("OpenList 修复后的播放逻辑测试")
    print("=" * 60)
    print()
    print("🔧 修复内容：")
    print("- 停止播放后，快捷键会恢复播放最后通过回车键选择的文件")
    print("- 而不是回到更早播放的文件")
    print()
    print("📋 关键测试场景：")
    print()
    print("场景1：基本功能验证")
    print("1. 选择文件A，回车播放")
    print("2. 按停止键（Ctrl+End）")
    print("3. 按播放快捷键（Ctrl+Home）")
    print("4. ✅ 应该恢复播放文件A")
    print()
    print("场景2：文件切换验证")
    print("1. 选择文件A，回车播放")
    print("2. 按停止键")
    print("3. 选择文件B，回车播放")
    print("4. 按停止键")
    print("5. 选择文件C（不要回车）")
    print("6. 按播放快捷键")
    print("7. ✅ 应该恢复播放文件B（最后回车选择的）")
    print()
    print("场景3：快捷键控制验证")
    print("1. 选择文件A，回车播放")
    print("2. 选择文件B（不要回车）")
    print("3. 按播放快捷键")
    print("4. ✅ 应该继续播放文件A（不切换到B）")
    print("5. 按停止键")
    print("6. 按播放快捷键")
    print("7. ✅ 应该恢复播放文件A")
    print()
    print("🔍 观察日志确认：")
    print("- '使用音频控制器播放: [文件名]' - 回车键播放新文件")
    print("- '已记住最后选择的文件: [文件名]' - 记录选择")
    print("- '恢复播放最后选择的文件: [文件名]' - 停止后恢复")
    print("- '控制当前播放文件' - 有播放文件时的快捷键控制")
    print()
    print("✅ 修复成功标准：")
    print("- 停止后总是恢复最后回车选择的文件")
    print("- 快捷键不会自动切换到当前选中的文件")
    print("- 日志显示正确的文件恢复行为")
    print()
    print("现在启动测试？(y/n): ", end="")

    choice = input().lower().strip()
    if choice not in ['y', 'yes', '是', '']:
        print("❌ 测试已取消")
        return

    # 启动带调试日志的应用程序
    env = os.environ.copy()
    env['OPENLIST_LOG_LEVEL'] = 'on'
    env['OPENLIST_CONSOLE_LEVEL'] = 'DEBUG'

    print("\n🚀 正在启动应用程序进行测试...")

    try:
        if sys.platform == "win32":
            subprocess.Popen([sys.executable, "main.py"], env=env, creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            subprocess.Popen([sys.executable, "main.py"], env=env)

        print("✅ 应用程序已启动")
        print("\n📝 请按照上述测试场景进行验证")
        print("🎵 重点关注场景2和场景3的行为")
        print()
        print("💡 重要提示：")
        print("- 确保在包含多个音频文件的目录中测试")
        print("- 仔细区分回车键和播放快捷键的作用")
        print("- 观察日志确认文件记忆和恢复功能")

    except Exception as e:
        print(f"❌ 启动失败: {e}")

def print_summary():
    """打印修复总结"""
    print("\n📚 修复总结")
    print("-" * 30)
    print()
    print("🐛 原始问题：")
    print("- 停止播放后，快捷键恢复的是很早播放的文件")
    print("- 而不是最后通过回车键选择的文件")
    print()
    print("🔧 解决方案：")
    print("1. 添加了 `_last_selected_file` 变量记住最后回车选择的文件")
    print("2. 在 `_play_media_file` 中记录选择的文件")
    print("3. 在 `_control_current_playback` 中优先恢复记录的文件")
    print()
    print("🎯 现在的行为：")
    print("- 回车键：播放新文件并记录")
    print("- 停止后播放：恢复最后记录的文件")
    print("- 快捷键控制：只控制当前播放，不自动切换")
    print()
    print("📝 代码修改：")
    print("- `__init__`: 添加 `_last_selected_file` 变量")
    print("- `_play_media_file`: 记录最后选择的文件")
    print("- `_control_current_playback`: 优先恢复记录的文件")

if __name__ == "__main__":
    try:
        main()
        print_summary()
    except KeyboardInterrupt:
        print("\n\n❌ 测试被用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试过程中发生错误: {e}")

    print("\n按回车键退出...")
    try:
        input()
    except:
        pass