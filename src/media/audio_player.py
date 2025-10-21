#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频播放器
专门用于音频播放的简化接口
"""

import os
from typing import Optional, Callable
from src.core.logger import get_logger
from .media_player_core import MediaPlayerCore, MediaPlayerState
from .file_detector import MediaFileDetector


class AudioPlayer:
    """音频播放器"""

    def __init__(self):
        """初始化音频播放器"""
        self.logger = get_logger()
        self.player_core = None
        self.current_file = None
        self.is_initialized = False

        # 播放状态回调
        self.on_play_callback = None
        self.on_pause_callback = None
        self.on_stop_callback = None
        self.on_time_update_callback = None
        self.on_error_callback = None

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

            self.logger.info("音频播放器初始化成功")

        except Exception as e:
            self.logger.error(f"音频播放器初始化失败: {e}")
            self.is_initialized = False
            if self.on_error_callback:
                self.on_error_callback(f"播放器初始化失败: {e}")

    def load_and_play(self, file_path: str) -> bool:
        """
        加载并播放音频文件

        Args:
            file_path: 音频文件路径（本地路径或网络URL）

        Returns:
            bool: 是否成功
        """
        if not self.is_initialized:
            self.logger.error("音频播放器未初始化")
            return False

        # 检查文件类型（支持本地文件和网络URL）
        if file_path.startswith(('http://', 'https://')):
            # 网络URL，跳过文件存在性检查
            self.logger.info(f"加载网络音频URL: {file_path}")
        else:
            # 本地文件，检查是否存在
            if not os.path.exists(file_path):
                self.logger.error(f"音频文件不存在: {file_path}")
                return False

        if not MediaFileDetector.is_audio_file(file_path):
            self.logger.error(f"不支持的音频格式: {file_path}")
            return False

        try:
            # 停止当前播放
            if self.player_core.is_playing() or self.player_core.is_paused():
                self.player_core.stop()

            # 加载新文件
            if self.player_core.load_media(file_path):
                self.current_file = file_path
                # 开始播放
                return self.play()
            else:
                self.logger.error(f"加载音频文件失败: {file_path}")
                return False

        except Exception as e:
            self.logger.error(f"播放音频失败: {e}")
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
                self.logger.info("音频播放开始")
                if self.on_play_callback:
                    self.on_play_callback()

            return result

        except Exception as e:
            self.logger.error(f"播放音频失败: {e}")
            return False

    def pause(self) -> bool:
        """暂停播放"""
        if not self.is_initialized:
            return False

        try:
            result = self.player_core.pause()
            if result:
                self.logger.info("音频播放暂停")
                if self.on_pause_callback:
                    self.on_pause_callback()

            return result

        except Exception as e:
            self.logger.error(f"暂停音频失败: {e}")
            return False

    def resume(self) -> bool:
        """恢复播放"""
        if not self.is_initialized:
            return False

        try:
            result = self.player_core.resume()
            if result:
                self.logger.info("音频播放恢复")
                if self.on_play_callback:
                    self.on_play_callback()

            return result

        except Exception as e:
            self.logger.error(f"恢复音频播放失败: {e}")
            return False

    def stop(self) -> bool:
        """停止播放"""
        if not self.is_initialized:
            return False

        try:
            result = self.player_core.stop()
            if result:
                self.logger.info("音频播放停止")
                if self.on_stop_callback:
                    self.on_stop_callback()

            return result

        except Exception as e:
            self.logger.error(f"停止音频失败: {e}")
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
        """获取音频总时长（毫秒）"""
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

    def seek_forward(self, seconds: int = 5) -> bool:
        """快进"""
        if not self.is_initialized:
            return False
        return self.player_core.seek_forward(seconds)

    def seek_backward(self, seconds: int = 5) -> bool:
        """快退"""
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

    def set_mute(self, muted: bool) -> bool:
        """设置静音"""
        if not self.is_initialized:
            return False
        return self.player_core.set_mute(muted)

    def toggle_mute(self) -> bool:
        """切换静音状态"""
        if not self.is_initialized:
            return False
        return self.player_core.toggle_mute()

    def is_mute(self) -> bool:
        """检查是否静音"""
        if not self.is_initialized:
            return False
        return self.player_core.is_mute()

    def get_current_file(self) -> Optional[str]:
        """获取当前播放文件"""
        return self.current_file

    def get_file_name(self) -> str:
        """获取当前文件名"""
        if self.current_file:
            return os.path.basename(self.current_file)
        return ""

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

    def _on_state_changed(self, state):
        """状态变化事件处理"""
        state_str = str(state)
        self.logger.debug(f"音频播放器状态变化: {state_str}")

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
        self.logger.error(f"音频播放器错误: {error_msg}")
        if self.on_error_callback:
            self.on_error_callback(error_msg)

    def cleanup(self):
        """清理资源"""
        try:
            if self.player_core:
                self.player_core.cleanup()
            self.logger.info("音频播放器资源已清理")
        except Exception as e:
            self.logger.error(f"清理音频播放器资源失败: {e}")

    def __del__(self):
        """析构函数"""
        self.cleanup()