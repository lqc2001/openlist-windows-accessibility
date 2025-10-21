#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版音频控制器
借鉴ForumAssist的播放控制逻辑，提供完整的播放控制功能
"""

import wx
import wx.adv
from typing import List, Dict, Optional, Callable
from pathlib import Path
from src.core.logger import get_logger
from src.media.enhanced_audio_player import EnhancedAudioPlayer
from src.ui.enhanced_status_bar import EnhancedStatusBar


class EnhancedAudioController:
    """增强版音频控制器

    功能：
    1. 播放控制（播放/暂停/停止/上一首/下一首）
    2. 音量控制和静音
    3. 进度控制和跳转
    4. 播放列表管理
    5. 音频设备切换
    6. 快捷键支持
    7. 菜单集成
    """

    def __init__(self, parent_frame: wx.Frame, status_bar: EnhancedStatusBar):
        """初始化音频控制器

        Args:
            parent_frame: 父窗口
            status_bar: 状态栏管理器
        """
        self.logger = get_logger()
        self.parent_frame = parent_frame
        self.status_bar = status_bar

        # 音频播放器
        self.audio_player = EnhancedAudioPlayer()

        # 播放状态
        self.current_file: Optional[str] = None
        self.playlist: List[Dict] = []
        self.current_index = 0
        self.volume_before_mute = 100
        self.is_muted = False

        # 菜单项
        self.play_menu: Optional[wx.Menu] = None
        self.device_menu: Optional[wx.Menu] = None

        # 回调函数
        self.on_file_changed: Optional[Callable] = None
        self.on_playlist_changed: Optional[Callable] = None

        # 初始化
        self._setup_audio_player_callbacks()
        self._create_menus()

        self.logger.info("音频控制器初始化完成")

    def _setup_audio_player_callbacks(self):
        """设置音频播放器回调"""
        if self.audio_player:
            self.audio_player.on_status_update = self._on_status_update
            self.audio_player.on_device_changed = self._on_device_changed

    def _create_menus(self):
        """创建播放菜单"""
        try:
            # 创建播放菜单
            self.play_menu = wx.Menu()

            # 播放控制
            play_pause_item = self.play_menu.Append(wx.ID_ANY, "播放/暂停\tCtrl+Home")
            stop_item = self.play_menu.Append(wx.ID_ANY, "停止\tCtrl+End")
            self.play_menu.AppendSeparator()

            # 播放列表导航
            prev_item = self.play_menu.Append(wx.ID_ANY, "上一个\tCtrl+PageUp")
            next_item = self.play_menu.Append(wx.ID_ANY, "下一个\tCtrl+PageDown")
            self.play_menu.AppendSeparator()

            # 音量控制
            volume_menu = wx.Menu()
            volume_up_item = volume_menu.Append(wx.ID_ANY, "音量增加\tCtrl+Up")
            volume_down_item = volume_menu.Append(wx.ID_ANY, "音量减少\tCtrl+Down")
            mute_item = volume_menu.Append(wx.ID_ANY, "静音/取消静音\tCtrl+M")
            self.play_menu.AppendSubMenu(volume_menu, "音量控制")

            self.play_menu.AppendSeparator()

            # 音频设备
            self.device_menu = wx.Menu()
            self._refresh_device_menu()
            self.play_menu.AppendSubMenu(self.device_menu, "音频设备")

            # 绑定菜单事件
            self.parent_frame.Bind(wx.EVT_MENU, self._on_play_pause, play_pause_item)
            self.parent_frame.Bind(wx.EVT_MENU, self._on_stop, stop_item)
            self.parent_frame.Bind(wx.EVT_MENU, self._on_previous, prev_item)
            self.parent_frame.Bind(wx.EVT_MENU, self._on_next, next_item)
            self.parent_frame.Bind(wx.EVT_MENU, self._on_volume_up, volume_up_item)
            self.parent_frame.Bind(wx.EVT_MENU, self._on_volume_down, volume_down_item)
            self.parent_frame.Bind(wx.EVT_MENU, self._on_mute_toggle, mute_item)

            self.logger.info("播放菜单创建成功")

        except Exception as e:
            self.logger.error(f"创建播放菜单失败: {e}")

    def _refresh_device_menu(self):
        """刷新音频设备菜单"""
        if not self.device_menu or not self.audio_player:
            return

        try:
            # 清空现有菜单项
            for item in self.device_menu.GetMenuItems():
                self.device_menu.Remove(item)
                item.Destroy()

            # 获取设备列表
            devices = self.audio_player.get_audio_devices()

            # 添加设备菜单项
            for device in devices:
                device_id = device['id']
                device_name = device['name']

                # 创建菜单项
                item = self.device_menu.AppendRadioItem(wx.ID_ANY, device_name)
                if device.get('is_current', False):
                    item.Check(True)

                # 绑定事件
                self.parent_frame.Bind(wx.EVT_MENU,
                                     lambda evt, did=device_id: self._on_device_selected(did),
                                     item)

            self.logger.debug(f"音频设备菜单刷新完成，共{len(devices)}个设备")

        except Exception as e:
            self.logger.error(f"刷新音频设备菜单失败: {e}")

    def setup_keyboard_shortcuts(self):
        """设置键盘快捷键"""
        try:
            # 创建快捷键表（使用自定义ID避免冲突）
            ID_PLAY_PAUSE = wx.NewId()
            ID_STOP_PLAY = wx.NewId()
            ID_PREV_TRACK = wx.NewId()
            ID_NEXT_TRACK = wx.NewId()
            ID_VOLUME_UP = wx.NewId()
            ID_VOLUME_DOWN = wx.NewId()
            ID_MUTE_TOGGLE = wx.NewId()
            ID_SEEK_BACK = wx.NewId()
            ID_SEEK_FORWARD = wx.NewId()

            # 保存ID供事件处理使用
            self._accel_ids = {
                'play_pause': ID_PLAY_PAUSE,
                'stop': ID_STOP_PLAY,
                'prev': ID_PREV_TRACK,
                'next': ID_NEXT_TRACK,
                'vol_up': ID_VOLUME_UP,
                'vol_down': ID_VOLUME_DOWN,
                'mute': ID_MUTE_TOGGLE,
                'seek_back': ID_SEEK_BACK,
                'seek_forward': ID_SEEK_FORWARD,
            }

            accel_tbl = wx.AcceleratorTable([
                (wx.ACCEL_CTRL, wx.WXK_HOME, ID_PLAY_PAUSE),    # Ctrl+Home: 播放/暂停
                (wx.ACCEL_CTRL, wx.WXK_END, ID_STOP_PLAY),      # Ctrl+End: 停止
                (wx.ACCEL_CTRL, wx.WXK_PAGEUP, ID_PREV_TRACK),  # Ctrl+PageUp: 上一个
                (wx.ACCEL_CTRL, wx.WXK_PAGEDOWN, ID_NEXT_TRACK),# Ctrl+PageDown: 下一个
                (wx.ACCEL_CTRL, wx.WXK_UP, ID_VOLUME_UP),       # Ctrl+Up: 音量增加
                (wx.ACCEL_CTRL, wx.WXK_DOWN, ID_VOLUME_DOWN),   # Ctrl+Down: 音量减少
                (wx.ACCEL_CTRL, ord('M'), ID_MUTE_TOGGLE),      # Ctrl+M: 静音切换
                (wx.ACCEL_CTRL, wx.WXK_LEFT, ID_SEEK_BACK),     # Ctrl+Left: 快退
                (wx.ACCEL_CTRL, wx.WXK_RIGHT, ID_SEEK_FORWARD), # Ctrl+Right: 快进
            ])

            self.parent_frame.SetAcceleratorTable(accel_tbl)

            # 绑定快捷键事件
            self.parent_frame.Bind(wx.EVT_MENU, self._on_accel_home, source=ID_PLAY_PAUSE)
            self.parent_frame.Bind(wx.EVT_MENU, self._on_accel_end, source=ID_STOP_PLAY)
            self.parent_frame.Bind(wx.EVT_MENU, self._on_accel_up, source=ID_PREV_TRACK)
            self.parent_frame.Bind(wx.EVT_MENU, self._on_accel_down, source=ID_NEXT_TRACK)
            self.parent_frame.Bind(wx.EVT_MENU, self._on_accel_refresh, source=ID_VOLUME_UP)
            self.parent_frame.Bind(wx.EVT_MENU, self._on_accel_backward, source=ID_VOLUME_DOWN)
            self.parent_frame.Bind(wx.EVT_MENU, self._on_accel_execute, source=ID_MUTE_TOGGLE)
            self.parent_frame.Bind(wx.EVT_MENU, self._on_accel_forward, source=ID_SEEK_BACK)
            self.parent_frame.Bind(wx.EVT_MENU, self._on_accel_replace, source=ID_SEEK_FORWARD)

            self.logger.info("快捷键设置完成")

        except Exception as e:
            self.logger.error(f"设置快捷键失败: {e}")

    def _on_accel_home(self, event):
        """Ctrl+Home: 播放/暂停"""
        self.toggle_play_pause()

    def _on_accel_end(self, event):
        """Ctrl+End: 停止"""
        self.stop()

    def _on_accel_up(self, event):
        """Ctrl+PageUp: 上一个"""
        self.play_previous()

    def _on_accel_down(self, event):
        """Ctrl+PageDown: 下一个"""
        self.play_next()

    def _on_accel_refresh(self, event):
        """Ctrl+Up: 音量增加"""
        self.increase_volume()

    def _on_accel_backward(self, event):
        """Ctrl+Down: 音量减少"""
        self.decrease_volume()

    def _on_accel_execute(self, event):
        """Ctrl+M: 静音切换"""
        self.toggle_mute()

    def _on_accel_forward(self, event):
        """Ctrl+Left: 快退"""
        self.seek_backward()

    def _on_accel_replace(self, event):
        """Ctrl+Right: 快进"""
        self.seek_forward()

    def load_and_play_file(self, file_path: str) -> bool:
        """加载并播放文件

        Args:
            file_path: 文件路径

        Returns:
            bool: 是否成功
        """
        try:
            if not Path(file_path).exists():
                self.status_bar.show_error_message(f"文件不存在: {file_path}")
                return False

            # 停止当前播放
            self.stop()

            # 加载新文件
            if self.audio_player.load_file(file_path):
                self.current_file = file_path
                self.current_index = 0
                self.playlist = [{'path': file_path, 'name': Path(file_path).name}]

                # 开始播放
                if self.play():
                    self.status_bar.show_success_message(f"开始播放: {Path(file_path).name}")

                    # 触发文件变化回调
                    if self.on_file_changed:
                        self.on_file_changed(file_path)

                    return True
                else:
                    self.status_bar.show_error_message("播放失败")
                    return False
            else:
                self.status_bar.show_error_message("文件加载失败")
                return False

        except Exception as e:
            self.logger.error(f"加载播放文件失败: {e}")
            self.status_bar.show_error_message(f"播放失败: {str(e)}")
            return False

    def set_playlist(self, files: List[str], start_index: int = 0) -> bool:
        """设置播放列表

        Args:
            files: 文件路径列表
            start_index: 开始播放的索引

        Returns:
            bool: 是否成功
        """
        try:
            if not files:
                return False

            # 创建播放列表
            self.playlist = []
            for file_path in files:
                path_obj = Path(file_path)
                if path_obj.exists():
                    self.playlist.append({
                        'path': str(path_obj),
                        'name': path_obj.name
                    })

            if not self.playlist:
                self.status_bar.show_error_message("没有有效的音频文件")
                return False

            # 设置当前索引
            self.current_index = max(0, min(start_index, len(self.playlist) - 1))

            # 加载并播放当前文件
            current_file = self.playlist[self.current_index]['path']
            success = self.load_and_play_file(current_file)

            if success:
                # 触发播放列表变化回调
                if self.on_playlist_changed:
                    self.on_playlist_changed(self.playlist, self.current_index)

                self.logger.info(f"播放列表设置成功，共{len(self.playlist)}个文件")
                self.status_bar.show_success_message(f"播放列表: {len(self.playlist)}个文件")

            return success

        except Exception as e:
            self.logger.error(f"设置播放列表失败: {e}")
            self.status_bar.show_error_message(f"播放列表设置失败: {str(e)}")
            return False

    def play(self) -> bool:
        """播放"""
        if self.audio_player:
            success = self.audio_player.play()
            if success:
                self._update_menu_states()
            return success
        return False

    def pause(self) -> bool:
        """暂停"""
        if self.audio_player:
            success = self.audio_player.pause()
            if success:
                self._update_menu_states()
            return success
        return False

    def stop(self) -> bool:
        """停止"""
        if self.audio_player:
            success = self.audio_player.stop()
            if success:
                self._update_menu_states()
            return success
        return False

    def toggle_play_pause(self) -> bool:
        """播放/暂停切换"""
        if self.audio_player:
            success = self.audio_player.toggle_play_pause()
            if success:
                self._update_menu_states()
            return success
        return False

    def play_next(self) -> bool:
        """播放下一个"""
        if not self.playlist or self.current_index >= len(self.playlist) - 1:
            self.status_bar.show_temporary_message("已是最后一个文件", 0, 2000)
            return False

        try:
            self.current_index += 1
            next_file = self.playlist[self.current_index]['path']

            # 停止当前播放，加载新文件
            self.audio_player.stop()
            if self.audio_player.load_file(next_file):
                self.current_file = next_file
                success = self.audio_player.play()

                if success:
                    self.status_bar.show_success_message(f"播放: {self.playlist[self.current_index]['name']}")
                    if self.on_file_changed:
                        self.on_file_changed(next_file)

                return success

            return False

        except Exception as e:
            self.logger.error(f"播放下一个失败: {e}")
            self.status_bar.show_error_message(f"播放失败: {str(e)}")
            return False

    def play_previous(self) -> bool:
        """播放上一个"""
        if not self.playlist or self.current_index <= 0:
            self.status_bar.show_temporary_message("已是第一个文件", 0, 2000)
            return False

        try:
            self.current_index -= 1
            prev_file = self.playlist[self.current_index]['path']

            # 停止当前播放，加载新文件
            self.audio_player.stop()
            if self.audio_player.load_file(prev_file):
                self.current_file = prev_file
                success = self.audio_player.play()

                if success:
                    self.status_bar.show_success_message(f"播放: {self.playlist[self.current_index]['name']}")
                    if self.on_file_changed:
                        self.on_file_changed(prev_file)

                return success

            return False

        except Exception as e:
            self.logger.error(f"播放上一个失败: {e}")
            self.status_bar.show_error_message(f"播放失败: {str(e)}")
            return False

    def set_volume(self, volume: int) -> bool:
        """设置音量

        Args:
            volume: 音量值 (0-100)

        Returns:
            bool: 是否成功
        """
        if self.audio_player:
            success = self.audio_player.set_volume(volume)
            if success:
                self.status_bar.show_temporary_message(f"音量: {volume}%", 3, 2000)
            return success
        return False

    def increase_volume(self, step: int = 10) -> bool:
        """增加音量

        Args:
            step: 增加的步长

        Returns:
            bool: 是否成功
        """
        if self.audio_player:
            current_volume = self.audio_player.get_volume()
            new_volume = min(100, current_volume + step)
            return self.set_volume(new_volume)
        return False

    def decrease_volume(self, step: int = 10) -> bool:
        """减少音量

        Args:
            step: 减少的步长

        Returns:
            bool: 是否成功
        """
        if self.audio_player:
            current_volume = self.audio_player.get_volume()
            new_volume = max(0, current_volume - step)
            return self.set_volume(new_volume)
        return False

    def toggle_mute(self) -> bool:
        """切换静音状态"""
        if self.audio_player:
            if self.is_muted:
                # 取消静音
                success = self.audio_player.set_volume(self.volume_before_mute)
                if success:
                    self.is_muted = False
                    self.status_bar.show_temporary_message(f"取消静音: {self.volume_before_mute}%", 3, 2000)
                return success
            else:
                # 静音
                self.volume_before_mute = self.audio_player.get_volume()
                success = self.audio_player.set_volume(0)
                if success:
                    self.is_muted = True
                    self.status_bar.show_temporary_message("已静音", 3, 2000)
                return success
        return False

    def seek_to_position(self, position: float) -> bool:
        """跳转到指定位置

        Args:
            position: 位置 (0.0-1.0)

        Returns:
            bool: 是否成功
        """
        if self.audio_player:
            return self.audio_player.seek(position)
        return False

    def seek_forward(self, seconds: int = 5) -> bool:
        """快进

        Args:
            seconds: 快进的秒数

        Returns:
            bool: 是否成功
        """
        if self.audio_player and self.current_time and self.total_time:
            current_pos = self.current_time / self.total_time
            forward_pos = min(1.0, current_pos + (seconds / self.total_time))
            success = self.audio_player.seek(forward_pos)
            if success:
                self.status_bar.show_temporary_message(f"快进{seconds}秒", 2, 2000)
            return success
        return False

    def seek_backward(self, seconds: int = 5) -> bool:
        """快退

        Args:
            seconds: 快退的秒数

        Returns:
            bool: 是否成功
        """
        if self.audio_player and self.current_time and self.total_time:
            current_pos = self.current_time / self.total_time
            backward_pos = max(0.0, current_pos - (seconds / self.total_time))
            success = self.audio_player.seek(backward_pos)
            if success:
                self.status_bar.show_temporary_message(f"快退{seconds}秒", 2, 2000)
            return success
        return False

    def switch_audio_device(self, device_id: str) -> bool:
        """切换音频设备

        Args:
            device_id: 设备ID

        Returns:
            bool: 是否成功
        """
        if self.audio_player:
            success = self.audio_player.set_audio_device(device_id)
            if success:
                # 刷新设备菜单
                self._refresh_device_menu()

                # 显示设备名称
                devices = self.audio_player.get_audio_devices()
                for device in devices:
                    if device['id'] == device_id:
                        device_name = device['name']
                        if device_id == 'default':
                            device_name = '系统默认'
                        self.status_bar.show_success_message(f"音频设备: {device_name}")
                        break
            return success
        return False

    def _on_status_update(self):
        """状态更新回调"""
        if self.audio_player and self.status_bar:
            try:
                # 获取状态信息
                status_info = self.audio_player.get_status_info()
                progress_info = self.audio_player.get_progress_info()

                # 添加播放列表信息
                status_info['playlist'] = self.playlist
                status_info['current_index'] = self.current_index

                # 获取设备信息
                devices = self.audio_player.get_audio_devices()
                current_device_id = status_info.get('current_device', 'default')
                current_device = None
                for device in devices:
                    if device['id'] == current_device_id:
                        current_device = device
                        break

                # 更新状态栏
                self.status_bar.update_audio_status(status_info, progress_info, current_device)

                # 更新菜单状态
                self._update_menu_states()

            except Exception as e:
                self.logger.debug(f"状态更新失败: {e}")

    def _on_device_changed(self, device_id: str):
        """设备切换回调"""
        self.logger.info(f"音频设备已切换到: {device_id}")
        self._refresh_device_menu()

    def _update_menu_states(self):
        """更新菜单状态"""
        if not self.play_menu or not self.audio_player:
            return

        try:
            # 这里可以根据播放状态更新菜单项的启用/禁用状态
            # 由于使用的是标准菜单项，这里不做复杂的菜单状态管理

            pass

        except Exception as e:
            self.logger.debug(f"更新菜单状态失败: {e}")

    # 菜单事件处理
    def _on_play_pause(self, event):
        """播放/暂停菜单事件"""
        self.toggle_play_pause()

    def _on_stop(self, event):
        """停止菜单事件"""
        self.stop()

    def _on_previous(self, event):
        """上一个菜单事件"""
        self.play_previous()

    def _on_next(self, event):
        """下一个菜单事件"""
        self.play_next()

    def _on_volume_up(self, event):
        """音量增加菜单事件"""
        self.increase_volume()

    def _on_volume_down(self, event):
        """音量减少菜单事件"""
        self.decrease_volume()

    def _on_mute_toggle(self, event):
        """静音切换菜单事件"""
        self.toggle_mute()

    def _on_device_selected(self, device_id: str):
        """设备选择菜单事件"""
        self.switch_audio_device(device_id)

    def get_audio_player(self) -> EnhancedAudioPlayer:
        """获取音频播放器实例"""
        return self.audio_player

    def get_current_playlist(self) -> List[Dict]:
        """获取当前播放列表"""
        return self.playlist.copy()

    def get_current_file(self) -> Optional[str]:
        """获取当前播放文件"""
        return self.current_file

    def is_playing(self) -> bool:
        """检查是否正在播放"""
        return self.audio_player.is_playing if self.audio_player else False

    def is_paused(self) -> bool:
        """检查是否已暂停"""
        return self.audio_player.is_paused if self.audio_player else False

    def get_play_menu(self) -> Optional[wx.Menu]:
        """获取播放菜单"""
        return self.play_menu

    def cleanup(self):
        """清理资源"""
        try:
            if self.audio_player:
                self.audio_player.cleanup()
                self.audio_player = None

            self.play_menu = None
            self.device_menu = None
            self.playlist.clear()
            self.current_file = None

            self.logger.info("音频控制器资源已清理")

        except Exception as e:
            self.logger.error(f"清理音频控制器资源失败: {e}")

    def __del__(self):
        """析构函数"""
        self.cleanup()