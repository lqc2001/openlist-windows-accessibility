#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
媒体播放模块
提供音视频播放功能，支持VLC便携式集成
"""

from .file_detector import MediaFileDetector
from .vlc_loader import VLCLoader
from .media_player_core import MediaPlayerCore
from .audio_player import AudioPlayer
from .accessibility_manager import AccessibilityManager

__all__ = [
    'MediaFileDetector',
    'VLCLoader',
    'MediaPlayerCore',
    'AudioPlayer',
    'AccessibilityManager'
]