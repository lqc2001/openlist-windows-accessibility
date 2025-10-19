#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VLC库打包工具
用于将VLC运行时库打包到项目中，实现完全内置的媒体播放支持
"""

import os
import sys
import shutil
import zipfile
import requests
import tempfile
import logging
from pathlib import Path
from typing import Optional, List, Dict, Tuple

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class VLCPackager:
    """VLC库打包器

    负责从VLC官方发行版中提取必要的库文件并打包到项目中
    """

    def __init__(self, project_root: Optional[str] = None):
        """初始化VLC打包器

        Args:
            project_root: 项目根目录，默认为脚本所在目录的上级目录
        """
        if project_root is None:
            self.project_root = Path(__file__).parent.parent
        else:
            self.project_root = Path(project_root)

        # 目标路径
        self.vlc_runtime_dir = self.project_root / "src" / "media" / "vlc_runtime"
        self.lib_dir = self.vlc_runtime_dir / "lib"
        self.plugins_dir = self.lib_dir / "plugins"

        # VLC配置
        self.vlc_version = "3.0.20"  # 使用LTS版本
        self.vlc_platform = "win64"   # Windows 64位
        self.vlc_archive_name = f"vlc-{self.vlc_version}-{self.vlc_platform}.7z"

        # 必需的库文件
        self.required_libraries = [
            "libvlc.dll",
            "libvlccore.dll"
        ]

        # 必需的插件类型（选择最常用的）
        self.required_plugin_patterns = [
            "libaccess_*.dll",
            "libaudio_filter_*.dll",
            "libaudio_mixer_*.dll",
            "libaudio_output_*.dll",
            "libcodec_*.dll",
            "libdemux_*.dll",
            "libgui_*.dll",
            "liblogger_*.dll",
            "libpacketizer_*.dll",
            "libservices_discovery_*.dll",
            "libstream_filter_*.dll",
            "libstream_out_*.dll",
            "libvideo_chroma_*.dll",
            "libvideo_filter_*.dll",
            "libvideo_output_*.dll",
            "libvisualization_*.dll"
        ]

        logger.info(f"VLC打包器初始化完成 - 项目根目录: {self.project_root}")

    def check_project_structure(self) -> bool:
        """检查项目结构是否正确

        Returns:
            bool: 结构是否正确
        """
        try:
            # 检查关键目录
            required_dirs = [
                self.project_root / "src" / "media",
                self.project_root / "resources",
                self.project_root / "tools"
            ]

            for dir_path in required_dirs:
                if not dir_path.exists():
                    logger.error(f"项目目录结构不完整: {dir_path}")
                    return False

            logger.info("项目结构检查通过")
            return True

        except Exception as e:
            logger.error(f"检查项目结构时发生错误: {e}")
            return False

    def download_vlc_portable(self, download_dir: Path) -> bool:
        """下载VLC便携版

        Args:
            download_dir: 下载目录

        Returns:
            bool: 下载是否成功
        """
        try:
            # VLC官方下载链接
            download_url = f"https://download.videolan.org/pub/videolan/vlc/{self.vlc_version}/{self.vlc_archive_name}"

            logger.info(f"开始下载VLC便携版: {download_url}")

            # 下载文件
            archive_path = download_dir / self.vlc_archive_name
            response = requests.get(download_url, stream=True, timeout=300)

            if response.status_code == 200:
                with open(archive_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.info(f"VLC便携版下载完成: {archive_path}")
                return True
            else:
                logger.error(f"下载失败，状态码: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"下载VLC便携版时发生错误: {e}")
            return False

    def extract_vlc_archive(self, archive_path: Path, extract_dir: Path) -> bool:
        """解压VLC压缩包

        Args:
            archive_path: 压缩包路径
            extract_dir: 解压目录

        Returns:
            bool: 解压是否成功
        """
        try:
            logger.info(f"开始解压VLC压缩包: {archive_path}")

            # 尝试使用7zip解压（需要系统安装7-Zip）
            try:
                import subprocess
                subprocess.run([
                    "7z", "x", str(archive_path), f"-o{extract_dir}", "-y"
                ], check=True, capture_output=True)
                logger.info("7zip解压成功")
            except (subprocess.CalledProcessError, FileNotFoundError):
                # 如果7zip不可用，尝试使用Python内置的zipfile（可能不支持7z格式）
                logger.warning("7zip不可用，尝试使用内置zip解压")
                try:
                    with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                        zip_ref.extractall(extract_dir)
                    logger.info("内置zip解压成功")
                except zipfile.BadZipFile:
                    logger.error("无法解压7z格式文件，请安装7-Zip")
                    return False

            return True

        except Exception as e:
            logger.error(f"解压VLC压缩包时发生错误: {e}")
            return False

    def extract_vlc_libraries(self, vlc_source_dir: Path) -> bool:
        """从VLC源目录提取必要库文件

        Args:
            vlc_source_dir: VLC源目录

        Returns:
            bool: 提取是否成功
        """
        try:
            logger.info("开始提取VLC库文件")

            # 确保目标目录存在
            self.lib_dir.mkdir(parents=True, exist_ok=True)
            self.plugins_dir.mkdir(parents=True, exist_ok=True)

            # 查找VLC主目录
            vlc_main_dir = None
            for item in vlc_source_dir.iterdir():
                if item.is_dir() and item.name.startswith("vlc"):
                    vlc_main_dir = item
                    break

            if not vlc_main_dir:
                logger.error("未找到VLC主目录")
                return False

            vlc_lib_dir = vlc_main_dir / "lib"
            vlc_plugins_dir = vlc_lib_dir / "plugins"

            if not vlc_lib_dir.exists():
                logger.error(f"VLC库目录不存在: {vlc_lib_dir}")
                return False

            # 1. 复制核心库文件
            copied_libs = 0
            for lib_file in self.required_libraries:
                src_path = vlc_lib_dir / lib_file
                dst_path = self.lib_dir / lib_file

                if src_path.exists():
                    shutil.copy2(src_path, dst_path)
                    copied_libs += 1
                    logger.debug(f"复制库文件: {lib_file}")
                else:
                    logger.error(f"找不到库文件: {src_path}")
                    return False

            logger.info(f"核心库文件复制完成 ({copied_libs}个)")

            # 2. 复制插件文件
            copied_plugins = 0
            if vlc_plugins_dir.exists():
                for pattern in self.required_plugin_patterns:
                    src_files = list(vlc_plugins_dir.glob(pattern))
                    for src_file in src_files:
                        dst_file = self.plugins_dir / src_file.name
                        shutil.copy2(src_file, dst_file)
                        copied_plugins += 1

                logger.info(f"插件文件复制完成 ({copied_plugins}个)")
            else:
                logger.error(f"VLC插件目录不存在: {vlc_plugins_dir}")
                return False

            # 3. 复制许可证和说明文件
            info_files = ["LICENSE.txt", "README.txt", "COPYING.txt"]
            for info_file in info_files:
                src_file = vlc_main_dir / info_file
                if src_file.exists():
                    dst_file = self.vlc_runtime_dir / info_file
                    shutil.copy2(src_file, dst_file)

            return True

        except Exception as e:
            logger.error(f"提取VLC库文件时发生错误: {e}")
            return False

    def create_vlc_runtime_info(self) -> bool:
        """创建VLC运行时信息文件

        Returns:
            bool: 创建是否成功
        """
        try:
            info_file = self.vlc_runtime_dir / "runtime_info.json"

            # 统计文件信息
            lib_files = list(self.lib_dir.glob("*.dll"))
            plugin_files = list(self.plugins_dir.glob("*.dll"))

            runtime_info = {
                "vlc_version": self.vlc_version,
                "platform": self.vlc_platform,
                "packaged_date": str(Path().absolute()),
                "libraries": {
                    "count": len(lib_files),
                    "files": [f.name for f in lib_files]
                },
                "plugins": {
                    "count": len(plugin_files),
                    "files": [f.name for f in plugin_files[:50]]  # 只列前50个文件名
                },
                "total_size_mb": sum(
                    f.stat().st_size for f in lib_files + plugin_files
                ) / 1024 / 1024
            }

            import json
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(runtime_info, f, indent=2, ensure_ascii=False)

            logger.info(f"VLC运行时信息文件已创建: {info_file}")
            return True

        except Exception as e:
            logger.error(f"创建运行时信息文件时发生错误: {e}")
            return False

    def verify_package(self) -> Tuple[bool, str]:
        """验证打包结果

        Returns:
            Tuple[bool, str]: (验证结果, 详细信息)
        """
        try:
            # 检查核心库文件
            missing_libs = []
            for lib_file in self.required_libraries:
                lib_path = self.lib_dir / lib_file
                if not lib_path.exists():
                    missing_libs.append(lib_file)

            if missing_libs:
                return False, f"缺少核心库文件: {', '.join(missing_libs)}"

            # 检查插件文件数量
            plugin_files = list(self.plugins_dir.glob("*.dll"))
            if len(plugin_files) < 20:
                return False, f"插件文件数量不足 ({len(plugin_files)}个)"

            # 检查文件大小
            total_size = sum(
                f.stat().st_size for f in plugin_files + list(self.lib_dir.glob("*.dll"))
            )
            if total_size < 50 * 1024 * 1024:  # 至少50MB
                return False, f"库文件总大小过小 ({total_size / 1024 / 1024:.1f}MB)"

            success_info = f"验证通过 - {len(plugin_files)}个插件, {total_size / 1024 / 1024:.1f}MB"
            return True, success_info

        except Exception as e:
            return False, f"验证时发生错误: {str(e)}"

    def package_vlc(self, download_vlc: bool = True, vlc_source_dir: Optional[str] = None) -> bool:
        """执行VLC打包流程

        Args:
            download_vlc: 是否下载VLC便携版
            vlc_source_dir: VLC源目录路径（如果不下载，从此路径提取）

        Returns:
            bool: 打包是否成功
        """
        try:
            logger.info("开始VLC打包流程")

            # 1. 检查项目结构
            if not self.check_project_structure():
                return False

            # 2. 准备临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # 3. 获取VLC源文件
                vlc_extract_dir = temp_path / "vlc_extracted"

                if download_vlc:
                    # 下载VLC便携版
                    if not self.download_vlc_portable(temp_path):
                        logger.error("VLC便携版下载失败")
                        return False

                    # 解压
                    archive_path = temp_path / self.vlc_archive_name
                    if not self.extract_vlc_archive(archive_path, vlc_extract_dir):
                        logger.error("VLC压缩包解压失败")
                        return False
                else:
                    # 使用指定的VLC源目录
                    if vlc_source_dir:
                        vlc_extract_dir = Path(vlc_source_dir)
                    else:
                        logger.error("未指定VLC源目录")
                        return False

                # 4. 提取库文件
                if not self.extract_vlc_libraries(vlc_extract_dir):
                    logger.error("VLC库文件提取失败")
                    return False

                # 5. 创建运行时信息
                if not self.create_vlc_runtime_info():
                    logger.error("运行时信息创建失败")
                    return False

                # 6. 验证打包结果
                success, message = self.verify_package()
                if not success:
                    logger.error(f"打包验证失败: {message}")
                    return False

            logger.info(f"VLC打包完成 - {message}")
            return True

        except Exception as e:
            logger.error(f"VLC打包流程失败: {e}")
            return False

    def clean_package(self) -> bool:
        """清理打包文件

        Returns:
            bool: 清理是否成功
        """
        try:
            if self.vlc_runtime_dir.exists():
                shutil.rmtree(self.vlc_runtime_dir)
                logger.info("已清理VLC运行时目录")
            return True
        except Exception as e:
            logger.error(f"清理打包文件失败: {e}")
            return False


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="VLC库打包工具")
    parser.add_argument("--project-root", help="项目根目录路径")
    parser.add_argument("--download", action="store_true", default=True, help="下载VLC便携版")
    parser.add_argument("--no-download", action="store_false", dest="download", help="不下载VLC便携版")
    parser.add_argument("--vlc-source", help="VLC源目录路径（与--no-download配合使用）")
    parser.add_argument("--clean", action="store_true", help="清理现有打包文件")
    parser.add_argument("--verify", action="store_true", help="仅验证现有打包")

    args = parser.parse_args()

    # 创建打包器
    packager = VLCPackager(args.project_root)

    if args.clean:
        success = packager.clean_package()
        sys.exit(0 if success else 1)

    if args.verify:
        success, message = packager.verify_package()
        print(f"验证结果: {'成功' if success else '失败'} - {message}")
        sys.exit(0 if success else 1)

    # 执行打包
    success = packager.package_vlc(
        download_vlc=args.download,
        vlc_source_dir=args.vlc_source
    )

    if success:
        print("✅ VLC库打包成功！")
        print("现在可以在应用程序中使用内置VLC功能了。")
    else:
        print("❌ VLC库打包失败！")
        print("请检查日志信息并重试。")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()