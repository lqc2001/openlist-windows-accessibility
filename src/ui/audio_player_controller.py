#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频播放控制器
集成音频播放功能到主窗口，不打开新窗口
"""

import wx
import wx.lib.newevent
from typing import Optional, List, Callable
from src.core.logger import get_logger
from src.media.audio_player import AudioPlayer
from src.media.vlc_loader import VLCLoader

# 定义自定义事件
PlayerStatusEvent, EVT_PLAYER_STATUS = wx.lib.newevent.NewEvent()
PlayerProgressEvent, EVT_PLAYER_PROGRESS = wx.lib.newevent.NewEvent()


class AudioPlayerController:
    """音频播放控制器"""

    def __init__(self, parent_window):
        """
        初始化音频播放控制器

        Args:
            parent_window: 父窗口（主窗口）
        """
        self.parent_window = parent_window
        self.logger = get_logger()

        # 音频播放器
        self.audio_player = None
        self.is_initialized = False

        # 播放状态
        self.current_file = None
        self.current_filename = ""
        self.is_playing = False
        self.is_paused = False

        # 播放控制
        self.playback_rate = 1.0  # 播放倍速
        self.volume = 75  # 默认音量

        # 状态栏字段索引
        self.status_field = 0      # 播放状态和曲目名称
        self.time_field = 1        # 播放时间/总时间
        self.progress_field = 2    # 进度百分比
        self.volume_field = 3      # 音量
        self.speed_field = 4       # 倍速

        # 音频设备列表
        self.audio_devices = []
        self.current_device = None

        # 事件回调
        self.on_status_change_callback = None
        self.on_progress_change_callback = None

        # 初始化
        self._initialize_player()

    def _initialize_player(self):
        """初始化音频播放器"""
        try:
            self.audio_player = AudioPlayer()
            self.is_initialized = True

            # 设置回调
            self.audio_player.set_play_callback(self._on_play)
            self.audio_player.set_pause_callback(self._on_pause)
            self.audio_player.set_stop_callback(self._on_stop)
            self.audio_player.set_time_update_callback(self._on_time_update)
            self.audio_player.set_error_callback(self._on_error)

            # 设置初始音量
            self.audio_player.set_volume(self.volume)

            self.logger.info("音频播放控制器初始化成功")

        except Exception as e:
            self.logger.error(f"音频播放控制器初始化失败: {e}")
            self.is_initialized = False

    def set_status_bar(self, status_bar):
        """
        设置状态栏

        Args:
            status_bar: 状态栏对象
        """
        self.status_bar = status_bar
        self._update_status_bar()

    def set_status_change_callback(self, callback: Callable):
        """设置状态变化回调"""
        self.on_status_change_callback = callback

    def set_progress_change_callback(self, callback: Callable):
        """设置进度变化回调"""
        self.on_progress_change_callback = callback

    # 播放控制方法
    def play_file(self, file_path: str, filename: str = None) -> bool:
        """
        播放音频文件

        Args:
            file_path: 文件路径
            filename: 显示的文件名

        Returns:
            bool: 是否成功开始播放
        """
        if not self.is_initialized:
            self.logger.error("音频播放器未初始化")
            return False

        try:
            # 如果正在播放，先停止
            if self.is_playing or self.is_paused:
                self.stop()

            # 设置当前文件信息
            self.current_file = file_path
            self.current_filename = filename or file_path.split('/')[-1].split('\\')[-1]

            # 播放文件
            success = self.audio_player.load_and_play(file_path)
            if success:
                self.is_playing = True
                self.is_paused = False
                self._update_status_bar()
                self.logger.info(f"开始播放: {self.current_filename}")

                # 触发状态变化事件
                self._trigger_status_event("播放", self.current_filename)

            return success

        except Exception as e:
            self.logger.error(f"播放文件失败: {e}")
            return False

    def play_pause(self) -> bool:
        """播放/暂停切换"""
        if not self.is_initialized:
            return False

        try:
            if self.is_playing:
                return self.pause()
            elif self.is_paused:
                return self.resume()
            else:
                self.logger.debug("无正在播放的音频，忽略播放/暂停请求")
                return False

        except Exception as e:
            self.logger.error(f"播放/暂停失败: {e}")
            return False

    def pause(self) -> bool:
        """暂停播放"""
        if not self.is_initialized or not self.is_playing:
            return False

        try:
            success = self.audio_player.pause()
            if success:
                self.is_playing = False
                self.is_paused = True
                self._update_status_bar()
                self.logger.info("播放暂停")

                # 触发状态变化事件
                self._trigger_status_event("暂停", self.current_filename)

            return success

        except Exception as e:
            self.logger.error(f"暂停播放失败: {e}")
            return False

    def resume(self) -> bool:
        """恢复播放"""
        if not self.is_initialized or not self.is_paused:
            return False

        try:
            success = self.audio_player.resume()
            if success:
                self.is_playing = True
                self.is_paused = False
                self._update_status_bar()
                self.logger.info("恢复播放")

                # 触发状态变化事件
                self._trigger_status_event("播放", self.current_filename)

            return success

        except Exception as e:
            self.logger.error(f"恢复播放失败: {e}")
            return False

    def stop(self) -> bool:
        """停止播放"""
        if not self.is_initialized:
            return False

        try:
            success = self.audio_player.stop()
            if success:
                self.is_playing = False
                self.is_paused = False
                self.current_file = None
                self.current_filename = ""
                self._update_status_bar()
                self.logger.info("停止播放")

                # 触发状态变化事件
                self._trigger_status_event("停止", "")

            return success

        except Exception as e:
            self.logger.error(f"停止播放失败: {e}")
            return False

    def seek_forward(self, seconds: int = 5) -> bool:
        """快进"""
        if not self.is_initialized:
            return False

        try:
            success = self.audio_player.seek_forward(seconds)
            if success:
                self.logger.info(f"快进 {seconds} 秒")
            return success

        except Exception as e:
            self.logger.error(f"快进失败: {e}")
            return False

    def seek_backward(self, seconds: int = 5) -> bool:
        """快退"""
        if not self.is_initialized:
            return False

        try:
            success = self.audio_player.seek_backward(seconds)
            if success:
                self.logger.info(f"快退 {seconds} 秒")
            return success

        except Exception as e:
            self.logger.error(f"快退失败: {e}")
            return False

    def set_volume(self, volume: int) -> bool:
        """
        设置音量

        Args:
            volume: 音量值 (0-100)

        Returns:
            bool: 是否成功
        """
        if not self.is_initialized:
            return False

        volume = max(0, min(100, volume))  # 限制范围

        try:
            success = self.audio_player.set_volume(volume)
            if success:
                self.volume = volume
                self._update_status_bar()
                self.logger.info(f"音量设置为: {volume}%")

            return success

        except Exception as e:
            self.logger.error(f"设置音量失败: {e}")
            return False

    def volume_up(self, step: int = 5) -> bool:
        """音量增加"""
        return self.set_volume(self.volume + step)

    def volume_down(self, step: int = 5) -> bool:
        """音量减少"""
        return self.set_volume(self.volume - step)

    def get_volume(self) -> int:
        """获取当前音量"""
        return self.volume

    def set_playback_rate(self, rate: float) -> bool:
        """
        设置播放倍速

        Args:
            rate: 播放倍速

        Returns:
            bool: 是否成功
        """
        if not self.is_initialized:
            return False

        try:
            # VLC的倍速设置
            success = self.audio_player.player_core.set_rate(rate)
            if success:
                self.playback_rate = rate
                self._update_status_bar()
                self.logger.info(f"播放倍速设置为: {rate}x")
            return success

        except Exception as e:
            self.logger.error(f"设置播放倍速失败: {e}")
            return False

    def get_available_devices(self) -> List[dict]:
        """
        获取可用音频设备列表

        Returns:
            List[dict]: 音频设备列表，每个设备包含name和description
        """
        if not self.is_initialized:
            return []

        try:
            devices = self.audio_player.player_core.get_available_audio_devices()
            self.audio_devices = devices
            return devices
        except Exception as e:
            self.logger.error(f"获取音频设备列表失败: {e}")
            return [{"name": "默认设备", "description": "系统默认音频输出设备"}]

    def set_audio_device(self, device) -> bool:
        """
        设置音频设备

        Args:
            device: 设备信息字典或设备名称/ID

        Returns:
            bool: 是否成功
        """
        if not self.is_initialized:
            return False

        try:
            success = self.audio_player.player_core.set_audio_device(device)
            if success:
                info = self.audio_player.player_core.get_current_audio_device_info()
                self.current_device = info.get('name')
                self._update_status_bar()
                self.logger.info(f"音频设备已设置为: {self.current_device}")
            return success
        except Exception as e:
            self.logger.error(f"设置音频设备失败: {e}")
            return False

    def get_current_device(self) -> str:
        """获取当前音频设备"""
        if not self.is_initialized:
            return "默认设备"

        try:
            info = self.audio_player.player_core.get_current_audio_device_info()
            return info.get('name', '默认设备')
        except Exception as e:
            self.logger.error(f"获取当前音频设备失败: {e}")
            return "默认设备"

    def refresh_devices(self) -> List[dict]:
        """刷新音频设备列表"""
        if not self.is_initialized:
            return []

        try:
            devices = self.audio_player.player_core.refresh_audio_devices()
            self.audio_devices = devices
            return devices
        except Exception as e:
            self.logger.error(f"刷新音频设备列表失败: {e}")
            return []

    def create_device_menu(self, parent_menu):
        """
        创建音频设备子菜单

        Args:
            parent_menu: 父菜单对象
        """
        try:
            # 创建设备子菜单
            device_menu = wx.Menu()

            # 获取可用设备
            if not self.is_initialized:
                no_device_item = device_menu.Append(
                    wx.ID_ANY,
                    "播放器未初始化",
                    "音频播放功能尚未就绪"
                )
                no_device_item.Enable(False)
                return device_menu

            devices = self.get_available_devices()
            current_info = self.audio_player.player_core.get_current_audio_device_info()
            current_key = (current_info.get('module'), current_info.get('id'))

            for device in devices:
                device_name = device.get('name') or "未命名设备"
                device_desc = device.get('description') or ""
                module_name = device.get('module')
                device_id = device.get('id')

                if device_desc and device_desc != device_name:
                    label = f"{device_name} - {device_desc}"
                else:
                    label = device_name

                help_text = "切换音频输出设备"
                if device.get('is_default'):
                    help_text = "恢复系统默认音频输出设备"
                elif module_name:
                    help_text += f" (模块: {module_name})"

                menu_item = device_menu.AppendRadioItem(wx.ID_ANY, label, help_text)

                if (module_name, device_id) == current_key or (device.get('is_default') and current_key == (None, None)):
                    menu_item.Check(True)

                self.parent_window.Bind(
                    wx.EVT_MENU,
                    lambda event, info=device: self._on_device_selected(info),
                    menu_item
                )

            if not devices:
                device_menu.Append(wx.ID_SEPARATOR)
                no_device_item = device_menu.Append(
                    wx.ID_ANY,
                    "无可用设备",
                    "未检测到音频输出设备"
                )
                no_device_item.Enable(False)

            return device_menu

        except Exception as e:
            self.logger.error(f"创建设备菜单失败: {e}")
            return wx.Menu()

    def _on_device_selected(self, device):
        """
        设备选择事件处理

        Args:
            device: 选择的设备信息
        """
        try:
            success = self.set_audio_device(device)
            device_name = device.get('name') if isinstance(device, dict) else str(device)
            if success:
                if hasattr(self.parent_window, "_update_status"):
                    try:
                        self.parent_window._update_status(f"音频设备已切换到: {device_name}")
                    except Exception as status_err:
                        self.logger.debug(f"更新状态栏时发生异常: {status_err}")
            else:
                self.logger.error(f"切换音频设备失败: {device_name}")
                if hasattr(self.parent_window, "_update_status"):
                    try:
                        self.parent_window._update_status(f"切换音频设备失败: {device_name}")
                    except Exception as status_err:
                        self.logger.debug(f"更新状态栏时发生异常: {status_err}")
        except Exception as e:
            self.logger.error(f"处理设备选择事件失败: {e}")
            if hasattr(self.parent_window, "_update_status"):
                try:
                    self.parent_window._update_status(f"设备切换时发生错误: {e}")
                except Exception as status_err:
                    self.logger.debug(f"更新状态栏时发生异常: {status_err}")

    # 状态和进度方法
    def get_current_time(self) -> int:
        """获取当前播放时间（毫秒）"""
        if not self.is_initialized:
            return 0
        return self.audio_player.get_current_time()

    def get_duration(self) -> int:
        """获取总时长（毫秒）"""
        if not self.is_initialized:
            return 0
        return self.audio_player.get_duration()

    def get_progress_percentage(self) -> float:
        """获取播放进度百分比"""
        if not self.is_initialized:
            return 0.0

        current_time = self.get_current_time()
        duration = self.get_duration()

        if duration == 0:
            return 0.0

        return (current_time / duration) * 100

    def format_time(self, time_ms: int) -> str:
        """格式化时间显示 (MM:SS)"""
        if not self.is_initialized or time_ms <= 0:
            return "00:00"

        return self.audio_player.get_time_string(time_ms)

    def _update_status_bar(self):
        """更新状态栏显示 - 仅显示音频播放相关信息"""
        if not hasattr(self, 'status_bar') or not self.status_bar:
            return

        try:
            # 播放状态和曲目名称
            if self.is_playing:
                status_text = f"播放: {self.current_filename}"
            elif self.is_paused:
                status_text = f"暂停: {self.current_filename}"
            else:
                status_text = "停止"

            # 播放时间/总时间
            current_time = self.format_time(self.get_current_time())
            total_time = self.format_time(self.get_duration())
            time_text = f"{current_time}/{total_time}"

            # 进度百分比
            progress = self.get_progress_percentage()
            progress_text = f"{progress:.1f}%"

            # 音量和当前设备
            current_device = self.get_current_device()
            volume_text = f"音量:{self.volume}% [{current_device}]"

            # 倍速
            speed_text = f"{self.playback_rate}x"

            # 更新状态栏 - 5个字段全部用于音频播放功能
            self.status_bar.SetStatusText(status_text, self.status_field)     # 播放状态
            self.status_bar.SetStatusText(time_text, self.time_field)         # 播放时间
            self.status_bar.SetStatusText(progress_text, self.progress_field) # 播放进度
            self.status_bar.SetStatusText(volume_text, self.volume_field)     # 音量和设备
            self.status_bar.SetStatusText(speed_text, self.speed_field)       # 播放倍速

        except Exception as e:
            self.logger.error(f"更新状态栏失败: {e}")

    # 事件处理
    def _on_play(self):
        """播放事件回调"""
        self.is_playing = True
        self.is_paused = False
        self._update_status_bar()
        self._trigger_status_event("播放", self.current_filename)

    def _on_pause(self):
        """暂停事件回调"""
        self.is_playing = False
        self.is_paused = True
        self._update_status_bar()
        self._trigger_status_event("暂停", self.current_filename)

    def _on_stop(self):
        """停止事件回调"""
        self.is_playing = False
        self.is_paused = False
        self._update_status_bar()
        self._trigger_status_event("停止", "")

    def _on_time_update(self, time_ms):
        """时间更新事件回调"""
        self._update_status_bar()

        # 触发进度变化事件
        if self.on_progress_change_callback:
            wx.PostEvent(self.parent_window, PlayerProgressEvent(
                current_time=time_ms,
                duration=self.get_duration(),
                progress=self.get_progress_percentage()
            ))

    def _on_error(self, error_msg):
        """错误事件回调"""
        self.logger.error(f"音频播放错误: {error_msg}")
        self._trigger_status_event("错误", error_msg)

    def _trigger_status_event(self, status: str, filename: str):
        """触发状态变化事件"""
        if self.on_status_change_callback:
            wx.PostEvent(self.parent_window, PlayerStatusEvent(
                status=status,
                filename=filename
            ))

    # 工具方法
    def is_available(self) -> bool:
        """检查播放器是否可用"""
        return self.is_initialized

    def get_current_filename(self) -> str:
        """获取当前播放文件名"""
        return self.current_filename

    def get_playback_status(self) -> str:
        """获取播放状态"""
        if self.is_playing:
            return "播放中"
        elif self.is_paused:
            return "已暂停"
        else:
            return "已停止"

    def _clear_status_bar(self):
        """清理状态栏显示"""
        try:
            if self.status_bar:
                # 清空所有状态栏字段
                self.status_bar.SetStatusText("", 0)  # 播放状态
                self.status_bar.SetStatusText("", 1)  # 播放时间
                self.status_bar.SetStatusText("", 2)  # 进度百分比
                self.status_bar.SetStatusText("", 3)  # 音量/设备
                self.status_bar.SetStatusText("", 4)  # 播放倍速
                self.logger.debug("状态栏已清理")
        except Exception as e:
            self.logger.error(f"清理状态栏失败: {e}")

    def cleanup(self):
        """清理资源"""
        try:
            if self.audio_player:
                self.audio_player.cleanup()
            self.logger.info("音频播放控制器资源已清理")

        except Exception as e:
            self.logger.error(f"清理音频播放控制器资源失败: {e}")

    def __del__(self):
        """析构函数"""
        self.cleanup()
