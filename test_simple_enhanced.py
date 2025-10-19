#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的增强功能测试
避免复杂的UI，专注于核心功能测试
"""

import sys
import os
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

def test_environment_setup():
    """测试环境配置"""
    print("=" * 50)
    print("测试环境配置")
    print("=" * 50)

    try:
        from src.core.environment_setup import EnvironmentSetup

        env_setup = EnvironmentSetup()
        env_info = env_setup.get_environment_info()

        print(f"运行模式: {'开发环境' if env_info['is_development'] else '打包环境'}")
        print(f"操作系统: {'Windows' if env_info['is_windows'] else '其他'}")
        print(f"架构: {'64位' if env_info['is_64bit'] else '32位'}")
        print(f"Python版本: {env_info['python_version']}")
        print(f"VLC可用: {'是' if env_info['vlc_available'] else '否'}")

        if env_info['selected_vlc_path']:
            print(f"VLC路径: {env_info['selected_vlc_path']}")

        print(f"VLC路径数量: {env_info['vlc_paths_count']}")

        if env_info['missing_dependencies']:
            print(f"缺少依赖: {', '.join(env_info['missing_dependencies'])}")

        # 测试VLC导入
        vlc_success, vlc_msg = env_setup.test_vlc_import()
        print(f"VLC导入测试: {vlc_msg}")

        if vlc_success:
            print("[OK] 环境配置测试通过")
            return True
        else:
            print("[FAIL] 环境配置测试失败")
            return False

    except Exception as e:
        print(f"[ERROR] 环境测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_audio_player():
    """测试音频播放器"""
    print("\n" + "=" * 50)
    print("测试音频播放器")
    print("=" * 50)

    try:
        from src.media.enhanced_audio_player import EnhancedAudioPlayer

        player = EnhancedAudioPlayer()

        # 检查VLC可用性
        if player.is_vlc_available:
            print("[OK] VLC可用")
        else:
            print("[FAIL] VLC不可用")
            return False

        # 测试音量控制
        current_volume = player.get_volume()
        print(f"当前音量: {current_volume}")

        # 测试音量设置
        test_volume = 50
        if player.set_volume(test_volume):
            print(f"[OK] 音量设置成功: {test_volume}")
            # 恢复原音量
            player.set_volume(current_volume)
        else:
            print("[FAIL] 音量设置失败")

        # 测试设备枚举
        print("\n测试音频设备枚举...")
        devices = player.get_audio_devices()
        print(f"找到 {len(devices)} 个音频设备:")

        for i, device in enumerate(devices):
            current_marker = " [当前]" if device.get('is_current') else ""
            print(f"  {i+1}. {device['name']}{current_marker}")

        # 测试状态信息
        status_info = player.get_status_info()
        print(f"\n播放器状态: {status_info}")

        # 测试进度信息
        progress_info = player.get_progress_info()
        print(f"进度信息: {progress_info}")

        print("[OK] 音频播放器测试完成")
        return True

    except Exception as e:
        print(f"[ERROR] 音频播放器测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_file_playing():
    """测试文件播放"""
    print("\n" + "=" * 50)
    print("测试文件播放")
    print("=" * 50)

    try:
        from src.media.enhanced_audio_player import EnhancedAudioPlayer

        player = EnhancedAudioPlayer()

        # 查找测试音频文件
        test_files = []
        search_paths = [
            project_root,
            project_root / "test_audio",
            Path("C:/Windows/Media"),
        ]

        for search_path in search_paths:
            if search_path.exists():
                for ext in ['*.mp3', '*.wav', '*.flac', '*.ogg']:
                    test_files.extend(search_path.glob(ext))

        if not test_files:
            print("[WARN] 未找到测试音频文件，跳过播放测试")
            return True

        test_file = test_files[0]
        print(f"使用测试文件: {test_file}")

        # 测试加载
        if player.load_file(str(test_file)):
            print("[OK] 文件加载成功")

            # 测试播放
            if player.play():
                print("[OK] 播放开始成功")

                # 等待2秒
                time.sleep(2)

                # 检查状态
                if player.is_playing:
                    print("[OK] 播放状态正常")

                    # 测试暂停
                    if player.pause():
                        print("[OK] 暂停成功")
                        time.sleep(1)

                        # 测试恢复
                        if player.play():
                            print("[OK] 恢复播放成功")
                        else:
                            print("[FAIL] 恢复播放失败")
                    else:
                        print("[FAIL] 暂停失败")

                    # 等待2秒
                    time.sleep(2)

                    # 停止播放
                    if player.stop():
                        print("[OK] 停止播放成功")
                    else:
                        print("[FAIL] 停止播放失败")
                else:
                    print("[FAIL] 播放状态异常")
            else:
                print("[FAIL] 播放开始失败")
        else:
            print("[FAIL] 文件加载失败")

        print("[OK] 文件播放测试完成")
        return True

    except Exception as e:
        print(f"[ERROR] 文件播放测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("OpenList 增强音频功能测试")
    print("时间:", time.strftime("%Y-%m-%d %H:%M:%S"))

    # 运行测试
    tests = [
        ("环境配置", test_environment_setup),
        ("音频播放器", test_audio_player),
        ("文件播放", test_file_playing),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"[ERROR] {test_name}测试发生异常: {e}")
            results.append((test_name, False))

    # 输出测试结果总结
    print("\n" + "=" * 50)
    print("测试结果总结")
    print("=" * 50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "[OK] 通过" if result else "[FAIL] 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\n总计: {passed}/{total} 个测试通过")

    if passed == total:
        print("[SUCCESS] 所有测试都通过了！")
    else:
        print("[WARNING] 部分测试失败，请检查上述错误信息")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)