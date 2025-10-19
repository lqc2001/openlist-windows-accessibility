"""
VLC内置库管理器
负责管理内置的VLC库文件，提供加载和配置功能
"""

import os
import sys
import platform
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict

logger = logging.getLogger(__name__)


class VLCEmbeddedManager:
    """VLC内置库管理器

    负责管理内置的VLC运行时库，提供库文件的检测、验证和加载功能
    """

    def __init__(self):
        """初始化VLC内置管理器"""
        # 获取media模块目录
        self.media_dir = Path(__file__).parent
        # VLC运行时目录（优先使用便携版）
        self.vlc_runtime_dir = self.media_dir.parent / "vlc_portable"
        # 库文件目录
        self.lib_dir = self.vlc_runtime_dir
        # 插件目录
        self.plugins_dir = self.vlc_runtime_dir / "plugins"

        # 如果便携版不存在，则使用传统的runtime目录
        if not self.vlc_runtime_dir.exists():
            self.vlc_runtime_dir = self.media_dir / "vlc_runtime"
            self.lib_dir = self.vlc_runtime_dir / "lib"
            self.plugins_dir = self.lib_dir / "plugins"

        # 系统架构信息
        self.architecture = "x64" if platform.machine().endswith('64') else "x86"
        self.python_arch = "x64" if sys.maxsize > 2**32 else "x86"

        # 必需的库文件
        self.required_libraries = {
            "libvlc.dll": "VLC主库",
            "libvlccore.dll": "VLC核心库"
        }

        # 必需的插件类型
        self.required_plugin_types = [
            "access", "audio_filter", "audio_mixer", "audio_output",
            "codec", "demux", "gui", "logger", "services_discovery",
            "stream_filter", "stream_out", "video_chroma", "video_filter",
            "video_output", "visualization"
        ]

        logger.info(f"VLC内置管理器初始化完成 - Python架构: {self.python_arch}, 系统架构: {self.architecture}")

    def check_embedded_vlc_availability(self) -> Tuple[bool, str]:
        """检查内置VLC库是否可用

        Returns:
            Tuple[bool, str]: (是否可用, 详细信息)
        """
        try:
            # 1. 检查目录是否存在
            if not self.vlc_runtime_dir.exists():
                return False, f"VLC运行时目录不存在: {self.vlc_runtime_dir}"

            if not self.lib_dir.exists():
                return False, f"VLC库目录不存在: {self.lib_dir}"

            # 2. 检查必需的库文件
            missing_libs = []
            for lib_file, description in self.required_libraries.items():
                lib_path = self.lib_dir / lib_file
                if not lib_path.exists():
                    missing_libs.append(f"{lib_file} ({description})")

            if missing_libs:
                return False, f"缺少必需的库文件: {', '.join(missing_libs)}"

            # 3. 检查插件目录
            if not self.plugins_dir.exists():
                return False, f"VLC插件目录不存在: {self.plugins_dir}"

            # 4. 检查插件文件（支持子目录结构）
            plugin_files = list(self.plugins_dir.glob("*.dll"))
            # 如果没有直接的DLL文件，检查子目录
            if not plugin_files:
                # 检查子目录中的DLL文件
                for subdir in self.plugins_dir.iterdir():
                    if subdir.is_dir():
                        plugin_files.extend(subdir.glob("*.dll"))

            if len(plugin_files) < 20:  # VLC通常包含数十个插件
                return False, f"插件文件数量不足 ({len(plugin_files)}个，通常需要20+个)"

            # 5. 验证架构兼容性
            if self.python_arch == "x64" and self.architecture != "x64":
                logger.warning("64位Python在32位系统上运行，可能存在兼容性问题")

            return True, f"内置VLC库检查通过 - {len(plugin_files)}个插件"

        except Exception as e:
            return False, f"检查VLC库时发生错误: {str(e)}"

    def get_vlc_library_paths(self) -> Dict[str, str]:
        """获取VLC库文件路径

        Returns:
            Dict[str, str]: 库文件路径字典
        """
        paths = {}
        for lib_file in self.required_libraries.keys():
            lib_path = self.lib_dir / lib_file
            if lib_path.exists():
                paths[lib_file] = str(lib_path)

        return paths

    def setup_environment_variables(self) -> bool:
        """设置VLC相关的环境变量

        Returns:
            bool: 设置是否成功
        """
        try:
            # 设置VLC插件路径
            if self.plugins_dir.exists():
                vlc_plugin_path = str(self.plugins_dir)
                os.environ['VLC_PLUGIN_PATH'] = vlc_plugin_path
                logger.debug(f"设置VLC插件路径: {vlc_plugin_path}")

            # 添加库目录到PATH
            if self.lib_dir.exists():
                lib_path = str(self.lib_dir)
                current_path = os.environ.get('PATH', '')
                if lib_path not in current_path:
                    os.environ['PATH'] = lib_path + os.pathsep + current_path
                    logger.debug(f"添加库目录到PATH: {lib_path}")

            return True

        except Exception as e:
            logger.error(f"设置环境变量失败: {e}")
            return False

    def verify_library_integrity(self) -> Tuple[bool, str]:
        """验证库文件完整性

        Returns:
            Tuple[bool, str]: (验证结果, 详细信息)
        """
        try:
            verification_results = []

            # 检查主库文件大小
            for lib_file, description in self.required_libraries.items():
                lib_path = self.lib_dir / lib_file
                if lib_path.exists():
                    file_size = lib_path.stat().st_size
                    # libvlc.dll 通常较小（几百KB），libvlccore.dll 较大（几MB）
                    if lib_file == "libvlc.dll":
                        if file_size < 100 * 1024:  # 100KB
                            verification_results.append(f"{lib_file} 文件过小 ({file_size} bytes)")
                        else:
                            verification_results.append(f"{lib_file} 文件正常 ({file_size / 1024:.1f} KB)")
                    else:  # libvlccore.dll
                        if file_size < 1024 * 1024:  # 1MB
                            verification_results.append(f"{lib_file} 文件过小 ({file_size} bytes)")
                        else:
                            verification_results.append(f"{lib_file} 文件正常 ({file_size / 1024 / 1024:.1f} MB)")
                else:
                    verification_results.append(f"{lib_file} 文件不存在")

            # 检查插件数量（支持子目录结构）
            plugin_files = list(self.plugins_dir.glob("*.dll"))
            # 如果没有直接的DLL文件，检查子目录
            if not plugin_files:
                # 检查子目录中的DLL文件
                for subdir in self.plugins_dir.iterdir():
                    if subdir.is_dir():
                        plugin_files.extend(subdir.glob("*.dll"))

            plugin_count = len(plugin_files)
            verification_results.append(f"插件数量: {plugin_count}")

            # 检查插件类型覆盖（基于目录结构）
            plugin_types_found = set()
            if self.plugins_dir.exists():
                for plugin_type in self.required_plugin_types:
                    plugin_type_dir = self.plugins_dir / plugin_type
                    if plugin_type_dir.exists() and plugin_type_dir.is_dir():
                        # 检查目录中是否有插件文件
                        plugin_files_in_dir = list(plugin_type_dir.glob("*.dll"))
                        if plugin_files_in_dir:
                            plugin_types_found.add(plugin_type)

            missing_plugin_types = set(self.required_plugin_types) - plugin_types_found
            if missing_plugin_types:
                verification_results.append(f"缺少插件类型: {', '.join(missing_plugin_types)}")
            else:
                verification_results.append("所有必需插件类型都存在")

            # 综合评估
            success = len([r for r in verification_results if "不存在" in r or "过小" in r or "缺少" in r]) == 0

            return success, "; ".join(verification_results)

        except Exception as e:
            return False, f"验证库完整性时发生错误: {str(e)}"

    def get_version_info(self) -> Dict[str, str]:
        """获取VLC版本信息

        Returns:
            Dict[str, str]: 版本信息字典
        """
        version_info = {
            "architecture": self.python_arch,
            "platform": platform.system(),
            "python_version": sys.version.split()[0],
            "vlc_runtime_dir": str(self.vlc_runtime_dir),
            "lib_dir": str(self.lib_dir),
            "plugins_dir": str(self.plugins_dir)
        }

        # 尝试从库文件获取版本信息
        try:
            libvlc_path = self.lib_dir / "libvlc.dll"
            if libvlc_path.exists():
                # 通过文件修改时间估计版本
                mtime = libvlc_path.stat().st_mtime
                version_info["libvlc_modified"] = str(mtime)

                # 这里可以添加更复杂的版本检测逻辑
                # 比如读取DLL版本信息等
        except Exception as e:
            logger.warning(f"获取VLC版本信息失败: {e}")
            version_info["version_error"] = str(e)

        return version_info

    def create_fallback_configuration(self) -> Dict[str, any]:
        """创建降级配置

        当内置VLC不可用时，返回降级处理配置

        Returns:
            Dict[str, any]: 降级配置
        """
        return {
            "embedded_available": False,
            "fallback_options": [
                "try_system_vlc",
                "audio_only_mode",
                "disabled_mode"
            ],
            "user_message": "媒体播放功能暂时不可用，建议安装VLC媒体播放器",
            "error_code": "EMBEDDED_VLC_UNAVAILABLE"
        }

    def prepare_for_loading(self) -> Tuple[bool, Dict[str, any]]:
        """为VLC加载做准备

        Returns:
            Tuple[bool, Dict[str, any]]: (是否准备就绪, 配置信息)
        """
        try:
            # 1. 检查可用性
            available, message = self.check_embedded_vlc_availability()
            if not available:
                logger.warning(f"内置VLC不可用: {message}")
                return False, self.create_fallback_configuration()

            # 2. 验证完整性
            integrity_ok, integrity_message = self.verify_library_integrity()
            if not integrity_ok:
                logger.warning(f"VLC库完整性验证失败: {integrity_message}")
                # 可以选择继续或降级，这里选择继续但记录警告

            # 3. 设置环境变量
            if not self.setup_environment_variables():
                logger.error("设置VLC环境变量失败")
                return False, self.create_fallback_configuration()

            # 4. 准备配置信息
            config = {
                "embedded_available": True,
                "vlc_paths": self.get_vlc_library_paths(),
                "version_info": self.get_version_info(),
                "integrity_message": integrity_message,
                "plugins_dir": str(self.plugins_dir),
                "architecture": self.python_arch
            }

            logger.info(f"VLC内置库准备就绪: {message}")
            return True, config

        except Exception as e:
            logger.error(f"准备VLC加载时发生错误: {e}")
            return False, self.create_fallback_configuration()


# 全局实例
_vlc_embedded_manager = None


def get_vlc_embedded_manager() -> VLCEmbeddedManager:
    """获取VLC内置管理器单例"""
    global _vlc_embedded_manager
    if _vlc_embedded_manager is None:
        _vlc_embedded_manager = VLCEmbeddedManager()
    return _vlc_embedded_manager


def is_embedded_vlc_available() -> bool:
    """快速检查内置VLC是否可用"""
    try:
        manager = get_vlc_embedded_manager()
        available, _ = manager.check_embedded_vlc_availability()
        return available
    except Exception as e:
        logger.error(f"检查内置VLC可用性时发生错误: {e}")
        return False


def prepare_embedded_vlc() -> Tuple[bool, Dict[str, any]]:
    """准备内置VLC加载"""
    try:
        manager = get_vlc_embedded_manager()
        return manager.prepare_for_loading()
    except Exception as e:
        logger.error(f"准备内置VLC时发生错误: {e}")
        return False, {"embedded_available": False, "error": str(e)}