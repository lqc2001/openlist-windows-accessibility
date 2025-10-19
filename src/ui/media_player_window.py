#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
媒体播放器窗口
无障碍音视频播放器界面
"""

import wx
import os
import time
from src.core.logger import get_logger
from src.core.version import VERSION
from src.media.audio_player import AudioPlayer
from src.media.accessibility_manager import AccessibilityManager
from src.media.file_detector import MediaFileDetector


class MediaPlayerWindow(wx.Frame):
    """媒体播放器主窗口"""

    def __init__(self, parent=None, file_path: str = None):
        """
        初始化播放器窗口

        Args:
            parent: 父窗口
            file_path: 要播放的文件路径
        """
        style = wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER)  # 禁止调整大小
        title = f"媒体播放器 v{VERSION}"
        super().__init__(parent, title=title, size=(600, 400), style=style)

        self.logger = get_logger()
        self.file_path = file_path

        # 初始化组件
        self.audio_player = None
        self.accessibility_manager = None

        # UI控件
        self.play_button = None
        self.pause_button = None
        self.stop_button = None
        self.progress_slider = None
        self.time_label = None
        self.volume_slider = None
        self.volume_label = None
        self.mute_button = None
        self.file_label = None
        self.status_bar = None

        # 播放状态
        self.is_playing = False
        self.is_paused = False
        self.update_timer = None

        # 初始化无障碍管理器（必须在UI创建之前）
        try:
            self.accessibility_manager = AccessibilityManager(self)
            try:
                self.accessibility_manager.set_status_callback(self.update_status)
            except Exception as callback_error:
                self.logger.warning(f"设置无障碍状态回调失败: {callback_error}")
            self.logger.debug("无障碍管理器初始化成功")
        except Exception as e:
            self.logger.error(f"无障碍管理器初始化失败: {e}")
            self.accessibility_manager = None

        # 初始化界面
        self._initialize_ui()
        self._setup_accelerators()
        self._initialize_player()

        # 居中显示
        self.Center()

        # 如果有文件路径，自动加载
        if self.file_path:
            wx.CallAfter(self.load_and_play_file, self.file_path)

        self.logger.debug("媒体播放器窗口初始化完成")

    def _initialize_ui(self):
        """初始化用户界面"""
        # 创建主面板
        main_panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # 文件信息区域
        self._create_file_info_panel(main_panel, main_sizer)

        # 播放控制区域
        self._create_control_panel(main_panel, main_sizer)

        # 进度控制区域
        self._create_progress_panel(main_panel, main_sizer)

        # 音量控制区域
        self._create_volume_panel(main_panel, main_sizer)

        # 底部按钮区域
        self._create_button_panel(main_panel, main_sizer)

        main_panel.SetSizer(main_sizer)

        # 创建状态栏
        self.status_bar = self.CreateStatusBar(1)
        self.status_bar.SetStatusText("准备就绪")

        # 绑定窗口事件
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_ACTIVATE, self.on_activate)

    def _setup_accessibility(self, control, name, help_text, shortcut=""):
        """设置控件无障碍属性的安全方法"""
        try:
            if self.accessibility_manager:
                self.accessibility_manager.setup_control_accessibility(control, name, help_text, shortcut)
        except Exception as e:
            self.logger.warning(f"设置控件无障碍属性失败 ({name}): {e}")

    def _announce(self, message, priority=False):
        """播报消息的安全方法"""
        if self.accessibility_manager:
            self.accessibility_manager.announce(message, priority)
        elif self.status_bar:
            self.status_bar.SetStatusText(message)

    def _safe_announce_method(self, method_name, *args):
        """安全调用无障碍管理器方法"""
        if self.accessibility_manager and hasattr(self.accessibility_manager, method_name):
            method = getattr(self.accessibility_manager, method_name)
            try:
                method(*args)
            except Exception as e:
                self.logger.warning(f"无障碍方法调用失败 {method_name}: {e}")
        else:
            # 降级到基本状态栏显示
            if args:
                self._announce(str(args[0]))

    def _create_file_info_panel(self, parent, sizer):
        """创建文件信息面板"""
        file_panel = wx.Panel(parent)
        file_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # 文件名标签
        self.file_label = wx.StaticText(file_panel, label="未加载文件")
        font = self.file_label.GetFont()
        font.SetPointSize(10)
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        self.file_label.SetFont(font)

        file_sizer.Add(self.file_label, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 10)
        file_panel.SetSizer(file_sizer)

        # 设置无障碍属性
        try:
            self._setup_accessibility(
                self.file_label,
                "文件信息",
                "显示当前播放文件的名称"
            )
        except Exception as e:
            self.logger.warning(f"设置文件标签无障碍属性失败: {e}")

        sizer.Add(file_panel, 0, wx.EXPAND | wx.ALL, 5)

    def _create_control_panel(self, parent, sizer):
        """创建播放控制面板"""
        control_panel = wx.Panel(parent)
        control_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # 播放按钮
        self.play_button = wx.Button(control_panel, label="播放(&P)")
        self.pause_button = wx.Button(control_panel, label="暂停(&A)")
        self.stop_button = wx.Button(control_panel, label="停止(&S)")

        # 添加到sizer
        control_sizer.Add(self.play_button, 0, wx.ALL, 5)
        control_sizer.Add(self.pause_button, 0, wx.ALL, 5)
        control_sizer.Add(self.stop_button, 0, wx.ALL, 5)

        # 设置无障碍属性
        try:
            self._setup_accessibility(
                self.play_button,
                "播放按钮",
                "开始播放当前文件",
                "Alt+P"
            )
            self._setup_accessibility(
                self.pause_button,
                "暂停按钮",
                "暂停或恢复播放",
                "Alt+A"
            )
            self._setup_accessibility(
                self.stop_button,
                "停止按钮",
                "停止播放",
                "Alt+S"
            )
        except Exception as e:
            self.logger.warning(f"设置控制按钮无障碍属性失败: {e}")

        control_panel.SetSizer(control_sizer)
        sizer.Add(control_panel, 0, wx.CENTER | wx.ALL, 10)

        # 绑定按钮事件
        self.play_button.Bind(wx.EVT_BUTTON, self.on_play)
        self.pause_button.Bind(wx.EVT_BUTTON, self.on_pause)
        self.stop_button.Bind(wx.EVT_BUTTON, self.on_stop)

    def _create_progress_panel(self, parent, sizer):
        """创建进度控制面板"""
        progress_panel = wx.Panel(parent)
        progress_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # 时间标签
        self.time_label = wx.StaticText(progress_panel, label="00:00 / 00:00")
        self.time_label.SetMinSize((100, -1))

        # 进度滑块
        self.progress_slider = wx.Slider(
            progress_panel,
            value=0,
            minValue=0,
            maxValue=100,
            style=wx.SL_HORIZONTAL
        )
        self.progress_slider.SetMinSize((300, -1))

        # 添加到sizer
        progress_sizer.Add(self.time_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        progress_sizer.Add(self.progress_slider, 1, wx.EXPAND)

        # 设置无障碍属性
        self._setup_accessibility(
            self.time_label,
            "播放时间",
            "显示当前播放时间和总时长"
        )
        self._setup_accessibility(
            self.progress_slider,
            "播放进度条",
            "控制播放进度，左右方向键调节",
            "左右方向键"
        )

        progress_panel.SetSizer(progress_sizer)
        sizer.Add(progress_panel, 0, wx.EXPAND | wx.ALL, 10)

        # 绑定进度条事件
        self.progress_slider.Bind(wx.EVT_SLIDER, self.on_progress_change)

    def _create_volume_panel(self, parent, sizer):
        """创建音量控制面板"""
        volume_panel = wx.Panel(parent)
        volume_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # 音量标签
        self.volume_label = wx.StaticText(volume_panel, label="音量: 100%")
        self.volume_label.SetMinSize((80, -1))

        # 音量滑块
        self.volume_slider = wx.Slider(
            volume_panel,
            value=100,
            minValue=0,
            maxValue=100,
            style=wx.SL_HORIZONTAL
        )
        self.volume_slider.SetMinSize((150, -1))

        # 静音按钮
        self.mute_button = wx.Button(volume_panel, label="静音(&M)")

        # 添加到sizer
        volume_sizer.Add(self.volume_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        volume_sizer.Add(self.volume_slider, 1, wx.EXPAND | wx.RIGHT, 10)
        volume_sizer.Add(self.mute_button, 0, wx.ALIGN_CENTER_VERTICAL)

        # 设置无障碍属性
        self._setup_accessibility(
            self.volume_label,
            "音量显示",
            "显示当前音量大小"
        )
        self._setup_accessibility(
            self.volume_slider,
            "音量控制",
            "调节播放音量，上下方向键调节",
            "上下方向键"
        )
        self._setup_accessibility(
            self.mute_button,
            "静音按钮",
            "切换静音状态",
            "Alt+M"
        )

        volume_panel.SetSizer(volume_sizer)
        sizer.Add(volume_panel, 0, wx.EXPAND | wx.ALL, 10)

        # 绑定音量控制事件
        self.volume_slider.Bind(wx.EVT_SLIDER, self.on_volume_change)
        self.mute_button.Bind(wx.EVT_BUTTON, self.on_mute_toggle)

    def _create_button_panel(self, parent, sizer):
        """创建底部按钮面板"""
        button_panel = wx.Panel(parent)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # 功能按钮
        self.open_button = wx.Button(button_panel, label="打开文件(&O)")
        self.help_button = wx.Button(button_panel, label="帮助(&H)")

        # 添加到sizer
        button_sizer.AddStretchSpacer()
        button_sizer.Add(self.open_button, 0, wx.ALL, 5)
        button_sizer.Add(self.help_button, 0, wx.ALL, 5)
        button_sizer.AddStretchSpacer()

        # 设置无障碍属性
        self._setup_accessibility(
            self.open_button,
            "打开文件按钮",
            "选择要播放的媒体文件",
            "Alt+O"
        )
        self._setup_accessibility(
            self.help_button,
            "帮助按钮",
            "显示使用帮助信息",
            "Alt+H"
        )

        button_panel.SetSizer(button_sizer)
        sizer.Add(button_panel, 0, wx.EXPAND | wx.ALL, 10)

        # 绑定按钮事件
        self.open_button.Bind(wx.EVT_BUTTON, self.on_open_file)
        self.help_button.Bind(wx.EVT_BUTTON, self.on_help)

    def _setup_accelerators(self):
        """设置快捷键"""
        accel_table = wx.AcceleratorTable([
            (wx.ACCEL_NORMAL, wx.WXK_SPACE, wx.ID_HIGHEST + 1),      # 空格键 - 播放/暂停
            (wx.ACCEL_NORMAL, wx.WXK_RETURN, wx.ID_HIGHEST + 1),     # 回车键 - 播放/暂停
            (wx.ACCEL_NORMAL, ord('S'), wx.ID_HIGHEST + 2),          # S键 - 停止
            (wx.ACCEL_NORMAL, wx.WXK_LEFT, wx.ID_HIGHEST + 3),       # 左箭头 - 快退5秒
            (wx.ACCEL_NORMAL, wx.WXK_RIGHT, wx.ID_HIGHEST + 4),      # 右箭头 - 快进5秒
            (wx.ACCEL_CTRL, wx.WXK_LEFT, wx.ID_HIGHEST + 5),         # Ctrl+左箭头 - 快退30秒
            (wx.ACCEL_CTRL, wx.WXK_RIGHT, wx.ID_HIGHEST + 6),        # Ctrl+右箭头 - 快进30秒
            (wx.ACCEL_NORMAL, wx.WXK_UP, wx.ID_HIGHEST + 7),         # 上箭头 - 增加音量
            (wx.ACCEL_NORMAL, wx.WXK_DOWN, wx.ID_HIGHEST + 8),       # 下箭头 - 减少音量
            (wx.ACCEL_NORMAL, ord('M'), wx.ID_HIGHEST + 9),          # M键 - 静音
            (wx.ACCEL_NORMAL, ord('O'), wx.ID_HIGHEST + 10),         # O键 - 打开文件
            (wx.ACCEL_NORMAL, wx.WXK_F1, wx.ID_HIGHEST + 11),        # F1键 - 帮助
            (wx.ACCEL_NORMAL, wx.WXK_ESCAPE, wx.ID_HIGHEST + 12),     # Esc键 - 退出
        ])

        self.SetAcceleratorTable(accel_table)

        # 绑定快捷键事件
        self.Bind(wx.EVT_MENU, self.on_play_pause_hotkey, id=wx.ID_HIGHEST + 1)
        self.Bind(wx.EVT_MENU, self.on_stop_hotkey, id=wx.ID_HIGHEST + 2)
        self.Bind(wx.EVT_MENU, self.on_seek_backward_hotkey, id=wx.ID_HIGHEST + 3)
        self.Bind(wx.EVT_MENU, self.on_seek_forward_hotkey, id=wx.ID_HIGHEST + 4)
        self.Bind(wx.EVT_MENU, self.on_seek_backward_30_hotkey, id=wx.ID_HIGHEST + 5)
        self.Bind(wx.EVT_MENU, self.on_seek_forward_30_hotkey, id=wx.ID_HIGHEST + 6)
        self.Bind(wx.EVT_MENU, self.on_volume_up_hotkey, id=wx.ID_HIGHEST + 7)
        self.Bind(wx.EVT_MENU, self.on_volume_down_hotkey, id=wx.ID_HIGHEST + 8)
        self.Bind(wx.EVT_MENU, self.on_mute_hotkey, id=wx.ID_HIGHEST + 9)
        self.Bind(wx.EVT_MENU, self.on_open_file, id=wx.ID_HIGHEST + 10)
        self.Bind(wx.EVT_MENU, self.on_help, id=wx.ID_HIGHEST + 11)
        self.Bind(wx.EVT_MENU, self.on_close, id=wx.ID_HIGHEST + 12)

    def _initialize_player(self):
        """初始化音频播放器"""
        try:
            self.audio_player = AudioPlayer()

            # 设置播放器回调
            self.audio_player.set_play_callback(self.on_player_play)
            self.audio_player.set_pause_callback(self.on_player_pause)
            self.audio_player.set_stop_callback(self.on_player_stop)
            self.audio_player.set_time_update_callback(self.on_time_update)
            self.audio_player.set_error_callback(self.on_player_error)

            # 启动更新定时器
            self.update_timer = wx.Timer(self)
            self.Bind(wx.EVT_TIMER, self.on_update_timer, self.update_timer)
            self.update_timer.Start(1000)  # 每秒更新一次

            self.logger.info("音频播放器初始化成功")

        except Exception as e:
            self.logger.error(f"音频播放器初始化失败: {e}")
            self._announce("播放器初始化失败，请检查VLC是否正确安装", True)

    def load_and_play_file(self, file_path: str):
        """
        加载并播放文件

        Args:
            file_path: 文件路径（本地路径或网络URL）
        """
        try:
            # 检查文件类型（支持本地文件和网络URL）
            if file_path.startswith(('http://', 'https://')):
                # 网络URL，跳过文件存在性检查
                self.logger.info(f"加载网络URL: {file_path}")
                # 从URL提取文件名
                filename = file_path.split('/')[-1]
                if '?' in filename:
                    filename = filename.split('?')[0]  # 移除查询参数
                if not filename:
                    filename = "网络媒体文件"
            else:
                # 本地文件，检查是否存在
                if not os.path.exists(file_path):
                    self._announce("文件不存在，请检查文件路径", True)
                    return
                filename = os.path.basename(file_path)

            # 检查文件类型（对于网络URL，基于扩展名判断）
            if not MediaFileDetector.is_media_file(filename):
                self._announce("不支持的文件格式，请选择音频或视频文件", True)
                return

            # 更新文件显示
            self.file_label.SetLabel(filename)
            self.file_path = file_path  # 保存文件路径

            # 播放文件
            self.logger.info(f"开始播放: {filename}")
            if self.audio_player.load_and_play(file_path):
                self._announce(f"正在加载: {filename}")
                self.status_bar.SetStatusText(f"正在播放: {filename}")
            else:
                self._announce("文件加载失败，请检查文件是否损坏", True)
                self.status_bar.SetStatusText("加载失败")

        except Exception as e:
            self.logger.error(f"加载播放文件失败: {e}")
            self._announce(f"播放失败: {e}", True)
            self.status_bar.SetStatusText(f"播放失败: {str(e)}")

    # 事件处理方法
    def on_play(self, event):
        """播放按钮事件"""
        self.play_media()

    def on_pause(self, event):
        """暂停按钮事件"""
        self.pause_media()

    def on_stop(self, event):
        """停止按钮事件"""
        self.stop_media()

    def on_open_file(self, event):
        """打开文件事件"""
        self.show_open_file_dialog()

    def on_help(self, event):
        """帮助事件"""
        self.show_help()

    def on_close(self, event):
        """窗口关闭事件"""
        self.cleanup()
        if self.GetParent():
            self.Hide()
        else:
            self.Destroy()

    def on_activate(self, event):
        """窗口激活事件"""
        if event.GetActive():
            # 窗口激活时播报当前状态
            self._safe_announce_method("announce_focus_change")
        event.Skip()

    def on_progress_change(self, event):
        """进度条变化事件"""
        if self.audio_player:
            position = self.progress_slider.GetValue() / 100.0
            self.audio_player.set_position(position)

    def on_volume_change(self, event):
        """音量变化事件"""
        if self.audio_player:
            volume = self.volume_slider.GetValue()
            self.audio_player.set_volume(volume)
            self.volume_label.SetLabel(f"音量: {volume}%")
            if self.accessibility_manager:
                try:
                    self.accessibility_manager.announce_volume_status(volume, self.audio_player.is_mute())
                except Exception as e:
                    self.logger.warning(f"无障碍音量播报失败: {e}")
                    self._announce(f"音量: {volume}%")
            else:
                self._announce(f"音量: {volume}%")

    def on_mute_toggle(self, event):
        """静音切换事件"""
        if self.audio_player:
            self.audio_player.toggle_mute()
            self.update_ui_state()

    def on_update_timer(self, event):
        """定时更新事件"""
        if self.audio_player and (self.is_playing or self.is_paused):
            self.update_progress_display()

    # 播放器回调事件
    def on_player_play(self):
        """播放器播放回调"""
        self.is_playing = True
        self.is_paused = False
        self.update_ui_state()
        if self.file_path:
            filename = os.path.basename(self.file_path)
            self._safe_announce_method("announce_playback_status", 'playing', filename)

    def on_player_pause(self):
        """播放器暂停回调"""
        self.is_playing = False
        self.is_paused = True
        self.update_ui_state()
        self._safe_announce_method("announce_playback_status", 'paused')

    def on_player_stop(self):
        """播放器停止回调"""
        self.is_playing = False
        self.is_paused = False
        self.update_ui_state()
        self._safe_announce_method("announce_playback_status", 'stopped')

    def on_time_update(self, time_ms):
        """时间更新回调"""
        self.update_progress_display()

    def on_player_error(self, error_msg):
        """播放器错误回调"""
        self._safe_announce_method("announce_error", error_msg)

    # 快捷键事件处理
    def on_play_pause_hotkey(self, event):
        """播放/暂停快捷键"""
        if self.is_playing:
            self.pause_media()
        else:
            self.play_media()

    def on_stop_hotkey(self, event):
        """停止快捷键"""
        self.stop_media()

    def on_seek_backward_hotkey(self, event):
        """快退5秒快捷键"""
        if self.audio_player:
            self.audio_player.seek_backward(5)
            self._safe_announce_method("announce_seek_status", 'backward', 5)

    def on_seek_forward_hotkey(self, event):
        """快进5秒快捷键"""
        if self.audio_player:
            self.audio_player.seek_forward(5)
            self._safe_announce_method("announce_seek_status", 'forward', 5)

    def on_seek_backward_30_hotkey(self, event):
        """快退30秒快捷键"""
        if self.audio_player:
            self.audio_player.seek_backward(30)
            self._safe_announce_method("announce_seek_status", 'backward', 30)

    def on_seek_forward_30_hotkey(self, event):
        """快进30秒快捷键"""
        if self.audio_player:
            self.audio_player.seek_forward(30)
            self._safe_announce_method("announce_seek_status", 'forward', 30)

    def on_volume_up_hotkey(self, event):
        """增加音量快捷键"""
        if self.audio_player:
            current_volume = self.audio_player.get_volume()
            new_volume = min(100, current_volume + 5)
            self.audio_player.set_volume(new_volume)
            self.volume_slider.SetValue(new_volume)
            self.volume_label.SetLabel(f"音量: {new_volume}%")
            self._safe_announce_method("announce_volume_status", new_volume, self.audio_player.is_mute())

    def on_volume_down_hotkey(self, event):
        """减少音量快捷键"""
        if self.audio_player:
            current_volume = self.audio_player.get_volume()
            new_volume = max(0, current_volume - 5)
            self.audio_player.set_volume(new_volume)
            self.volume_slider.SetValue(new_volume)
            self.volume_label.SetLabel(f"音量: {new_volume}%")
            self._safe_announce_method("announce_volume_status", new_volume, self.audio_player.is_mute())

    def on_mute_hotkey(self, event):
        """静音快捷键"""
        self.on_mute_toggle(None)

    # 功能方法
    def play_media(self):
        """播放媒体"""
        if self.audio_player and not self.is_playing:
            if self.is_paused:
                self.audio_player.resume()
            elif self.file_path:
                self.audio_player.load_and_play(self.file_path)
            else:
                self.show_open_file_dialog()

    def pause_media(self):
        """暂停媒体"""
        if self.audio_player and self.is_playing:
            self.audio_player.pause()

    def stop_media(self):
        """停止媒体"""
        if self.audio_player:
            self.audio_player.stop()

    def show_open_file_dialog(self):
        """显示打开文件对话框"""
        wildcard = "媒体文件|*.mp3;*.wav;*.flac;*.aac;*.m4a;*.ogg;*.wma;*.mp4;*.avi;*.mkv;*.wmv;*.mov|All files (*.*)|*.*"

        dialog = wx.FileDialog(
            self,
            message="选择要播放的媒体文件",
            defaultDir=os.getcwd(),
            defaultFile="",
            wildcard=wildcard,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        )

        if dialog.ShowModal() == wx.ID_OK:
            file_path = dialog.GetPath()
            self.file_path = file_path
            self.load_and_play_file(file_path)

        dialog.Destroy()

    def show_help(self):
        """显示帮助信息"""
        help_text = "键盘快捷键:\n" \
                   "空格/回车 - 播放/暂停\n" \
                   "S - 停止\n" \
                   "左右方向键 - 快进/快退5秒\n" \
                   "Ctrl+左右方向键 - 快进/快退30秒\n" \
                   "上下方向键 - 调节音量\n" \
                   "M - 静音\n" \
                   "O - 打开文件\n" \
                   "F1 - 帮助\n" \
                   "Esc - 退出"

        dialog = wx.MessageDialog(
            self,
            help_text,
            "媒体播放器使用帮助",
            wx.OK | wx.ICON_INFORMATION
        )

        dialog.ShowModal()
        dialog.Destroy()

        self._announce("帮助信息已显示")

    def update_ui_state(self):
        """更新UI状态"""
        # 更新按钮状态
        self.play_button.Enable(not self.is_playing)
        self.pause_button.Enable(self.is_playing or self.is_paused)
        self.stop_button.Enable(self.is_playing or self.is_paused)

        # 更新按钮文本
        if self.is_paused:
            self.pause_button.SetLabel("恢复(&R)")
            self._setup_accessibility(
                self.pause_button,
                "恢复按钮",
                "恢复播放",
                "Alt+R"
            )
        else:
            self.pause_button.SetLabel("暂停(&A)")
            self._setup_accessibility(
                self.pause_button,
                "暂停按钮",
                "暂停播放",
                "Alt+A"
            )

        # 更新静音按钮
        if self.audio_player and self.audio_player.is_mute():
            self.mute_button.SetLabel("取消静音(&U)")
        else:
            self.mute_button.SetLabel("静音(&M)")

    def update_progress_display(self):
        """更新进度显示"""
        if self.audio_player:
            current_time = self.audio_player.get_current_time()
            total_time = self.audio_player.get_duration()

            current_str = self.audio_player.get_time_string(current_time)
            total_str = self.audio_player.get_time_string(total_time)
            self.time_label.SetLabel(f"{current_str} / {total_str}")

            if total_time > 0:
                position = (current_time / total_time) * 100
                self.progress_slider.SetValue(int(position))

    def update_status(self, message: str):
        """更新状态栏"""
        if self.status_bar:
            self.status_bar.SetStatusText(message)

    def cleanup(self):
        """清理资源"""
        try:
            if self.update_timer:
                self.update_timer.Stop()

            if self.audio_player:
                self.audio_player.cleanup()

            self.logger.info("媒体播放器窗口资源已清理")

        except Exception as e:
            self.logger.error(f"清理媒体播放器窗口资源失败: {e}")