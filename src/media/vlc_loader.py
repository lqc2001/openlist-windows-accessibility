#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VLC库加载器
负责VLC运行时库的加载、初始化和环境配置
支持便携式VLC集成和内置VLC库
"""

import os
import sys
import platform
from pathlib import Path
from typing import Optional, List, Tuple, Dict
from src.core.logger import get_logger

# 导入VLC内置管理器
try:
    from .vlc_embedded_manager import get_vlc_embedded_manager, prepare_embedded_vlc
except ImportError:
    # 如果在非标准位置导入，尝试相对导入
    try:
        from vlc_embedded_manager import get_vlc_embedded_manager, prepare_embedded_vlc
    except ImportError:
        # 如果无法导入，使用默认行为
        get_vlc_embedded_manager = None
        prepare_embedded_vlc = None


class VLCLoader:
    """VLC库动态加载器

    支持多种VLC源：
    1. 内置VLC库（优先级最高）
    2. 程序目录VLC
    3. 系统安装VLC
    4. 降级处理
    """

    def __init__(self, prefer_embedded: bool = False):
        """初始化VLC加载器

        Args:
            prefer_embedded: 是否优先使用内置VLC库
        """
        self.logger = get_logger()
        self.vlc_path = None
        self.vlc_instance = None
        self.vlc_lib = None
        self.is_loaded = False
        self.prefer_embedded = prefer_embedded
        self.embedded_config = None  # 内置VLC配置信息
        self.load_source = None      # 记录VLC加载来源

        # 初始化VLC
        self._initialize_vlc()

    def _initialize_vlc(self):
        """初始化VLC环境"""
        try:
            # 智能加载VLC：内置 → 程序目录 → 系统 → 降级
            success = self._load_vlc_smart()

            if success:
                self.is_loaded = True
                self.logger.info(f"VLC库加载成功 - 来源: {self.load_source}, 路径: {self.vlc_path}")
            else:
                self.logger.error("VLC库加载失败")
                self.is_loaded = False

        except Exception as e:
            self.logger.error(f"VLC库加载失败: {e}")
            self.is_loaded = False
            raise

    def _load_vlc_smart(self) -> bool:
        """智能加载VLC

        Returns:
            bool: 加载是否成功
        """
        if self.prefer_embedded:
            # 用户明确指定优先使用内置VLC
            # 1. 尝试加载内置VLC库
            if self._load_embedded_vlc():
                return True

            # 2. 内置VLC失败，尝试程序目录VLC
            if self._load_program_vlc():
                return True

            # 3. 最后尝试系统VLC作为后备
            if self._load_system_vlc():
                return True
        else:
            # 默认模式：优先使用系统VLC，因为它更稳定
            # 1. 尝试加载系统VLC
            if self._load_system_vlc():
                return True

            # 2. 尝试加载程序目录VLC
            if self._load_program_vlc():
                return True

            # 3. 最后尝试内置VLC库
            if self._load_embedded_vlc():
                return True

        # 4. 降级处理
        return self._handle_vlc_unavailable()

    def _load_embedded_vlc(self) -> bool:
        """加载内置VLC库

        Returns:
            bool: 加载是否成功
        """
        try:
            if not prepare_embedded_vlc:
                self.logger.debug("内置VLC管理器不可用")
                return False

            # 准备内置VLC
            success, config = prepare_embedded_vlc()
            if not success:
                self.logger.debug(f"内置VLC准备失败: {config}")
                return False

            self.embedded_config = config
            vlc_manager = get_vlc_embedded_manager()
            vlc_paths = config.get('vlc_paths', {})

            # 设置VLC路径
            if 'libvlc.dll' in vlc_paths:
                self.vlc_path = str(vlc_manager.lib_dir)
                self.load_source = "内置库"
            else:
                self.logger.debug("内置VLC路径配置不完整")
                return False

            # 设置环境变量（由内置管理器处理）
            # 导入VLC库
            self._import_vlc()

            # 创建VLC实例
            self._create_vlc_instance()

            self.logger.info(f"内置VLC加载成功 - {config.get('integrity_message', '')}")
            return True

        except Exception as e:
            self.logger.debug(f"内置VLC加载失败: {e}")
            return False

    def _load_program_vlc(self) -> bool:
        """加载程序目录VLC

        Returns:
            bool: 加载是否成功
        """
        try:
            # 查找程序目录下的VLC
            program_vlc = self._find_builtin_vlc()
            if not program_vlc:
                return False

            self.vlc_path = program_vlc
            self.load_source = "程序目录"

            # 设置环境变量
            self._setup_vlc_environment()

            # 导入VLC库
            self._import_vlc()

            # 创建VLC实例
            self._create_vlc_instance()

            return True

        except Exception as e:
            self.logger.debug(f"程序目录VLC加载失败: {e}")
            return False

    def _load_system_vlc(self) -> bool:
        """加载系统VLC

        Returns:
            bool: 加载是否成功
        """
        try:
            # 查找系统安装的VLC
            system_vlc = self._find_system_vlc()
            if not system_vlc:
                return False

            self.vlc_path = system_vlc
            self.load_source = "系统安装"

            # 设置环境变量
            self._setup_vlc_environment()

            # 导入VLC库
            self._import_vlc()

            # 创建VLC实例
            self._create_vlc_instance()

            return True

        except Exception as e:
            self.logger.debug(f"系统VLC加载失败: {e}")
            return False

    def _handle_vlc_unavailable(self) -> bool:
        """处理VLC不可用的情况

        Returns:
            bool: 降级处理是否成功
        """
        self.logger.warning("VLC不可用，媒体播放功能将被禁用")
        self.load_source = "不可用"

        # 可以在这里添加降级逻辑
        # 例如：使用其他音频库、显示友好提示等

        return False

    def _get_vlc_path(self) -> Optional[str]:
        """
        获取VLC库路径

        Returns:
            str: VLC库路径，未找到返回None
        """
        # 1. 优先使用程序内置VLC（便携式）
        builtin_vlc = self._find_builtin_vlc()
        if builtin_vlc:
            self.logger.info("使用程序内置VLC")
            return builtin_vlc

        # 2. 查找系统安装的VLC
        system_vlc = self._find_system_vlc()
        if system_vlc:
            self.logger.info("使用系统安装的VLC")
            return system_vlc

        self.logger.error("未找到VLC库")
        return None

    def _find_builtin_vlc(self) -> Optional[str]:
        """查找程序内置的VLC"""
        possible_paths = [
            # 当前程序目录下的vlc文件夹
            os.path.join(os.getcwd(), 'vlc'),
            os.path.join(os.getcwd(), 'vlc_portable'),  # 添加便携版VLC路径
            os.path.join(os.path.dirname(sys.executable), 'vlc'),
            os.path.join(os.path.dirname(sys.executable), 'vlc_portable'),
            # 相对于脚本目录
            os.path.join(os.path.dirname(__file__), '..', '..', '..', 'vlc'),
            os.path.join(os.path.dirname(__file__), '..', '..', '..', 'vlc_portable'),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                # 检查必要的VLC库文件
                if self._verify_vlc_installation(path):
                    return os.path.abspath(path)

        return None

    def _find_system_vlc(self) -> Optional[str]:
        """查找系统安装的VLC"""
        system = platform.system()

        if system == 'Windows':
            return self._find_windows_vlc()
        elif system == 'Linux':
            return self._find_linux_vlc()
        elif system == 'Darwin':
            return self._find_macos_vlc()

        return None

    def _find_windows_vlc(self) -> Optional[str]:
        """查找Windows系统VLC"""
        # 常见的VLC安装路径
        vlc_paths = [
            os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files'), 'VideoLAN', 'VLC'),
            os.path.join(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)'), 'VideoLAN', 'VLC'),
            'C:\\Program Files\\VideoLAN\\VLC',
            'C:\\Program Files (x86)\\VideoLAN\\VLC',
        ]

        for path in vlc_paths:
            if os.path.exists(path) and self._verify_vlc_installation(path):
                return path

        return None

    def _find_linux_vlc(self) -> Optional[str]:
        """查找Linux系统VLC"""
        # 常见的Linux VLC安装路径
        vlc_paths = [
            '/usr/lib/vlc',
            '/usr/local/lib/vlc',
            '/usr/lib/x86_64-linux-gnu/vlc',
        ]

        for path in vlc_paths:
            if os.path.exists(path) and self._verify_vlc_installation(path):
                return path

        # 尝试通过命令行查找
        try:
            import subprocess
            result = subprocess.run(['which', 'vlc'], capture_output=True, text=True)
            if result.returncode == 0:
                vlc_path = os.path.dirname(result.stdout.strip())
                if self._verify_vlc_installation(vlc_path):
                    return vlc_path
        except:
            pass

        return None

    def _find_macos_vlc(self) -> Optional[str]:
        """查找macOS系统VLC"""
        vlc_paths = [
            '/Applications/VLC.app/Contents/MacOS',
            '/Applications/VLC.app/Contents/lib',
        ]

        for path in vlc_paths:
            if os.path.exists(path) and self._verify_vlc_installation(path):
                return path

        return None

    def _verify_vlc_installation(self, vlc_path: str) -> bool:
        """
        验证VLC安装是否完整

        Args:
            vlc_path: VLC路径

        Returns:
            bool: 安装是否完整
        """
        if not os.path.exists(vlc_path):
            return False

        # 检查核心库文件
        system = platform.system()
        if system == 'Windows':
            required_files = ['libvlc.dll', 'libvlccore.dll']
        elif system == 'Linux':
            required_files = ['libvlc.so', 'libvlccore.so']
        elif system == 'Darwin':
            required_files = ['libvlc.dylib', 'libvlccore.dylib']
        else:
            return False

        for filename in required_files:
            filepath = os.path.join(vlc_path, filename)
            if not os.path.exists(filepath):
                self.logger.debug(f"缺少VLC核心文件: {filepath}")
                return False

        # 检查插件目录
        plugin_path = os.path.join(vlc_path, 'plugins')
        if not os.path.exists(plugin_path):
            self.logger.debug(f"VLC插件目录不存在: {plugin_path}")
            return False

        # 检查插件文件（支持子目录结构）
        plugin_files = []
        plugin_dir = Path(plugin_path)

        # 检查直接在插件目录下的DLL文件
        plugin_files.extend(plugin_dir.glob("*.dll"))

        # 如果没有直接找到DLL文件，检查子目录
        if not plugin_files:
            for subdir in plugin_dir.iterdir():
                if subdir.is_dir():
                    plugin_files.extend(subdir.glob("*.dll"))

        # 至少需要有一些插件文件
        if len(plugin_files) < 20:  # VLC通常有数百个插件
            self.logger.debug(f"VLC插件文件数量不足: {len(plugin_files)}个")
            return False

        self.logger.debug(f"VLC插件检查通过: {len(plugin_files)}个插件文件")
        return True

    def _setup_vlc_environment(self):
        """设置VLC环境变量"""
        if not self.vlc_path:
            return

        # 设置插件路径
        plugin_path = os.path.join(self.vlc_path, 'plugins')
        os.environ['VLC_PLUGIN_PATH'] = plugin_path

        # 添加VLC路径到系统PATH
        if self.vlc_path not in os.environ.get('PATH', ''):
            os.environ['PATH'] = self.vlc_path + os.pathsep + os.environ.get('PATH', '')

        self.logger.debug(f"VLC插件路径: {plugin_path}")

    def _import_vlc(self):
        """导入VLC库"""
        try:
            import vlc
            self.vlc_lib = vlc
            self.logger.info(f"VLC库导入成功，版本: {vlc.libvlc_get_version().decode()}")
        except ImportError as e:
            raise RuntimeError(f"无法导入VLC库: {e}")

    def _create_vlc_instance(self):
        """创建VLC实例"""
        if not self.vlc_lib:
            raise RuntimeError("VLC库未导入")

        # VLC启动参数 - 使用最小安全配置
        vlc_args = [
            '--quiet',                       # 静默模式
            '--no-stats',                    # 不收集统计信息
            '--no-video-title-show',         # 不显示视频标题
            '--no-sub-autodetect-file',      # 不自动检测字幕文件
            '--no-snapshot-preview',         # 不显示截图预览
            '--no-interact',                 # 禁用交互接口
            '--ignore-config',               # 忽略配置文件
            '--no-plugins-cache',            # 禁用插件缓存
            '--no-xlib',                     # 禁用X11相关功能
        ]

        # Windows特定优化
        if platform.system() == 'Windows':
            vlc_args.extend([
                '--aout=directsound',        # Windows音频输出
                '--vout=dummy',               # 使用虚拟视频输出避免冲突
            ])

        # 创建VLC实例
        try:
            self.vlc_instance = self.vlc_lib.Instance(vlc_args)
            self.logger.debug("VLC实例创建成功")
        except Exception as e:
            raise RuntimeError(f"VLC实例创建失败: {e}")

    def get_vlc_instance(self):
        """获取VLC实例"""
        if not self.is_loaded:
            raise RuntimeError("VLC未加载")
        return self.vlc_instance

    def get_vlc_lib(self):
        """获取VLC库"""
        if not self.is_loaded:
            raise RuntimeError("VLC未加载")
        return self.vlc_lib

    def is_vlc_available(self) -> bool:
        """检查VLC是否可用"""
        return self.is_loaded

    def get_vlc_version(self) -> str:
        """获取VLC版本"""
        if not self.is_loaded or not self.vlc_lib:
            return "未知"

        try:
            version = self.vlc_lib.libvlc_get_version()
            return version.decode('utf-8') if isinstance(version, bytes) else str(version)
        except:
            return "未知"

    def check_missing_plugins(self) -> List[str]:
        """检查缺失的VLC插件"""
        if not self.vlc_path:
            return ["VLC路径未设置"]

        plugin_path = os.path.join(self.vlc_path, 'plugins')
        if not os.path.exists(plugin_path):
            return ["VLC插件目录不存在"]

        # 必要的插件列表（Windows）- 支持子目录结构
        essential_plugins = [
            'libaccess_plugin.dll',
            'libfilesystem_plugin.dll',
            'libmp4_plugin.dll',
            'libmp3_plugin.dll',
            'libh264_plugin.dll',
            'libdirectsound_plugin.dll',
            'libdirect3d_plugin.dll',
        ]

        missing = []
        plugin_dir = Path(plugin_path)

        # 搜索插件文件（支持子目录）
        found_plugins = []
        found_plugins.extend(plugin_dir.glob("*.dll"))

        # 搜索子目录中的插件
        for subdir in plugin_dir.iterdir():
            if subdir.is_dir():
                found_plugins.extend(subdir.glob("*.dll"))

        found_plugin_names = {p.name for p in found_plugins}

        for plugin in essential_plugins:
            if plugin not in found_plugin_names:
                missing.append(plugin)

        return missing

    def cleanup(self):
        """清理VLC资源"""
        if self.vlc_instance:
            try:
                self.vlc_instance.release()
                self.logger.debug("VLC实例已释放")
            except:
                pass

        self.vlc_instance = None
        self.vlc_lib = None
        self.is_loaded = False
        self.load_source = None

    def get_load_info(self) -> Dict[str, any]:
        """获取VLC加载信息

        Returns:
            Dict[str, any]: 加载信息字典
        """
        return {
            "is_loaded": self.is_loaded,
            "load_source": self.load_source,
            "vlc_path": self.vlc_path,
            "prefer_embedded": self.prefer_embedded,
            "embedded_config": self.embedded_config,
            "version": self.get_vlc_version() if self.is_loaded else "未加载"
        }

    def is_embedded_available(self) -> bool:
        """检查内置VLC是否可用

        Returns:
            bool: 内置VLC是否可用
        """
        if not prepare_embedded_vlc:
            return False

        try:
            success, _ = prepare_embedded_vlc()
            return success
        except:
            return False

    def force_load_embedded(self) -> bool:
        """强制加载内置VLC

        Returns:
            bool: 加载是否成功
        """
        if self.is_embedded_available():
            return self._load_embedded_vlc()
        return False

    def reload_vlc(self, prefer_embedded: Optional[bool] = None) -> bool:
        """重新加载VLC

        Args:
            prefer_embedded: 是否优先使用内置VLC，None表示保持当前设置

        Returns:
            bool: 重新加载是否成功
        """
        try:
            # 清理当前VLC实例
            self.cleanup()

            # 更新偏好设置
            if prefer_embedded is not None:
                self.prefer_embedded = prefer_embedded

            # 重新初始化
            self._initialize_vlc()
            return self.is_loaded

        except Exception as e:
            self.logger.error(f"VLC重新加载失败: {e}")
            return False