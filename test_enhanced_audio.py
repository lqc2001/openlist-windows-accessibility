#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强音频功能测试
测试声卡切换、状态栏显示、播放控制等增强功能
"""

import sys
import os
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

try:
    import wx
    from src.core.environment_setup import EnvironmentSetup
    from src.media.enhanced_audio_player import EnhancedAudioPlayer
    from src.ui.enhanced_status_bar import EnhancedStatusBar
    from src.ui.enhanced_audio_controller import EnhancedAudioController
    from src.core.logger import get_logger
except ImportError as e:
    print(f"导入失败: {e}")
    print("请确保项目依赖已正确安装")
    sys.exit(1)


class EnhancedAudioTestFrame(wx.Frame):
    """增强音频测试窗口"""

    def __init__(self):
        super().__init__(None, title="OpenList 增强音频功能测试", size=(800, 600))

        self.logger = get_logger()

        # 初始化UI
        self.init_ui()

        # 初始化组件
        self.init_components()

        self.logger.info("增强音频测试窗口初始化完成")

    def init_ui(self):
        """初始化用户界面"""
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # 标题
        title = wx.StaticText(panel, label="OpenList 增强音频功能测试")
        title_font = wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        main_sizer.Add(title, 0, wx.ALL | wx.CENTER, 10)

        # 环境信息区域
        env_box = wx.StaticBox(panel, label="环境信息")
        env_sizer = wx.StaticBoxSizer(env_box, wx.VERTICAL)

        self.env_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 120))
        env_sizer.Add(self.env_text, 1, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(env_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # 测试按钮区域
        btn_box = wx.StaticBox(panel, label="功能测试")
        btn_sizer = wx.StaticBoxSizer(btn_box, wx.VERTICAL)

        btn_grid = wx.GridBagSizer(5, 5)

        # 环境测试按钮
        env_test_btn = wx.Button(panel, label="测试环境配置")
        env_test_btn.Bind(wx.EVT_BUTTON, self.on_test_environment)
        btn_grid.Add(env_test_btn, (0, 0), (1, 2), wx.EXPAND)

        # VLC测试按钮
        vlc_test_btn = wx.Button(panel, label="测试VLC")
        vlc_test_btn.Bind(wx.EVT_BUTTON, self.on_test_vlc)
        btn_grid.Add(vlc_test_btn, (1, 0), (1, 1), wx.EXPAND)

        # 设备测试按钮
        device_test_btn = wx.Button(panel, label="测试音频设备")
        device_test_btn.Bind(wx.EVT_BUTTON, self.on_test_audio_devices)
        btn_grid.Add(device_test_btn, (1, 1), (1, 1), wx.EXPAND)

        # 状态栏测试按钮
        status_test_btn = wx.Button(panel, label="测试状态栏")
        status_test_btn.Bind(wx.EVT_BUTTON, self.on_test_status_bar)
        btn_grid.Add(status_test_btn, (2, 0), (1, 1), wx.EXPAND)

        # 播放控制测试按钮
        control_test_btn = wx.Button(panel, label="测试播放控制")
        control_test_btn.Bind(wx.EVT_BUTTON, self.on_test_play_control)
        btn_grid.Add(control_test_btn, (2, 1), (1, 1), wx.EXPAND)

        # 文件选择按钮
        file_btn = wx.Button(panel, label="选择音频文件测试")
        file_btn.Bind(wx.EVT_BUTTON, self.on_select_audio_file)
        btn_grid.Add(file_btn, (3, 0), (1, 2), wx.EXPAND)

        btn_sizer.Add(btn_grid, 1, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # 测试结果区域
        result_box = wx.StaticBox(panel, label="测试结果")
        result_sizer = wx.StaticBoxSizer(result_box, wx.VERTICAL)

        self.result_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 150))
        result_sizer.Add(self.result_text, 1, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(result_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # 清除按钮
        clear_btn = wx.Button(panel, label="清除结果")
        clear_btn.Bind(wx.EVT_BUTTON, self.on_clear_results)
        main_sizer.Add(clear_btn, 0, wx.ALL | wx.CENTER, 10)

        panel.SetSizer(main_sizer)

        # 初始化环境信息显示
        self.update_env_info()

    def init_components(self):
        """初始化组件"""
        try:
            # 创建状态栏
            self.status_bar_manager = EnhancedStatusBar(self)

            # 创建音频控制器（这会自动创建音频播放器）
            self.audio_controller = EnhancedAudioController(self, self.status_bar_manager)

            # 设置快捷键
            self.audio_controller.setup_keyboard_shortcuts()

            # 添加播放菜单到菜单栏
            if self.audio_controller.get_play_menu():
                menubar = wx.MenuBar()
                menubar.Append(self.audio_controller.get_play_menu(), "播放(&P)")
                self.SetMenuBar(menubar)

            self.log_result("组件初始化成功")

        except Exception as e:
            self.log_result(f"组件初始化失败: {e}")

    def update_env_info(self):
        """更新环境信息显示"""
        try:
            env_setup = EnvironmentSetup()
            env_info = env_setup.get_environment_info()

            info_text = []
            info_text.append(f"运行模式: {'开发环境' if env_info['is_development'] else '打包环境'}")
            info_text.append(f"操作系统: {'Windows' if env_info['is_windows'] else '其他'}")
            info_text.append(f"架构: {'64位' if env_info['is_64bit'] else '32位'}")
            info_text.append(f"Python版本: {env_info['python_version']}")
            info_text.append(f"VLC可用: {'是' if env_info['vlc_available'] else '否'}")

            if env_info['selected_vlc_path']:
                info_text.append(f"VLC路径: {env_info['selected_vlc_path']}")

            info_text.append(f"VLC路径数量: {env_info['vlc_paths_count']}")

            if env_info['missing_dependencies']:
                info_text.append(f"缺少依赖: {', '.join(env_info['missing_dependencies'])}")

            self.env_text.SetValue('\n'.join(info_text))

        except Exception as e:
            self.env_text.SetValue(f"获取环境信息失败: {e}")

    def log_result(self, message: str):
        """记录测试结果"""
        timestamp = time.strftime("%H:%M:%S")
        self.result_text.AppendText(f"[{timestamp}] {message}\n")

        # 自动滚动到底部
        self.result_text.SetInsertionPointEnd()
        self.result_text.ShowPosition(self.result_text.GetLastPosition())

    def on_test_environment(self, event):
        """测试环境配置"""
        self.log_result("=== 开始环境配置测试 ===")

        try:
            env_setup = EnvironmentSetup()

            # 显示环境报告
            report = env_setup.create_environment_report()
            self.log_result("环境报告:")
            for line in report.split('\n'):
                self.log_result(line)

            # 测试VLC导入
            vlc_success, vlc_msg = env_setup.test_vlc_import()
            self.log_result(f"VLC导入测试: {vlc_msg}")

            if vlc_success:
                self.log_result("✅ 环境配置测试通过")
            else:
                self.log_result("❌ 环境配置测试失败")

        except Exception as e:
            self.log_result(f"❌ 环境测试异常: {e}")

    def on_test_vlc(self, event):
        """测试VLC功能"""
        self.log_result("=== 开始VLC功能测试 ===")

        try:
            if not self.audio_controller:
                self.log_result("❌ 音频控制器未初始化")
                return

            audio_player = self.audio_controller.get_audio_player()

            # 检查VLC可用性
            if audio_player.is_vlc_available:
                self.log_result("✅ VLC可用")
            else:
                self.log_result("❌ VLC不可用")
                return

            # 获取VLC版本
            if hasattr(audio_player, 'vlc_loader') and audio_player.vlc_loader:
                version = audio_player.vlc_loader.get_vlc_version()
                self.log_result(f"VLC版本: {version}")

            # 测试音量控制
            current_volume = audio_player.get_volume()
            self.log_result(f"当前音量: {current_volume}")

            # 测试音量设置
            test_volume = 50
            if audio_player.set_volume(test_volume):
                self.log_result(f"✅ 音量设置成功: {test_volume}")
                # 恢复原音量
                audio_player.set_volume(current_volume)
            else:
                self.log_result("❌ 音量设置失败")

            self.log_result("✅ VLC功能测试完成")

        except Exception as e:
            self.log_result(f"❌ VLC测试异常: {e}")

    def on_test_audio_devices(self, event):
        """测试音频设备"""
        self.log_result("=== 开始音频设备测试 ===")

        try:
            if not self.audio_controller:
                self.log_result("❌ 音频控制器未初始化")
                return

            audio_player = self.audio_controller.get_audio_player()

            # 获取设备列表
            devices = audio_player.get_audio_devices()
            self.log_result(f"找到 {len(devices)} 个音频设备:")

            for i, device in enumerate(devices):
                current_marker = " [当前]" if device.get('is_current') else ""
                self.log_result(f"  {i+1}. {device['name']}{current_marker}")
                self.log_result(f"     ID: {device['id']}")
                self.log_result(f"     描述: {device['description']}")

            # 测试设备切换（如果不是默认设备）
            non_default_devices = [d for d in devices if d['id'] != 'default']
            if non_default_devices:
                test_device = non_default_devices[0]
                self.log_result(f"测试切换到设备: {test_device['name']}")

                if audio_player.set_audio_device(test_device['id']):
                    self.log_result("✅ 设备切换成功")

                    # 切换回默认设备
                    time.sleep(1)
                    if audio_player.set_audio_device('default'):
                        self.log_result("✅ 切换回默认设备成功")
                    else:
                        self.log_result("⚠️ 切换回默认设备失败")
                else:
                    self.log_result("❌ 设备切换失败")
            else:
                self.log_result("⚠️ 没有可切换的非默认设备")

            self.log_result("✅ 音频设备测试完成")

        except Exception as e:
            self.log_result(f"❌ 音频设备测试异常: {e}")

    def on_test_status_bar(self, event):
        """测试状态栏"""
        self.log_result("=== 开始状态栏测试 ===")

        try:
            if not self.status_bar_manager:
                self.log_result("❌ 状态栏管理器未初始化")
                return

            # 测试基本功能
            if self.status_bar_manager.is_available():
                self.log_result("✅ 状态栏可用")
            else:
                self.log_result("❌ 状态栏不可用")
                return

            # 测试临时消息
            self.log_result("测试临时消息显示...")
            self.status_bar_manager.show_temporary_message("测试消息", 0, 2000)
            time.sleep(1)

            # 测试设备状态更新
            self.status_bar_manager.update_device_status("测试设备")
            self.log_result("✅ 设备状态更新测试")

            # 测试操作提示
            self.status_bar_manager.update_operation_tip("测试提示: Ctrl+X执行测试")
            self.log_result("✅ 操作提示更新测试")

            # 测试成功/错误消息
            self.status_bar_manager.show_success_message("测试成功")
            time.sleep(1)
            self.status_bar_manager.show_error_message("测试错误")
            time.sleep(1)

            # 重置状态
            self.status_bar_manager.reset_to_idle()
            self.log_result("✅ 状态栏重置完成")

            self.log_result("✅ 状态栏测试完成")

        except Exception as e:
            self.log_result(f"❌ 状态栏测试异常: {e}")

    def on_test_play_control(self, event):
        """测试播放控制"""
        self.log_result("=== 开始播放控制测试 ===")

        try:
            if not self.audio_controller:
                self.log_result("❌ 音频控制器未初始化")
                return

            # 测试基本控制
            self.log_result("测试播放控制命令...")

            # 测试播放状态
            is_playing = self.audio_controller.is_playing()
            is_paused = self.audio_controller.is_paused()
            self.log_result(f"当前状态: 播放={is_playing}, 暂停={is_paused}")

            # 测试音量控制
            self.log_result("测试音量控制...")
            original_volume = self.audio_controller.get_audio_player().get_volume()

            # 增加音量
            self.audio_controller.increase_volume(10)
            time.sleep(0.5)

            # 减少音量
            self.audio_controller.decrease_volume(10)
            time.sleep(0.5)

            # 恢复原音量
            self.audio_controller.get_audio_player().set_volume(original_volume)

            self.log_result("✅ 音量控制测试完成")

            # 测试静音功能
            self.log_result("测试静音功能...")
            self.audio_controller.toggle_mute()
            time.sleep(1)
            self.audio_controller.toggle_mute()  # 取消静音

            self.log_result("✅ 静音功能测试完成")

            # 测试快进快退（即使没有播放也要测试API）
            self.log_result("测试快进快退功能...")
            self.audio_controller.seek_forward(5)
            self.audio_controller.seek_backward(5)

            self.log_result("✅ 播放控制测试完成")

        except Exception as e:
            self.log_result(f"❌ 播放控制测试异常: {e}")

    def on_select_audio_file(self, event):
        """选择音频文件测试"""
        self.log_result("=== 开始音频文件测试 ===")

        try:
            if not self.audio_controller:
                self.log_result("❌ 音频控制器未初始化")
                return

            # 文件选择对话框
            wildcard = "音频文件 (*.mp3;*.wav;*.flac;*.ogg;*.m4a)|*.mp3;*.wav;*.flac;*.ogg;*.m4a|所有文件 (*.*)|*.*"
            dialog = wx.FileDialog(self, "选择音频文件", wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)

            if dialog.ShowModal() == wx.ID_CANCEL:
                self.log_result("用户取消了文件选择")
                dialog.Destroy()
                return

            file_path = dialog.GetPath()
            dialog.Destroy()

            self.log_result(f"选择的文件: {file_path}")

            # 测试加载和播放
            if self.audio_controller.load_and_play_file(file_path):
                self.log_result("✅ 文件加载成功")

                # 等待一段时间让播放开始
                time.sleep(2)

                # 检查播放状态
                if self.audio_controller.is_playing():
                    self.log_result("✅ 播放开始成功")

                    # 测试暂停
                    time.sleep(2)
                    if self.audio_controller.pause():
                        self.log_result("✅ 暂停成功")
                        time.sleep(1)

                        # 测试恢复
                        if self.audio_controller.play():
                            self.log_result("✅ 恢复播放成功")
                        else:
                            self.log_result("❌ 恢复播放失败")
                    else:
                        self.log_result("❌ 暂停失败")

                    # 等待一段时间
                    time.sleep(3)

                    # 停止播放
                    if self.audio_controller.stop():
                        self.log_result("✅ 停止播放成功")
                    else:
                        self.log_result("❌ 停止播放失败")
                else:
                    self.log_result("❌ 播放未开始")
            else:
                self.log_result("❌ 文件加载失败")

            self.log_result("✅ 音频文件测试完成")

        except Exception as e:
            self.log_result(f"❌ 音频文件测试异常: {e}")

    def on_clear_results(self, event):
        """清除测试结果"""
        self.result_text.Clear()
        self.log_result("测试结果已清除")


def main():
    """主函数"""
    try:
        # 创建wxPython应用
        app = wx.App()

        # 创建测试窗口
        frame = EnhancedAudioTestFrame()
        frame.Center()
        frame.Show()

        # 运行应用
        app.MainLoop()

    except Exception as e:
        print(f"运行测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()