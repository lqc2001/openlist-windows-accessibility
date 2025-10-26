# 快捷键修复与播放逻辑优化总结

## 问题描述
用户报告音频播放快捷键（播放/暂停、快进/快退、音量调节、上一曲/下一曲）无法正常工作，但菜单功能正常。后续用户希望调整播放逻辑，让回车键和快捷键有不同的行为。

## 问题根本原因分析

### 第一阶段：快捷键不工作
经过多轮分析发现了两个根本问题：

1. **事件处理逻辑不一致**：
   - 菜单调用 `_play_selected_or_current()` 方法（智能选择）
   - 快捷键直接调用 `audio_controller.play_pause()` 方法（仅控制已播放）

2. **事件绑定位置错误**：
   - 音频快捷键的事件绑定被错误地放在了 `_on_retry` 方法中
   - 只有在错误对话框出现并点击重试时才会被调用
   - 正常启动时音频快捷键根本没有被绑定

### 第二阶段：播放逻辑需求
用户希望实现更符合音乐播放器的行为：
- 回车键：播放选中的新文件（替换当前播放）
- 快捷键/菜单：控制当前播放状态（不切换到选中文件）
- 停止后播放：恢复最后通过回车键选择的文件

## 修复内容

### 1. 修复快捷键绑定位置错误
**问题**：音频快捷键绑定在 `_on_retry` 方法中
**解决**：将所有快捷键绑定移动到 `_setup_accelerators` 方法

```python
# 修复前 - 在 _on_retry 方法中（错误位置）
def _on_retry(self, dialog, retry_callback):
    # ... 错误处理代码 ...
    self.Bind(wx.EVT_MENU, self.on_play_pause_hotkey, id=wx.ID_HIGHEST + 20)
    # ... 其他音频快捷键绑定 ...

# 修复后 - 在 _setup_accelerators 方法中（正确位置）
def _setup_accelerators(self):
    # ... 设置 AcceleratorTable ...
    self.Bind(wx.EVT_MENU, self.on_play_pause_hotkey, id=wx.ID_HIGHEST + 20)
    # ... 其他快捷键绑定 ...
```

### 2. 实现播放逻辑分离
**文件**：`src/ui/file_manager_window.py`

#### 2.1 创建专门的播放控制方法
```python
def _control_current_playback(self):
    """控制当前播放（用于快捷键和菜单，不切换到选中文件）"""
    try:
        if self.audio_controller.current_file:
            # 有当前播放文件，直接控制播放/暂停
            self.audio_controller.play_pause()
            self.logger.info("控制当前播放文件")
        else:
            # 没有当前播放文件，优先播放最后选择的文件
            # ... 智能恢复逻辑 ...
    except Exception as e:
        self.logger.error(f"播放控制失败: {e}")
```

#### 2.2 添加文件记忆功能
```python
# 在 __init__ 中添加
self._last_selected_file = None  # 记住最后通过回车键选择的文件

# 在 _play_media_file 中记录
def _play_media_file(self, file_item):
    # ... 播放逻辑 ...
    if media_type == 'audio':
        # ... 播放文件 ...
        # 记住最后通过回车键选择的文件
        self._last_selected_file = file_item
        self.logger.info(f"已记住最后选择的文件: {file_item['name']}")
```

#### 2.3 修改快捷键和菜单事件
```python
def on_play_pause_hotkey(self, event):
    """播放/暂停快捷键事件"""
    self.logger.info("播放/暂停快捷键被触发")
    # 只控制当前播放，不切换到选中文件
    self._control_current_playback()

def on_play_pause(self, event):
    """播放/暂停菜单事件"""
    # 只控制当前播放，不切换到选中文件
    self._control_current_playback()
```

### 3. 添加调试日志
为所有关键操作添加了调试日志：

```python
# 快捷键触发日志
def on_play_pause_hotkey(self, event):
    self.logger.info("播放/暂停快捷键被触发")

# 文件选择记录日志
def _play_media_file(self, file_item):
    self.logger.info(f"已记住最后选择的文件: {file_item['name']}")

# 播放恢复日志
def _control_current_playback(self):
    self.logger.info(f"恢复播放最后选择的文件: {target_file['name']}")
```

### 4. 修复事件处理冲突
修改 `on_char` 方法，确保事件正确传播：

```python
def on_char(self, event):
    """键盘事件处理"""
    key_code = event.GetKeyCode()

    # 空格键 - 播放/暂停（仅在文件列表有焦点时生效）
    if key_code == wx.WXK_SPACE and self.file_list_ctrl.HasFocus():
        self._handle_space_key_playback()
        return  # 不继续处理事件

    # 退格键 - 返回上级目录
    if key_code == wx.WXK_BACK:
        self._go_back()
        return  # 不继续处理事件

    # 对于其他按键，让事件继续传播到快捷键处理
    event.Skip()
```

## 新的播放逻辑

### 🎯 行为定义

1. **回车键/双击**：
   - 总是播放选中的新文件（替换当前播放）
   - 记住这个选择，用于停止后的恢复
   - 用于主动切换要播放的文件

2. **快捷键/菜单（Ctrl+Home、空格键等）**：
   - 只控制当前播放状态
   - 不会自动切换到选中的文件
   - 用于播放控制（播放/暂停/停止等）

3. **停止后的行为**：
   - 优先恢复最后通过回车键选择的文件
   - 如果没有回车选择的文件，自动播放第一个音频文件
   - 不会自动切换到当前选中的文件

### 📋 测试场景

| 操作序列 | 预期行为 |
|---------|---------|
| 选择文件A，回车播放 | 播放文件A，记住A |
| 选择文件B，按快捷键 | 继续播放文件A（不切换） |
| 停止播放，按快捷键 | 恢复播放文件A |
| 选择文件C，回车播放 | 停止A，播放C，记住C |
| 选择文件D，停止，按快捷键 | 恢复播放文件C |

## 快捷键列表
- **空格键**：播放/暂停（控制当前播放）
- **Ctrl+Home**：播放/暂停（控制当前播放）
- **Ctrl+End**：停止播放
- **Ctrl+PageUp**：上一曲
- **Ctrl+PageDown**：下一曲
- **Ctrl+Left**：快退5秒
- **Ctrl+Right**：快进5秒
- **Ctrl+Up**：音量增加
- **Ctrl+Down**：音量减少
- **回车键**：播放选中的新文件
- **双击**：播放选中的新文件

## 测试工具
创建了多个测试脚本：

1. **`test_shortcuts.py`**：基础快捷键测试
2. **`debug_shortcuts.py`**：快捷键调试工具
3. **`test_playback_logic.py`**：播放逻辑测试
4. **`test_fixed_playback.py`**：修复后功能验证

## 技术细节
- **修复文件**：`src/ui/file_manager_window.py`
- **核心修改**：
  - 第55行：添加 `_last_selected_file` 变量
  - 第229-251行：修复快捷键事件绑定位置
  - 第1305-1349行：新增播放控制逻辑
  - 第1513行：添加文件选择记录
- **兼容性**：保持所有现有功能完整性
- **性能影响**：最小，仅增加少量日志和变量存储

## 调试功能
添加了多层调试信息：
- 快捷键初始化日志
- 键盘事件捕获日志
- 快捷键触发日志
- 文件选择记录日志
- 播放恢复日志

---
**修复完成时间**：2025年10月26日
**主要修复文件**：`src/ui/file_manager_window.py`
**测试工具**：`test_shortcuts.py`, `debug_shortcuts.py`, `test_playback_logic.py`, `test_fixed_playback.py`