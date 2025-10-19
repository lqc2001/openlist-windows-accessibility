#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版音频播放器
借鉴ForumAssist项目的声卡切换、状态栏显示和播放控制逻辑
"""

import os
import sys
import time
import threading
import platform
from typing import List, Dict, Optional, Callable
from pathlib import Path
from src.core.logger import get_logger

# 尝试导入VLC加载器
try:
    from .vlc_loader import VLCLoader
except ImportError:
    try:
        from vlc_loader import VLCLoader
    except ImportError:
        VLCLoader = None


class EnhancedAudioPlayer:
    """增强版音频播放器

    支持功能：
    1. 声卡设备枚举和切换
    2. 实时状态显示
    3. 播放控制逻辑
    4. 播放列表管理
    5. 音量控制
    """

    def __init__(self):
        """初始化增强版音频播放器"""
        self.logger = get_logger()

        # VLC相关
        self.vlc_loader = None
        self.vlc_lib = None
        self.instance = None
        self.player = None
        self.is_vlc_available = False

        # 播放状态
        self.is_playing = False
        self.is_paused = False
        self.current_index = 0
        self.current_time = 0
        self.total_time = 0
        self.current_volume = 100

        # 声卡设备
        self.use_system_default_device = True
        self.selected_device_id: Optional[str] = None
        self.audio_devices: List[Dict] = []

        # 播放列表
        self.playlist: List[Dict] = []

        # 更新定时器
        self.update_timer = None
        self.update_interval = 1.0  # 1秒更新一次

        # 回调函数
        self.on_status_update: Optional[Callable] = None
        self.on_device_changed: Optional[Callable] = None

        # 初始化
        self._initialize_vlc()
        self._initialize_com()  # Windows COM初始化

    def _initialize_com(self):
        """初始化COM（Windows平台）"""
        if platform.system() == 'Windows':
            try:
                import pythoncom
                pythoncom.CoInitialize()
                self.logger.info("COM初始化成功")
            except ImportError:
                self.logger.warning("pythoncom不可用，COM初始化跳过")
            except Exception as e:
                self.logger.warning(f"COM初始化失败: {e}")

    def _initialize_vlc(self):
        """初始化VLC"""
        try:
            # 使用VLC加载器
            if VLCLoader:
                self.vlc_loader = VLCLoader()
                if self.vlc_loader.is_vlc_available():
                    self.vlc_lib = self.vlc_loader.get_vlc_lib()
                    self.instance = self.vlc_loader.get_vlc_instance()
                    self.is_vlc_available = True
                    self.logger.info(f"VLC加载成功 - 版本: {self.vlc_loader.get_vlc_version()}")
                else:
                    self.logger.error("VLC加载失败")
                    self.is_vlc_available = False
            else:
                # 直接导入VLC
                self._direct_import_vlc()

            if self.is_vlc_available:
                self._create_player()
                self._refresh_audio_devices()

        except Exception as e:
            self.logger.error(f"VLC初始化失败: {e}")
            self.is_vlc_available = False

    def _direct_import_vlc(self):
        """直接导入VLC（备用方法）"""
        try:
            import vlc
            self.vlc_lib = vlc

            # VLC启动参数 - 借鉴ForumAssist的配置
            args = [
                '--quiet',  # 安静模式
                '--no-video-title-show',  # 不显示视频标题
                '--no-sub-autodetect-file',  # 不自动检测字幕文件
                '--no-snapshot-preview',  # 不显示快照预览
                '--no-stats',  # 不收集统计信息（减少资源占用）
                '--no-audio-time-stretch',  # 禁用音频时间拉伸
                '--network-caching=3000',  # 网络缓存3秒，提高流媒体稳定性
                '--http-reconnect',  # 启用HTTP重连
            ]

            # Windows特定优化
            if platform.system() == 'Windows':
                try:
                    args.extend(['--aout=directx'])
                except:
                    try:
                        args.extend(['--aout=waveout'])
                    except:
                        pass  # 使用默认音频输出

            self.instance = vlc.Instance(args)
            self.is_vlc_available = True
            self.logger.info("VLC直接导入成功")

        except Exception as e:
            self.logger.error(f"VLC直接导入失败: {e}")
            self.is_vlc_available = False

    def _create_player(self):
        """创建VLC播放器"""
        if not self.instance:
            raise RuntimeError("VLC实例未创建")

        try:
            self.player = self.instance.media_player_new()
            if self.player is None:
                raise RuntimeError("VLC播放器创建失败")

            # 应用用户选择的音频设备
            self._apply_selected_audio_device()

            self.logger.info("VLC播放器创建成功")

        except Exception as e:
            self.logger.error(f"VLC播放器创建失败: {e}")
            raise

    def get_audio_devices(self) -> List[Dict]:
        """
        枚举可用的音频输出设备
        基于VLC官方API获取真实设备列表
        """
        if not self.is_vlc_available or not self.player:
            return [{
                'id': 'default',
                'name': '系统默认设备',
                'is_current': True,
                'description': 'VLC不可用或不支持音频设备切换'
            }]

        devices = []

        try:
            # 获取当前设备
            try:
                current_device_raw = self.player.audio_output_device_get()
            except Exception as e:
                self.logger.warning(f"获取当前音频设备失败: {e}")
                current_device_raw = None

            current_device_id = self._normalize_device_identifier(current_device_raw)

            # 更新设备状态
            if current_device_id:
                self.use_system_default_device = False
                self.selected_device_id = current_device_id
            else:
                self.use_system_default_device = True
                self.selected_device_id = None

            # 枚举所有设备
            list_head = None
            try:
                # 使用VLC官方API枚举设备（需要指定音频输出模块）
                # 常见的音频输出模块
                audio_modules = ['directx', 'waveout', 'mmdevice'] if platform.system() == 'Windows' else ['alsa', 'pulse', 'oss']

                for module in audio_modules:
                    try:
                        list_head = self.vlc_lib.libvlc_audio_output_device_enum(module)
                        if list_head:
                            break
                    except:
                        continue

                if not list_head:
                    # 如果所有模块都失败，尝试使用空字符串
                    try:
                        list_head = self.vlc_lib.libvlc_audio_output_device_enum('')
                    except:
                        pass

                if list_head:
                    current = list_head
                    seen_devices = set()  # 去重

                    while current:
                        try:
                            # 获取设备信息
                            device_id = current.contents.psz_identifier
                            description = current.contents.psz_description

                            if device_id and device_id not in seen_devices:
                                seen_devices.add(device_id)

                                # 规范化设备ID
                                normalized_id = self._normalize_device_identifier(device_id)

                                # 判断是否为当前设备
                                is_current = (normalized_id == current_device_id)

                                # 使用友好名称
                                friendly_name = description or device_id

                                devices.append({
                                    'id': normalized_id,
                                    'name': friendly_name,
                                    'description': friendly_name,
                                    'is_current': is_current
                                })

                        except Exception as e:
                            self.logger.debug(f"处理音频设备信息失败: {e}")

                        # 移动到下一个设备
                        try:
                            current = current.contents.p_next
                        except:
                            break

                # 添加系统默认设备选项
                default_device = {
                    'id': 'default',
                    'name': '系统默认设备',
                    'description': '使用系统默认音频输出设备',
                    'is_current': self.use_system_default_device
                }

                # 将默认设备放在第一位
                devices.insert(0, default_device)

                self.audio_devices = devices
                return devices

            finally:
                # 释放设备列表
                if list_head:
                    try:
                        self.vlc_lib.libvlc_audio_output_device_list_release(list_head)
                    except Exception as e:
                        self.logger.warning(f"释放音频设备列表失败: {e}")

        except Exception as e:
            self.logger.error(f"枚举音频设备失败: {e}")
            return [{
                'id': 'default',
                'name': '系统默认设备',
                'is_current': True,
                'description': f'音频设备枚举失败: {str(e)}'
            }]

    def _normalize_device_identifier(self, device_id: Optional[str]) -> Optional[str]:
        """规范化设备标识符"""
        if not device_id:
            return None

        # 移除空白字符
        device_id = device_id.strip()

        # 处理特殊字符
        if device_id in ('{00000000-0000-0000-0000-000000000000}', ''):
            return None

        return device_id

    def set_audio_device(self, device_id: str) -> bool:
        """
        切换音频输出设备

        Args:
            device_id: 设备ID，'default'表示系统默认设备，
                      其他值应来自get_audio_devices返回的id字段。

        Returns:
            bool: 切换是否成功
        """
        if not self.is_vlc_available or not self.player:
            self.logger.error("VLC不可用，无法切换音频设备")
            return False

        try:
            # 记录当前状态用于回滚
            old_use_default = self.use_system_default_device
            old_device_id = self.selected_device_id

            # 设置新设备
            if device_id == 'default':
                self.player.audio_output_device_set(None, '')
                self.use_system_default_device = True
                self.selected_device_id = None
                self.logger.info("已切换到系统默认音频设备")
            else:
                self.player.audio_output_device_set(None, device_id)
                self.use_system_default_device = False
                self.selected_device_id = device_id
                self.logger.info(f"已切换到音频设备: {device_id}")

            # 验证切换是否成功
            time.sleep(0.1)  # 短暂等待
            try:
                current_device = self.player.audio_output_device_get()
                current_normalized = self._normalize_device_identifier(current_device)

                if device_id == 'default':
                    success = current_normalized is None
                else:
                    success = (current_normalized == self._normalize_device_identifier(device_id))

                if success:
                    # 刷新设备列表
                    self._refresh_audio_devices()

                    # 触发回调
                    if self.on_device_changed:
                        self.on_device_changed(device_id)

                    return True
                else:
                    # 切换失败，回滚
                    self.logger.warning("音频设备切换验证失败，正在回滚...")
                    if old_use_default:
                        self.player.audio_output_device_set(None, '')
                    elif old_device_id:
                        self.player.audio_output_device_set(None, old_device_id)

                    self.use_system_default_device = old_use_default
                    self.selected_device_id = old_device_id
                    return False

            except Exception as verify_error:
                self.logger.warning(f"音频设备切换验证失败: {verify_error}")
                # 即使验证失败，也认为切换成功（某些环境下无法验证）
                self._refresh_audio_devices()
                if self.on_device_changed:
                    self.on_device_changed(device_id)
                return True

        except Exception as e:
            self.logger.error(f"切换音频设备失败: {e}")
            return False

    def _apply_selected_audio_device(self):
        """应用用户选择的音频设备"""
        if not self.player:
            return

        try:
            if self.use_system_default_device:
                # 官方建议传入空字符串即可恢复系统默认输出
                self.player.audio_output_device_set(None, '')
            elif self.selected_device_id:
                self.player.audio_output_device_set(None, self.selected_device_id)
        except Exception as e:
            self.logger.warning(f"应用音频输出设备失败: {e}")

    def _refresh_audio_devices(self):
        """刷新音频设备列表"""
        try:
            self.get_audio_devices()
        except Exception as e:
            self.logger.warning(f"刷新音频设备列表失败: {e}")

    def load_file(self, file_path: str) -> bool:
        """加载音频文件"""
        if not self.is_vlc_available or not self.player:
            self.logger.error("VLC不可用，无法加载文件")
            return False

        try:
            if not os.path.exists(file_path):
                self.logger.error(f"文件不存在: {file_path}")
                return False

            # 创建媒体对象
            media = self.instance.media_new(file_path)
            if media is None:
                self.logger.error(f"创建媒体对象失败: {file_path}")
                return False

            # 设置到播放器
            self.player.set_media(media)

            # 解析媒体信息
            media.parse()

            # 获取时长
            self.total_time = media.get_duration() // 1000  # 转换为秒

            # 更新当前文件信息
            self.current_file = file_path

            self.logger.info(f"音频文件加载成功: {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"加载音频文件失败: {e}")
            return False

    def play(self) -> bool:
        """开始播放"""
        if not self.is_vlc_available or not self.player:
            self.logger.error("VLC不可用，无法播放")
            return False

        try:
            if self.is_paused:
                # 恢复播放
                result = self.player.pause() == 0  # pause()在暂停时返回0，播放时返回-1
                if result:
                    self.is_paused = False
            else:
                # 开始播放
                result = self.player.play() == 0

            if result:
                self.is_playing = True
                self.is_paused = False
                self._start_update_timer()
                self.logger.info("开始播放")

                # 触发状态更新回调
                if self.on_status_update:
                    self.on_status_update()

                return True
            else:
                self.logger.error("播放失败")
                return False

        except Exception as e:
            self.logger.error(f"播放失败: {e}")
            return False

    def pause(self) -> bool:
        """暂停播放"""
        if not self.is_vlc_available or not self.player:
            return False

        try:
            if self.is_playing and not self.is_paused:
                self.player.pause()
                self.is_paused = True
                self.logger.info("暂停播放")

                # 触发状态更新回调
                if self.on_status_update:
                    self.on_status_update()

                return True
            return False

        except Exception as e:
            self.logger.error(f"暂停失败: {e}")
            return False

    def toggle_play_pause(self) -> bool:
        """播放/暂停切换"""
        if not self.is_vlc_available:
            return False

        if self.is_paused:
            return self.play()
        elif self.is_playing:
            return self.pause()
        else:
            # 未开始播放，尝试播放
            return self.play()

    def stop(self) -> bool:
        """停止播放"""
        if not self.is_vlc_available or not self.player:
            return False

        try:
            self.player.stop()
            self.is_playing = False
            self.is_paused = False
            self.current_time = 0
            self.current_index = 0

            self._stop_update_timer()
            self.logger.info("停止播放")

            # 触发状态更新回调
            if self.on_status_update:
                self.on_status_update()

            return True

        except Exception as e:
            self.logger.error(f"停止失败: {e}")
            return False

    def set_volume(self, volume: int) -> bool:
        """设置音量 0-100"""
        if not self.is_vlc_available or not self.player:
            return False

        try:
            volume = max(0, min(100, volume))
            self.current_volume = volume
            self.player.audio_set_volume(volume)
            return True

        except Exception as e:
            self.logger.error(f"设置音量失败: {e}")
            return False

    def get_volume(self) -> int:
        """获取当前音量"""
        if self.is_vlc_available and self.player:
            try:
                return self.player.audio_get_volume()
            except:
                pass
        return self.current_volume

    def seek(self, position: float) -> bool:
        """跳转到指定位置（0.0-1.0）"""
        if not self.is_vlc_available or not self.player:
            return False

        try:
            position = max(0.0, min(1.0, position))
            self.player.set_position(position)
            return True

        except Exception as e:
            self.logger.error(f"跳转失败: {e}")
            return False

    def _start_update_timer(self):
        """启动状态更新定时器"""
        if self.update_timer is None:
            self.update_timer = threading.Timer(self.update_interval, self._update_position)
            self.update_timer.daemon = True
            self.update_timer.start()

    def _stop_update_timer(self):
        """停止状态更新定时器"""
        if self.update_timer:
            self.update_timer.cancel()
            self.update_timer = None

    def _update_position(self):
        """更新播放位置信息"""
        if self.is_playing and not self.is_paused and self.player:
            try:
                # 更新当前时间
                self.current_time = self.player.get_time() // 1000

                # 触发状态更新回调
                if self.on_status_update:
                    self.on_status_update()

                # 重新启动定时器
                if self.is_playing and not self.is_paused:
                    self._start_update_timer()

            except Exception as e:
                self.logger.debug(f"更新播放位置失败: {e}")
                self._start_update_timer()  # 继续定时器

    def get_status_info(self) -> Dict:
        """获取播放状态信息"""
        return {
            'is_playing': self.is_playing,
            'is_paused': self.is_paused,
            'current_time': self.current_time,
            'total_time': self.total_time,
            'current_file': getattr(self, 'current_file', None),
            'volume': self.get_volume(),
            'vlc_available': self.is_vlc_available,
            'current_device': self.selected_device_id if not self.use_system_default_device else 'default',
            'device_count': len(self.audio_devices)
        }

    def format_time(self, seconds: int) -> str:
        """格式化时间显示"""
        if seconds <= 0:
            return "00:00"

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"

    def get_progress_info(self) -> Dict:
        """获取进度信息（用于状态栏显示）"""
        if not self.is_playing and not self.is_paused:
            return {
                'status_text': '就绪',
                'track_info': '[无音频播放]',
                'progress_text': '',
                'tip_text': 'Ctrl+Home播放'
            }

        # 播放状态
        if self.is_paused:
            status_text = '已暂停'
            tip_text = 'Ctrl+Home播放，Ctrl+End停止'
        else:
            status_text = '播放中'
            tip_text = 'Ctrl+Home暂停，Ctrl+End停止'

        # 曲目信息
        if hasattr(self, 'current_file') and self.current_file:
            track_name = os.path.basename(self.current_file)
        else:
            track_name = '未知音频'

        # 进度信息
        current_str = self.format_time(self.current_time)
        total_str = self.format_time(self.total_time)

        if self.total_time > 0:
            progress = (self.current_time / self.total_time) * 100
            progress_text = f"{current_str}/{total_str} ({progress:.1f}%)"
        else:
            progress_text = current_str

        return {
            'status_text': status_text,
            'track_info': track_name,
            'progress_text': progress_text,
            'tip_text': tip_text
        }

    def cleanup(self):
        """清理资源"""
        try:
            # 停止播放
            self.stop()

            # 释放播放器
            if self.player:
                self.player.release()
                self.player = None

            # 释放VLC加载器
            if self.vlc_loader:
                self.vlc_loader.cleanup()
                self.vlc_loader = None

            self.is_vlc_available = False
            self.logger.info("音频播放器资源已清理")

        except Exception as e:
            self.logger.error(f"清理资源失败: {e}")

    def __del__(self):
        """析构函数"""
        self.cleanup()