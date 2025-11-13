#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
媒体播放器核心
基于VLC的媒体播放核心实现，支持音视频播放控制
"""

import os
import time
import platform
import threading
from typing import Optional, Callable

import vlc
from src.core.logger import get_logger
from .vlc_loader import VLCLoader


class MediaPlayerState:
    """播放器状态枚举"""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    LOADING = "loading"
    ERROR = "error"


class MediaInfo:
    """媒体信息类"""

    def __init__(self):
        self.title = ""
        self.artist = ""
        self.album = ""
        self.duration = 0  # 毫秒
        self.current_time = 0  # 毫秒
        self.file_path = ""
        self.media_type = ""  # audio, video
        self.bitrate = 0
        self.sample_rate = 0
        self.channels = 0
        self.video_width = 0
        self.video_height = 0


class MediaPlayerCore:
    """媒体播放器核心类"""

    def __init__(self):
        """初始化媒体播放器"""
        self.logger = get_logger()
        self.vlc_loader = None
        self.vlc_instance = None
        self.vlc_player = None
        self.vlc_media = None
        self.vlc_media_list = None
        self.vlc_media_list_player = None

        # 播放状态
        self.state = MediaPlayerState.STOPPED
        self.current_media_info = MediaInfo()

        # 音量控制
        self.volume = 100
        self.is_muted = False

        # 播放倍速控制
        self.playback_rate = 1.0

        # 循环控制
        self.repeat_mode = "none"  # none, one, all

        # 音频设备管理
        self.current_audio_device = self._default_audio_device_entry()
        self.available_audio_devices = []
        self.device_cache_time = 0
        self.device_cache_timeout = 30  # 缓存30秒
        self._audio_output_module = None
        self._audio_device_pending = False
        self._pending_audio_device_id = None
        self._device_sync_thread = None
        self._device_sync_lock = threading.Lock()

        # 事件回调
        self.event_callbacks = {
            'on_media_loaded': [],
            'on_state_changed': [],
            'on_time_changed': [],
            'on_volume_changed': [],
            'on_error': [],
            'on_audio_device_changed': []
        }

        # 初始化VLC
        self._initialize_player()

    def _initialize_player(self):
        """初始化播放器"""
        try:
            # 加载VLC
            self.vlc_loader = VLCLoader()
            self.vlc_instance = self.vlc_loader.get_vlc_instance()

            # 创建播放器
            self.vlc_player = self.vlc_instance.media_player_new()

            # 创建媒体列表播放器（用于播放列表）
            self.vlc_media_list = self.vlc_instance.media_list_new()
            self.vlc_media_list_player = self.vlc_instance.media_list_player_new()
            self.vlc_media_list_player.set_media_list(self.vlc_media_list)

            # 设置事件监听
            self._setup_event_manager()

            # 确保音频输出模块可用
            self._select_audio_output_module()

            self.logger.info("媒体播放器初始化成功")

        except Exception as e:
            self.logger.error(f"媒体播放器初始化失败: {e}")
            self.state = MediaPlayerState.ERROR
            raise

    def _setup_event_manager(self):
        """Set up VLC event listeners."""
        try:
            event_manager = self.vlc_player.event_manager()
            vlc_lib = self.vlc_loader.get_vlc_lib()

            # Media end event
            event_manager.event_attach(
                vlc_lib.EventType.MediaPlayerEndReached,
                self._on_media_ended
            )

            # Playback time changed
            event_manager.event_attach(
                vlc_lib.EventType.MediaPlayerTimeChanged,
                self._on_time_changed
            )

            # Player state changed (not available on some builds)
            try:
                event_manager.event_attach(
                    vlc_lib.EventType.MediaPlayerStateChanged,
                    self._on_state_changed
                )
            except AttributeError:
                self.logger.warning("MediaPlayerStateChanged event unavailable; state updates may be limited")

            # Player started playing – used to reapply audio device
            try:
                event_manager.event_attach(
                    vlc_lib.EventType.MediaPlayerPlaying,
                    self._on_media_playing
                )
            except AttributeError:
                self.logger.debug("MediaPlayerPlaying event unavailable; audio device reapply relies on manual calls")

            # Media parsed event
            try:
                event_manager.event_attach(
                    vlc_lib.EventType.MediaParsedChanged,
                    self._on_media_parsed
                )
            except AttributeError:
                self.logger.warning("MediaParsedChanged event unavailable; metadata updates may be limited")

        except Exception as e:
            self.logger.error(f"Failed to set up VLC event manager: {e}")
            # allow playback to continue even if hooks fail


    def load_media(self, file_path: str) -> bool:
        """
        加载媒体文件

        Args:
            file_path: 媒体文件路径（本地路径或网络URL）

        Returns:
            bool: 是否加载成功
        """
        try:
            # 检查文件类型（支持本地文件和网络URL）
            if file_path.startswith(('http://', 'https://')):
                # 网络URL，跳过文件存在性检查
                self.logger.info(f"加载网络媒体URL: {file_path}")
            else:
                # 本地文件，检查是否存在
                if not os.path.exists(file_path):
                    self.logger.error(f"媒体文件不存在: {file_path}")
                    return False

            self.state = MediaPlayerState.LOADING
            self.logger.info(f"正在加载媒体: {file_path}")

            # 创建媒体对象
            self.vlc_media = self.vlc_instance.media_new(file_path)

            # 设置媒体到播放器
            self.vlc_player.set_media(self.vlc_media)

            # 解析媒体信息
            self.vlc_media.parse()

            # 更新媒体信息
            self._update_media_info(file_path)

            self.logger.info(f"媒体加载成功: {file_path}")
            self._trigger_event('on_media_loaded', self.current_media_info)

            return True

        except Exception as e:
            self.logger.error(f"媒体加载失败: {e}")
            self.state = MediaPlayerState.ERROR
            self._trigger_event('on_error', str(e))
            return False

    def play(self) -> bool:
        """
        开始播放

        Returns:
            bool: 是否播放成功
        """
        try:
            if not self.vlc_player:
                self.logger.error("播放器未初始化")
                return False

            if not self.vlc_media:
                self.logger.error("未加载媒体")
                return False

            # Ensure selected audio device is applied before playback
            self._apply_audio_device(reason='pre-play')

            # 开始播放
            result = self.vlc_player.play()
            if result == 0:  # VLC返回0表示成功
                self.state = MediaPlayerState.PLAYING
                self.logger.info("开始播放")
                return True
            else:
                self.logger.error(f"播放失败，错误代码: {result}")
                return False

        except Exception as e:
            self.logger.error(f"播放失败: {e}")
            self.state = MediaPlayerState.ERROR
            self._trigger_event('on_error', str(e))
            return False

    def pause(self) -> bool:
        """
        暂停播放

        Returns:
            bool: 是否暂停成功
        """
        try:
            if not self.vlc_player:
                return False

            if self.state == MediaPlayerState.PLAYING:
                self.vlc_player.pause()
                self.state = MediaPlayerState.PAUSED
                self.logger.info("暂停播放")
                return True

            return False

        except Exception as e:
            self.logger.error(f"暂停失败: {e}")
            return False

    def resume(self) -> bool:
        """
        恢复播放

        Returns:
            bool: 是否恢复成功
        """
        try:
            if not self.vlc_player:
                return False

            if self.state == MediaPlayerState.PAUSED:
                self._apply_audio_device(reason='pre-resume')
                self.vlc_player.pause()  # VLC的pause()是播放/暂停切换
                self.state = MediaPlayerState.PLAYING
                self.logger.info("恢复播放")
                return True

            return False

        except Exception as e:
            self.logger.error(f"恢复播放失败: {e}")
            return False

    def stop(self) -> bool:
        """
        停止播放

        Returns:
            bool: 是否停止成功
        """
        try:
            if not self.vlc_player:
                return False

            info = self.get_current_audio_device_info()
            pending_value = self._normalize_device_id(info.get('id')) or ''

            self.vlc_player.stop()
            self._audio_device_pending = True
            self._pending_audio_device_id = pending_value
            self.state = MediaPlayerState.STOPPED
            self.current_media_info.current_time = 0
            self.logger.info("停止播放")
            self._trigger_event('on_state_changed', self.state)
            return True

        except Exception as e:
            self.logger.error(f"停止播放失败: {e}")
            return False

    def is_playing(self) -> bool:
        """检查是否正在播放"""
        return self.state == MediaPlayerState.PLAYING

    def is_paused(self) -> bool:
        """检查是否已暂停"""
        return self.state == MediaPlayerState.PAUSED

    def is_stopped(self) -> bool:
        """检查是否已停止"""
        return self.state == MediaPlayerState.STOPPED

    def get_current_time(self) -> int:
        """获取当前播放时间（毫秒）"""
        try:
            if self.vlc_player:
                time_ms = self.vlc_player.get_time()
                self.current_media_info.current_time = time_ms
                return time_ms
            return 0
        except (AttributeError, ReferenceError):
            # VLC播放器未初始化或已释放
            return 0
        except Exception as e:
            # 其他未知异常，记录但不中断程序
            self.logger.debug(f"获取播放时间失败: {e}")
            return 0

    def get_duration(self) -> int:
        """获取媒体总时长（毫秒）"""
        try:
            if self.vlc_player:
                return self.vlc_player.get_length()
            return 0
        except (AttributeError, ReferenceError):
            # VLC播放器未初始化或已释放
            return 0
        except Exception as e:
            # 其他未知异常，记录但不中断程序
            self.logger.debug(f"获取媒体时长失败: {e}")
            return 0

    def set_position(self, position: float) -> bool:
        """
        设置播放位置

        Args:
            position: 播放位置（0.0 - 1.0）

        Returns:
            bool: 是否设置成功
        """
        try:
            if not self.vlc_player:
                return False

            if 0.0 <= position <= 1.0:
                self.vlc_player.set_position(position)
                self.logger.debug(f"设置播放位置: {position:.2f}")
                return True
            else:
                self.logger.error(f"无效的播放位置: {position}")
                return False

        except Exception as e:
            self.logger.error(f"设置播放位置失败: {e}")
            return False

    def get_position(self) -> float:
        """获取当前播放位置（0.0 - 1.0）"""
        try:
            if self.vlc_player:
                return self.vlc_player.get_position()
            return 0.0
        except:
            return 0.0

    def seek_forward(self, seconds: int = 5) -> bool:
        """
        快进

        Args:
            seconds: 快进秒数

        Returns:
            bool: 是否成功
        """
        try:
            current_time = self.get_current_time()
            new_time = current_time + (seconds * 1000)  # 转换为毫秒

            duration = self.get_duration()
            if new_time > duration:
                new_time = duration

            new_position = new_time / duration if duration > 0 else 0.0
            return self.set_position(new_position)

        except Exception as e:
            self.logger.error(f"快进失败: {e}")
            return False

    def seek_backward(self, seconds: int = 5) -> bool:
        """
        快退

        Args:
            seconds: 快退秒数

        Returns:
            bool: 是否成功
        """
        try:
            current_time = self.get_current_time()
            new_time = current_time - (seconds * 1000)  # 转换为毫秒

            if new_time < 0:
                new_time = 0

            duration = self.get_duration()
            new_position = new_time / duration if duration > 0 else 0.0
            return self.set_position(new_position)

        except Exception as e:
            self.logger.error(f"快退失败: {e}")
            return False

    def set_volume(self, volume: int) -> bool:
        """
        设置音量

        Args:
            volume: 音量值（0-100）

        Returns:
            bool: 是否设置成功
        """
        try:
            if not self.vlc_player:
                return False

            if 0 <= volume <= 100:
                self.vlc_player.audio_set_volume(volume)
                self.volume = volume
                self.is_muted = False
                self.logger.debug(f"设置音量: {volume}")
                self._trigger_event('on_volume_changed', volume)
                return True
            else:
                self.logger.error(f"无效的音量值: {volume}")
                return False

        except Exception as e:
            self.logger.error(f"设置音量失败: {e}")
            return False

    def get_volume(self) -> int:
        """获取当前音量"""
        try:
            if self.vlc_player:
                self.volume = self.vlc_player.audio_get_volume()
            return self.volume
        except:
            return 0

    def set_playback_rate(self, rate: float) -> bool:
        """
        设置播放倍速

        Args:
            rate: 播放倍速 (0.5, 1.0, 1.5, 2.0, 3.0等)

        Returns:
            bool: 是否设置成功
        """
        try:
            if not self.vlc_player:
                return False

            # VLC支持的范围是0.25到4.0
            if 0.25 <= rate <= 4.0:
                self.vlc_player.set_rate(rate)
                self.playback_rate = rate
                self.logger.debug(f"设置播放倍速: {rate}x")
                self._trigger_event('on_playback_rate_changed', rate)
                return True
            else:
                self.logger.error(f"无效的播放倍速: {rate}")
                return False

        except Exception as e:
            self.logger.error(f"设置播放倍速失败: {e}")
            return False

    def get_playback_rate(self) -> float:
        """获取当前播放倍速"""
        try:
            if self.vlc_player:
                self.playback_rate = self.vlc_player.get_rate()
            return self.playback_rate
        except:
            return 1.0

    def get_available_audio_tracks(self) -> list:
        """获取可用的音频轨道列表

        Returns:
            list: 音频轨道信息列表
        """
        try:
            if not self.vlc_player:
                return []

            audio_tracks = []

            # 方法1: 首先检查是否有媒体正在播放 (最可靠的方法)
            try:
                track_count = self.vlc_player.audio_get_track_count()
                self.logger.debug(f"VLC audio_get_track_count() 返回: {track_count}")

                # VLC返回-1表示没有媒体或错误，>0表示有音轨，0表示媒体存在但没有音轨
                if track_count > 0:
                    # 有音轨，尝试获取详细信息
                    try:
                        track_description = self.vlc_player.audio_get_track_description()
                        self.logger.debug(f"VLC audio_get_track_description() 返回: {track_description}")

                        if track_description and len(track_description) > 0:
                            # 使用VLC提供的轨道描述
                            for track_id, track_name in track_description:
                                # 处理轨道名称（可能是bytes类型）
                                if isinstance(track_name, bytes):
                                    try:
                                        track_name = track_name.decode('utf-8')
                                    except:
                                        track_name = str(track_name)

                                # 跳过"禁用"选项（track_id为-1）
                                if track_id == -1 and "禁用" in track_name:
                                    continue

                                # 包含所有有效轨道（包括ID为0的轨道）
                                if track_id >= 0:
                                    audio_tracks.append({
                                        'id': track_id,
                                        'name': track_name or f"音轨 {track_id}",
                                        'language': '',
                                        'type': 'audio'
                                    })

                            # 如果从描述中获取的轨道数量少于实际数量，补充默认轨道
                            if len(audio_tracks) < track_count:
                                existing_ids = {track['id'] for track in audio_tracks}
                                for i in range(track_count):
                                    if i not in existing_ids:
                                        audio_tracks.append({
                                            'id': i,
                                            'name': f"音轨 {i + 1}",
                                            'language': '',
                                            'type': 'audio'
                                        })
                        else:
                            # 如果没有描述，基于数量创建默认音轨
                            # VLC音轨ID可能从0开始，所以从0开始编号
                            for i in range(track_count):
                                audio_tracks.append({
                                    'id': i,
                                    'name': f"音轨 {i + 1}",  # 显示名称从1开始
                                    'language': '',
                                    'type': 'audio'
                                })
                    except Exception as e:
                        self.logger.debug(f"获取轨道描述失败，使用默认方式: {e}")
                        # 降级到基础方式
                        for i in range(track_count):
                            audio_tracks.append({
                                'id': i,
                                'name': f"音轨 {i + 1}",
                                'language': '',
                                'type': 'audio'
                            })

                elif track_count == 0:
                    # 明确返回0表示媒体存在但没有音频轨道
                    self.logger.debug("媒体存在但没有音频轨道")
                else:  # track_count == -1
                    # -1表示没有媒体加载或其他错误
                    self.logger.debug("没有媒体加载或VLC状态异常")

            except Exception as e:
                self.logger.error(f"获取音轨数量失败: {e}")

            # 方法2: 如果上面的方法失败，尝试从媒体信息获取详细信息 (备用方法)
            if not audio_tracks and self.vlc_media:
                try:
                    # 获取媒体信息 (这个API可能不稳定)
                    media_info = self.vlc_media.get_media_info()
                    if media_info:
                        # 获取音轨信息
                        audio_info = media_info.audio_tracks()
                        if audio_info:
                            track_count = audio_info.count()
                            for i in range(track_count):
                                try:
                                    track = audio_info.at(i)
                                    track_id = i  # VLC音轨ID可能从0开始
                                    track_name = getattr(track, 'description', lambda: f"音轨 {i + 1}")()
                                    track_language = getattr(track, 'language', lambda: "")()

                                    # 格式化轨道名称
                                    if track_language:
                                        name = f"{track_name} ({track_language})"
                                    else:
                                        name = track_name

                                    audio_tracks.append({
                                        'id': track_id,
                                        'name': name,
                                        'language': track_language,
                                        'type': 'audio'
                                    })
                                except Exception as e:
                                    self.logger.debug(f"处理媒体信息音轨 {i} 失败: {e}")
                                    # 创建基础音轨
                                    audio_tracks.append({
                                        'id': i,
                                        'name': f"音轨 {i + 1}",
                                        'language': '',
                                        'type': 'audio'
                                    })
                except Exception as e:
                    self.logger.debug(f"从媒体信息获取音轨失败: {e}")

            self.logger.debug(f"最终获取到 {len(audio_tracks)} 个音频轨道")
            return audio_tracks

        except Exception as e:
            self.logger.error(f"获取音频轨道列表失败: {e}")
            return []

    def set_audio_track(self, track_id: int) -> bool:
        """设置音频轨道

        Args:
            track_id: 轨道ID

        Returns:
            bool: 是否设置成功
        """
        try:
            if not self.vlc_player:
                return False

            # 设置音频轨道
            self.vlc_player.audio_set_track(track_id)
            self.logger.debug(f"设置音频轨道: {track_id}")

            # 触发轨道变更事件
            self._trigger_event('on_audio_track_changed', track_id)
            return True

        except Exception as e:
            self.logger.error(f"设置音频轨道失败: {e}")
            return False

    def get_current_audio_track(self) -> int:
        """获取当前音频轨道ID

        Returns:
            int: 当前轨道ID，0表示无轨道
        """
        try:
            if not self.vlc_player:
                return 0

            current_track = self.vlc_player.audio_get_track()
            return current_track if current_track > 0 else 0

        except Exception as e:
            self.logger.error(f"获取当前音频轨道失败: {e}")
            return 0

    def get_current_audio_track_info(self) -> dict:
        """获取当前音频轨道信息

        Returns:
            dict: 轨道信息字典
        """
        try:
            current_id = self.get_current_audio_track()
            if current_id == 0:
                return {}

            # 获取所有轨道信息
            all_tracks = self.get_available_audio_tracks()

            for track in all_tracks:
                if track.get('id') == current_id:
                    return track

            return {'id': current_id, 'name': f"音轨 {current_id}", 'type': 'audio'}

        except Exception as e:
            self.logger.error(f"获取当前音频轨道信息失败: {e}")
            return {}

    def set_mute(self, muted: bool) -> bool:
        """
        设置静音

        Args:
            muted: 是否静音

        Returns:
            bool: 是否设置成功
        """
        try:
            if not self.vlc_player:
                return False

            self.vlc_player.audio_set_mute(muted)
            self.is_muted = muted
            self.logger.debug(f"设置静音: {muted}")
            return True

        except Exception as e:
            self.logger.error(f"设置静音失败: {e}")
            return False

    def toggle_mute(self) -> bool:
        """切换静音状态"""
        return self.set_mute(not self.is_muted)

    def is_mute(self) -> bool:
        """检查是否静音"""
        return self.is_muted

    def set_rate(self, rate: float) -> bool:
        """
        设置播放倍速

        Args:
            rate: 播放倍速 (0.5 - 3.0)

        Returns:
            bool: 是否设置成功
        """
        try:
            if not self.vlc_player:
                return False

            # 限制倍速范围
            rate = max(0.1, min(4.0, rate))

            # 设置倍速
            self.vlc_player.set_rate(rate)
            self.logger.debug(f"设置播放倍速: {rate}x")
            return True

        except Exception as e:
            self.logger.error(f"设置播放倍速失败: {e}")
            return False

    def get_rate(self) -> float:
        """获取当前播放倍速"""
        try:
            if self.vlc_player:
                return self.vlc_player.get_rate()
            return 1.0
        except:
            return 1.0

    def set_fullscreen(self, fullscreen: bool) -> bool:
        """设置全屏模式

        Args:
            fullscreen: 是否全屏

        Returns:
            bool: 是否设置成功
        """
        try:
            if self.vlc_player:
                self.vlc_player.set_fullscreen(fullscreen)
                self.logger.debug(f"设置全屏模式: {fullscreen}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"设置全屏模式失败: {e}")
            return False

    def get_fullscreen(self) -> bool:
        """获取当前全屏状态"""
        try:
            if self.vlc_player:
                return self.vlc_player.get_fullscreen()
            return False
        except:
            return False

    def toggle_fullscreen(self) -> bool:
        """切换全屏模式"""
        try:
            if self.vlc_player:
                current = self.vlc_player.get_fullscreen()
                self.vlc_player.set_fullscreen(not current)
                self.logger.debug(f"切换全屏模式: {not current}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"切换全屏模式失败: {e}")
            return False

    def set_video_window(self, window_handle) -> bool:
        """设置视频渲染窗口

        Args:
            window_handle: 窗口句柄（Windows上为HWND，Linux上为XID）

        Returns:
            bool: 是否设置成功
        """
        try:
            if not self.vlc_player:
                return False

            if hasattr(self.vlc_player, 'set_hwnd'):
                # Windows平台
                self.vlc_player.set_hwnd(window_handle)
                self.logger.debug(f"设置Windows视频窗口句柄: {window_handle}")
                return True
            elif hasattr(self.vlc_player, 'set_xwindow'):
                # Linux平台
                self.vlc_player.set_xwindow(window_handle)
                self.logger.debug(f"设置X11视频窗口句柄: {window_handle}")
                return True
            elif hasattr(self.vlc_player, 'set_nsobject'):
                # macOS平台
                self.vlc_player.set_nsobject(window_handle)
                self.logger.debug(f"设置macOS视频窗口对象: {window_handle}")
                return True
            else:
                self.logger.warning("当前VLC版本不支持视频窗口设置")
                return False

        except Exception as e:
            self.logger.error(f"设置视频窗口失败: {e}")
            return False

    def get_media_info(self) -> MediaInfo:
        """获取当前媒体信息"""
        # 更新当前时间
        self.current_media_info.current_time = self.get_current_time()
        return self.current_media_info

    def _update_media_info(self, file_path: str):
        """更新媒体信息"""
        try:
            self.current_media_info.file_path = file_path
            self.current_media_info.title = os.path.splitext(os.path.basename(file_path))[0]

            # 获取媒体详细信息
            if self.vlc_media:
                # 获取时长
                self.current_media_info.duration = self.vlc_player.get_length()

                # 获取媒体信息（需要等待解析完成）
                self._extract_media_details()

            # 检测媒体类型
            from .file_detector import MediaFileDetector
            self.current_media_info.media_type = MediaFileDetector.get_media_type(file_path) or "unknown"

        except Exception as e:
            self.logger.error(f"更新媒体信息失败: {e}")

    def _extract_media_details(self):
        """提取媒体详细信息"""
        try:
            # 这里可以添加更多媒体信息提取逻辑
            # VLC的媒体信息提取比较复杂，暂时使用基础信息
            pass
        except Exception as e:
            self.logger.error(f"提取媒体详细信息失败: {e}")

    def _on_media_ended(self, event):
        """媒体播放结束事件"""
        self.logger.info("媒体播放结束")
        self.state = MediaPlayerState.STOPPED
        self.current_media_info.current_time = 0
        self._trigger_event('on_state_changed', self.state)
        # 触发播放完成事件
        self._trigger_event('on_finished')

    def _on_time_changed(self, event):
        """播放时间变化事件"""
        self._trigger_event('on_time_changed', self.get_current_time())

    def _on_state_changed(self, event):
        """播放器状态变化事件"""
        try:
            vlc_state = self.vlc_player.get_state()
            vlc_lib = self.vlc_loader.get_vlc_lib()

            # 映射VLC状态到我们的状态
            state_map = {
                vlc_lib.State.NothingSpecial: MediaPlayerState.STOPPED,
                vlc_lib.State.Opening: MediaPlayerState.LOADING,
                vlc_lib.State.Buffering: MediaPlayerState.LOADING,
                vlc_lib.State.Playing: MediaPlayerState.PLAYING,
                vlc_lib.State.Paused: MediaPlayerState.PAUSED,
                vlc_lib.State.Stopped: MediaPlayerState.STOPPED,
                vlc_lib.State.Ended: MediaPlayerState.STOPPED,
                vlc_lib.State.Error: MediaPlayerState.ERROR,
            }

            new_state = state_map.get(vlc_state, MediaPlayerState.STOPPED)
            if new_state != self.state:
                old_state = self.state
                self.state = new_state
                self.logger.debug(f"播放器状态变化: {old_state} -> {new_state}")
                self._trigger_event('on_state_changed', new_state)

        except Exception as e:
            self.logger.error(f"处理状态变化事件失败: {e}")

    def _on_media_playing(self, event):
        """Handle MediaPlayerPlaying event to reapply audio device if needed."""
        if self._audio_device_pending:
            if self._apply_audio_device(reason='playing-event'):
                self.logger.debug('Audio device reapplied after MediaPlayerPlaying event')
            else:
                self.logger.debug('Audio device still pending after MediaPlayerPlaying event')


    def _on_media_parsed(self, event):
        """媒体解析完成事件"""
        try:
            if self.vlc_media.get_parsed_status() == self.vlc_loader.get_vlc_lib().MediaParsedStatus.Done:
                self._extract_media_details()
                self.logger.debug("媒体解析完成")
        except Exception as e:
            self.logger.error(f"处理媒体解析事件失败: {e}")

    def add_event_callback(self, event_name: str, callback: Callable):
        """添加事件回调"""
        if event_name in self.event_callbacks:
            self.event_callbacks[event_name].append(callback)

    def remove_event_callback(self, event_name: str, callback: Callable):
        """移除事件回调"""
        if event_name in self.event_callbacks:
            if callback in self.event_callbacks[event_name]:
                self.event_callbacks[event_name].remove(callback)

    def _trigger_event(self, event_name: str, data=None):
        """触发事件回调"""
        if event_name in self.event_callbacks:
            for callback in self.event_callbacks[event_name]:
                try:
                    callback(data)
                except Exception as e:
                    self.logger.error(f"事件回调执行失败: {e}")

    @staticmethod
    def _decode_c_string(value) -> str:
        """将C风格字符串安全解码为Python字符串"""
        if value is None:
            return ""
        if isinstance(value, bytes):
            for encoding in ('utf-8', 'gbk'):
                try:
                    return value.decode(encoding)
                except UnicodeDecodeError:
                    continue
            return value.decode('utf-8', errors='ignore')
        return str(value)

    @staticmethod
    def _normalize_device_id(device_id: Optional[str]) -> Optional[str]:
        """规范化VLC返回的设备标识"""
        if device_id is None:
            return None
        if isinstance(device_id, bytes):
            device_id = device_id.decode('utf-8', errors='ignore')
        device_id = str(device_id).strip()
        return device_id or None

    def _default_audio_device_entry(self) -> dict:
        """构造默认音频设备描述"""
        return {
            'id': None,
            'name': '默认设备',
            'description': '系统默认音频输出设备',
            'module': None,
            'module_description': '系统默认音频输出设备',
            'is_default': True
        }

    def _select_audio_output_module(self) -> Optional[str]:
        """确保使用能够枚举真实设备的音频输出模块"""
        if self._audio_output_module is not None:
            return self._audio_output_module

        if not self.vlc_player or not hasattr(self.vlc_player, 'audio_output_set'):
            return None

        if platform.system() == 'Windows':
            candidates = ['mmdevice', 'directsound', 'waveout']
        else:
            candidates = [None]

        for module in candidates:
            try:
                if module:
                    self.vlc_player.audio_output_set(module)
                self._audio_output_module = module
                self.logger.debug(f"音频输出模块选择: {module or '默认'}")
                return module
            except Exception as e:
                self.logger.debug(f"设置音频输出模块失败 {module}: {e}")

        self._audio_output_module = None
        return None

    def _apply_audio_device(self, reason: str = "manual") -> bool:
        """Apply the cached audio device selection to VLC."""
        if not self.vlc_player:
            return False

        info = self.current_audio_device or self._default_audio_device_entry()
        device_id = self._normalize_device_id(info.get('id'))
        module_name = info.get('module') or self._audio_output_module or self._select_audio_output_module()
        target_value = device_id or ''

        # LibVLC recommends passing None for MMDevice/PulseAudio to switch devices immediately.
        module_arg = module_name or ''
        module_for_device_set = None
        if module_name:
            lowered = module_name.lower()
            if lowered in ('mmdevice', 'pulse', 'pulseaudio'):
                module_for_device_set = None
            else:
                module_for_device_set = module_arg
        py_module_arg = module_for_device_set

        try:
            if module_arg:
                try:
                    self.vlc_player.audio_output_set(module_arg)
                    self._audio_output_module = module_arg
                except Exception as module_error:
                    self.logger.debug(f"Failed to set audio output module ({reason}): {module_error}")

            applied = False
            if hasattr(self.vlc_player, 'audio_output_device_set'):
                try:
                    self.vlc_player.audio_output_device_set(py_module_arg, target_value)
                    applied = True
                except Exception as py_vlc_error:
                    self.logger.debug(f"python-vlc audio_output_device_set failed ({reason}): {py_vlc_error}")

            if not applied:
                try:
                    vlc_lib = self.vlc_loader.get_vlc_lib()
                    module_bytes = module_for_device_set.encode('utf-8') if isinstance(module_for_device_set, str) and module_for_device_set else None
                    device_bytes = target_value.encode('utf-8') if target_value else b''
                    vlc_lib.libvlc_audio_output_device_set(self.vlc_player, module_bytes, device_bytes)
                    applied = True
                except Exception as c_error:
                    self.logger.debug(f"libvlc audio_output_device_set failed ({reason}): {c_error}")

            if applied:
                self._audio_device_pending = False
                self._pending_audio_device_id = None
                self.logger.debug(
                    f"Audio device applied ({reason}): {info.get('name', 'default')} -> {target_value or 'default'}")
                return True

        except Exception as apply_error:
            self.logger.debug(f"Applying audio device failed ({reason}): {apply_error}")

        self._audio_device_pending = True
        self._pending_audio_device_id = target_value
        return False

    def _current_vlc_device_id(self) -> Optional[str]:
        """读取当前激活的 VLC 音频设备标识。"""
        if not self.vlc_player or not hasattr(self.vlc_player, 'audio_output_device_get'):
            return None

        try:
            current_raw = self.vlc_player.audio_output_device_get()
        except Exception as read_error:
            self.logger.debug(f"读取当前音频设备失败: {read_error}")
            return None

        return self._normalize_device_id(current_raw)

    def _verify_audio_device_selection(self, expected_id: Optional[str]) -> bool:
        """验证 VLC 报告的当前设备是否与目标设备一致。"""
        if expected_id is None:
            return self._current_vlc_device_id() is None
        return self._current_vlc_device_id() == expected_id

    def _schedule_audio_device_resync(
            self,
            expected_id: Optional[str],
            device_name: str,
            retries: int = 3,
            delay: float = 0.4,
            force_restart: bool = False
    ) -> None:
        """在后台重试应用音频设备，避免阻塞 UI 线程。"""
        if retries <= 0:
            self.logger.warning(f'音频设备仍未切换到: {device_name}，请手动重试')
            self._audio_device_pending = True
            self._pending_audio_device_id = expected_id
            return

        with self._device_sync_lock:
            if self._device_sync_thread and self._device_sync_thread.is_alive():
                # 合并新的切换请求，交由现有任务处理
                self._pending_audio_device_id = expected_id
                self.logger.debug('已有音频设备重试任务在运行，更新待应用的目标设备')
                return

            def worker():
                try:
                    attempts = retries
                    success = False
                    wait_time = delay
                    first_attempt = True

                    while attempts > 0:
                        if not first_attempt:
                            time.sleep(max(0.05, wait_time))
                        first_attempt = False

                        # 如果用户改选了其他设备，提前结束任务
                        current_expected = self._normalize_device_id(
                            (self.current_audio_device or {}).get('id')
                        )
                        if current_expected != expected_id:
                            self.logger.debug('检测到新的音频设备选择，取消旧的重试任务')
                            return

                        restarted = False
                        needs_restart = (
                            self.state == MediaPlayerState.PLAYING
                            and (self._audio_output_module or '').lower() in ('mmdevice', 'pulse', 'pulseaudio')
                        )

                        if force_restart and needs_restart:
                            self.logger.debug('后台执行播放重启以应用音频设备')
                            restarted = self._restart_playback_for_device_change()

                        applied = self._apply_audio_device(reason='device-sync')
                        if applied or restarted:
                            if self._verify_audio_device_selection(expected_id):
                                success = True
                                break

                            if needs_restart and not restarted:
                                self.logger.debug('常规设置未生效，尝试后台重启播放')
                                if self._restart_playback_for_device_change() and self._verify_audio_device_selection(expected_id):
                                    success = True
                                    break

                        attempts -= 1
                        wait_time *= 1.5

                    if not success and self.state == MediaPlayerState.PLAYING:
                        self.logger.debug('常规重试未成功，尝试通过后台重启播放应用设备')
                        success = self._restart_playback_for_device_change() and \
                                  self._verify_audio_device_selection(expected_id)

                    if success:
                        self._audio_device_pending = False
                        self._pending_audio_device_id = None
                        self.logger.info(f'音频设备已设置为: {device_name}')
                        self._trigger_event('on_audio_device_changed', device_name)
                    else:
                        self.logger.error(f'音频设备应用失败: {device_name}')
                        self._audio_device_pending = True
                        self._pending_audio_device_id = expected_id
                finally:
                    with self._device_sync_lock:
                        self._device_sync_thread = None

            thread = threading.Thread(
                target=worker,
                name='AudioDeviceResync',
                daemon=True
            )
            self._device_sync_thread = thread

        thread.start()


    def _restart_playback_for_device_change(self) -> bool:
        """在播放过程中重启播放器以应用音频设备变更，同时尽量保持当前播放进度。"""
        if not self.vlc_player or not self.vlc_media:
            return False
        if self.state != MediaPlayerState.PLAYING:
            return False

        try:
            resume_time = max(0, int(self.vlc_player.get_time()))
        except Exception:
            resume_time = 0

        self.logger.debug('尝试通过重启播放来应用音频设备变更')

        try:
            self.vlc_player.stop()
        except Exception as stop_err:
            self.logger.debug(f'停止播放器失败（重启播放）: {stop_err}')
            return False

        time.sleep(0.05)

        try:
            self.vlc_player.set_media(self.vlc_media)
        except Exception as media_err:
            self.logger.debug(f'重新绑定媒体失败: {media_err}')
            return False

        applied = self._apply_audio_device(reason='device-restart')

        try:
            result = self.vlc_player.play()
        except Exception as play_err:
            self.logger.error(f'音频设备变更后重启播放失败: {play_err}')
            return False

        if result != 0:
            self.logger.error(f'音频设备变更后重启播放失败，VLC返回值: {result}')
            return False

        target_state = None
        try:
            target_state = self.vlc_loader.get_vlc_lib().State.Playing
        except Exception:
            target_state = None

        start_time = time.time()
        while time.time() - start_time < 1.0:
            try:
                state = self.vlc_player.get_state()
                if target_state is None or state == target_state:
                    break
            except Exception:
                break
            time.sleep(0.05)

        if resume_time > 0:
            try:
                self.vlc_player.set_time(resume_time)
            except Exception as resume_err:
                self.logger.debug(f'恢复播放进度失败: {resume_err}')

        if applied:
            self._audio_device_pending = False
            self._pending_audio_device_id = None
        else:
            info = self.get_current_audio_device_info()
            self._audio_device_pending = True
            self._pending_audio_device_id = self._normalize_device_id(info.get('id'))

        return applied


    def _enumerate_audio_output_devices(self) -> list:
        """使用 audio_output_device_enum 枚举当前模块下的音频设备"""
        devices = []

        if not self.vlc_player or not hasattr(self.vlc_player, 'audio_output_device_enum'):
            return devices

        try:
            list_head = self.vlc_player.audio_output_device_enum()
        except AttributeError:
            self.logger.debug("当前VLC版本不支持 audio_output_device_enum")
            return devices
        except Exception as e:
            self.logger.debug(f"获取音频设备列表失败: {e}")
            return devices

        node = list_head
        seen = set()
        try:
            while node:
                struct = node.contents
                device_id = self._decode_c_string(getattr(struct, 'device', None))
                description = self._decode_c_string(getattr(struct, 'description', None))
                node = getattr(struct, 'next', None)

                if not device_id or device_id in seen:
                    continue

                seen.add(device_id)
                friendly = description or device_id
                devices.append({
                    'id': device_id,
                    'name': friendly,
                    'description': friendly,
                })
        finally:
            if list_head:
                try:
                    vlc.libvlc_audio_output_device_list_release(list_head)
                except Exception as release_err:
                    self.logger.debug(f"释放音频设备列表失败: {release_err}")

        return devices

    def get_available_audio_devices(self, force_refresh: bool = False) -> list:
        """
        获取可用的音频设备列表

        Args:
            force_refresh: 是否强制刷新设备列表

        Returns:
            list: 音频设备列表，每个设备包含name和description
        """
        import time

        current_time = time.time()
        if (not force_refresh and self.available_audio_devices and
                current_time - self.device_cache_time < self.device_cache_timeout):
            return list(self.available_audio_devices)

        devices = []
        try:
            if not self.vlc_instance:
                self.logger.warning("VLC实例不可用，无法获取音频设备")
            else:
                self._select_audio_output_module()
                devices = self._enumerate_audio_output_devices()
        except Exception as e:
            self.logger.error(f"获取音频设备列表失败: {e}")
            devices = []

        result_devices = [self._default_audio_device_entry()]

        module_name = self._audio_output_module
        module_desc = '系统默认音频输出设备' if module_name is None else module_name

        for device in devices:
            result_devices.append({
                'id': device['id'],
                'name': device['name'],
                'description': device['description'],
                'module': module_name,
                'module_description': module_desc,
                'is_default': False
            })

        if len(result_devices) == 1:
            self.logger.debug("音频设备枚举为空，使用默认设备")

        self.available_audio_devices = result_devices
        self.device_cache_time = current_time

        # Ensure current audio device still exists; otherwise fall back to default
        valid_ids = {self._normalize_device_id(dev.get('id')) for dev in result_devices}
        current_info = self.current_audio_device if isinstance(self.current_audio_device, dict) else None
        current_id = self._normalize_device_id(current_info.get('id')) if current_info else None
        if current_id not in valid_ids:
            self.current_audio_device = self._default_audio_device_entry()

        self.logger.info(f"发现 {len(result_devices)} 个音频设备")
        for device in result_devices:
            self.logger.debug(
                f"  - {device['name']} (id: {device.get('id') or 'default'})"
            )

        return list(result_devices)

    def _get_fallback_devices(self) -> list:
        """获取回退设备列表（当VLC API不可用时）"""
        return [self._default_audio_device_entry()]

    def set_audio_device(self, device) -> bool:
        """Set the preferred audio output device."""
        try:
            if not self.vlc_player:
                self.logger.error('播放器未初始化，无法设置音频设备')
                return False

            self._select_audio_output_module()
            available_devices = self.available_audio_devices or self.get_available_audio_devices(force_refresh=True)

            target_entry = None
            if isinstance(device, dict):
                target_entry = dict(device)
            else:
                normalized = self._normalize_device_id(device)
                for candidate in available_devices:
                    if normalized in (self._normalize_device_id(candidate.get('id')), self._normalize_device_id(candidate.get('name'))):
                        target_entry = dict(candidate)
                        break

            if target_entry is None:
                display = device.get('name') if isinstance(device, dict) else device
                self.logger.error(f'不可用的音频设备: {display}')
                return False

            if target_entry.get('is_default') or not target_entry.get('id'):
                self.current_audio_device = self._default_audio_device_entry()
            else:
                self.current_audio_device = {
                    'id': target_entry.get('id'),
                    'name': target_entry.get('name'),
                    'description': target_entry.get('description'),
                    'module': target_entry.get('module'),
                    'module_description': target_entry.get('module_description'),
                    'is_default': False
                }

            applied = self._apply_audio_device(reason='user-select')
            device_name = self.current_audio_device.get('name', '默认设备')
            expected_id = self._normalize_device_id(self.current_audio_device.get('id'))
            needs_restart = (
                self.state == MediaPlayerState.PLAYING
                and (self._audio_output_module or '').lower() in ('mmdevice', 'pulse', 'pulseaudio')
            )
            if applied:
                if needs_restart:
                    self.logger.info(f'音频设备已设置为: {device_name}（后台重启播放以生效）')
                    self._audio_device_pending = True
                    self._pending_audio_device_id = expected_id
                    self._schedule_audio_device_resync(expected_id, device_name, force_restart=True)
                    return True

                if self._verify_audio_device_selection(expected_id):
                    self._audio_device_pending = False
                    self._pending_audio_device_id = None
                    self.logger.info(f'音频设备已设置为: {device_name}')
                    self._trigger_event('on_audio_device_changed', device_name)
                    return True

                self.logger.info(f'音频设备切换正在应用: {device_name}（后台重试）')
                self._audio_device_pending = True
                self._pending_audio_device_id = expected_id
                self._schedule_audio_device_resync(expected_id, device_name)
                return True

            self.logger.error(f'音频设备应用失败: {device_name}')
            self._audio_device_pending = True
            self._pending_audio_device_id = expected_id
            self._schedule_audio_device_resync(expected_id, device_name, retries=2, force_restart=needs_restart)
            return False

        except Exception as e:
            self.logger.error(f'设置音频设备失败: {e}')
            self._audio_device_pending = True
            return False

    def get_current_audio_device(self) -> str:
        info = self.get_current_audio_device_info()
        return info.get('name', '默认设备')

    def get_current_audio_device_info(self) -> dict:
        if isinstance(self.current_audio_device, dict):
            info = dict(self.current_audio_device)
            if info.get('module') is None:
                info['module'] = self._audio_output_module
                info['module_description'] = self._audio_output_module or '系统默认音频输出设备'
            return info
        return self._default_audio_device_entry()



    def refresh_audio_devices(self) -> list:
        """强制刷新音频设备列表"""
        return self.get_available_audio_devices(force_refresh=True)

    def is_audio_device_available(self, device_name: str) -> bool:
        """检查指定音频设备是否可用"""
        available_devices = self.get_available_audio_devices()
        return any(d['name'] == device_name for d in available_devices)

    def cleanup(self):
        """清理播放器资源"""
        try:
            self.logger.debug("开始清理媒体播放器资源")

            # 停止播放 - 添加更安全的检查
            if self.vlc_player is not None:
                try:
                    self.vlc_player.stop()
                except Exception as stop_error:
                    self.logger.warning(f"停止播放时出错: {stop_error}")

            # 按照依赖关系顺序释放VLC资源
            # 先释放媒体和播放器相关的资源
            if self.vlc_media is not None:
                try:
                    self.vlc_media.release()
                    self.logger.debug("已释放VLC媒体资源")
                except Exception as media_error:
                    self.logger.warning(f"释放VLC媒体资源时出错: {media_error}")
                finally:
                    self.vlc_media = None

            if self.vlc_player is not None:
                try:
                    self.vlc_player.release()
                    self.logger.debug("已释放VLC播放器")
                except Exception as player_error:
                    self.logger.warning(f"释放VLC播放器时出错: {player_error}")
                finally:
                    self.vlc_player = None

            if self.vlc_media_list_player is not None:
                try:
                    self.vlc_media_list_player.release()
                    self.logger.debug("已释放VLC媒体列表播放器")
                except Exception as list_player_error:
                    self.logger.warning(f"释放VLC媒体列表播放器时出错: {list_player_error}")
                finally:
                    self.vlc_media_list_player = None

            if self.vlc_media_list is not None:
                try:
                    self.vlc_media_list.release()
                    self.logger.debug("已释放VLC媒体列表")
                except Exception as list_error:
                    self.logger.warning(f"释放VLC媒体列表时出错: {list_error}")
                finally:
                    self.vlc_media_list = None

            # 最后清理VLC加载器
            if self.vlc_loader is not None:
                try:
                    self.vlc_loader.cleanup()
                    self.logger.debug("已清理VLC加载器")
                except Exception as loader_error:
                    self.logger.warning(f"清理VLC加载器时出错: {loader_error}")
                finally:
                    self.vlc_loader = None

            self.logger.info("媒体播放器资源已清理完成")

        except Exception as e:
            self.logger.error(f"清理播放器资源失败: {e}")
            import traceback
            self.logger.debug(f"清理异常详情: {traceback.format_exc()}")
        finally:
            # 确保所有引用都被清空
            self.vlc_media = None
            self.vlc_player = None
            self.vlc_media_list_player = None
            self.vlc_media_list = None
            self.vlc_loader = None
