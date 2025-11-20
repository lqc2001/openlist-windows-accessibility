#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频播放器窗口类 - 简化版本
"""

import wx
import logging
from urllib.parse import unquote
import time

from ..media.video_player import VideoPlayer
from ..core.logger import get_logger
from .audio_player_controller import AudioPlayerController


class VideoPlayerWindow(wx.Frame):
    """视频播放器窗口"""

    def __init__(self, parent, video_url, title=None, on_close_callback=None):
        """
        初始化视频播放器窗口

        Args:
            parent: 父窗口
            video_url: 视频文件URL
            title: 窗口标题
            on_close_callback: 关闭回调函数
        """
        super().__init__(parent, title=title or "视频播放器")

        # 设置日志记录器
        self.logger = get_logger()

        # 视频相关属性
        self.video_url = video_url
        self.window_title = title or self._extract_filename_from_url(video_url)
        self.video_player = None
        self.is_playing = False
        self.is_paused = False
        self.is_initialized = False

        # 进度更新相关
        self.progress_timer = None
        self.progress_update_interval = 500  # 500ms更新一次进度

        # 菜单状态跟踪
        self._menu_visible_time = 0
        self._alt_key_pressed = False

        # 播放进度信息显示控制
        self.show_progress_info = False  # 默认隐藏进度信息，提供完整的观影体验

        # 菜单项引用（用于动态更新）
        self.progress_info_menu_item = None

        # 临时退出全屏状态跟踪
        self._temporarily_exited_fullscreen = False
        self._fullscreen_restore_timer = None

        # 回调函数
        self.on_close_callback = on_close_callback

        # 音频控制器（用于Alt菜单的音频设备功能）
        self.audio_controller = AudioPlayerController(self)

        # 设置窗口属性
        self.SetBackgroundColour(wx.BLACK)

        # 设置可访问性标签
        self._setup_accessibility_labels()

        # 初始化UI
        self._create_ui()
        self._setup_video_player()  # 先创建播放器
        self._create_menu()  # 再创建菜单
        self._setup_event_handlers()

        # 绑定键盘事件
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.Bind(wx.EVT_CLOSE, self.on_close)

        # 设置初始窗口标题
        self.SetTitle(f"视频播放: {self.window_title}")

        # 先显示窗口，确保菜单栏可见
        self.Show(True)

        # 延迟进入全屏模式，确保菜单栏完全初始化
        wx.CallLater(100, self._delayed_fullscreen)

        # 自动开始播放
        if self.video_url:
            self._start_playback()

        self.logger.info("视频播放器窗口初始化完成")

    def _extract_filename_from_url(self, url: str) -> str:
        """
        从URL中提取文件名

        Args:
            url: 视频文件URL

        Returns:
            str: 解码后的文件名
        """
        try:
            if not url:
                return "未知文件"

            # 移除查询参数（如 ?sign=xxx）
            if '?' in url:
                url = url.split('?')[0]

            # URL解码
            decoded_url = unquote(url)

            # 提取文件名（最后一个斜杠后的部分）
            if '/' in decoded_url:
                filename = decoded_url.split('/')[-1]
            else:
                filename = decoded_url

            # 如果文件名为空，返回默认值
            if not filename or filename.isspace():
                return "未知文件"

            return filename

        except Exception as e:
            self.logger.error(f"提取文件名失败: {e}")
            return "未知文件"

    def _setup_accessibility_labels(self):
        """设置可访问性标签"""
        try:
            # 设置窗口名称（屏幕阅读器会朗读这个）
            if self.window_title:
                self.SetName(f"视频播放: {self.window_title}")
                self.SetHelpText(f"正在播放视频: {self.window_title}。使用空格键播放或暂停，ESC键退出。")
            else:
                self.SetName("视频播放器")
                self.SetHelpText("视频播放器。使用空格键播放或暂停，ESC键退出。")

            self.logger.debug("可访问性标签设置完成")

        except Exception as e:
            self.logger.error(f"设置可访问性标签失败: {e}")

    def _create_ui(self):
        """创建用户界面"""
        main_panel = wx.Panel(self)
        main_panel.SetBackgroundColour(wx.BLACK)

        # 使用垂直布局
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # 创建视频渲染面板（占据大部分空间）
        self.video_panel = wx.Panel(main_panel)
        self.video_panel.SetBackgroundColour(wx.BLACK)
        self.video_panel.SetMinSize((640, 360))  # 设置最小尺寸

        # 标题标签（可选显示）
        self.title_label = wx.StaticText(
            main_panel,
            label="视频播放中...",
            style=wx.ALIGN_CENTER
        )
        self.title_label.SetForegroundColour(wx.WHITE)
        font = wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        self.title_label.SetFont(font)

        # 进度显示（只显示时间百分比）
        self.time_label = wx.StaticText(
            main_panel,
            label="00:00 / 00:00",
            style=wx.ALIGN_CENTER
        )
        self.time_label.SetForegroundColour(wx.WHITE)
        time_font = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.time_label.SetFont(time_font)

        # 控制提示标签
        self.control_label = wx.StaticText(
            main_panel,
            label="空格键: 播放/暂停  |  ESC: 退出  |  Alt+P: 播放菜单  |  Alt+D: 音频设备  |  ←/→: 快进/快退  |  ↑/↓: 音量调节",
            style=wx.ALIGN_CENTER
        )
        self.control_label.SetForegroundColour(wx.WHITE)
        control_font = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.control_label.SetFont(control_font)

        # 添加到布局
        main_sizer.Add(self.video_panel, 1, wx.EXPAND | wx.ALL, 5)  # 视频面板占据所有可用空间
        main_sizer.Add(self.title_label, 0, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(self.time_label, 0, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(self.control_label, 0, wx.EXPAND | wx.ALL, 10)

        main_panel.SetSizer(main_sizer)

        # 默认隐藏进度信息，提供完整的观影体验
        self._update_progress_info_visibility()

        # 设置焦点以接收键盘事件
        self.SetFocus()

    def _create_video_device_submenu(self, parent_menu):
        """为视频播放器创建音频设备子菜单（恢复原有结构）

        Args:
            parent_menu: 父菜单对象

        Returns:
            wx.Menu: 设备选择子菜单
        """
        try:
            device_menu = wx.Menu()

            # 总是添加一个默认的"刷新设备列表"选项
            refresh_item = device_menu.Append(
                wx.ID_ANY,
                "刷新设备列表",
                "重新扫描音频设备"
            )
            self.Bind(wx.EVT_MENU, self._refresh_audio_devices, refresh_item)
            device_menu.AppendSeparator()

            # 尝试获取设备列表
            devices = []
            try:
                if self.video_player:
                    devices = self.video_player.get_available_audio_devices()
                    self.logger.debug(f"获取到{len(devices)}个音频设备")
                else:
                    self.logger.warning("video_player为None，无法获取音频设备")
            except Exception as e:
                self.logger.error(f"获取音频设备列表失败: {e}")

            # 添加设备选项
            if devices:
                # 为每个设备创建菜单项
                for device in devices:
                    device_name = device.get('name', '未知设备')
                    device_id = device.get('id', '')

                    # 限制设备名称长度
                    if len(device_name) > 40:
                        device_name = device_name[:37] + "..."

                    # 创建菜单项
                    device_item = device_menu.Append(
                        wx.ID_ANY,
                        device_name,
                        f"切换到音频设备: {device['name']}"
                    )

                    # 绑定设备切换事件
                    self.Bind(wx.EVT_MENU,
                            lambda event, dev=device: self.on_video_device_change(event, dev),
                            device_item)

                    # 标记当前设备
                    try:
                        current_device = self.video_player.get_current_audio_device_info()
                        if current_device and current_device.get('id') == device_id:
                            # 确保菜单项是可检查的，然后添加勾选标记
                            if device_item.IsCheckable():
                                device_item.Check(True)
                            else:
                                self.logger.debug(f"设备菜单项不可检查: {device_name}")
                    except Exception as e:
                        self.logger.debug(f"获取当前设备信息失败: {e}")

                self.logger.info(f"创建了{len(devices)}个音频设备选项")

            else:
                # 没有可用设备时添加提示项
                no_device_item = device_menu.Append(
                    wx.ID_ANY,
                    "无可用设备 (点击刷新)",
                    "未检测到可用的音频输出设备，点击刷新"
                )
                self.Bind(wx.EVT_MENU, self._refresh_audio_devices, no_device_item)

            # 确保菜单不为空
            if device_menu.GetMenuItemCount() == 0:
                fallback_item = device_menu.Append(
                    wx.ID_ANY,
                    "音频设备菜单",
                    "音频设备选项"
                )
                fallback_item.Enable(False)

            self.logger.info(f"音频设备子菜单创建完成，包含{device_menu.GetMenuItemCount()}个选项")
            return device_menu

        except Exception as e:
            self.logger.error(f"创建视频设备子菜单失败: {e}")
            # 返回一个基本的菜单，确保不会崩溃
            fallback_menu = wx.Menu()
            fallback_item = fallback_menu.Append(
                wx.ID_ANY,
                "音频设备",
                "音频设备选项"
            )
            fallback_item.Enable(False)
            return fallback_menu

    def _refresh_audio_devices(self, event):
        """刷新音频设备列表"""
        try:
            self.logger.info("正在刷新音频设备列表...")

            # 强制重新获取设备列表
            if self.video_player:
                devices = self.video_player.get_available_audio_devices(force_refresh=True)
                self.logger.info(f"刷新后获得{len(devices)}个音频设备")

                # 重新创建菜单（如果需要）
                if hasattr(self, 'device_menu') and self.device_menu:
                    # 这里可以添加菜单刷新逻辑
                    self.logger.debug("音频设备列表已刷新")
            else:
                self.logger.warning("video_player为空，无法刷新设备列表")

        except Exception as e:
            self.logger.error(f"刷新音频设备列表失败: {e}")

    def _create_audio_track_submenu(self, parent_menu):
        """为视频播放器创建音轨子菜单

        Args:
            parent_menu: 父菜单对象

        Returns:
            wx.Menu: 音轨选择子菜单
        """
        try:
            track_menu = wx.Menu()

            # 总是添加一个默认的"刷新音轨列表"选项
            refresh_item = track_menu.Append(
                wx.ID_ANY,
                "刷新音轨列表",
                "重新扫描音频轨道"
            )
            self.Bind(wx.EVT_MENU, self._refresh_audio_tracks, refresh_item)
            track_menu.AppendSeparator()

            # 尝试获取音轨列表
            tracks = []
            try:
                if self.video_player:
                    tracks = self.video_player.get_available_audio_tracks()
                    self.logger.debug(f"获取到{len(tracks)}个音频轨道")
                else:
                    self.logger.warning("video_player为None，无法获取音频轨道")
            except Exception as e:
                self.logger.error(f"获取音频轨道列表失败: {e}")

            # 添加音轨选项
            if tracks:
                # 为每个音轨创建菜单项
                for track in tracks:
                    track_name = track.get('name', '未知音轨')
                    track_id = track.get('id', 0)

                    # 限制音轨名称长度
                    if len(track_name) > 40:
                        track_name = track_name[:37] + "..."

                    # 创建菜单项 (使用RadioItem以支持勾选)
                    if len(tracks) > 1:
                        # 多个音轨时使用RadioItem
                        track_item = track_menu.AppendRadioItem(
                            wx.ID_ANY,
                            track_name,
                            f"切换到音频轨道: {track_name}"
                        )
                    else:
                        # 单个音轨时使用普通菜单项
                        track_item = track_menu.Append(
                            wx.ID_ANY,
                            track_name,
                            f"切换到音频轨道: {track_name}"
                        )

                    # 绑定音轨切换事件
                    self.Bind(wx.EVT_MENU,
                            lambda event, tid=track_id, tname=track_name: self.on_audio_track_change(event, tid, tname),
                            track_item)

                    # 标记当前音轨 (只对RadioItem生效)
                    try:
                        current_track_id = self.video_player.get_current_audio_track()
                        if current_track_id == track_id and len(tracks) > 1:
                            # 确保菜单项是可检查的，然后添加勾选标记
                            if track_item.IsCheckable():
                                track_item.Check(True)
                            else:
                                self.logger.debug(f"音轨菜单项不可检查: {track_name}")
                    except Exception as e:
                        self.logger.debug(f"获取当前音轨信息失败: {e}")

                self.logger.info(f"创建了{len(tracks)}个音轨选项")

            else:
                # 没有可用音轨时添加提示项
                no_track_item = track_menu.Append(
                    wx.ID_ANY,
                    "无可用音轨 (点击刷新)",
                    "未检测到可用的音频轨道，点击刷新"
                )
                self.Bind(wx.EVT_MENU, self._refresh_audio_tracks, no_track_item)

            # 确保菜单不为空
            if track_menu.GetMenuItemCount() == 0:
                fallback_item = track_menu.Append(
                    wx.ID_ANY,
                    "音轨菜单",
                    "音频轨道选项"
                )
                fallback_item.Enable(False)

            self.logger.info(f"音轨子菜单创建完成，包含{track_menu.GetMenuItemCount()}个选项")
            return track_menu

        except Exception as e:
            self.logger.error(f"创建音轨子菜单失败: {e}")
            # 返回一个基本的菜单，确保不会崩溃
            fallback_menu = wx.Menu()
            fallback_item = fallback_menu.Append(
                wx.ID_ANY,
                "音轨",
                "音频轨道选项"
            )
            fallback_item.Enable(False)
            return fallback_menu

    def _refresh_audio_tracks(self, event):
        """刷新音频轨道列表"""
        try:
            self.logger.info("[DEBUG] 用户手动刷新音频轨道列表...")
            if self.video_player:
                self._refresh_audio_tracks_menu()
            else:
                self.logger.warning("[DEBUG] video_player为空，无法刷新轨道列表")

        except Exception as e:
            self.logger.error(f"[DEBUG] 手动刷新音频轨道列表失败: {e}")

    def _refresh_audio_tracks_menu_fallback(self):
        """音轨菜单回退检测（确保VLC完全解析后的第二次检测）"""
        try:
            self.logger.info("[DEBUG] 执行音轨菜单回退检测（4000ms后）")

            if self.video_player:
                # 获取当前音轨数量
                tracks = self.video_player.get_available_audio_tracks()
                self.logger.info(f"[DEBUG] 回退检测获取到{len(tracks)}个音频轨道")

                # 如果还是没有音轨，再尝试一次
                if len(tracks) == 0:
                    self.logger.warning("[DEBUG] 4000ms后仍无音轨，可能该视频确实没有多音轨")
                else:
                    self.logger.info(f"[DEBUG] 4000ms后成功获取到音轨，详情:")
                    for i, track in enumerate(tracks):
                        self.logger.info(f"[DEBUG]   轨道{i+1}: ID={track.get('id')}, 名称={track.get('name')}")

                # 无论是否有音轨，都更新一次菜单
                self._refresh_audio_tracks_menu()
            else:
                self.logger.warning("[DEBUG] video_player为None，无法执行回退检测")

        except Exception as e:
            self.logger.error(f"[DEBUG] 音轨菜单回退检测失败: {e}")

    def _refresh_audio_tracks_menu(self):
        """刷新音轨菜单（内部方法）"""
        try:
            self.logger.info("[DEBUG] _refresh_audio_tracks_menu开始执行")

            if self.video_player:
                self.logger.info("[DEBUG] video_player存在，开始获取音轨列表")

                # 重新获取音轨列表
                tracks = self.video_player.get_available_audio_tracks()
                self.logger.info(f"[DEBUG] 获取到{len(tracks)}个音频轨道")

                if tracks:
                    self.logger.info("[DEBUG] 音轨详情:")
                    for i, track in enumerate(tracks):
                        self.logger.info(f"[DEBUG]   轨道{i+1}: ID={track.get('id')}, 名称={track.get('name')}")

                # 如果存在音轨菜单，重新创建
                if hasattr(self, 'track_menu') and self.track_menu:
                    self.logger.info("[DEBUG] 找到现有音轨菜单，准备更新")

                    # 找到播放菜单
                    menubar = self.GetMenuBar()
                    self.logger.info(f"[DEBUG] 菜单栏存在: {menubar is not None}")

                    if menubar:
                        play_menu = None
                        self.logger.info(f"[DEBUG] 菜单数量: {len(menubar.GetMenus())}")

                        for i, menu_info in enumerate(menubar.GetMenus()):
                            self.logger.info(f"[DEBUG] 菜单{i}: {menu_info}")
                            if isinstance(menu_info, tuple) and len(menu_info) == 2:
                                # 元组格式: (menu, title)
                                menu, title = menu_info
                                self.logger.info(f"[DEBUG] 菜单{i} 标题: {title}")
                                if title == "播放(&P)":
                                    play_menu = menu
                                    self.logger.info("[DEBUG] 找到播放菜单")
                                    break
                            else:
                                # 直接是Menu对象
                                if hasattr(menu_info, 'GetTitle'):
                                    title = menu_info.GetTitle()
                                    self.logger.info(f"[DEBUG] 菜单{i} 标题: {title}")
                                    if title == "播放(&P)":
                                        play_menu = menu_info
                                        self.logger.info("[DEBUG] 找到播放菜单")
                                        break
                                else:
                                    self.logger.info(f"[DEBUG] 菜单{i} 没有GetTitle方法")
                                    # 尝试通过其他方式识别菜单
                                    if hasattr(menu_info, 'GetMenuItemCount'):
                                        self.logger.info(f"[DEBUG] 菜单{i} 项目数: {menu_info.GetMenuItemCount()}")
                                        # 检查是否是播放菜单（通过菜单项目数量）
                                        if menu_info.GetMenuItemCount() > 10:  # 播放菜单项目较多
                                            play_menu = menu_info
                                            self.logger.info("[DEBUG] 通过项目数找到播放菜单")
                                            break

                        if play_menu:
                            self.logger.info(f"[DEBUG] 播放菜单项目数: {play_menu.GetMenuItemCount()}")

                            # 找到音轨子菜单的位置
                            track_menu_pos = -1
                            for i in range(play_menu.GetMenuItemCount()):
                                item = play_menu.FindItemByPosition(i)
                                if item:
                                    label = item.GetItemLabel()
                                    self.logger.info(f"[DEBUG] 菜单项{i}: {label}")
                                    if label.startswith("音轨(&T)"):
                                        track_menu_pos = i
                                        self.logger.info(f"[DEBUG] 找到音轨菜单位置: {i}")
                                        break

                            if track_menu_pos >= 0:
                                self.logger.info("[DEBUG] 开始重建音轨菜单")

                                # 获取当前的音轨菜单项
                                track_item = play_menu.FindItemByPosition(track_menu_pos)
                                if track_item:
                                    # 创建新的音轨菜单
                                    new_track_menu = self._create_audio_track_submenu(play_menu)

                                    # 替换子菜单项
                                    play_menu.Remove(track_item)
                                    new_item = play_menu.Insert(track_menu_pos, -1, "音轨(&T)", new_track_menu, "选择音频轨道")
                                    self.track_menu = new_track_menu

                                    self.logger.info("[DEBUG] 音轨菜单替换完成")
                                else:
                                    self.logger.warning("[DEBUG] 无法找到音轨菜单项")

                                return
                            else:
                                self.logger.warning("[DEBUG] 未找到音轨菜单位置")
                        else:
                            self.logger.warning("[DEBUG] 未找到播放菜单")
                    else:
                        self.logger.warning("[DEBUG] 菜单栏不存在")
                else:
                    self.logger.warning("[DEBUG] 没有找到track_menu属性")
            else:
                self.logger.warning("[DEBUG] video_player为空")

        except Exception as e:
            self.logger.error(f"[DEBUG] 刷新音轨菜单失败: {e}")
            import traceback
            self.logger.error(f"[DEBUG] 异常详情: {traceback.format_exc()}")

    def on_audio_track_change(self, event, track_id, track_name):
        """音频轨道切换事件处理

        Args:
            event: wx菜单事件
            track_id: 轨道ID
            track_name: 轨道名称
        """
        try:
            if self.video_player:
                self.logger.info(f"尝试切换到音频轨道: {track_name} (ID: {track_id})")

                # 切换轨道
                result = self.video_player.set_audio_track(track_id)

                if result:
                    self.logger.info(f"成功切换到音频轨道: {track_name}")

                    # 显示切换成功的临时消息
                    self._show_track_change_message(track_name)

                    # 菜单操作完成，安排全屏恢复
                    self._on_menu_operation_complete()

                else:
                    self.logger.warning(f"切换音频轨道失败: {track_name}")

            else:
                self.logger.warning("视频播放器未创建，无法切换音频轨道")

        except Exception as e:
            self.logger.error(f"音频轨道切换失败: {e}")

    def _show_track_change_message(self, track_name):
        """显示音轨切换成功的临时消息

        Args:
            track_name: 轨道名称
        """
        try:
            # 更新窗口标题临时显示轨道切换信息
            original_title = self.GetTitle()
            self.SetTitle(f"已切换到: {track_name}")

            # 2秒后恢复原标题
            wx.CallLater(2000, lambda: self.SetTitle(original_title))

        except Exception as e:
            self.logger.error(f"显示音轨切换消息失败: {e}")

    def on_video_device_change(self, event, device):
        """视频音频设备切换事件处理

        Args:
            event: wx菜单事件
            device: 设备信息字典
        """
        try:
            if self.video_player:
                device_name = device.get('name', '未知设备')
                self.logger.info(f"尝试切换到音频设备: {device_name}")

                # 切换设备
                result = self.video_player.set_audio_device(device)

                if result:
                    self.logger.info(f"成功切换到音频设备: {device_name}")

                    # 更新菜单显示（刷新勾选状态）
                    self._refresh_device_menu(device)

                else:
                    self.logger.warning(f"切换音频设备失败: {device_name}")
                    # 可以在这里显示用户友好的错误消息

            else:
                self.logger.warning("视频播放器未创建，无法切换音频设备")

        except Exception as e:
            self.logger.error(f"音频设备切换失败: {e}")

    def on_switch_to_next_device(self, event):
        """切换到下一个音频设备"""
        try:
            if self.video_player:
                # 获取可用设备列表
                devices = self.video_player.get_available_audio_devices()

                if len(devices) > 1:
                    # 获取当前设备
                    current_device = self.video_player.get_current_audio_device_info()
                    current_id = current_device.get('id', '') if current_device else ''

                    # 找到当前设备的索引
                    current_index = -1
                    for i, device in enumerate(devices):
                        if device.get('id', '') == current_id:
                            current_index = i
                            break

                    # 计算下一个设备索引（循环）
                    next_index = (current_index + 1) % len(devices)
                    next_device = devices[next_index]

                    # 切换到下一个设备
                    self.logger.info(f"切换到下一个音频设备: {next_device.get('name', '未知设备')}")
                    result = self.video_player.set_audio_device(next_device)

                    if result:
                        self.logger.info(f"成功切换到音频设备: {next_device.get('name', '未知设备')}")
                        # 可以添加成功提示，比如更新窗口标题或显示临时消息
                        self._show_device_change_message(next_device.get('name', '未知设备'))
                    else:
                        self.logger.warning(f"切换音频设备失败: {next_device.get('name', '未知设备')}")

                else:
                    self.logger.info("只有一个或没有可用设备，无需切换")

            else:
                self.logger.warning("视频播放器未创建，无法切换音频设备")

        except Exception as e:
            self.logger.error(f"切换到下一个设备失败: {e}")

    def _temporarily_exit_fullscreen_for_menu(self):
        """临时退出全屏模式以显示完整菜单"""
        try:
            if self.IsFullScreen() and not self._temporarily_exited_fullscreen:
                self.logger.info("临时退出全屏模式以显示菜单")

                # 退出全屏
                self.ShowFullScreen(False)
                self._temporarily_exited_fullscreen = True

                # 强制刷新菜单栏
                menubar = self.GetMenuBar()
                if menubar:
                    menubar.Refresh()
                    wx.Yield()  # 让UI更新

                # 设置定时器，在用户完成操作后恢复全屏
                self._schedule_fullscreen_restore()

                # 手动触发菜单显示
                self._force_menu_display()

        except Exception as e:
            # 优雅处理已删除对象
            if "has been deleted" in str(e):
                self.logger.debug("视频窗口对象已被销毁，忽略全屏操作")
            else:
                self.logger.error(f"临时退出全屏失败: {e}")

    def _force_menu_display(self):
        """强制显示菜单"""
        try:
            # 确保窗口有焦点
            self.SetFocus()
            self.Raise()

            # 刷新菜单栏
            menubar = self.GetMenuBar()
            if menubar:
                menubar.Refresh()
                # 多次刷新确保菜单显示
                for i in range(3):
                    wx.CallLater(50 * i, lambda: menubar.Refresh() if menubar else None)

            self.logger.debug("强制菜单显示完成")

        except Exception as e:
            self.logger.error(f"强制菜单显示失败: {e}")

    def _schedule_fullscreen_restore(self):
        """安排全屏恢复"""
        try:
            # 取消之前的定时器
            if self._fullscreen_restore_timer:
                self._fullscreen_restore_timer.Stop()

            # 设置新的定时器，10秒后恢复全屏
            self._fullscreen_restore_timer = wx.Timer(self)
            self.Bind(wx.EVT_TIMER, self._on_fullscreen_restore_timer, self._fullscreen_restore_timer)
            self._fullscreen_restore_timer.Start(10000)  # 10秒

            self.logger.debug("已安排全屏恢复定时器 (10秒)")

        except Exception as e:
            self.logger.error(f"安排全屏恢复失败: {e}")

    def _on_fullscreen_restore_timer(self, event):
        """全屏恢复定时器事件"""
        try:
            self._restore_fullscreen_after_menu()

            # 停止定时器
            if self._fullscreen_restore_timer:
                self._fullscreen_restore_timer.Stop()
                self._fullscreen_restore_timer = None

        except Exception as e:
            self.logger.error(f"全屏恢复定时器处理失败: {e}")

    def _restore_fullscreen_after_menu(self):
        """菜单操作完成后恢复全屏"""
        try:
            if self._temporarily_exited_fullscreen:
                self.logger.info("恢复全屏模式")

                # 重新进入全屏
                self.ShowFullScreen(True)
                self._temporarily_exited_fullscreen = False

                self.logger.debug("全屏模式已恢复")

        except Exception as e:
            self.logger.error(f"恢复全屏失败: {e}")

    def _on_menu_operation_complete(self):
        """菜单操作完成时调用"""
        try:
            # 安排更快的全屏恢复（3秒后）
            if self._fullscreen_restore_timer:
                self._fullscreen_restore_timer.Stop()

            self._fullscreen_restore_timer = wx.Timer(self)
            self.Bind(wx.EVT_TIMER, self._on_fullscreen_restore_timer, self._fullscreen_restore_timer)
            self._fullscreen_restore_timer.Start(3000)  # 3秒

            self.logger.debug("菜单操作完成，安排3秒后恢复全屏")

        except Exception as e:
            self.logger.error(f"菜单操作完成处理失败: {e}")

    def _show_device_change_message(self, device_name):
        """显示设备切换成功的临时消息

        Args:
            device_name: 设备名称
        """
        try:
            # 更新窗口标题临时显示设备切换信息
            original_title = self.GetTitle()
            self.SetTitle(f"已切换到: {device_name}")

            # 2秒后恢复原标题
            wx.CallLater(2000, lambda: self.SetTitle(original_title))

            # 菜单操作完成，安排全屏恢复
            self._on_menu_operation_complete()

        except Exception as e:
            self.logger.error(f"显示设备切换消息失败: {e}")

    def _refresh_device_menu(self, selected_device=None):
        """刷新设备菜单的勾选状态

        Args:
            selected_device: 当前选中的设备
        """
        try:
            if hasattr(self, 'device_menu') and self.device_menu:
                # 这里可以添加菜单状态刷新逻辑
                # 由于wxPython的菜单项状态管理比较复杂，暂时只记录日志
                self.logger.debug("设备菜单状态已刷新")

        except Exception as e:
            self.logger.error(f"刷新设备菜单失败: {e}")

    def _create_menu(self):
        """创建菜单栏（按照wxPython官方无障碍标准）"""
        menubar = wx.MenuBar()

        # 播放菜单
        play_menu = wx.Menu()

        # 音频设备子菜单（恢复原有结构）
        device_menu = self._create_video_device_submenu(play_menu)
        play_menu.AppendSubMenu(device_menu, "音频设备(&D)", "选择音频输出设备")
        self.device_menu = device_menu

        # 音轨子菜单
        track_menu = self._create_audio_track_submenu(play_menu)
        play_menu.AppendSubMenu(track_menu, "音轨(&T)", "选择音频轨道")
        self.track_menu = track_menu
        play_menu.AppendSeparator()

        # 播放控制（使用通用ID）
        play_pause_item = play_menu.Append(wx.ID_ANY, "播放/暂停(&P)", "播放或暂停当前视频")
        stop_item = play_menu.Append(wx.ID_ANY, "停止(&S)", "停止视频播放")
        play_menu.AppendSeparator()

        # 快进快退
        seek_backward_item = play_menu.Append(wx.ID_ANY, "快退5秒(&J)\tLeft", "快退5秒")
        seek_forward_item = play_menu.Append(wx.ID_ANY, "快进5秒(&L)\tRight", "快进5秒")
        play_menu.AppendSeparator()

        # 音量控制
        volume_up_item = play_menu.Append(wx.ID_ANY, "音量增加(&U)\tUp", "增加音量")
        volume_down_item = play_menu.Append(wx.ID_ANY, "音量减少(&D)\tDown", "减少音量")
        play_menu.AppendSeparator()

        # 播放信息控制
        self.progress_info_menu_item = play_menu.Append(wx.ID_ANY, "显示播放信息", "显示所有播放信息（标题、时间进度、控制提示等）")
        play_menu.AppendSeparator()

        # 倍速选择（简化）
        speed_menu = wx.Menu()
        speed_0_5x = speed_menu.AppendRadioItem(wx.ID_ANY, "0.5倍速(&5)", "0.5倍播放速度")
        speed_1_0x = speed_menu.AppendRadioItem(wx.ID_ANY, "1.0倍速(&1)", "正常播放速度")
        speed_1_5x = speed_menu.AppendRadioItem(wx.ID_ANY, "1.5倍速(&2)", "1.5倍播放速度")
        speed_2_0x = speed_menu.AppendRadioItem(wx.ID_ANY, "2.0倍速(&3)", "2倍播放速度")
        speed_3_0x = speed_menu.AppendRadioItem(wx.ID_ANY, "3.0倍速(&4)", "3倍播放速度")

        # 默认选择1.0倍速
        speed_1_0x.Check(True)

        play_menu.AppendSubMenu(speed_menu, "播放倍速(&S)", "选择播放倍速")

        # 帮助菜单
        help_menu = wx.Menu()
        controls_help_item = help_menu.Append(wx.ID_HELP, "控制说明(&C)", "显示播放控制说明")
        help_menu.AppendSeparator()
        about_item = help_menu.Append(wx.ID_ABOUT, "关于(&A)", "关于视频播放器")

        # 添加到菜单栏
        menubar.Append(play_menu, "播放(&P)")
        menubar.Append(help_menu, "帮助(&H)")

        # 按照wxPython官方标准设置菜单栏
        self.SetMenuBar(menubar)

        # 绑定菜单事件（使用标准wxPython事件ID）
        self.Bind(wx.EVT_MENU, self.on_play_pause, play_pause_item)
        self.Bind(wx.EVT_MENU, self.on_stop, stop_item)
        self.Bind(wx.EVT_MENU, self.on_seek_backward, seek_backward_item)
        self.Bind(wx.EVT_MENU, self.on_seek_forward, seek_forward_item)
        self.Bind(wx.EVT_MENU, self.on_volume_up, volume_up_item)
        self.Bind(wx.EVT_MENU, self.on_volume_down, volume_down_item)
        self.Bind(wx.EVT_MENU, self.on_toggle_progress_info, self.progress_info_menu_item)
        self.Bind(wx.EVT_MENU, self.on_speed_0_5, speed_0_5x)
        self.Bind(wx.EVT_MENU, self.on_speed_1_0, speed_1_0x)
        self.Bind(wx.EVT_MENU, self.on_speed_1_5, speed_1_5x)
        self.Bind(wx.EVT_MENU, self.on_speed_2_0, speed_2_0x)
        self.Bind(wx.EVT_MENU, self.on_speed_3_0, speed_3_0x)
        self.Bind(wx.EVT_MENU, self.on_controls_help, controls_help_item)
        self.Bind(wx.EVT_MENU, self.on_about, about_item)

        # 绑定标准wxPython事件
        self.Bind(wx.EVT_MENU, self.on_standard_help, id=wx.ID_HELP)
        self.Bind(wx.EVT_MENU, self.on_standard_about, id=wx.ID_ABOUT)

        # 初始化菜单项状态
        self._update_progress_info_menu_text()

        self.logger.info("标准菜单栏创建完成")

    def _delayed_fullscreen(self):
        """延迟进入全屏模式，确保菜单栏完全初始化"""
        try:
            # 强制刷新菜单栏多次确保初始化
            menubar = self.GetMenuBar()
            if menubar:
                for i in range(3):  # 多次刷新确保初始化
                    menubar.Refresh()
                    wx.Yield()  # 让UI更新
                    self.SetMenuBar(menubar)
                    time.sleep(0.01)  # 10毫秒延迟

            # 再次延迟确保菜单完全初始化
            wx.CallLater(200, self._final_fullscreen)
            self.logger.info("延迟全屏准备完成")

        except Exception as e:
            self.logger.error(f"延迟全屏失败: {e}")

    def _final_fullscreen(self):
        """最终进入全屏模式"""
        try:
            # 最后一次确保菜单栏状态
            menubar = self.GetMenuBar()
            if menubar:
                menubar.Refresh()
                self.SetMenuBar(menubar)

            # 进入全屏模式
            self.ShowFullScreen(True)
            self.logger.info("全屏模式已最终激活")

        except Exception as e:
            self.logger.error(f"最终全屏失败: {e}")

    def _setup_video_player(self):
        """设置视频播放器"""
        try:
            self.video_player = VideoPlayer()

            # 设置视频渲染窗口
            if hasattr(self, 'video_panel'):
                # 获取视频面板的窗口句柄
                window_handle = self.video_panel.GetHandle()
                if window_handle:
                    success = self.video_player.set_video_window(window_handle)
                    if success:
                        self.logger.info(f"视频窗口设置成功，句柄: {window_handle}")
                    else:
                        self.logger.warning(f"视频窗口设置失败，句柄: {window_handle}")
                else:
                    self.logger.warning("无法获取视频面板句柄")

            # 设置回调函数
            self.video_player.set_play_callback(self._on_video_play)
            self.video_player.set_pause_callback(self._on_video_pause)
            self.video_player.set_stop_callback(self._on_video_stop)
            self.video_player.set_error_callback(self._on_video_error)
            self.video_player.set_finished_callback(self._on_video_finished)

            self.logger.info("视频播放器初始化成功")

        except Exception as e:
            self.logger.error(f"设置视频播放器失败: {e}")
            self._show_error_message(f"视频播放器初始化失败: {e}")

    def _setup_event_handlers(self):
        """设置事件处理器"""
        try:
            # 绑定窗口事件
            self.Bind(wx.EVT_ACTIVATE, self.on_activate)
            self.Bind(wx.EVT_SHOW, self.on_show)

            self.logger.debug("事件处理器设置完成")

        except Exception as e:
            self.logger.error(f"设置事件处理器失败: {e}")

    def _start_playback(self):
        """开始播放"""
        try:
            if self.video_player and self.video_url:
                success = self.video_player.load_and_play(self.video_url, fullscreen=False)  # 不强制全屏，因为窗口已经是全屏
                if success:
                    self.logger.info(f"开始播放视频: {self.window_title}")
                    # 设置播放状态并更新标题
                    self.is_playing = True
                    self.is_paused = False
                    self._update_display()
                else:
                    raise Exception("视频加载失败")

        except Exception as e:
            self.logger.error(f"开始播放失败: {e}")
            self._show_error_message(f"播放视频失败: {e}")

    def _update_display(self):
        """更新显示"""
        try:
            # 更新窗口标题
            if self.is_playing:
                self.SetTitle(f"正在播放: {self.window_title}")
                title_text = f"正在播放: {self.window_title}"
            elif self.is_paused:
                self.SetTitle(f"已暂停: {self.window_title}")
                title_text = f"已暂停: {self.window_title}"
            else:
                self.SetTitle(f"视频播放: {self.window_title}")
                title_text = f"准备播放: {self.window_title}"

            # 更新界面标签
            if self.title_label:
                self.title_label.SetLabel(title_text)

        except Exception as e:
            self.logger.error(f"更新显示失败: {e}")

    def _update_progress(self):
        """更新时间显示"""
        try:
            if self.video_player and self.is_initialized:
                current_time = self.video_player.get_current_time()
                duration = self.video_player.get_duration()

                if duration > 0:
                    # 更新时间显示
                    current_str = self.video_player.get_time_string(current_time)
                    duration_str = self.video_player.get_time_string(duration)
                    self.time_label.SetLabel(f"{current_str} / {duration_str}")
                else:
                    # 如果没有总时长，只显示当前时间
                    current_str = self.video_player.get_time_string(current_time)
                    self.time_label.SetLabel(f"{current_str} / --:--")

        except Exception as e:
            self.logger.error(f"更新进度失败: {e}")

    def _start_progress_timer(self):
        """开始进度更新定时器"""
        try:
            if self.progress_timer:
                self.progress_timer.Stop()
                self.progress_timer = None

            self.progress_timer = wx.Timer(self, self.progress_update_interval)
            self.Bind(wx.EVT_TIMER, self._on_progress_timer, self.progress_timer)
            self.progress_timer.Start(self.progress_update_interval)

            self.logger.info("进度更新定时器已启动")

        except Exception as e:
            self.logger.error(f"启动进度定时器失败: {e}")

    def _stop_progress_timer(self):
        """停止进度更新定时器"""
        try:
            if self.progress_timer:
                self.progress_timer.Stop()
                self.progress_timer = None
                self.Unbind(wx.EVT_TIMER)
                self.logger.info("进度更新定时器已停止")

        except Exception as e:
            self.logger.error(f"停止进度定时器失败: {e}")

    def _on_progress_timer(self, event):
        """定时器事件处理"""
        self._update_progress()

    def _show_error_message(self, message):
        """显示错误消息"""
        try:
            wx.MessageBox(message, "错误", wx.OK | wx.ICON_ERROR)
        except Exception as e:
            self.logger.error(f"显示错误消息失败: {e}")

    # 键盘事件处理（按照wxPython官方标准）
    def on_key_down(self, event):
        """键盘事件处理"""
        key_code = event.GetKeyCode()

        # Alt键 - 增强处理逻辑
        if key_code == wx.WXK_ALT:
            if not self._alt_key_pressed:  # 防止重复触发
                self._alt_key_pressed = True
                self._ensure_menu_visibility()
                # 在全屏模式下临时退出全屏以显示完整菜单
                self._temporarily_exit_fullscreen_for_menu()
                # 设置定时器重置Alt键状态
                wx.CallLater(200, self._reset_alt_key_state)
            event.Skip()
            return

        # 空格键 - 播放/暂停
        elif key_code == wx.WXK_SPACE:
            self._toggle_playback()

        # ESC键 - 直接退出播放器
        elif key_code == wx.WXK_ESCAPE:
            self._cleanup()
            wx.CallLater(50, self.Close)  # 延迟关闭以确保清理完成

        # 左箭头 - 快退
        elif key_code == wx.WXK_LEFT:
            self._seek_backward()
            self.logger.debug("左箭头 - 快退10秒")

        # 右箭头 - 快进
        elif key_code == wx.WXK_RIGHT:
            self._seek_forward()
            self.logger.debug("右箭头 - 快进10秒")

        # 上箭头 - 音量加
        elif key_code == wx.WXK_UP:
            self._volume_up()

        # 下箭头 - 音量减
        elif key_code == wx.WXK_DOWN:
            self._volume_down()

        # F11键 - 切换全屏
        elif key_code == wx.WXK_F11:
            self._toggle_fullscreen()

        else:
            # 让wxPython原生处理其他按键
            event.Skip()

    def _reset_alt_key_state(self):
        """重置Alt键状态"""
        self._alt_key_pressed = False

    def _ensure_menu_visibility(self):
        """确保菜单栏在全屏模式下可见（增强版）"""
        try:
            current_time = time.time()

            # 防止过于频繁的菜单显示
            if current_time - self._menu_visible_time < 0.5:
                self.logger.debug("菜单显示过于频繁，跳过")
                return

            menubar = self.GetMenuBar()
            if menubar:
                # 如果在全屏模式下，临时退出以显示菜单
                if self.IsFullScreen():
                    self.logger.info("临时退出全屏显示菜单")
                    self.ShowFullScreen(False)

                    # 强制刷新菜单栏
                    for i in range(2):
                        menubar.Refresh()
                        self.SetMenuBar(menubar)
                        wx.Yield()
                        time.sleep(0.01)

                    # 设置菜单可见时间
                    self._menu_visible_time = current_time

                    # 重新进入全屏，延迟足够时间让用户看到菜单
                    wx.CallLater(800, self._restore_fullscreen)
                else:
                    menubar.Refresh()

            self.logger.debug("菜单可见性已强制刷新")
        except Exception as e:
            # 只在这里添加优雅的错误处理
            if "has been deleted" in str(e):
                self.logger.debug("菜单对象已被销毁，忽略操作")
            else:
                self.logger.error(f"强制菜单可见性失败: {e}")

    def _restore_fullscreen(self):
        """恢复全屏模式"""
        try:
            if not self.IsFullScreen():
                self.ShowFullScreen(True)
                self.logger.info("全屏模式已恢复")
        except Exception as e:
            # 优雅处理已删除对象
            if "has been deleted" in str(e):
                self.logger.debug("窗口对象已销毁，忽略全屏恢复")
            else:
                self.logger.error(f"恢复全屏失败: {e}")

    # 播放控制方法
    def _toggle_playback(self):
        """切换播放/暂停"""
        try:
            if self.video_player:
                if self.is_playing:
                    self.video_player.pause()
                else:
                    self.video_player.play()
        except Exception as e:
            self.logger.error(f"切换播放状态失败: {e}")

    def _stop_playback(self):
        """停止播放"""
        try:
            if self.video_player:
                self.video_player.stop()
                self.is_playing = False
                self.is_paused = False
                self._update_display()
        except Exception as e:
            self.logger.error(f"停止播放失败: {e}")

    def _seek_backward(self):
        """快退"""
        try:
            if self.video_player:
                # 检查是否有视频内容
                duration = self.video_player.get_duration()
                current_time = self.video_player.get_current_time()

                if duration <= 0 or current_time < 0:
                    self.logger.info("无视频内容或视频未开始播放，快退无效")
                    return

                if self.video_player.is_paused() or self.video_player.player_core.is_playing():
                    self.logger.debug(f"快退10秒 - 当前时间: {current_time}ms, 总时长: {duration}ms")
                    result = self.video_player.seek_backward(10)  # 快退10秒

                    if result:
                        new_time = self.video_player.get_current_time()
                        self.logger.info(f"快退成功 - 新时间: {new_time}ms")
                        # 强制更新进度显示
                        self._update_progress()
                    else:
                        self.logger.warning("快退操作失败")
                else:
                    self.logger.info("视频未播放，快退无效")
            else:
                self.logger.warning("video_player为空，无法快退")
        except Exception as e:
            self.logger.error(f"快退失败: {e}")
            import traceback
            self.logger.debug(f"快退异常详情: {traceback.format_exc()}")

    def _seek_forward(self):
        """快进"""
        try:
            if self.video_player:
                # 检查是否有视频内容
                duration = self.video_player.get_duration()
                current_time = self.video_player.get_current_time()

                if duration <= 0 or current_time < 0:
                    self.logger.info("无视频内容或视频未开始播放，快进无效")
                    return

                if self.video_player.is_paused() or self.video_player.player_core.is_playing():
                    self.logger.debug(f"快进10秒 - 当前时间: {current_time}ms, 总时长: {duration}ms")
                    result = self.video_player.seek_forward(10)  # 快进10秒

                    if result:
                        new_time = self.video_player.get_current_time()
                        self.logger.info(f"快进成功 - 新时间: {new_time}ms")
                        # 强制更新进度显示
                        self._update_progress()
                    else:
                        self.logger.warning("快进操作失败")
                else:
                    self.logger.info("视频未播放，快进无效")
            else:
                self.logger.warning("video_player为空，无法快进")
        except Exception as e:
            self.logger.error(f"快进失败: {e}")
            import traceback
            self.logger.debug(f"快进异常详情: {traceback.format_exc()}")

    def _volume_up(self):
        """音量增加"""
        try:
            if self.video_player:
                current_volume = self.video_player.get_volume()
                new_volume = min(100, current_volume + 10)
                self.video_player.set_volume(new_volume)
        except Exception as e:
            self.logger.error(f"增加音量失败: {e}")

    def _volume_down(self):
        """音量减少"""
        try:
            if self.video_player:
                current_volume = self.video_player.get_volume()
                new_volume = max(0, current_volume - 10)
                self.video_player.set_volume(new_volume)
        except Exception as e:
            self.logger.error(f"减少音量失败: {e}")

    def _toggle_fullscreen(self):
        """切换全屏模式"""
        try:
            if self.IsFullScreen():
                self.ShowFullScreen(False)
                self.logger.info("退出全屏模式")
            else:
                self.ShowFullScreen(True)
                self.logger.info("进入全屏模式")
        except Exception as e:
            self.logger.error(f"切换全屏模式失败: {e}")

    def _exit_fullscreen(self):
        """退出全屏并关闭"""
        try:
            if self.IsFullScreen():
                self.ShowFullScreen(False)
            wx.CallLater(100, self.Close)  # 延迟关闭以确保全屏退出完成
        except Exception as e:
            self.logger.error(f"退出全屏失败: {e}")
            self.Close()

    # 播放进度信息显示控制方法
    def _toggle_progress_info(self, show=None):
        """切换播放信息显示

        Args:
            show: 可选，True显示，False隐藏，None表示切换
        """
        if show is not None:
            self.show_progress_info = show
        else:
            self.show_progress_info = not self.show_progress_info

        # 更新界面可见性
        self._update_progress_info_visibility()

        # 更新菜单项文本
        self._update_progress_info_menu_text()

        self.logger.info(f"播放信息显示状态: {'显示' if self.show_progress_info else '隐藏'}")

    def _update_progress_info_visibility(self):
        """更新播放进度信息可见性"""
        try:
            # 控制所有播放相关信息显示（包括视频标题、时间进度、控制提示）
            # 只有窗口标题栏保持显示播放状态
            if hasattr(self, 'title_label'):
                self.title_label.Show(self.show_progress_info)

            if hasattr(self, 'time_label'):
                self.time_label.Show(self.show_progress_info)

            if hasattr(self, 'control_label'):
                self.control_label.Show(self.show_progress_info)

            # 刷新布局
            if hasattr(self, 'main_panel'):
                self.main_panel.Layout()
                self.main_panel.Refresh()

            self.logger.debug(f"播放信息可见性更新完成: {'显示' if self.show_progress_info else '隐藏'}")

        except Exception as e:
            self.logger.error(f"更新播放信息可见性失败: {e}")

    def _show_progress_info(self):
        """显示播放进度信息"""
        self._toggle_progress_info(show=True)

    def _hide_progress_info(self):
        """隐藏播放进度信息"""
        self._toggle_progress_info(show=False)

    def _update_progress_info_menu_text(self):
        """更新播放信息菜单项的文本"""
        try:
            if self.progress_info_menu_item:
                if self.show_progress_info:
                    self.progress_info_menu_item.SetItemLabel("隐藏播放信息")
                    self.progress_info_menu_item.SetHelpText("隐藏所有播放信息（标题、时间进度、控制提示等）")
                else:
                    self.progress_info_menu_item.SetItemLabel("显示播放信息")
                    self.progress_info_menu_item.SetHelpText("显示所有播放信息（标题、时间进度、控制提示等）")
        except Exception as e:
            self.logger.error(f"更新播放信息菜单项文本失败: {e}")

    # 菜单事件处理方法
    
    # 视频播放器的菜单事件处理方法
    def on_play_pause(self, event):
        """播放/暂停菜单事件"""
        try:
            if self.video_player and self.is_initialized:
                if self.is_playing:
                    self.video_player.pause()
                    self.is_playing = False
                    self.is_paused = True
                else:
                    self.video_player.play()
                    self.is_playing = True
                    self.is_paused = False
                self._update_display()
                self.logger.info("菜单播放/暂停操作完成")
                self._on_menu_operation_complete()  # 安排全屏恢复
            else:
                self.logger.warning("视频播放器未初始化，无法播放/暂停")
                self._on_menu_operation_complete()  # 也要安排全屏恢复
        except Exception as e:
            self.logger.error(f"菜单播放/暂停失败: {e}")
            self._on_menu_operation_complete()  # 也要安排全屏恢复

    def on_stop(self, event):
        """停止菜单事件"""
        try:
            self._stop_playback()
            self.logger.info("菜单停止操作完成")
            self._on_menu_operation_complete()  # 安排全屏恢复
        except Exception as e:
            self.logger.error(f"菜单停止失败: {e}")
            self._on_menu_operation_complete()  # 也要安排全屏恢复

    
    def on_seek_backward(self, event):
        """快退菜单事件"""
        try:
            self._seek_backward()
            self.logger.info("菜单快退操作完成")
            self._on_menu_operation_complete()  # 安排全屏恢复
        except Exception as e:
            self.logger.error(f"菜单快退失败: {e}")
            self._on_menu_operation_complete()  # 也要安排全屏恢复

    def on_seek_forward(self, event):
        """快进菜单事件"""
        try:
            self._seek_forward()
            self.logger.info("菜单快进操作完成")
        except Exception as e:
            self.logger.error(f"菜单快进失败: {e}")

    def on_volume_up(self, event):
        """音量增加菜单事件"""
        try:
            self._volume_up()
            self.logger.info("菜单音量增加操作完成")
        except Exception as e:
            self.logger.error(f"菜单音量增加失败: {e}")

    def on_volume_down(self, event):
        """音量减少菜单事件"""
        try:
            self._volume_down()
            self.logger.info("菜单音量减少操作完成")
        except Exception as e:
            self.logger.error(f"菜单音量减少失败: {e}")

    def on_toggle_progress_info(self, event):
        """切换播放信息显示的菜单事件"""
        try:
            self._toggle_progress_info()
            self.logger.info("菜单播放信息显示切换操作完成")
        except Exception as e:
            self.logger.error(f"菜单播放信息显示切换失败: {e}")

    def on_speed_0_5(self, event):
        """0.5倍速菜单事件"""
        try:
            if self.video_player and self.is_initialized:
                result = self.video_player.set_playback_rate(0.5)
                if result:
                    self.logger.info("菜单设置0.5倍速成功")
                else:
                    self.logger.warning("菜单设置0.5倍速失败")
            else:
                self.logger.warning("视频播放器未初始化，无法设置倍速")
        except Exception as e:
            self.logger.error(f"菜单设置0.5倍速失败: {e}")

    def on_speed_1_0(self, event):
        """1.0倍速菜单事件"""
        try:
            if self.video_player and self.is_initialized:
                result = self.video_player.set_playback_rate(1.0)
                if result:
                    self.logger.info("菜单设置1.0倍速成功")
                else:
                    self.logger.warning("菜单设置1.0倍速失败")
            else:
                self.logger.warning("视频播放器未初始化，无法设置倍速")
        except Exception as e:
            self.logger.error(f"菜单设置1.0倍速失败: {e}")

    def on_speed_1_5(self, event):
        """1.5倍速菜单事件"""
        try:
            if self.video_player and self.is_initialized:
                result = self.video_player.set_playback_rate(1.5)
                if result:
                    self.logger.info("菜单设置1.5倍速成功")
                else:
                    self.logger.warning("菜单设置1.5倍速失败")
            else:
                self.logger.warning("视频播放器未初始化，无法设置倍速")
        except Exception as e:
            self.logger.error(f"菜单设置1.5倍速失败: {e}")

    def on_speed_2_0(self, event):
        """2.0倍速菜单事件"""
        try:
            if self.video_player and self.is_initialized:
                result = self.video_player.set_playback_rate(2.0)
                if result:
                    self.logger.info("菜单设置2.0倍速成功")
                else:
                    self.logger.warning("菜单设置2.0倍速失败")
            else:
                self.logger.warning("视频播放器未初始化，无法设置倍速")
        except Exception as e:
            self.logger.error(f"菜单设置2.0倍速失败: {e}")

    def on_speed_3_0(self, event):
        """3.0倍速菜单事件"""
        try:
            if self.video_player and self.is_initialized:
                result = self.video_player.set_playback_rate(3.0)
                if result:
                    self.logger.info("菜单设置3.0倍速成功")
                else:
                    self.logger.warning("菜单设置3.0倍速失败")
            else:
                self.logger.warning("视频播放器未初始化，无法设置倍速")
        except Exception as e:
            self.logger.error(f"菜单设置3.0倍速失败: {e}")

    # 标准wxPython事件处理
    def on_standard_help(self, event):
        """标准帮助事件"""
        self.on_controls_help(event)

    def on_standard_about(self, event):
        """标准关于事件"""
        self.on_about(event)

    def on_controls_help(self, event):
        """控制说明菜单事件"""
        help_text = """视频播放控制说明：

基本控制：
- 空格键：播放/暂停
- ESC键：退出视频播放
- F11键：切换全屏模式

播放控制：
- 左箭头：快退10秒
- 右箭头：快进10秒
- 上箭头：音量增加
- 下箭头：音量减少

音频控制（Alt菜单）：
- Alt+P：播放菜单
- Alt+D：音频设备切换
- Ctrl+Home：播放/暂停音频
- Ctrl+End：停止音频
- Ctrl+PageUp/PageDown：上一首/下一首
- Ctrl+Left/Right：快进/快退5秒
- Ctrl+Up/Down：音量增减

其他功能：
- 全屏模式：点击菜单或按F11键切换
- 播放信息控制：点击菜单显示/隐藏所有播放信息（标题、时间进度、控制提示等）
- 截图功能：开发中

注意：默认隐藏所有播放信息以提供完全沉浸的观影体验，只有窗口标题栏显示播放状态。需要时可使用菜单显示详细播放信息。"""

        wx.MessageBox(help_text, "视频播放控制说明", wx.OK | wx.ICON_INFORMATION)

    def on_about(self, event):
        """菜单关于事件"""
        about_text = """OpenList 视频播放器

全屏视频播放器，支持：
- 基本的播放控制
- 全屏模式切换
- 键盘快捷键操作
- 音频设备切换

版本：1.0
更新：2025年11月11日"""

        wx.MessageBox(about_text, "关于视频播放器", wx.OK | wx.ICON_INFORMATION)

    # 窗口事件处理
    def on_activate(self, event):
        """窗口激活事件"""
        if event.GetActive():
            self.SetFocus()
        event.Skip()

    def on_show(self, event):
        """窗口显示事件"""
        self.SetFocus()
        event.Skip()

    def on_close(self, event):
        """窗口关闭事件"""
        try:
            self.logger.info("开始关闭视频播放器窗口")

            # 暂时注释掉我们的修改，恢复原始逻辑
            # self._cleanup_timers()

            self._cleanup()

            # 调用关闭回调函数
            if self.on_close_callback:
                self.on_close_callback()

            self.logger.info("视频播放器窗口关闭完成")
            event.Skip()
        except Exception as e:
            self.logger.error(f"关闭窗口时发生错误: {e}")
            event.Skip()

    # 视频播放器回调函数
    def _on_video_play(self):
        """视频播放回调"""
        self.logger.info("[DEBUG] _on_video_play回调被调用")
        self.is_playing = True
        self.is_paused = False
        self.is_initialized = True
        wx.CallAfter(self._update_display)
        wx.CallAfter(self._start_progress_timer)

        # 视频开始播放时，分阶段更新音轨菜单，确保VLC完全解析
        self.logger.info("[DEBUG] 准备分阶段刷新音轨菜单")
        # 第一次检测：2000ms后（通常VLC已经基本解析完成）
        wx.CallLater(2000, self._refresh_audio_tracks_menu)
        # 第二次检测：4000ms后（确保VLC完全解析，补充第一次可能遗漏的音轨）
        wx.CallLater(4000, self._refresh_audio_tracks_menu_fallback)

    def _on_video_pause(self):
        """视频暂停回调"""
        self.is_playing = False
        self.is_paused = True
        wx.CallAfter(self._update_display)
        wx.CallAfter(self._stop_progress_timer)

    def _on_video_stop(self):
        """视频停止回调"""
        self.is_playing = False
        self.is_paused = False
        self.is_initialized = False
        wx.CallAfter(self._update_display)
        wx.CallAfter(self._stop_progress_timer)

    def _on_video_error(self, error_msg: str):
        """视频错误回调"""
        self.logger.error(f"视频播放错误: {error_msg}")
        wx.CallAfter(self._show_error_message, error_msg)

    def _on_video_finished(self):
        """视频播放完成回调"""
        self.logger.info("视频播放完成")
        wx.CallAfter(self._exit_fullscreen)

    def _cleanup_timers(self):
        """清理所有活动定时器"""
        try:
            # 清理全屏恢复定时器 - 使用更安全的检查方式
            if hasattr(self, '_fullscreen_restore_timer'):
                try:
                    if self._fullscreen_restore_timer and hasattr(self._fullscreen_restore_timer, 'Stop'):
                        self._fullscreen_restore_timer.Stop()
                    self._fullscreen_restore_timer = None
                    self.logger.debug("全屏恢复定时器已清理")
                except Exception as timer_error:
                    self.logger.debug(f"清理全屏定时器时出错（可能是正常的）: {timer_error}")

            # 清理其他可能的定时器
            # 这里可以添加更多定时器的清理逻辑

        except Exception as e:
            self.logger.error(f"清理定时器失败: {e}")

    def _cleanup(self):
        """清理资源"""
        try:
            # 停止进度定时器
            self._stop_progress_timer()

            if self.video_player:
                self.video_player.stop()
                self.video_player.cleanup()
                self.video_player = None

            self.logger.info("视频播放器资源清理完成")

        except Exception as e:
            self.logger.error(f"清理视频播放器资源失败: {e}")

    def __del__(self):
        """析构函数"""
        self._cleanup()