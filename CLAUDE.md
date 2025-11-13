# OpenList Windows Management Tool – Developer Guide (Claude Edition)

> Keep the codebase accessibility-first while refining the audio experience. This guide summarizes coding standards, shortcut contracts, and regression checks. Treat it as the living reference before shipping changes.

---

## 1. Project Overview
- **Tech stack**: wxPython, requests, python-vlc, cryptography, pypinyin
- **Focus**: Screen-reader friendly UI, full keyboard navigation, integrated audio playback with device selection, secure configuration management, Chinese localization
- **Architecture**: Layered architecture with modular design, event-driven patterns, and intelligent caching
- **Directory layout**
  ```text
  src/
    ui/               # windowing & interaction (main_frame, file_manager_window, dialogs, video_player_window)
    media/            # VLC wrapper and playback control (audio_player, media_player_core, vlc_loader, video_player)
    core/             # logging, configuration, utilities (logger, config_manager, version)
    api/              # OpenList API client (openlist_client)
    accessibility/    # light-weight accessibility helpers (future expansion)
  ```

### 1.1 Key Features
- **File Management**: Smart directory navigation with position memory, intelligent error handling, and Chinese pinyin sorting
- **File Type Handling**: API-driven file type detection with appropriate actions for audio, video, images, text, and other files
- **Audio Integration**: Built-in VLC-based media player with device selection and audio track switching
- **Video Integration**: Complete video player with audio track switching, menu controls, and accessibility support
- **Security**: Encrypted server configurations with secure key management
- **Accessibility**: Complete keyboard navigation and screen reader support
- **Logging**: Silent-by-default logging with environment variable control
- **Error Handling**: User-friendly error dialogs with retry functionality and specific API error messages
- **Chinese Localization**: Pinyin-based file name sorting for Chinese users

---

## 2. Accessibility & Interaction Guidelines
### 2.1 Principles
- **Native first** – rely on wxPython’s built-in accessibility facilities.  
- **Keyboard reachable** – every feature must expose a keyboard path (Tab order or shortcut).  
- **Clear naming** – call `SetName` and `SetHelpText` for every interactive control to describe function and shortcut.  
- **Screen reader parity** – periodically test with NVDA/Narrator to verify announcement order.

### 2.2 Layout & Tab Flow
1. Embed groups of controls within `wx.Panel` instances.  
2. Keep the creation order in line with logical Tab navigation; avoid manual Tab-index tweaks.  
3. Split complex areas into multiple panels to maintain predictable focus moves.

### 2.3 Do / Don’t
| ✅ Do | ❌ Don’t |
| --- | --- |
| Use wxPython native accessibility | Build custom accessibility frameworks |
| Keep controls enabled for Tab navigation | Trap or override Tab key handling |
| Provide concise, descriptive captions | Add chatty or flashy voice prompts |
| Use `Alt+letter`, `Ctrl+combo` accelerators | Bind Tab shortcuts in menus |

---

## 3. Directory Navigation Implementation Notes
1. **Smart History Stack** – use path-verified navigation history (`_navigation_history`) to store file lists and selected positions.
2. **Auto-select First Item** – when entering a new directory, automatically select and focus the first item (`_auto_select_first_item()`).
3. **Position Memory** – returning to parent directories restores the exact previous selection and scroll position.
4. **Focus Management** – complete focus state includes selection, keyboard focus, and visibility (`_select_file_index()`).
5. **Empty Directory Handling** – set focus to list control without selecting any item when directory is empty.
6. **Load Failure Recovery** – preserve current selection state when directory loading fails.
7. **Refresh Behavior** – F5 refresh reloads current directory and selects first item.

### 3.1 Navigation History Stack Architecture
- **Structure**: Each entry contains `{'path': str, 'files': list, 'selected_index': int}`
- **Validation**: Path verification prevents stale history restoration
- **Size Limit**: No size limit (cleared on program exit)
- **Save Point**: `_save_current_state_to_history()` called before navigation
- **Restore Point**: `_try_restore_from_history()` called on back navigation

### 3.2 Chinese Pinyin Sorting Implementation
The application provides intelligent file name sorting optimized for Chinese users using pinyin-based ordering.

#### 3.2.1 Pinyin Sorting Architecture
- **Library**: Uses `pypinyin` library for Chinese character to pinyin conversion
- **Implementation**: `FileListCtrl.load_files()` applies automatic pinyin sorting
- **Scope**: Applied to all file listings except history stack restorations
- **Consistency**: Ensures uniform sorting behavior across all directories

#### 3.2.2 Sorting Logic
```python
def chinese_sort_key(name):
    """Convert Chinese filenames to pinyin for sorting"""
    pinyin_list = pypinyin.lazy_pinyin(name)
    return ''.join(pinyin_list)

# Applied during file loading
self.files.sort(key=lambda x: chinese_sort_key(x["name"]))
```

#### 3.2.3 Sorting Behavior
- **New Directory Entry**: Automatic pinyin sorting applied on first load
- **Manual Sorting**: Menu options for name, size, and date sorting with toggle capability
- **History Stack Restoration**: Preserves original sorted order without re-sorting
- **Mixed Content**: Handles Chinese, English, numbers, and special characters uniformly

#### 3.2.4 User Experience
- **Intuitive Ordering**: Files are sorted alphabetically by pinyin (e.g., 北京(B) < 上海(S) < 张三(Z))
- **Cultural Consistency**: Follows Chinese user expectations for alphabetical ordering
- **Performance**: Fast sorting with minimal overhead for typical file lists
- **Reliability**: Consistent behavior across all directory operations

#### 3.2.5 Menu Integration
- **View Menu**: Access to sorting options (View → Sort by Name/Size/Date)
- **Keyboard Support**: Alt+V shortcuts for menu navigation
- **Toggle Functionality**: Each click switches between ascending/descending order
- **Visual Feedback**: Current sort method indicated in menu state

### 3.3 Error Handling Implementation Notes
1. **No Mock Data** – API failures never return simulated files or example data; failures are transparent to users.
2. **User-Friendly Dialogs** – API errors display modal dialogs with specific error messages and retry functionality.
3. **Retry Mechanism** – Error dialogs include "重试" (Retry) and "确定" (OK) buttons; "确定" is the default button.
4. **Window-Level Modality** – Error dialogs are window-modal, allowing audio playback to continue uninterrupted.
5. **Screen-Center Display** – Error dialogs appear centered on screen with error icons and proper accessibility labels.
6. **Empty List on Failure** – When file loading fails, the list displays blank instead of showing mock data.
7. **Auto-Retry Preservation** – Built-in HTTP-level retry mechanisms (3x for connections, 3x for authentication) are preserved.
8. **Specific Error Messages** – Dialogs display the actual API error message without modification or filtering.

---

## 4. File Type Handling Implementation Notes

### 4.1 API-Driven File Type Detection
The application uses OpenList API responses to determine file types, not filename extensions. The API returns a `type` field (integer) that gets mapped to mime_type strings:

```python
type_mapping = {
    0: 'file',        # Regular file
    1: 'folder',      # Directory
    2: 'video',       # Video file
    3: 'audio',       # Audio file
    4: 'text',        # Text document
    5: 'image'        # Image file
}
```

### 4.2 File Type Processing Logic

#### 4.2.1 Main Entry Point
The `_open_file()` method in `FileManagerWindow` handles all file opening based on API-returned `mime_type`:

- **Audio files** (`mime_type == 'audio'`): Use existing `AudioPlayerController` for playback
- **Video files** (`mime_type == 'video'`): Show development dialog, then open in browser
- **Image files** (`mime_type == 'image'`): Open directly in browser
- **Text documents** (`mime_type == 'text'`): Show development dialog, then open in browser
- **Other files** (`mime_type == 'file'` or unknown): Open directly in browser

#### 4.2.2 Development Dialog Pattern
For features under development (video playback, text document viewing), the application uses `_show_development_dialog()`:

```python
def _show_development_dialog(self, feature_name, file_item):
    """Display development-in-progress dialog"""
    dialog = wx.MessageDialog(
        self,
        f"{feature_name}功能正在开发中，敬请期待！\n\n当前将使用网页方式打开。",
        feature_name,
        wx.OK | wx.ICON_INFORMATION
    )
    dialog.ShowModal()
    dialog.Destroy()
```

#### 4.2.3 Web Browser Opening
The `on_context_web_open()` method handles browser-based file opening:
- Constructs URL from server URL, port, current path, and filename
- Uses `webbrowser.open()` to launch default browser
- Handles URL encoding for special characters
- Logs success/failure appropriately

### 4.3 File Type Handling Guidelines

1. **API-First Approach**: Always use API-returned `mime_type`, never file extensions
2. **User-Friendly Fallbacks**: For unsupported file types, fall back to browser opening
3. **Progressive Enhancement**: Show development dialogs for future functionality
4. **Consistent Logging**: Log file type information for debugging: `f"准备打开文件: {file_item['name']} (类型: {file_item['mime_type']})"`
5. **Error Handling**: Gracefully handle failed file operations with user feedback

### 4.4 Integration Points

- **File Selection**: `on_item_activated()` calls `_open_file()` on Enter/Double-click
- **Right-Click Menu**: Context menu provides additional file operations
- **Keyboard Shortcuts**: Ctrl+W for web open, O for open, consistent with existing patterns
- **Navigation**: File type processing doesn't interrupt directory navigation or audio playback

---

## 5. Audio Playback Implementation Notes
1. **File detection** – always use `MediaFileDetector` to identify playable items.
2. **Single controller** – UI code should speak only to `AudioPlayerController`.
3. **State sync** – update status bar, selected list item, and controller state together (`_select_file_index` is the helper).
4. **Pause semantics** – `AudioPlayerController.play_pause()` returns `False` when nothing is playing/paused; never reload media inside that method.
5. **Shortcut parity** – Space bar and `Ctrl+Home` call the same pause/resume logic; when nothing is playing the UI just reports "no active audio".
6. **VLC management** – let `MediaPlayerCore` manage instance reuse, device enumeration, and teardown; no raw VLC calls in UI.
7. **Error feedback** – log failures and surface them via the status bar instead of modal dialogs.
8. **Device persistence** – cache the selected audio device and call `_apply_audio_device()` before each play/resume; the `MediaPlayerPlaying` hook re-applies the device because LibVLC rebuilds the output chain after `stop()`.
9. **Navigation Independence** – directory navigation does not interrupt active audio playback.
10. **Status Bar Dedication** – the status bar is exclusively dedicated to audio playback functionality with 5 fields: playback status, time progress, percentage, volume/device, and playback rate. No non-audio information should be displayed in the status bar.

---

## 6. Video Playback Implementation Notes
1. **Full-Screen Architecture** – VideoPlayerWindow creates a dedicated full-screen window for video playback with comprehensive menu controls.
2. **Audio Interruption** – Video playback automatically stops any active audio playback and manages state transitions.
3. **Menu System** – Replicates audio player's complete menu structure with video-specific controls and audio track switching.
4. **Audio Track Support** – Complete audio track detection, switching, and management with multi-language support.
   - **Track Detection**: Automatically detects audio tracks after video starts playing (2-second delay for VLC parsing)
   - **Menu Integration**: Dynamic audio track menu under "播放(&P)" → "音轨(&T)" with real-time updates
   - **Track Types**: Supports multiple audio formats, language identification, and track metadata
   - **Screen Reader Support**: Audio track names are properly formatted for screen readers (e.g., "轨道 1 - [中文]")
   - **Refresh Capability**: Manual refresh option when track detection fails or tracks become available
   - **Current Track Indication**: Visual checkmarks indicate active audio track in menu
5. **State Management** – Proper coordination between video and audio playback states, preventing conflicts.
6. **Accessibility** – Full keyboard navigation, screen reader support, and menu accessibility compliance.
7. **Error Handling** – Graceful error handling for media loading, playback issues, and menu operations.
8. **Title Display** – Shows original video filename in window title with playback status and time information.
9. **Progress Tracking** – Real-time progress display with time formatting and seek functionality.
10. **Clean Exit** – Proper resource cleanup and state restoration when closing video windows.

---

## 5. Shortcut Contracts
### 5.1 General
- `Alt+letter` — primary actions in menus/dialogs  
- `Ctrl+Tab` — switch panes  
- `Alt+F4` — exit  
- `F1` — help

### 5.2 File Navigation (global)
- `Backspace` — go to parent directory (restores previous selection)
- `Enter` or `Double-click` — enter selected folder or open selected file
- `F5` — refresh current directory and select first item

### 5.3 Audio Playback (global)
- `Ctrl+Home` — pause/resume current playback (controls current playing file, not selected)
- `Ctrl+End` — stop playback and clear the active file reference
- `Ctrl+PageUp / PageDown` — previous / next track
- `Ctrl+Left / Right` — seek backward / forward
- `Ctrl+Up / Down` — volume up / down
- `Space` — identical to `Ctrl+Home`; works regardless of focus location
- **Fallback behavior**: if no current file, shortcuts will resume playing the last selected file via Enter, or automatically play the first audio file in the directory. Status bar is managed exclusively by AudioPlayerController.

### 5.4 Video Playback (full-screen mode)
- `Space` — play/pause video playback
- `ESC` — exit video player and return to file browser
- `Left / Right` — seek backward/forward 10 seconds
- `Up / Down` — volume up/down
- `F` — toggle fullscreen mode
- `Alt+P` — show/hide menu with full video controls
- **Audio Track Switching**: Alt+P → 音轨(T) → select track (multi-language videos only)

### 5.5 File Selection vs Playback Control
- **Enter / Double-click** — play selected file (replaces current playback and remembers selection)
- **Audio shortcuts** — control current playback only (does not switch to selected file)
- **After stopping** — shortcuts resume playing the last file selected via Enter
- **Smart recovery** — if no file was ever selected via Enter, automatically plays first audio file in directory

---

## 6. Coding Standards
- Class names use **PascalCase**; functions & variables use **snake_case**; constants use **UPPER_SNAKE_CASE**.
- Every non-trivial method should include a short docstring with intent and caveats.
- Logging goes through `get_logger()`; never use `print`.
- API interaction funnels through `OpenListClient`; avoid stray `requests` calls.

### 6.1 Security Guidelines
- **Configuration Encryption**: Use `ConfigManager` for all server configuration storage.
- **Password Handling**: Never log passwords or sensitive configuration data.
- **Key Management**: Let `ConfigManager` handle key generation and rotation automatically.
- **API Security**: Use `OpenListClient` for all network operations; includes path validation and SSL verification.

### 6.2 User Authentication and Path Management
- **User Information Retrieval**: After successful login, automatically call `/api/me` to retrieve user information including `base_path`.
- **Dynamic Path Construction**: Playback URLs are constructed using `user_base_path + current_browsing_path + filename` instead of hardcoded paths.
- **Path Storage**: User information is stored in `OpenListClient.user_info` for the duration of the session.
- **Error Handling**: If user information retrieval fails, login is cancelled and user is prompted to retry.
- **URL Building**: The final playback path follows the pattern: `{user_base_path}{relative_file_path}` and is encoded for URL safety.

#### 6.2.1 User Information Structure
```python
user_info = {
    'id': user_id,
    'username': username,
    'base_path': '/user/username/',  # User's base storage path
    'role': role,
    'permissions': [],
    # ... other fields
}
```

#### 6.2.2 Playback URL Construction
1. **Login Phase**:
   - Call `/api/auth/login` with credentials
   - If successful, call `/api/me` to get user info
   - Store `base_path` from user info

2. **Playback Phase**:
   - Get current browsing path from `self.current_path`
   - Get filename from selected file item
   - Construct: `{base_path}{current_path}/{filename}`
   - Remove leading `/` for URL encoding
   - Build final URL: `{server_url}/d/{encoded_path}?sign={signature}`

### 6.3 Logging System Guidelines
- **Default behavior**: Logging is completely disabled by default for silent operation.
- **Enable logging**: Set environment variable `OPENLIST_LOG_LEVEL=on` to enable full debug logging.
- **Log levels**: Can be set to `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`, or `on` (full debug).
- **Console output**: Optional `OPENLIST_CONSOLE_LEVEL` for separate console log control.
- **Usage**: All logging must use `get_logger()` from `core.logger`; no direct `logging` module calls.
- **File location**: Logs are written to `logs/debug_YYYYMMDD.log` when enabled.

---

## 7. Regression Checklist (run before commit)
### 7.1 Core UX
- [ ] Application launches without errors.  
- [ ] Tab navigation covers all controls in logical order.  
- [ ] Screen reader announces names/help texts correctly.  
- [ ] Menu items and buttons include shortcut hints.

### 7.2 Directory Navigation
- [ ] Entering a directory automatically selects the first item.
- [ ] Backspace returns to parent directory and restores previous selection.
- [ ] F5 refresh reloads current directory and selects first item.
- [ ] Empty directories focus list control without selecting items.
- [ ] Navigation history correctly stores and restores positions.
- [ ] Directory switching doesn't interrupt audio playback.

### 7.2.1 Chinese Pinyin Sorting
- [ ] New directories automatically apply pinyin sorting to file listings.
- [ ] Chinese filenames are sorted alphabetically by pinyin (北京 < 上海 < 张三).
- [ ] Mixed content (Chinese, English, numbers) sorts correctly and intuitively.
- [ ] Manual sorting via View menu works correctly with ascending/descending toggle.
- [ ] History stack restoration maintains consistent sorting behavior.
- [ ] All directories show consistent pinyin-based ordering regardless of navigation path.

### 7.3 Error Handling
- [ ] API failures display error dialogs with specific error messages.
- [ ] Error dialogs show both "重试" (Retry) and "确定" (OK) buttons.
- [ ] Error dialogs are centered on screen with proper error icons.
- [ ] File list shows blank when loading fails, no mock data appears.
- [ ] Retry button successfully reloads the file list.
- [ ] Error dialogs are window-modal and don't interrupt audio playback.
- [ ] "确定" button is the default button (activated with Enter key).
- [ ] All controls in error dialogs have proper accessibility labels.

### 7.4 User Authentication and Dynamic Paths
- [ ] Login process automatically retrieves user information via `/api/me`.
- [ ] User base path is correctly stored and used for URL construction.
- [ ] Playback URLs are built using `user_base_path + current_browsing_path + filename`.
- [ ] If user info retrieval fails, login is properly cancelled with error message.
- [ ] Dynamic path construction works for both root and subdirectory browsing.
- [ ] URL encoding properly handles Chinese characters and special symbols.
- [ ] Final playback URLs follow the pattern: `{server_url}/d/{encoded_path}?sign={signature}`.

### 7.5 File Type Handling
- [ ] Audio files (`mime_type == 'audio'`) are played using AudioPlayerController.
- [ ] Video files show development dialog and then open in browser.
- [ ] Image files open directly in browser without any dialog.
- [ ] Text documents show development dialog and then open in browser.
- [ ] Other files (`mime_type == 'file'`) open directly in browser.
- [ ] Development dialogs use consistent Chinese messaging and proper icons.
- [ ] File type logging includes both filename and mime_type for debugging.
- [ ] File type processing doesn't interrupt audio playback or navigation.
- [ ] Browser opening uses correct URL construction with server, port, path, and filename.
- [ ] Error handling for file operations shows user-friendly error messages.

### 7.6 Audio Playback
- [ ] Play, pause, and stop update the status bar and current track name.
- [ ] Space / `Ctrl+Home` only pause/resume active playback; no unintended restarts.
- [ ] After stopping, repeated pause/resume commands return "no audio playing".
- [ ] Previous/next track updates the list selection to match the active file.
- [ ] Device enumeration shows real outputs (no Dummy fallback); reselecting devices is applied before each playback.
- [ ] Stopping playback preserves the cached device and the next play/replay uses the selected output without defaulting back.
- [ ] Failure cases log a descriptive message and update the status bar without modal dialogs.
- [ ] Status bar displays only audio-related information: playback status, time, progress, volume/device, and playback rate.
- [ ] Non-audio operations (file loading, navigation, connection status) only log to console, never display in status bar.

### 7.7 Suggested scripts
```bash
python test_startup.py
python test_tab_navigation.py
python test_accessibility.py
python test_audio_player.py
python demo_logger_switch.py    # Test logging system behavior
```

### 7.6 Security & Configuration Verification
- [ ] Server configurations are encrypted and stored securely.
- [ ] Passwords are never logged or exposed in error messages.
- [ ] SSL certificate verification works correctly.
- [ ] Path injection protection prevents malicious directory traversal.

### 7.7 Logging System Verification
- [ ] Default operation produces no log output or files.
- [ ] With `OPENLIST_LOG_LEVEL=on`, all debug information is captured.
- [ ] Log files are created in `logs/` directory with proper rotation.
- [ ] Console logging respects `OPENLIST_CONSOLE_LEVEL` setting.
- [ ] Application runs silently without logging overhead when disabled.

---

## 9. Documentation Map
- `README.md` — complete project documentation (includes user guide, logging system, troubleshooting)
- `CLAUDE.md` — (this document) engineering conventions
- `AUDIO_PLAYER_UPDATE_SUMMARY.md` — playback change log

**Current version**: v1.1.9 (Chinese Pinyin Sorting)
**Last update**: 13 Nov 2025
**Highlights**: implemented intelligent Chinese pinyin-based file name sorting for improved user experience with consistent sorting behavior across all directories

---

## 10. Development History & Key Fixes

### 10.1 Chinese Pinyin Sorting Implementation (v1.1.9)

#### Problem Analysis
Chinese users experienced inconsistent file name ordering across different directories due to Unicode-based sorting, which doesn't align with pinyin alphabetical expectations. Files would appear in arbitrary order (e.g., 上海 < 北京) making navigation difficult for Chinese users.

#### Technical Challenges
- **Unicode vs Pinyin**: Native Unicode character ordering doesn't match Chinese alphabetical conventions
- **Mixed Content Handling**: Need to sort Chinese, English, numbers, and special characters coherently
- **History Stack Consistency**: Maintain sorting behavior during navigation with back/forward operations
- **Performance Considerations**: Apply sorting efficiently without impacting file loading performance

#### Implementation Details
**Library Integration**: Added `pypinyin` dependency for intelligent Chinese character conversion

**Core Algorithm**:
```python
def chinese_sort_key(name):
    pinyin_list = pypinyin.lazy_pinyin(name)
    return ''.join(pinyin_list)
```

**Sorting Strategy**:
- **New Directory Loading**: Automatic pinyin sorting applied during `FileListCtrl.load_files()`
- **History Stack Preservation**: Skip re-sorting during history restoration to maintain user context
- **Manual Sorting Controls**: Enhanced View menu with toggle-based ascending/descending options

**Architecture Changes**:
- Modified `load_files()` method to apply consistent sorting across all directory operations
- Updated `_save_current_state_to_history()` to preserve sorted file lists
- Enhanced `_try_restore_from_history()` with skip-sorting mechanism for history restoration

#### User Experience Improvements
- **Intuitive Ordering**: Files now sort alphabetically by pinyin (北京 < 上海 < 张三)
- **Consistent Behavior**: All directories display files in expected pinyin order
- **Cultural Alignment**: Follows Chinese user expectations for alphabetical file organization
- **Mixed Language Support**: Handles Chinese-English filenames correctly (e.g., 北京Beijing < 上海Shanghai)

#### Technical Benefits
- **Performance Optimized**: Efficient sorting with minimal overhead for typical file lists
- **Reliable Implementation**: Consistent behavior regardless of navigation path or file types
- **Maintainable Code**: Clear separation of sorting logic with comprehensive error handling
- **Accessibility Compliant**: Maintains screen reader compatibility with sorted content

### 10.2 Shortcut System & Playback Logic Evolution

#### Problem Analysis (Historical)
Early versions suffered from inconsistent shortcut behavior and confusing playback logic:

1. **Shortcut Binding Issue**: Audio shortcuts were incorrectly bound in `_on_retry()` method instead of `_setup_accelerators()`
2. **Event Handling Inconsistency**: Menu and shortcuts used different code paths
3. **Playback Logic Confusion**: Users expected music player-like behavior but got file-manager behavior

#### Key Architectural Changes

**Fix 1: Correct Shortcut Binding**
```python
# Before (incorrect)
def _on_retry(self, dialog, retry_callback):
    self.Bind(wx.EVT_MENU, self.on_play_pause_hotkey, id=wx.ID_HIGHEST + 20)

# After (correct)
def _setup_accelerators(self):
    self.Bind(wx.EVT_MENU, self.on_play_pause_hotkey, id=wx.ID_HIGHEST + 20)
```

**Fix 2: Separated Playback Logic**
- **File Selection**: Enter/DoubleClick plays selected file and remembers selection
- **Playback Control**: Shortcuts/menus control current playing file only
- **Smart Recovery**: Stopped playback resumes last selected file via Enter

#### Implementation Details

**Core Methods Added**:
```python
def _play_selected_file(self):
    """Play selected file and remember for recovery"""

def _control_current_playback(self):
    """Control current playback without changing selected file"""

def _resume_last_selected(self):
    """Resume last file selected via Enter"""
```

**State Management**:
- `current_file`: Currently playing file
- `last_selected_file`: Last file selected via Enter
- Smart fallback to first audio file when no selection exists

### 10.2 Audio Track Detection Implementation

#### Technical Challenges
- VLC API returns -1 when no media loaded
- Media parsing requires delay for complete track detection
- Menu system needs dynamic updates without replacing entire menubar

#### Solutions Implemented
- **2-second delay** after video start for track detection
- **Remove+Insert pattern** for menu updates (wx.Menu has no Replace method)
- **RadioItem usage** for multi-track scenarios with visual checkmarks

#### Code Architecture
```python
def get_available_audio_tracks(self) -> list:
    # Handle VLC API -1 return values correctly
    track_count = self.vlc_player.audio_get_track_count()
    if track_count <= 0: return []

def _refresh_audio_tracks_menu(self):
    # Dynamic menu updates with proper wxPython patterns
    play_menu.Remove(track_item)
    new_item = play_menu.Insert(pos, -1, title, new_menu)
```

---

## 11. Code Review Focus
1. **Accessibility First**: All changes must maintain or improve screen reader support and keyboard navigation.
2. **Navigation Consistency**: Directory navigation should preserve user context and provide predictable behavior.
3. **Chinese Localization**: File sorting must use pinyin-based ordering for optimal Chinese user experience.
4. **Audio Integration**: Ensure audio playback is not interrupted by directory operations or file type processing.
5. **Security Compliance**: Configuration data must remain encrypted and secure.
6. **Error Handling**: API failures should be transparent to users with clear error messages and recovery options.
7. **User Information Management**: Login process must successfully retrieve and store user information for dynamic path construction.
8. **File Type Processing**: File handling must use API-returned `mime_type`, never filename extensions, with appropriate user feedback for different file types.
9. **Path Construction**: Playback URLs must use dynamic user-based paths instead of hardcoded values.
10. **Performance Impact**: Changes should not affect the silent-by-default logging performance.
11. **Documentation Update**: New features must be documented in this guide before merge.

When proposing a new convention or shortcut, update this guide in the same pull request. Thanks!
