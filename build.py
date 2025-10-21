#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenList Windows管理工具打包脚本
使用PyInstaller打包为单文件可执行程序
"""

import os
import sys
import subprocess
import shutil
import zipfile
from datetime import datetime


def check_dependencies():
    """检查依赖项"""
    print("检查依赖项...")

    required_packages = [
        "wxPython",
        "requests",
        "cryptography",
        "PyInstaller"
    ]

    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✓ {package} 已安装")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package} 未安装")

    if missing_packages:
        print(f"正在安装缺失的包: {', '.join(missing_packages)}")
        for package in missing_packages:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print("依赖项安装完成")

    return True


def run_tests():
    """运行测试"""
    print("运行基本功能测试...")

    try:
        result = subprocess.run([
            sys.executable, "test_basic_functionality.py"
        ], capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            print("✓ 所有测试通过")
            return True
        else:
            print("✗ 测试失败")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False

    except subprocess.TimeoutExpired:
        print("✗ 测试超时")
        return False
    except Exception as e:
        print(f"✗ 测试执行失败: {e}")
        return False


def clean_build():
    """清理构建目录"""
    print("清理构建目录...")

    dirs_to_clean = ["build", "dist", "__pycache__"]
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"  已清理: {dir_name}")

    # 清理Python缓存文件
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".pyc") or file.endswith(".pyo"):
                os.remove(os.path.join(root, file))

    print("清理完成")


def create_spec_file():
    """创建PyInstaller规格文件"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config', 'config'),
        ('resources', 'resources') if os.path.exists('resources') else None,
    ],
    hiddenimports=[
        'wx',
        'wx.lib.agw.aui',
        'wx.lib.scrolledpanel',
        'requests',
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.kdf.pbkdf2',
        'cryptography.hazmat.primitives.hashes',
        'urllib3.util.retry',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 过滤掉None值
a.datas = [item for item in a.datas if item]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='OpenList管理器',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icons/app.ico' if os.path.exists('resources/icons/app.ico') else None,
    version='version_info.txt' if os.path.exists('version_info.txt') else None,
)
'''

    with open("OpenListManager.spec", "w", encoding="utf-8") as f:
        f.write(spec_content)

    print("已创建PyInstaller规格文件")


def create_version_info():
    """创建版本信息文件"""
    version_info = '''# UTF-8
#
# 版本信息文件
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'080404B0',
        [StringStruct(u'CompanyName', u'OpenList Manager Team'),
        StringStruct(u'FileDescription', u'OpenList服务器管理工具'),
        StringStruct(u'FileVersion', u'1.0.0.0'),
        StringStruct(u'InternalName', u'OpenListManager'),
        StringStruct(u'LegalCopyright', u'Copyright (C) 2024 OpenList Manager Team'),
        StringStruct(u'OriginalFilename', u'OpenList管理器.exe'),
        StringStruct(u'ProductName', u'OpenList管理器'),
        StringStruct(u'ProductVersion', u'1.0.0.0')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [2052, 1200])])
  ]
)
'''

    with open("version_info.txt", "w", encoding="utf-8") as f:
        f.write(version_info)

    print("已创建版本信息文件")


def build_executable():
    """打包可执行文件"""
    print("开始打包OpenList管理器...")

    # 创建规格文件和版本信息
    create_spec_file()
    create_version_info()

    # 打包命令
    cmd = [
        "pyinstaller",
        "--clean",
        "--noconfirm",
        "OpenListManager.spec"
    ]

    print("执行打包命令...")
    print(f"命令: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✓ 打包成功")

        # 检查输出文件
        exe_path = os.path.join("dist", "OpenList管理器.exe")
        if os.path.exists(exe_path):
            file_size = os.path.getsize(exe_path) / (1024 * 1024)  # MB
            print(f"✓ 可执行文件已生成: {os.path.abspath(exe_path)}")
            print(f"✓ 文件大小: {file_size:.1f} MB")
            return True
        else:
            print("✗ 可执行文件未找到")
            return False

    except subprocess.CalledProcessError as e:
        print(f"✗ 打包失败: {e}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False


def create_release_package():
    """创建发布包"""
    print("创建发布包...")

    release_dir = f"OpenList管理器_v1.0.0_{datetime.now().strftime('%Y%m%d')}"
    os.makedirs(release_dir, exist_ok=True)

    # 复制可执行文件
    exe_source = os.path.join("dist", "OpenList管理器.exe")
    exe_dest = os.path.join(release_dir, "OpenList管理器.exe")
    if os.path.exists(exe_source):
        shutil.copy2(exe_source, exe_dest)
        print(f"✓ 已复制可执行文件")

    # 创建便携版说明文件
    readme_content = """OpenList管理器 v1.0.0 便携版

这是一个便携版程序，无需安装即可使用。

使用方法：
1. 双击 "OpenList管理器.exe" 启动程序
2. 首次运行会自动创建配置文件目录
3. 通过菜单或工具栏添加OpenList服务器配置
4. 连接到服务器后可以进行用户管理

目录说明：
- config/: 配置文件目录（自动创建）
- logs/: 日志文件目录（自动创建）
- cache/: 缓存文件目录（自动创建）
- tmp/: 临时文件目录（自动创建）

注意事项：
- 程序支持NVDA屏幕阅读器
- 支持键盘导航（Tab键和快捷键）
- 密码采用加密存储
- 支持自签名HTTPS证书

技术支持：
- 项目主页: https://github.com/your-repo/openlist-windows
- 问题反馈: https://github.com/your-repo/openlist-windows/issues

版权信息：
Copyright (C) 2024 OpenList Manager Team
"""

    with open(os.path.join(release_dir, "README.txt"), "w", encoding="utf-8") as f:
        f.write(readme_content)

    # 创建启动脚本
    bat_content = """@echo off
echo 启动OpenList管理器...
start "" "OpenList管理器.exe"
"""

    with open(os.path.join(release_dir, "启动.bat"), "w", encoding="gbk") as f:
        f.write(bat_content)

    print(f"✓ 发布包已创建: {release_dir}")

    # 压缩发布包
    zip_filename = f"{release_dir}.zip"
    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(release_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, release_dir)
                zipf.write(file_path, arcname)

    zip_size = os.path.getsize(zip_filename) / (1024 * 1024)  # MB
    print(f"✓ 压缩包已创建: {zip_filename}")
    print(f"✓ 压缩包大小: {zip_size:.1f} MB")

    return True


def main():
    """主函数"""
    print("OpenList管理器打包脚本")
    print("=" * 50)

    # 检查依赖
    if not check_dependencies():
        print("✗ 依赖检查失败")
        return False

    # 运行测试
    if not run_tests():
        print("⚠ 测试未通过，但继续打包...")

    # 清理
    clean_build()

    # 打包
    if not build_executable():
        print("✗ 打包失败")
        return False

    # 创建发布包
    if not create_release_package():
        print("✗ 创建发布包失败")
        return False

    print("=" * 50)
    print("✓ 打包完成！")
    print("发布包已准备就绪，可以进行分发。")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)