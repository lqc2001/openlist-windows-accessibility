# OpenList Windows 音频设备切换功能使用指南

## 功能概述

OpenList Windows管理器现在支持音频播放设备的动态切换功能，允许用户在播放音频时选择不同的音频输出设备。

## 主要特性

### 1. 智能设备枚举
- 自动检测系统可用的音频输出设备
- 支持DirectSound、WASAPI等Windows音频API
- 提供设备描述信息，便于用户识别

### 2. 动态菜单系统
- 播放菜单中的"音频设备"子菜单实时显示可用设备
- 当前设备会显示✓标记
- 设备列表支持动态刷新

### 3. 状态栏集成
- 状态栏第4字段显示当前音量和设备信息
- 格式：`音量:75% [扬声器]`

### 4. 无障碍支持
- 完整的键盘导航支持
- 屏幕阅读器兼容
- 清晰的设备名称和描述

## 使用方法

### 通过菜单切换设备

1. 启动OpenList管理器
2. 点击菜单栏中的"播放(&P)"
3. 选择"音频设备(&D)"子菜单
4. 从列表中选择目标设备
5. 确认切换成功

### 设备列表说明

菜单中的设备项格式为：
- `✓ 设备名 - 设备描述`：当前选中的设备
- `设备名 - 设备描述`：其他可用设备

### 状态栏信息

状态栏第4字段显示：
- `音量:XX% [当前设备名]`

## 技术实现

### 核心组件

1. **MediaPlayerCore** (`src/media/media_player_core.py`)
   - 扩展了音频设备管理功能
   - 实现VLC音频设备枚举
   - 提供设备缓存机制

2. **AudioPlayerController** (`src/ui/audio_player_controller.py`)
   - 集成设备菜单生成
   - 处理设备切换事件
   - 更新状态栏显示

3. **MainFrame** (`src/ui/main_frame.py`)
   - 动态设备菜单初始化
   - 菜单事件绑定和处理

### 设备枚举策略

1. **VLC API优先**：尝试使用VLC的音频输出API
2. **回退方案**：如果VLC API不可用，使用预定义的常见设备列表
3. **缓存机制**：设备列表缓存30秒，提高响应速度

### 支持的设备类型

- 默认设备（系统默认音频输出）
- 扬声器（主扬声器设备）
- 耳机（耳机设备）
- 数字输出（S/PDIF数字输出）
- 其他VLC检测到的音频设备

## 配置和自定义

### 修改设备列表

可以通过修改 `MediaPlayerCore._get_fallback_devices()` 方法来自定义回退设备列表：

```python
def _get_fallback_devices(self) -> list:
    """获取回退设备列表（当VLC API不可用时）"""
    fallback_devices = [
        {
            'name': '默认设备',
            'description': '系统默认音频输出设备'
        },
        # 添加自定义设备...
    ]
    return fallback_devices
```

### 调整缓存时间

修改 `MediaPlayerCore` 中的 `device_cache_timeout` 属性：

```python
self.device_cache_timeout = 30  # 缓存30秒
```

## 故障排除

### 常见问题

1. **设备列表为空**
   - 检查VLC是否正确安装
   - 确认音频驱动程序正常工作
   - 重新启动应用程序

2. **设备切换失败**
   - 确保正在播放音频文件
   - 检查目标设备是否连接正常
   - 尝试使用"默认设备"选项

3. **菜单不显示设备**
   - 检查音频播放器是否初始化成功
   - 查看应用程序日志获取详细错误信息

### 调试模式

启用详细日志记录：

```python
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

## 开发者信息

### API接口

```python
# 获取可用设备
devices = player_core.get_available_audio_devices()

# 切换设备
success = player_core.set_audio_device("扬声器")

# 获取当前设备
current = player_core.get_current_audio_device()

# 刷新设备列表
devices = player_core.refresh_audio_devices()
```

### 事件系统

```python
# 监听设备变化事件
player_core.add_event_callback('on_audio_device_changed', callback_function)
```

## 版本信息

- **添加版本**：v1.1.0
- **最后更新**：2025年10月17日
- **兼容性**：Windows 7/8/10/11
- **VLC版本**：3.0.0+

## 注意事项

1. **VLC依赖**：功能依赖于正确安装的VLC媒体播放器
2. **媒体要求**：设备切换需要正在播放媒体文件
3. **权限要求**：可能需要管理员权限访问某些音频设备
4. **硬件兼容**：部分专业音频设备可能需要特殊驱动

---

*此功能遵循OpenList项目的无障碍设计原则，为视障用户提供完整的音频设备管理支持。*