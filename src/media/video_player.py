#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频播放器
专门用于视频播放的简化接口，支持全屏播放
"""

import os
from typing import Optional, Callable
from src.core.logger import get_logger
from .media_player_core import MediaPlayerCore, MediaPlayerState
from .file_detector import MediaFileDetector


class VideoPlayer:
    """视频播放器"""

    def __init__(self):
        """初始化视频播放器"""
        self.logger = get_logger()
        self.player_core = None
        self.current_file = None
        self.is_initialized = False
        self.is_fullscreen = False

        # 播放状态回调
        self.on_play_callback = None
        self.on_pause_callback = None
        self.on_stop_callback = None
        self.on_time_update_callback = None
        self.on_error_callback = None
        self.on_finished_callback = None

        # 初始化播放器
        self._initialize()

    def _initialize(self):
        """初始化播放器核心"""
        try:
            self.player_core = MediaPlayerCore()
            self.is_initialized = True

            # 设置事件回调
            self.player_core.add_event_callback('on_state_changed', self._on_state_changed)
            self.player_core.add_event_callback('on_time_changed', self._on_time_changed)
            self.player_core.add_event_callback('on_error', self._on_error)
            self.player_core.add_event_callback('on_finished', self._on_finished)

            self.logger.info("视频播放器初始化成功")

        except Exception as e:
            self.logger.error(f"视频播放器初始化失败: {e}")
            self.is_initialized = False
            if self.on_error_callback:
                self.on_error_callback(f"播放器初始化失败: {e}")

    def load_and_play(self, file_path: str, fullscreen: bool = True) -> bool:
        """
        加载并播放视频文件

        Args:
            file_path: 视频文件路径（本地路径或网络URL）
            fullscreen: 是否全屏播放

        Returns:
            bool: 是否成功
        """
        if not self.is_initialized:
            self.logger.error("视频播放器未初始化")
            return False

        # 检查文件类型（支持本地文件和网络URL）
        if file_path.startswith(('http://', 'https://')):
            # 网络URL，跳过文件存在性检查
            self.logger.info(f"加载网络视频URL: {file_path}")
        else:
            # 本地文件，检查是否存在
            if not os.path.exists(file_path):
                self.logger.error(f"视频文件不存在: {file_path}")
                return False

        if not MediaFileDetector.is_video_file(file_path):
            self.logger.error(f"不支持的视频格式: {file_path}")
            return False

        try:
            # 停止当前播放
            if self.player_core.is_playing() or self.player_core.is_paused():
                self.player_core.stop()

            # 加载新文件
            if self.player_core.load_media(file_path):
                self.current_file = file_path
                self.is_fullscreen = fullscreen

                # 设置全屏模式
                if fullscreen:
                    self.player_core.set_fullscreen(True)

                # 开始播放
                return self.play()
            else:
                self.logger.error(f"加载视频文件失败: {file_path}")
                return False

        except Exception as e:
            self.logger.error(f"播放视频失败: {e}")
            if self.on_error_callback:
                self.on_error_callback(f"播放失败: {e}")
            return False

    def play(self) -> bool:
        """开始播放"""
        if not self.is_initialized:
            return False

        try:
            if self.player_core.is_paused():
                # 恢复播放
                result = self.player_core.resume()
            else:
                # 开始播放
                result = self.player_core.play()

            if result:
                self.logger.info("视频播放开始")
                if self.on_play_callback:
                    self.on_play_callback()

            return result

        except Exception as e:
            self.logger.error(f"播放视频失败: {e}")
            return False

    def pause(self) -> bool:
        """暂停播放"""
        if not self.is_initialized:
            return False

        try:
            result = self.player_core.pause()
            if result:
                self.logger.info("视频播放暂停")
                if self.on_pause_callback:
                    self.on_pause_callback()

            return result

        except Exception as e:
            self.logger.error(f"暂停视频失败: {e}")
            return False

    def resume(self) -> bool:
        """恢复播放"""
        if not self.is_initialized:
            return False

        try:
            result = self.player_core.resume()
            if result:
                self.logger.info("视频播放恢复")
                if self.on_play_callback:
                    self.on_play_callback()

            return result

        except Exception as e:
            self.logger.error(f"恢复视频播放失败: {e}")
            return False

    def stop(self) -> bool:
        """停止播放"""
        if not self.is_initialized:
            return False

        try:
            # 退出全屏
            if self.is_fullscreen:
                self.player_core.set_fullscreen(False)
                self.is_fullscreen = False

            result = self.player_core.stop()
            if result:
                self.logger.info("视频播放停止")
                if self.on_stop_callback:
                    self.on_stop_callback()

            return result

        except Exception as e:
            self.logger.error(f"停止视频失败: {e}")
            return False

    def toggle_fullscreen(self) -> bool:
        """切换全屏模式"""
        if not self.is_initialized:
            return False

        try:
            self.is_fullscreen = not self.is_fullscreen
            result = self.player_core.set_fullscreen(self.is_fullscreen)
            self.logger.info(f"全屏模式: {'开启' if self.is_fullscreen else '关闭'}")
            return result

        except Exception as e:
            self.logger.error(f"切换全屏模式失败: {e}")
            return False

    def is_playing(self) -> bool:
        """检查是否正在播放"""
        if not self.is_initialized:
            return False
        return self.player_core.is_playing()

    def is_paused(self) -> bool:
        """检查是否已暂停"""
        if not self.is_initialized:
            return False
        return self.player_core.is_paused()

    def get_current_time(self) -> int:
        """获取当前播放时间（毫秒）"""
        if not self.is_initialized:
            return 0
        return self.player_core.get_current_time()

    def get_duration(self) -> int:
        """获取视频总时长（毫秒）"""
        if not self.is_initialized:
            return 0
        return self.player_core.get_duration()

    def get_time_string(self, time_ms: int) -> str:
        """将毫秒转换为时间字符串 (MM:SS)"""
        try:
            seconds = time_ms // 1000
            minutes = seconds // 60
            seconds = seconds % 60
            return f"{minutes:02d}:{seconds:02d}"
        except:
            return "00:00"

    def get_current_time_string(self) -> str:
        """获取当前播放时间字符串"""
        return self.get_time_string(self.get_current_time())

    def get_duration_string(self) -> str:
        """获取总时长字符串"""
        return self.get_time_string(self.get_duration())

    def seek_forward(self, seconds: int = 10) -> bool:
        """快进（视频默认快进10秒）"""
        if not self.is_initialized:
            return False
        return self.player_core.seek_forward(seconds)

    def seek_backward(self, seconds: int = 10) -> bool:
        """快退（视频默认快退10秒）"""
        if not self.is_initialized:
            return False
        return self.player_core.seek_backward(seconds)

    def set_position(self, position: float) -> bool:
        """设置播放位置

        Args:
            position: 播放位置 (0.0 - 1.0)

        Returns:
            bool: 是否成功
        """
        if not self.is_initialized:
            return False
        return self.player_core.set_position(position)

    def set_volume(self, volume: int) -> bool:
        """设置音量 (0-100)"""
        if not self.is_initialized:
            return False
        return self.player_core.set_volume(volume)

    def get_volume(self) -> int:
        """获取当前音量"""
        if not self.is_initialized:
            return 0
        return self.player_core.get_volume()

    def set_playback_rate(self, rate: float) -> bool:
        """设置播放倍速

        Args:
            rate: 播放倍速 (0.5, 1.0, 1.5, 2.0, 3.0等)

        Returns:
            bool: 是否成功
        """
        if not self.is_initialized:
            return False
        return self.player_core.set_playback_rate(rate)

    def get_playback_rate(self) -> float:
        """获取当前播放倍速"""
        if not self.is_initialized:
            return 1.0
        return self.player_core.get_playback_rate()

    def get_available_audio_tracks(self) -> list:
        """获取可用的音频轨道列表

        Returns:
            list: 音频轨道信息列表
        """
        if not self.is_initialized:
            return []
        return self.player_core.get_available_audio_tracks()

    def set_audio_track(self, track_id: int) -> bool:
        """设置音频轨道

        Args:
            track_id: 轨道ID

        Returns:
            bool: 是否成功
        """
        if not self.is_initialized:
            return False
        return self.player_core.set_audio_track(track_id)

    def get_current_audio_track(self) -> int:
        """获取当前音频轨道ID

        Returns:
            int: 当前轨道ID
        """
        if not self.is_initialized:
            return 0
        return self.player_core.get_current_audio_track()

    def get_current_audio_track_info(self) -> dict:
        """获取当前音频轨道信息

        Returns:
            dict: 轨道信息字典
        """
        if not self.is_initialized:
            return {}
        return self.player_core.get_current_audio_track_info()

    def get_current_file(self) -> Optional[str]:
        """获取当前播放文件"""
        return self.current_file

    def get_file_name(self) -> str:
        """获取当前文件名"""
        if self.current_file:
            return os.path.basename(self.current_file)
        return ""

    def set_audio_device(self, device) -> bool:
        """设置音频输出设备

        Args:
            device: 设备信息字典

        Returns:
            bool: 是否成功
        """
        if not self.is_initialized:
            return False
        return self.player_core.set_audio_device(device)

    def get_available_audio_devices(self, force_refresh: bool = False) -> list:
        """获取可用音频设备列表

        Args:
            force_refresh: 是否强制刷新设备列表

        Returns:
            list: 设备列表
        """
        if not self.is_initialized:
            return []
        return self.player_core.get_available_audio_devices(force_refresh)

    def get_current_audio_device_info(self) -> dict:
        """获取当前音频设备信息

        Returns:
            dict: 设备信息
        """
        if not self.is_initialized:
            return {}
        return self.player_core.get_current_audio_device_info()

    def set_video_window(self, window_handle) -> bool:
        """设置视频渲染窗口

        Args:
            window_handle: 窗口句柄（Windows上为HWND，Linux上为XID）

        Returns:
            bool: 是否设置成功
        """
        if not self.is_initialized:
            return False
        return self.player_core.set_video_window(window_handle)

    def get_media_info(self):
        """获取媒体信息"""
        if not self.is_initialized:
            return None
        return self.player_core.get_media_info()

    def set_play_callback(self, callback: Callable):
        """设置播放回调"""
        self.on_play_callback = callback

    def set_pause_callback(self, callback: Callable):
        """设置暂停回调"""
        self.on_pause_callback = callback

    def set_stop_callback(self, callback: Callable):
        """设置停止回调"""
        self.on_stop_callback = callback

    def set_time_update_callback(self, callback: Callable):
        """设置时间更新回调"""
        self.on_time_update_callback = callback

    def set_error_callback(self, callback: Callable):
        """设置错误回调"""
        self.on_error_callback = callback

    def set_finished_callback(self, callback: Callable):
        """设置播放完成回调"""
        self.on_finished_callback = callback

    def _on_state_changed(self, state):
        """状态变化事件处理"""
        state_str = str(state)
        self.logger.debug(f"视频播放器状态变化: {state_str}")

        if state == MediaPlayerState.PLAYING:
            if self.on_play_callback:
                self.on_play_callback()
        elif state == MediaPlayerState.PAUSED:
            if self.on_pause_callback:
                self.on_pause_callback()
        elif state == MediaPlayerState.STOPPED:
            if self.on_stop_callback:
                self.on_stop_callback()

    def _on_time_changed(self, time_ms):
        """时间变化事件处理"""
        if self.on_time_update_callback:
            self.on_time_update_callback(time_ms)

    def _on_error(self, error_msg):
        """错误事件处理"""
        self.logger.error(f"视频播放器错误: {error_msg}")
        if self.on_error_callback:
            self.on_error_callback(error_msg)

    def _on_finished(self):
        """播放完成事件处理"""
        self.logger.info("视频播放完成")
        if self.on_finished_callback:
            self.on_finished_callback()

    def cleanup(self):
        """清理资源"""
        try:
            if self.player_core:
                # 退出全屏
                if self.is_fullscreen:
                    self.player_core.set_fullscreen(False)

                self.player_core.cleanup()
            self.logger.info("视频播放器资源已清理")
        except Exception as e:
            self.logger.error(f"清理视频播放器资源失败: {e}")

    def __del__(self):
        """析构函数"""
        self.cleanup()