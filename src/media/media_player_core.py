#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
媒体播放器核心
基于VLC的媒体播放核心实现，支持音视频播放控制
"""

import os
import time
import platform
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

        # 循环控制
        self.repeat_mode = "none"  # none, one, all

        # 音频设备管理
        self.current_audio_device = self._default_audio_device_entry()
        self.available_audio_devices = []
        self.device_cache_time = 0
        self.device_cache_timeout = 30  # 缓存30秒
        self._audio_output_module = None

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
        """设置VLC事件监听"""
        try:
            event_manager = self.vlc_player.event_manager()
            vlc_lib = self.vlc_loader.get_vlc_lib()

            # 媒体结束事件
            event_manager.event_attach(
                vlc_lib.EventType.MediaPlayerEndReached,
                self._on_media_ended
            )

            # 媒体时间变化事件
            event_manager.event_attach(
                vlc_lib.EventType.MediaPlayerTimeChanged,
                self._on_time_changed
            )

            # 播放器状态变化事件 - 尝试不同的事件名称
            try:
                event_manager.event_attach(
                    vlc_lib.EventType.MediaPlayerStateChanged,
                    self._on_state_changed
                )
            except AttributeError:
                # 如果新版本没有这个事件，跳过
                self.logger.warning("MediaPlayerStateChanged事件不可用，跳过状态监听")

            # 媒体解析结束事件
            try:
                event_manager.event_attach(
                    vlc_lib.EventType.MediaParsedChanged,
                    self._on_media_parsed
                )
            except AttributeError:
                # 如果新版本没有这个事件，跳过
                self.logger.warning("MediaParsedChanged事件不可用，跳过解析监听")

        except Exception as e:
            self.logger.error(f"设置VLC事件监听失败: {e}")
            # 继续执行，不影响基本播放功能

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

            self.vlc_player.stop()
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

        current_info = self.get_current_audio_device_info()
        self.current_audio_device = current_info

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
        """
        设置音频输出设备

        Args:
            device: 设备描述字典或设备名称/ID

        Returns:
            bool: 是否设置成功
        """
        try:
            if not self.vlc_player:
                self.logger.error("播放器未初始化，无法设置音频设备")
                return False

            self._select_audio_output_module()

            available_devices = self.available_audio_devices or self.get_available_audio_devices(force_refresh=True)

            target_entry = None
            if isinstance(device, dict):
                target_entry = device
            else:
                normalized = self._normalize_device_id(device)
                for candidate in available_devices:
                    if normalized in (
                        self._normalize_device_id(candidate.get('id')),
                        self._normalize_device_id(candidate.get('name'))
                    ):
                        target_entry = candidate
                        break

            if target_entry is None:
                if isinstance(device, dict):
                    display = device.get('name', '默认设备')
                else:
                    display = device
                self.logger.error(f"不可用的音频设备: {display}")
                return False

            target_id = self._normalize_device_id(target_entry.get('id'))
            display_name = target_entry.get('name', '默认设备')

            try:
                target_value = '' if target_id is None else target_id
                if hasattr(self.vlc_player, 'audio_output_device_set'):
                    self.vlc_player.audio_output_device_set(None, target_value)
                else:
                    self.logger.error("当前VLC播放器缺少 audio_output_device_set 接口")
                    return False
            except Exception as e:
                self.logger.error(f"设置音频输出设备失败: {e}")
                return False

            try:
                current_raw = self.vlc_player.audio_output_device_get()
            except Exception as e:
                self.logger.debug(f"读取当前音频设备失败: {e}")
                current_raw = None

            current_id = self._normalize_device_id(current_raw)
            if target_id is not None and current_id != target_id:
                self.logger.warning(f"期望切换到 {display_name}，但实际为 {current_id or '默认'}")

            if current_id is None:
                self.current_audio_device = self._default_audio_device_entry()
            else:
                matched = None
                for candidate in self.available_audio_devices:
                    if self._normalize_device_id(candidate.get('id')) == current_id:
                        matched = candidate
                        break
                if not matched:
                    matched = {
                        'id': current_id,
                        'name': display_name,
                        'description': display_name,
                        'module': self._audio_output_module,
                        'module_description': self._audio_output_module or '系统默认音频输出设备',
                        'is_default': False
                    }
                self.current_audio_device = matched

            self.logger.info(f"音频设备已设置为: {self.current_audio_device.get('name', '默认设备')}")
            self._trigger_event('on_audio_device_changed', self.current_audio_device.get('name'))

            return True

        except Exception as e:
            self.logger.error(f"设置音频设备失败: {e}")
            return False

    def get_current_audio_device(self) -> str:
        """获取当前音频设备"""
        info = self.get_current_audio_device_info()
        return info.get('name', '默认设备')

    def get_current_audio_device_info(self) -> dict:
        """获取当前音频设备的完整信息"""
        if not self.vlc_player or not hasattr(self.vlc_player, 'audio_output_device_get'):
            return self._default_audio_device_entry()

        try:
            current_raw = self.vlc_player.audio_output_device_get()
        except Exception as e:
            self.logger.debug(f"读取当前音频设备信息失败: {e}")
            current_raw = None

        current_id = self._normalize_device_id(current_raw)
        if current_id is None:
            return self._default_audio_device_entry()

        for device in self.available_audio_devices:
            if self._normalize_device_id(device.get('id')) == current_id:
                return dict(device)

        return {
            'id': current_id,
            'name': current_id,
            'description': current_id,
            'module': self._audio_output_module,
            'module_description': self._audio_output_module or '系统默认音频输出设备',
            'is_default': False
        }

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
            # 停止播放
            if self.vlc_player:
                self.vlc_player.stop()

            # 释放VLC资源
            if self.vlc_media:
                self.vlc_media.release()
            if self.vlc_player:
                self.vlc_player.release()
            if self.vlc_media_list_player:
                self.vlc_media_list_player.release()
            if self.vlc_media_list:
                self.vlc_media_list.release()

            # 清理VLC加载器
            if self.vlc_loader:
                self.vlc_loader.cleanup()

            self.logger.info("媒体播放器资源已清理")

        except Exception as e:
            self.logger.error(f"清理播放器资源失败: {e}")
