#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
媒体文件检测器
检测文件类型，判断是否为支持的音视频格式
"""

import os
import urllib.parse
from typing import Optional


class MediaFileDetector:
    """媒体文件检测器"""

    # 支持的音频格式
    SUPPORTED_AUDIO = [
        '.mp3', '.wav', '.flac', '.aac', '.m4a', '.ogg',
        '.wma', '.ape', '.opus', '.m4p', '.mp4a'
    ]

    # 支持的视频格式
    SUPPORTED_VIDEO = [
        '.mp4', '.avi', '.mkv', '.wmv', '.mov', '.webm',
        '.flv', '.m4v', '.3gp', '.ogv', '.ts', '.mts'
    ]

    # 支持的播放列表格式
    SUPPORTED_PLAYLISTS = [
        '.m3u', '.m3u8', '.pls', '.xspf'
    ]

    @classmethod
    def _clean_filename(cls, filename: str) -> str:
        """
        清理文件名，去除URL查询参数和锚点

        Args:
            filename: 原始文件名或URL

        Returns:
            str: 清理后的文件名
        """
        if not filename:
            return filename

        # 如果是URL，去除查询参数和锚点
        if '?' in filename:
            filename = filename.split('?')[0]
        if '#' in filename:
            filename = filename.split('#')[0]

        # 对于URL，提取最后的部分作为文件名
        if filename.startswith(('http://', 'https://')):
            # 提取URL路径的最后部分
            parsed = urllib.parse.urlparse(filename)
            filename = os.path.basename(parsed.path)

        return filename

    @classmethod
    def is_media_file(cls, filename: str) -> bool:
        """
        检测是否为媒体文件

        Args:
            filename: 文件名或URL

        Returns:
            bool: 是否为媒体文件
        """
        if not filename:
            return False

        clean_name = cls._clean_filename(filename)
        ext = os.path.splitext(clean_name)[1].lower()
        return (ext in cls.SUPPORTED_AUDIO or
                ext in cls.SUPPORTED_VIDEO or
                ext in cls.SUPPORTED_PLAYLISTS)

    @classmethod
    def get_media_type(cls, filename: str) -> Optional[str]:
        """
        获取媒体类型

        Args:
            filename: 文件名或URL

        Returns:
            str: 媒体类型 ('audio', 'video', 'playlist', None)
        """
        if not filename:
            return None

        clean_name = cls._clean_filename(filename)
        ext = os.path.splitext(clean_name)[1].lower()

        if ext in cls.SUPPORTED_AUDIO:
            return 'audio'
        elif ext in cls.SUPPORTED_VIDEO:
            return 'video'
        elif ext in cls.SUPPORTED_PLAYLISTS:
            return 'playlist'

        return None

    @classmethod
    def is_audio_file(cls, filename: str) -> bool:
        """检测是否为音频文件"""
        if not filename:
            return False
        clean_name = cls._clean_filename(filename)
        ext = os.path.splitext(clean_name)[1].lower()
        return ext in cls.SUPPORTED_AUDIO

    @classmethod
    def is_video_file(cls, filename: str) -> bool:
        """检测是否为视频文件"""
        if not filename:
            return False
        clean_name = cls._clean_filename(filename)
        ext = os.path.splitext(clean_name)[1].lower()
        return ext in cls.SUPPORTED_VIDEO

    @classmethod
    def is_playlist_file(cls, filename: str) -> bool:
        """检测是否为播放列表文件"""
        if not filename:
            return False
        clean_name = cls._clean_filename(filename)
        ext = os.path.splitext(clean_name)[1].lower()
        return ext in cls.SUPPORTED_PLAYLISTS

    @classmethod
    def get_supported_formats(cls) -> dict:
        """
        获取所有支持的格式

        Returns:
            dict: 支持的格式分类
        """
        return {
            'audio': cls.SUPPORTED_AUDIO,
            'video': cls.SUPPORTED_VIDEO,
            'playlist': cls.SUPPORTED_PLAYLISTS,
            'all': cls.SUPPORTED_AUDIO + cls.SUPPORTED_VIDEO + cls.SUPPORTED_PLAYLISTS
        }

    @classmethod
    def filter_media_files(cls, file_list: list) -> dict:
        """
        从文件列表中筛选出媒体文件

        Args:
            file_list: 文件列表

        Returns:
            dict: 分类后的媒体文件
        """
        result = {
            'audio': [],
            'video': [],
            'playlist': [],
            'other': []
        }

        for filename in file_list:
            media_type = cls.get_media_type(filename)
            if media_type:
                result[media_type].append(filename)
            else:
                result['other'].append(filename)

        return result

    @classmethod
    def get_file_info(cls, filepath: str) -> dict:
        """
        获取文件基本信息

        Args:
            filepath: 文件路径

        Returns:
            dict: 文件信息
        """
        if not os.path.exists(filepath):
            return {}

        stat = os.stat(filepath)
        filename = os.path.basename(filepath)
        media_type = cls.get_media_type(filename)

        return {
            'name': filename,
            'path': filepath,
            'size': stat.st_size,
            'modified': stat.st_mtime,
            'media_type': media_type,
            'is_media': media_type is not None,
            'extension': os.path.splitext(filename)[1].lower()
        }