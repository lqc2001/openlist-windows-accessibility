# VLC内置集成使用指南

本文档介绍如何使用VLC内置集成功能，为OpenList管理工具提供完整的媒体播放支持。

## 概述

VLC内置集成系统允许应用程序自动加载和管理VLC库，支持以下特性：

- **零依赖部署**：VLC库完全内置，用户无需额外安装
- **智能加载**：自动选择最佳VLC源（内置 → 程序目录 → 系统）
- **降级处理**：优雅处理VLC不可用的情况
- **架构支持**：支持64位VLC库

## 目录结构

```
E:\openlist-windows\
├── src/
│   ├── media/
│   │   ├── vlc_embedded_manager.py  # VLC内置管理器
│   │   ├── vlc_loader.py             # VLC加载器（升级版）
│   │   └── vlc_runtime/              # VLC运行时库目录
│   │       ├── lib/                  # VLC核心库
│   │       │   ├── libvlc.dll
│   │       │   ├── libvlccore.dll
│   │       │   └── plugins/          # VLC插件
│   │       └── README.md             # 说明文档
│   └── ...
├── tools/
│   └── vlc_packager.py               # VLC库打包工具
└── docs/
    └── VLC_INTEGRATION_GUIDE.md      # 本文档
```

## 使用方法

### 1. 获取VLC库文件

#### 方法A：使用打包工具（推荐）

```bash
# 下载并打包VLC库
cd tools
python vlc_packager.py

# 或者指定已有的VLC目录
python vlc_packager.py --no-download --vlc-source "C:\path\to\vlc"
```

#### 方法B：手动复制

1. 下载VLC便携版（推荐3.0.20 LTS版本）
2. 复制以下文件到 `src/media/vlc_runtime/lib/`：
   - `libvlc.dll`
   - `libvlccore.dll`
3. 复制 `plugins/` 目录到 `src/media/vlc_runtime/lib/`

### 2. 验证安装

```bash
# 运行测试脚本
python test_embedded_vlc.py
```

预期输出：
```
开始内置VLC集成测试
==================================================
[OK] VLC内置管理器初始化
   架构: x64, 目录: src\media\vlc_runtime
[OK] VLC可用性检查
   内置VLC库检查通过 - 120个插件
[OK] 环境变量设置
   VLC_PLUGIN_PATH: src\media\vlc_runtime\lib\plugins
[OK] 库文件完整性
   libvlc.dll 文件正常 (15.2 MB)
[OK] 版本信息获取
   Python: 3.13.7, 架构: x64
[OK] 加载准备
   内置可用: True
[OK] VLC加载器基本功能
   偏好内置: True
[OK] 加载信息获取
   已加载: True, 来源: 内置库
[OK] 内置可用性检查
   内置VLC库可用
[OK] VLC功能测试
   版本: 3.0.20

==================================================
测试完成: 11/11 通过
```

### 3. 在代码中使用

#### 基本使用

```python
from media.vlc_loader import VLCLoader

# 创建VLC加载器（优先使用内置库）
loader = VLCLoader(prefer_embedded=True)

if loader.is_vlc_available():
    # 获取VLC实例
    vlc_instance = loader.get_vlc_instance()

    # 获取版本信息
    version = loader.get_vlc_version()
    print(f"VLC版本: {version}")

    # 获取加载信息
    load_info = loader.get_load_info()
    print(f"加载来源: {load_info['load_source']}")
else:
    print("VLC不可用")
```

#### 高级使用

```python
from media.vlc_embedded_manager import get_vlc_embedded_manager

# 获取VLC管理器
manager = get_vlc_embedded_manager()

# 检查可用性
available, message = manager.check_embedded_vlc_availability()

if available:
    # 准备加载
    success, config = manager.prepare_for_loading()
    if success:
        print("VLC准备就绪")
        print(f"版本信息: {config['version_info']}")
```

## 配置选项

### VLC加载器选项

```python
# 创建加载器时指定选项
loader = VLCLoader(prefer_embedded=True)  # 优先使用内置库

# 强制使用内置VLC
success = loader.force_load_embedded()

# 重新加载VLC
success = loader.reload_vlc(prefer_embedded=True)
```

### 内置管理器选项

```python
manager = get_vlc_embedded_manager()

# 检查可用性
available, message = manager.check_embedded_vlc_availability()

# 验证库完整性
integrity_ok, integrity_message = manager.verify_library_integrity()

# 获取版本信息
version_info = manager.get_version_info()
```

## 故障排除

### 常见问题

#### 1. "缺少必需的库文件"

**问题**：测试显示缺少 `libvlc.dll` 或 `libvlccore.dll`

**解决方案**：
```bash
# 使用打包工具重新打包
cd tools
python vlc_packager.py --clean
python vlc_packager.py
```

#### 2. "插件文件数量不足"

**问题**：插件文件少于20个

**解决方案**：
- 确保复制了完整的 `plugins/` 目录
- 使用打包工具自动提取必要的插件

#### 3. "VLC不可用"

**问题**：VLC加载失败

**解决方案**：
```python
# 检查加载信息
loader = VLCLoader()
load_info = loader.get_load_info()
print(f"加载状态: {load_info}")

# 尝试不同的加载策略
loader.reload_vlc(prefer_embedded=False)  # 优先使用系统VLC
```

#### 4. 环境变量问题

**问题**：VLC插件路径未设置

**解决方案**：
```python
# 手动设置环境变量
import os
vlc_plugins_path = "src/media/vlc_runtime/lib/plugins"
os.environ['VLC_PLUGIN_PATH'] = vlc_plugins_path
```

### 调试方法

#### 启用详细日志

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 然后运行VLC相关代码
loader = VLCLoader()
```

#### 检查加载状态

```python
loader = VLCLoader()
load_info = loader.get_load_info()

print("VLC加载状态:")
for key, value in load_info.items():
    print(f"  {key}: {value}")
```

#### 验证文件完整性

```python
from media.vlc_embedded_manager import get_vlc_embedded_manager

manager = get_vlc_embedded_manager()

# 检查可用性
available, message = manager.check_embedded_vlc_availability()
print(f"可用性: {available}, 详情: {message}")

# 验证完整性
integrity_ok, integrity_message = manager.verify_library_integrity()
print(f"完整性: {integrity_ok}, 详情: {integrity_message}")
```

## 性能优化

### 内存使用

- VLC库加载后占用约50-100MB内存
- 建议在程序启动时加载，避免重复加载

### 启动速度

- 内置VLC库启动速度与系统VLC相当
- 首次加载可能需要1-3秒，后续加载较快

### 文件大小

- 完整的VLC库约100-150MB
- 可以通过删除不需要的插件来减少大小

## 打包部署

### PyInstaller配置

```python
# build.spec
a = Analysis(
    ['src/main.py'],
    datas=[
        ('src/media/vlc_runtime/**', 'media/vlc_runtime'),
    ],
    # ... 其他配置
)
```

### 构建脚本

```python
# tools/build.py
import subprocess
import os
import shutil

def build_with_embedded_vlc():
    # 1. 确保VLC库存在
    if not os.path.exists('src/media/vlc_runtime/lib/libvlc.dll'):
        print("VLC库不存在，正在打包...")
        subprocess.run(['python', 'tools/vlc_packager.py'])

    # 2. 构建应用程序
    subprocess.run(['pyinstaller', 'build.spec'])

    print("构建完成")

if __name__ == "__main__":
    build_with_embedded_vlc()
```

## 版本管理

### VLC版本

- 推荐使用VLC 3.0.20 LTS版本
- 可以通过修改 `vlc_packager.py` 中的版本号来更新

### 更新流程

1. 更新 `vlc_packager.py` 中的版本号
2. 运行打包工具下载新版本
3. 测试兼容性
4. 更新文档

## 技术细节

### 加载优先级

1. **内置VLC库**（最高优先级）
2. **程序目录VLC**
3. **系统安装VLC**
4. **降级处理**

### 环境变量

- `VLC_PLUGIN_PATH`：VLC插件目录
- `PATH`：添加VLC库目录

### 架构支持

- 目前支持Windows x64
- 可以扩展支持Linux和macOS

## 许可证

VLC使用GPLv2许可证，集成VLC库时需要遵守相关许可证要求。

## 支持和反馈

如果遇到问题或需要帮助，请：

1. 查看本文档的故障排除部分
2. 运行测试脚本获取详细信息
3. 检查日志输出
4. 提交问题报告

---

*本文档随VLC集成功能的更新而维护*