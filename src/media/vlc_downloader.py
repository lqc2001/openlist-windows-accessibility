#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VLC便携包下载管理器
自动下载和集成VideoLAN官方便携版VLC
"""

import os
import sys
import zipfile
import requests
import tempfile
from pathlib import Path
from urllib.parse import urljoin
import shutil
from typing import Optional, Callable
import threading
import time

class VLCDownloader:
    """VLC便携包下载管理器"""

    # VideoLAN官方下载配置
    VLC_BASE_URL = "https://get.videolan.org/vlc/"
    VLC_LATEST_VERSION = "3.0.20"  # 当前最新稳定版
    VLC_DOWNLOAD_URL = f"https://download.videolan.org/pub/videolan/vlc/{VLC_LATEST_VERSION}/win64/"
    VLC_PORTABLE_FILENAME = f"vlc-{VLC_LATEST_VERSION}-win64.zip"

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.vlc_dir = project_root / "vlc_portable"
        self.temp_dir = project_root / "temp"

        # 确保目录存在
        self.temp_dir.mkdir(exist_ok=True)
        self.vlc_dir.mkdir(exist_ok=True)

        # 版本信息文件
        self.version_file = self.vlc_dir / "version.txt"

        # 下载状态
        self.is_downloading = False
        self.download_progress = 0
        self.download_status = ""
        self.callback = None

        # 获取VLC便携包完整下载URL
        self.vlc_download_url = urljoin(self.VLC_DOWNLOAD_URL, self.VLC_PORTABLE_FILENAME)

        self.logger = self._create_logger()

    def _create_logger(self):
        """创建日志记录器"""
        import logging
        logger = logging.getLogger("VLCDownloader")
        logger.setLevel(logging.INFO)

        # 文件处理器
        log_file = self.project_root / "logs" / "vlc_download.log"
        log_file.parent.mkdir(exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)

        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 格式化器
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def check_vlc_installed(self) -> bool:
        """检查VLC便携版是否已安装"""
        if not self.vlc_dir.exists():
            return False

        # 检查关键文件
        vlc_exe = self.vlc_dir / "vlc.exe"
        libvlc = self.vlc_dir / "libvlc.dll"

        if not vlc_exe.exists() or not libvlc.exists():
            return False

        # 检查版本
        if self.version_file.exists():
            try:
                current_version = self.version_file.read_text(encoding='utf-8').strip()
                if current_version == self.VLC_LATEST_VERSION:
                    self.logger.info(f"VLC便携版已安装，版本: {current_version}")
                    return True
            except Exception as e:
                self.logger.warning(f"读取版本文件失败: {e}")

        return False

    def get_download_size(self) -> Optional[int]:
        """获取下载文件大小"""
        try:
            response = requests.head(self.vlc_download_url, timeout=10)
            if response.status_code == 200:
                return int(response.headers.get('content-length', 0))
        except Exception as e:
            self.logger.error(f"获取下载大小失败: {e}")
        return None

    def download_progress_callback(self, downloaded: int, total: int):
        """下载进度回调"""
        if total > 0:
            self.download_progress = (downloaded / total) * 100
        else:
            self.download_progress = 0

        # 更新状态
        mb_downloaded = downloaded / (1024 * 1024)
        mb_total = total / (1024 * 1024)
        self.download_status = f"下载中: {mb_downloaded:.1f}MB / {mb_total:.1f}MB ({self.download_progress:.1f}%)"

        # 调用回调函数
        if self.callback:
            self.callback(self.download_progress, self.download_status)

        print(f"\r[下载进度] {self.download_status}", end="", flush=True)

    def download_vlc(self, progress_callback: Optional[Callable] = None) -> bool:
        """下载VLC便携包"""
        if self.is_downloading:
            self.logger.warning("VLC正在下载中...")
            return False

        self.callback = progress_callback
        self.is_downloading = True
        self.download_progress = 0
        self.download_status = "准备下载..."

        try:
            self.logger.info(f"开始下载VLC便携版: {self.vlc_download_url}")

            # 创建临时下载文件
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip', dir=self.temp_dir)
            temp_path = temp_file.name
            temp_file.close()

            # 下载文件
            response = requests.get(self.vlc_download_url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            self.logger.info(f"下载大小: {total_size / (1024 * 1024):.1f}MB")

            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        self.download_progress_callback(downloaded, total_size)

            print()  # 换行

            # 解压文件
            self.download_status = "解压中..."
            self.logger.info("解压VLC便携包...")

            if self.callback:
                self.callback(100, self.download_status)

            # 清理旧的VLC目录
            if self.vlc_dir.exists():
                shutil.rmtree(self.vlc_dir)
            self.vlc_dir.mkdir(exist_ok=True)

            # 解压到临时目录
            with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                zip_ref.extractall(self.temp_dir)

            # 移动文件到VLC目录
            extracted_folder = self.temp_dir / f"vlc-{self.VLC_LATEST_VERSION}"
            if extracted_folder.exists():
                for item in extracted_folder.iterdir():
                    shutil.move(str(item), str(self.vlc_dir))
            else:
                # 如果解压结构不同，查找vlc.exe
                vlc_exe_found = False
                for root, dirs, files in os.walk(self.temp_dir):
                    if 'vlc.exe' in files:
                        src_dir = Path(root)
                        for item in src_dir.iterdir():
                            shutil.move(str(item), str(self.vlc_dir))
                        vlc_exe_found = True
                        break

                if not vlc_exe_found:
                    raise Exception("解压文件中未找到vlc.exe")

            # 创建版本文件
            self.version_file.write_text(self.VLC_LATEST_VERSION, encoding='utf-8')

            # 清理临时文件
            os.unlink(temp_path)

            # 清理解压目录
            for item in self.temp_dir.iterdir():
                if item.is_dir() and item.name.startswith(f"vlc-{self.VLC_LATEST_VERSION}"):
                    shutil.rmtree(item)

            self.download_status = "下载完成"
            self.logger.info("VLC便携版下载安装完成")

            return True

        except Exception as e:
            self.download_status = f"下载失败: {str(e)}"
            self.logger.error(f"VLC下载失败: {e}")
            return False

        finally:
            self.is_downloading = False

    def get_vlc_path(self) -> Optional[Path]:
        """获取VLC可执行文件路径"""
        if not self.check_vlc_installed():
            return None

        vlc_exe = self.vlc_dir / "vlc.exe"
        return vlc_exe if vlc_exe.exists() else None

    def get_libvlc_path(self) -> Optional[Path]:
        """获取libvlc.dll路径"""
        if not self.check_vlc_installed():
            return None

        libvlc = self.vlc_dir / "libvlc.dll"
        return libvlc if libvlc.exists() else None

    def get_vlc_info(self) -> dict:
        """获取VLC安装信息"""
        info = {
            'installed': self.check_vlc_installed(),
            'version': None,
            'path': str(self.vlc_dir),
            'exe_path': None,
            'dll_path': None,
            'download_url': self.vlc_download_url,
            'download_size': None
        }

        if info['installed']:
            if self.version_file.exists():
                try:
                    info['version'] = self.version_file.read_text(encoding='utf-8').strip()
                except:
                    pass

            vlc_exe = self.get_vlc_path()
            if vlc_exe:
                info['exe_path'] = str(vlc_exe)

            libvlc = self.get_libvlc_path()
            if libvlc:
                info['dll_path'] = str(libvlc)
        else:
            # 获取下载大小
            info['download_size'] = self.get_download_size()

        return info

    def cleanup(self):
        """清理临时文件"""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                self.temp_dir.mkdir(exist_ok=True)
            self.logger.info("临时文件清理完成")
        except Exception as e:
            self.logger.error(f"清理临时文件失败: {e}")

def main():
    """测试VLC下载器"""
    print("VLC便携包下载管理器测试")
    print("=" * 50)

    project_root = Path(__file__).parent
    downloader = VLCDownloader(project_root)

    # 检查当前状态
    info = downloader.get_vlc_info()
    print(f"VLC状态: {'已安装' if info['installed'] else '未安装'}")

    if info['installed']:
        print(f"当前版本: {info['version']}")
        print(f"安装路径: {info['path']}")
        print(f"可执行文件: {info['exe_path']}")
        print(f"库文件: {info['dll_path']}")
    else:
        print(f"下载地址: {info['download_url']}")
        if info['download_size']:
            size_mb = info['download_size'] / (1024 * 1024)
            print(f"下载大小: {size_mb:.1f}MB")

        # 询问是否下载
        choice = input("\n是否下载VLC便携版? (y/n): ").lower()
        if choice == 'y':
            def progress_callback(progress, status):
                pass  # 控制台输出由download_progress_callback处理

            print("开始下载...")
            success = downloader.download_vlc(progress_callback)

            if success:
                print("\n✅ VLC便携版下载成功!")

                # 显示安装信息
                new_info = downloader.get_vlc_info()
                print(f"版本: {new_info['version']}")
                print(f"路径: {new_info['path']}")
                print(f"可执行文件: {new_info['exe_path']}")
            else:
                print(f"\n❌ 下载失败: {downloader.download_status}")

    print("\n测试完成")

if __name__ == "__main__":
    main()