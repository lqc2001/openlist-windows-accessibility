#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
无障碍管理器
为媒体播放器提供完整的无障碍功能支持
"""

import wx
import time
from typing import Optional, Callable
from src.core.logger import get_logger


class AccessibilityManager:
    """无障碍功能管理器"""

    def __init__(self, parent_window):
        """
        初始化无障碍管理器

        Args:
            parent_window: 父窗口对象
        """
        self.logger = get_logger()
        self.parent_window = parent_window

        # 语音播报状态
        self.last_announcement = ""
        self.last_announcement_time = 0
        self.announcement_debounce = 1.0  # 防抖时间（秒）

        # 状态回调
        self.status_callback = None

        self.logger.debug("无障碍管理器初始化完成")

    def announce(self, message: str, priority: bool = False):
        """
        播报消息（屏幕阅读器友好）

        Args:
            message: 要播报的消息
            priority: 是否为高优先级消息（忽略防抖）
        """
        try:
            current_time = time.time()

            # 防抖处理，避免重复播报相同消息
            if (not priority and
                message == self.last_announcement and
                current_time - self.last_announcement_time < self.announcement_debounce):
                return

            self.last_announcement = message
            self.last_announcement_time = current_time

            # 记录播报内容
            self.logger.debug(f"无障碍播报: {message}")

            # 如果有状态回调，调用它
            if self.status_callback:
                self.status_callback(message)

            # 在实际应用中，这里可以集成屏幕阅读器API
            # 目前使用状态栏显示作为备选方案
            if hasattr(self.parent_window, 'SetStatusText'):
                self.parent_window.SetStatusText(message)

        except Exception as e:
            self.logger.error(f"无障碍播报失败: {e}")

    def announce_time_status(self, current_time: int, total_time: int):
        """
        播报时间状态

        Args:
            current_time: 当前时间（毫秒）
            total_time: 总时长（毫秒）
        """
        try:
            current_str = self._format_time(current_time)
            total_str = self._format_time(total_time)
            message = f"播放时间: {current_str} / {total_str}"
            self.announce(message)

        except Exception as e:
            self.logger.error(f"播报时间状态失败: {e}")

    def announce_volume_status(self, volume: int, is_muted: bool):
        """
        播报音量状态

        Args:
            volume: 音量值（0-100）
            is_muted: 是否静音
        """
        try:
            if is_muted:
                message = "静音"
            else:
                message = f"音量: {volume}%"
            self.announce(message)

        except Exception as e:
            self.logger.error(f"播报音量状态失败: {e}")

    def announce_playback_status(self, status: str, filename: str = ""):
        """
        播报播放状态

        Args:
            status: 播放状态 ('playing', 'paused', 'stopped', 'error')
            filename: 文件名
        """
        try:
            status_messages = {
                'playing': '开始播放',
                'paused': '已暂停',
                'stopped': '已停止',
                'loading': '正在加载',
                'error': '播放错误'
            }

            message = status_messages.get(status, status)

            if filename:
                # 只显示文件名，不显示完整路径
                import os
                name = os.path.basename(filename)
                message = f"{message}: {name}"

            self.announce(message, priority=True)

        except Exception as e:
            self.logger.error(f"播报播放状态失败: {e}")

    def announce_seek_status(self, direction: str, seconds: int):
        """
        播报快进/快退状态

        Args:
            direction: 方向 ('forward', 'backward')
            seconds: 快进/快退秒数
        """
        try:
            if direction == 'forward':
                message = f"快进 {seconds} 秒"
            else:
                message = f"快退 {seconds} 秒"
            self.announce(message)

        except Exception as e:
            self.logger.error(f"播报快进/快退状态失败: {e}")

    def announce_error(self, error_message: str, suggestion: str = ""):
        """
        播报错误信息

        Args:
            error_message: 错误消息
            suggestion: 解决建议
        """
        try:
            message = f"错误: {error_message}"
            if suggestion:
                message += f"。建议: {suggestion}"
            self.announce(message, priority=True)

        except Exception as e:
            self.logger.error(f"播报错误信息失败: {e}")

    def setup_control_accessibility(self, control, name: str, help_text: str, shortcut: str = ""):
        """
        为控件设置无障碍属性

        Args:
            control: 控件对象
            name: 控件名称
            help_text: 帮助文本
            shortcut: 快捷键说明
        """
        try:
            if hasattr(control, 'SetName'):
                control.SetName(name)

            if hasattr(control, 'SetHelpText'):
                full_help = help_text
                if shortcut:
                    full_help += f" 快捷键: {shortcut}"
                control.SetHelpText(full_help)

            self.logger.debug(f"控件无障碍设置: {name}")

        except Exception as e:
            self.logger.error(f"设置控件无障碍属性失败: {e}")

    def _format_time(self, time_ms: int) -> str:
        """
        格式化时间显示

        Args:
            time_ms: 时间（毫秒）

        Returns:
            str: 格式化的时间字符串 (MM:SS)
        """
        try:
            if time_ms <= 0:
                return "00:00"

            seconds = time_ms // 1000
            minutes = seconds // 60
            seconds = seconds % 60
            return f"{minutes:02d}:{seconds:02d}"

        except:
            return "00:00"

    def get_keyboard_navigation_help(self) -> str:
        """
        获取键盘导航帮助信息

        Returns:
            str: 帮助信息
        """
        help_text = """
键盘快捷键说明：
空格键 - 播放/暂停
Enter键 - 播放/暂停
S键 - 停止播放
左右方向键 - 快进/快退5秒
Ctrl+左右方向键 - 快进/快退30秒
上下方向键 - 增加/减少音量
M键 - 静音切换
L键 - 循环播放切换
F键 - 全屏切换（视频）
O键 - 打开文件
P键 - 显示播放列表
Esc键 - 退出播放器
Tab键 - 在控件间导航
Shift+Tab - 反向导航
F1键 - 显示帮助信息
        """.strip()

        return help_text

    def announce_help(self):
        """播报帮助信息"""
        help_text = self.get_keyboard_navigation_help()
        self.announce("帮助信息已显示，请查看帮助窗口", priority=True)

    def set_status_callback(self, callback: Callable):
        """
        设置状态更新回调

        Args:
            callback: 回调函数，接收消息参数
        """
        self.status_callback = callback

    def get_current_focus_description(self) -> str:
        """
        获取当前焦点控件的描述

        Returns:
            str: 焦点控件描述
        """
        try:
            window = wx.GetActiveWindow()
            if window:
                focus = window.FindFocus()
                if focus and hasattr(focus, 'GetName'):
                    name = focus.GetName()
                    if hasattr(focus, 'GetHelpText'):
                        help_text = focus.GetHelpText()
                        return f"{name}。{help_text}"
                    return name
            return ""

        except Exception as e:
            self.logger.error(f"获取焦点描述失败: {e}")
            return ""

    def announce_focus_change(self):
        """播报焦点变化"""
        description = self.get_current_focus_description()
        if description:
            self.announce(description)