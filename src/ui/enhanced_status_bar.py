#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版状态栏管理器
借鉴ForumAssist的5字段状态栏设计，提供实时音频播放状态显示
"""

import wx
from typing import Optional, Dict
from src.core.logger import get_logger


class EnhancedStatusBar:
    """增强版状态栏管理器

    状态栏布局（5个字段）：
    0: 播放状态（播放中/已暂停/就绪）
    1: 曲目信息（文件名或播放列表信息）
    2: 进度信息（当前时间/总时间 - 进度百分比）
    3: 设备信息（当前音频设备）
    4: 操作提示（快捷键说明）
    """

    def __init__(self, parent_frame: wx.Frame):
        """初始化状态栏

        Args:
            parent_frame: 父窗口
        """
        self.logger = get_logger()
        self.parent_frame = parent_frame
        self.status_bar = None
        self.is_initialized = False

        # 初始化状态栏
        self._create_status_bar()
        self._update_idle_status()

    def _create_status_bar(self):
        """创建状态栏"""
        try:
            # 创建5字段状态栏
            self.status_bar = self.parent_frame.CreateStatusBar(5)

            # 设置字段宽度（-1表示自适应）
            self.status_bar.SetStatusWidths([-1, -2, -2, -1, -1])

            # 设置字段样式
            self.status_bar.SetStatusStyles([wx.SB_FLAT, wx.SB_FLAT, wx.SB_FLAT, wx.SB_FLAT, wx.SB_FLAT])

            self.is_initialized = True
            self.logger.info("状态栏创建成功")

        except Exception as e:
            self.logger.error(f"状态栏创建失败: {e}")
            self.is_initialized = False

    def _update_idle_status(self):
        """更新空闲状态显示"""
        if not self.is_initialized:
            return

        try:
            self.status_bar.SetStatusText("就绪", 0)
            self.status_bar.SetStatusText("[无音频播放]", 1)
            self.status_bar.SetStatusText("", 2)
            self.status_bar.SetStatusText("系统默认", 3)
            self.status_bar.SetStatusText("Ctrl+Home播放", 4)

        except Exception as e:
            self.logger.debug(f"更新空闲状态失败: {e}")

    def update_audio_status(self, status_info: Dict, progress_info: Dict, device_info: Optional[Dict] = None):
        """更新音频播放状态

        Args:
            status_info: 播放状态信息
            progress_info: 进度信息
            device_info: 设备信息
        """
        if not self.is_initialized:
            return

        try:
            # 字段0: 播放状态
            self.status_bar.SetStatusText(progress_info['status_text'], 0)

            # 字段1: 曲目信息
            track_text = progress_info['track_info']
            if status_info.get('current_file'):
                # 添加播放列表信息
                if 'playlist' in status_info:
                    current = status_info.get('current_index', 0) + 1
                    total = len(status_info['playlist'])
                    track_text = f"第{current}个，共{total}个 - {track_text}"
            self.status_bar.SetStatusText(track_text, 1)

            # 字段2: 进度信息
            self.status_bar.SetStatusText(progress_info['progress_text'], 2)

            # 字段3: 设备信息
            if device_info:
                device_name = device_info.get('name', '未知设备')
                if device_info.get('id') == 'default':
                    device_name = '系统默认'
                self.status_bar.SetStatusText(device_name, 3)
            else:
                self.status_bar.SetStatusText("系统默认", 3)

            # 字段4: 操作提示
            self.status_bar.SetStatusText(progress_info['tip_text'], 4)

        except Exception as e:
            self.logger.debug(f"更新音频状态失败: {e}")

    def update_device_status(self, device_name: str = "系统默认"):
        """更新设备状态显示

        Args:
            device_name: 设备名称
        """
        if not self.is_initialized:
            return

        try:
            self.status_bar.SetStatusText(device_name, 3)
            self.logger.debug(f"设备状态更新: {device_name}")

        except Exception as e:
            self.logger.debug(f"更新设备状态失败: {e}")

    def update_playlist_info(self, current_index: int, total_count: int, current_track: str):
        """更新播放列表信息

        Args:
            current_index: 当前索引（从0开始）
            total_count: 总数
            current_track: 当前曲目名称
        """
        if not self.is_initialized or total_count <= 0:
            return

        try:
            current_num = current_index + 1
            playlist_text = f"第{current_num}个，共{total_count}个 - {current_track}"
            self.status_bar.SetStatusText(playlist_text, 1)

        except Exception as e:
            self.logger.debug(f"更新播放列表信息失败: {e}")

    def show_temporary_message(self, message: str, field: int = 0, duration: int = 3000):
        """显示临时消息

        Args:
            message: 消息内容
            field: 状态栏字段（0-4）
            duration: 显示时长（毫秒）
        """
        if not self.is_initialized:
            return

        try:
            # 保存当前内容
            original_text = self.status_bar.GetStatusText(field)

            # 显示临时消息
            self.status_bar.SetStatusText(message, field)

            # 定时恢复原内容
            wx.CallLater(duration, self._restore_field, field, original_text)

        except Exception as e:
            self.logger.debug(f"显示临时消息失败: {e}")

    def _restore_field(self, field: int, original_text: str):
        """恢复状态栏字段内容

        Args:
            field: 状态栏字段
            original_text: 原始内容
        """
        if not self.is_initialized:
            return

        try:
            self.status_bar.SetStatusText(original_text, field)
        except Exception as e:
            self.logger.debug(f"恢复状态栏字段失败: {e}")

    def update_operation_tip(self, tip_text: str):
        """更新操作提示

        Args:
            tip_text: 提示文本
        """
        if not self.is_initialized:
            return

        try:
            self.status_bar.SetStatusText(tip_text, 4)
        except Exception as e:
            self.logger.debug(f"更新操作提示失败: {e}")

    def show_error_message(self, error_text: str):
        """显示错误消息

        Args:
            error_text: 错误信息
        """
        if not self.is_initialized:
            return

        try:
            self.show_temporary_message(f"错误: {error_text}", 0, 5000)
            self.logger.warning(f"状态栏显示错误: {error_text}")

        except Exception as e:
            self.logger.debug(f"显示错误消息失败: {e}")

    def show_success_message(self, success_text: str):
        """显示成功消息

        Args:
            success_text: 成功信息
        """
        if not self.is_initialized:
            return

        try:
            self.show_temporary_message(f"成功: {success_text}", 0, 3000)
            self.logger.info(f"状态栏显示成功: {success_text}")

        except Exception as e:
            self.logger.debug(f"显示成功消息失败: {e}")

    def reset_to_idle(self):
        """重置到空闲状态"""
        self._update_idle_status()

    def get_current_status(self) -> Dict[str, str]:
        """获取当前状态栏内容

        Returns:
            Dict: 各字段的状态文本
        """
        if not self.is_initialized:
            return {}

        try:
            return {
                'status': self.status_bar.GetStatusText(0),
                'track': self.status_bar.GetStatusText(1),
                'progress': self.status_bar.GetStatusText(2),
                'device': self.status_bar.GetStatusText(3),
                'tip': self.status_bar.GetStatusText(4)
            }
        except Exception as e:
            self.logger.debug(f"获取状态栏内容失败: {e}")
            return {}

    def set_field_text(self, field: int, text: str):
        """直接设置指定字段的文本

        Args:
            field: 字段索引（0-4）
            text: 要设置的文本
        """
        if not self.is_initialized or field < 0 or field > 4:
            return

        try:
            self.status_bar.SetStatusText(text, field)
        except Exception as e:
            self.logger.debug(f"设置状态栏字段失败: {e}")

    def clear_field(self, field: int):
        """清空指定字段

        Args:
            field: 字段索引（0-4）
        """
        self.set_field_text(field, "")

    def highlight_field(self, field: int, highlight: bool = True):
        """高亮显示指定字段（简单实现）

        Args:
            field: 字段索引（0-4）
            highlight: 是否高亮
        """
        if not self.is_initialized or field < 0 or field > 4:
            return

        try:
            # 通过修改文本来实现简单的高亮效果
            current_text = self.status_bar.GetStatusText(field)
            if highlight and not current_text.startswith('★ '):
                self.status_bar.SetStatusText('★ ' + current_text, field)
            elif not highlight and current_text.startswith('★ '):
                self.status_bar.SetStatusText(current_text[2:], field)

        except Exception as e:
            self.logger.debug(f"高亮状态栏字段失败: {e}")

    def set_tooltip(self, field: int, tooltip_text: str):
        """为状态栏字段设置提示信息（如果支持）

        Args:
            field: 字段索引（0-4）
            tooltip_text: 提示文本
        """
        # wxPython的标准状态栏不支持tooltip，这里只做日志记录
        self.logger.debug(f"状态栏字段{field}提示: {tooltip_text}")

    def get_status_bar(self) -> Optional[wx.StatusBar]:
        """获取状态栏对象

        Returns:
            wx.StatusBar: 状态栏对象，如果未初始化返回None
        """
        return self.status_bar if self.is_initialized else None

    def is_available(self) -> bool:
        """检查状态栏是否可用

        Returns:
            bool: 是否可用
        """
        return self.is_initialized and self.status_bar is not None

    def refresh_layout(self):
        """刷新状态栏布局"""
        if not self.is_initialized:
            return

        try:
            self.status_bar.Refresh()
            self.parent_frame.Layout()
            self.logger.debug("状态栏布局已刷新")

        except Exception as e:
            self.logger.debug(f"刷新状态栏布局失败: {e}")

    def __del__(self):
        """析构函数"""
        self.is_initialized = False
        self.status_bar = None
        self.parent_frame = None