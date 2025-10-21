#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
播放列表管理器
管理音频播放列表，支持上一首/下一首功能
"""

from typing import List, Optional, Dict, Any
from src.core.logger import get_logger


class PlaylistItem:
    """播放列表项"""
    def __init__(self, file_path: str, display_name: str = None, metadata: Dict[str, Any] = None):
        self.file_path = file_path
        self.display_name = display_name or file_path.split('/')[-1].split('\\')[-1]
        self.metadata = metadata or {}

    def __str__(self):
        return self.display_name


class PlaylistManager:
    """播放列表管理器"""

    def __init__(self):
        """初始化播放列表管理器"""
        self.logger = get_logger()

        # 播放列表
        self.playlist: List[PlaylistItem] = []
        self.current_index: int = -1
        self.repeat_mode: str = "none"  # none, one, all

        # 播放历史
        self.played_history: List[int] = []
        self.max_history_size: int = 100

        # 回调函数
        self.on_playlist_changed = None
        self.on_current_track_changed = None

    def add_item(self, file_path: str, display_name: str = None, metadata: Dict[str, Any] = None) -> bool:
        """
        添加项目到播放列表

        Args:
            file_path: 文件路径
            display_name: 显示名称
            metadata: 元数据

        Returns:
            bool: 是否添加成功
        """
        try:
            if not file_path:
                return False

            # 检查是否已存在
            for item in self.playlist:
                if item.file_path == file_path:
                    self.logger.debug(f"项目已存在于播放列表: {file_path}")
                    return True

            # 创建新的播放项
            item = PlaylistItem(file_path, display_name, metadata)
            self.playlist.append(item)

            self.logger.info(f"添加到播放列表: {item.display_name}")
            self._trigger_playlist_changed()
            return True

        except Exception as e:
            self.logger.error(f"添加播放列表项失败: {e}")
            return False

    def remove_item(self, index: int) -> bool:
        """
        从播放列表中移除项目

        Args:
            index: 项目索引

        Returns:
            bool: 是否移除成功
        """
        try:
            if 0 <= index < len(self.playlist):
                removed_item = self.playlist.pop(index)
                self.logger.info(f"从播放列表移除: {removed_item.display_name}")

                # 调整当前索引
                if self.current_index == index:
                    self.current_index = -1
                elif self.current_index > index:
                    self.current_index -= 1

                self._trigger_playlist_changed()
                return True
            return False

        except Exception as e:
            self.logger.error(f"移除播放列表项失败: {e}")
            return False

    def clear_playlist(self) -> bool:
        """清空播放列表"""
        try:
            self.playlist.clear()
            self.current_index = -1
            self.played_history.clear()
            self.logger.info("播放列表已清空")
            self._trigger_playlist_changed()
            return True

        except Exception as e:
            self.logger.error(f"清空播放列表失败: {e}")
            return False

    def get_current_item(self) -> Optional[PlaylistItem]:
        """获取当前播放项"""
        if 0 <= self.current_index < len(self.playlist):
            return self.playlist[self.current_index]
        return None

    def get_playlist(self) -> List[PlaylistItem]:
        """获取播放列表"""
        return self.playlist.copy()

    def get_current_index(self) -> int:
        """获取当前索引"""
        return self.current_index

    def set_current_index(self, index: int) -> bool:
        """
        设置当前播放索引

        Args:
            index: 索引

        Returns:
            bool: 是否设置成功
        """
        try:
            if 0 <= index < len(self.playlist):
                # 记录到历史
                if self.current_index != -1:
                    self._add_to_history(self.current_index)

                self.current_index = index
                self.logger.info(f"切换到播放项: {self.playlist[index].display_name}")
                self._trigger_current_track_changed()
                return True
            return False

        except Exception as e:
            self.logger.error(f"设置当前索引失败: {e}")
            return False

    def next_track(self) -> Optional[PlaylistItem]:
        """
        播放下一首

        Returns:
            PlaylistItem: 下一首项目，如果没有则返回None
        """
        try:
            if not self.playlist:
                return None

            # 记录当前到历史
            if self.current_index != -1:
                self._add_to_history(self.current_index)

            # 根据重复模式决定下一首
            if self.repeat_mode == "one":
                # 单曲循环，返回当前项
                next_index = self.current_index if self.current_index != -1 else 0
            else:
                # 获取下一首
                if self.current_index < len(self.playlist) - 1:
                    next_index = self.current_index + 1
                elif self.repeat_mode == "all":
                    # 列表循环，回到第一首
                    next_index = 0
                else:
                    # 没有更多项目
                    return None

            if 0 <= next_index < len(self.playlist):
                self.current_index = next_index
                item = self.playlist[next_index]
                self.logger.info(f"播放下一首: {item.display_name}")
                self._trigger_current_track_changed()
                return item

            return None

        except Exception as e:
            self.logger.error(f"播放下一首失败: {e}")
            return None

    def previous_track(self) -> Optional[PlaylistItem]:
        """
        播放上一首

        Returns:
            PlaylistItem: 上一首项目，如果没有则返回None
        """
        try:
            if not self.playlist:
                return None

            # 记录当前到历史
            if self.current_index != -1:
                self._add_to_history(self.current_index)

            # 根据重复模式决定上一首
            if self.repeat_mode == "one":
                # 单曲循环，返回当前项
                prev_index = self.current_index if self.current_index != -1 else len(self.playlist) - 1
            else:
                # 获取上一首
                if self.current_index > 0:
                    prev_index = self.current_index - 1
                elif self.repeat_mode == "all":
                    # 列表循环，回到最后一首
                    prev_index = len(self.playlist) - 1
                else:
                    # 没有更多项目
                    return None

            if 0 <= prev_index < len(self.playlist):
                self.current_index = prev_index
                item = self.playlist[prev_index]
                self.logger.info(f"播放上一首: {item.display_name}")
                self._trigger_current_track_changed()
                return item

            return None

        except Exception as e:
            self.logger.error(f"播放上一首失败: {e}")
            return None

    def set_repeat_mode(self, mode: str) -> bool:
        """
        设置重复模式

        Args:
            mode: 重复模式 (none, one, all)

        Returns:
            bool: 是否设置成功
        """
        if mode in ["none", "one", "all"]:
            self.repeat_mode = mode
            self.logger.info(f"重复模式设置为: {mode}")
            return True
        return False

    def get_repeat_mode(self) -> str:
        """获取重复模式"""
        return self.repeat_mode

    def has_next(self) -> bool:
        """是否有下一首"""
        if not self.playlist:
            return False

        if self.repeat_mode == "one":
            return True

        if self.repeat_mode == "all":
            return True

        return self.current_index < len(self.playlist) - 1

    def has_previous(self) -> bool:
        """是否有上一首"""
        if not self.playlist:
            return False

        if self.repeat_mode == "one":
            return True

        if self.repeat_mode == "all":
            return True

        return self.current_index > 0

    def get_playlist_info(self) -> Dict[str, Any]:
        """获取播放列表信息"""
        return {
            "total_tracks": len(self.playlist),
            "current_index": self.current_index,
            "current_track": self.get_current_item().display_name if self.get_current_item() else None,
            "repeat_mode": self.repeat_mode,
            "has_next": self.has_next(),
            "has_previous": self.has_previous()
        }

    def _add_to_history(self, index: int):
        """添加到播放历史"""
        if index not in self.played_history:
            self.played_history.append(index)

            # 限制历史大小
            if len(self.played_history) > self.max_history_size:
                self.played_history.pop(0)

    def _trigger_playlist_changed(self):
        """触发播放列表变化事件"""
        if self.on_playlist_changed:
            try:
                self.on_playlist_changed()
            except Exception as e:
                self.logger.error(f"播放列表变化事件回调失败: {e}")

    def _trigger_current_track_changed(self):
        """触发当前曲目变化事件"""
        if self.on_current_track_changed:
            try:
                self.on_current_track_changed()
            except Exception as e:
                self.logger.error(f"当前曲目变化事件回调失败: {e}")