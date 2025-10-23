# OpenList Windows Management Tool – Developer Guide (Claude Edition)

> Keep the codebase accessibility-first while refining the audio experience. This guide summarizes coding standards, shortcut contracts, and regression checks. Treat it as the living reference before shipping changes.

---

## 1. Project Overview
- **Tech stack**: wxPython, requests, python-vlc, cryptography
- **Focus**: Screen-reader friendly UI, full keyboard navigation, integrated audio playback with device selection, secure configuration management
- **Architecture**: Layered architecture with modular design, event-driven patterns, and intelligent caching
- **Directory layout**
  ```text
  src/
    ui/               # windowing & interaction (main_frame, file_manager_window, dialogs)
    media/            # VLC wrapper and playback control (audio_player, media_player_core, vlc_loader)
    core/             # logging, configuration, utilities (logger, config_manager, version)
    api/              # OpenList API client (openlist_client)
    accessibility/    # light-weight accessibility helpers (future expansion)
  ```

### 1.1 Key Features
- **File Management**: Smart directory navigation with position memory
- **Audio Integration**: Built-in VLC-based media player with device selection
- **Security**: Encrypted server configurations with secure key management
- **Accessibility**: Complete keyboard navigation and screen reader support
- **Logging**: Silent-by-default logging with environment variable control

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

---

## 4. Audio Playback Implementation Notes
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
- `Ctrl+Home` — pause/resume, only when audio is currently playing or paused  
- `Ctrl+End` — stop playback and clear the active file reference  
- `Ctrl+PageUp / PageDown` — previous / next track  
- `Ctrl+Left / Right` — seek backward / forward  
- `Ctrl+Up / Down` — volume up / down  
- `Space` — identical to `Ctrl+Home`; works regardless of focus location  
- **Fallback behavior**: if neither playing nor paused, the shortcut simply logs "no audio playing" (no implicit load). Status bar is managed exclusively by AudioPlayerController.

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

### 6.2 Logging System Guidelines
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

### 7.3 Audio Playback
- [ ] Play, pause, and stop update the status bar and current track name.
- [ ] Space / `Ctrl+Home` only pause/resume active playback; no unintended restarts.
- [ ] After stopping, repeated pause/resume commands return "no audio playing".
- [ ] Previous/next track updates the list selection to match the active file.
- [ ] Device enumeration shows real outputs (no Dummy fallback); reselecting devices is applied before each playback.
- [ ] Stopping playback preserves the cached device and the next play/replay uses the selected output without defaulting back.
- [ ] Failure cases log a descriptive message and update the status bar without modal dialogs.
- [ ] Status bar displays only audio-related information: playback status, time, progress, volume/device, and playback rate.
- [ ] Non-audio operations (file loading, navigation, connection status) only log to console, never display in status bar.

### 7.4 Suggested scripts
```bash
python test_startup.py
python test_tab_navigation.py
python test_accessibility.py
python test_audio_player.py
python demo_logger_switch.py    # Test logging system behavior
```

### 7.5 Security & Configuration Verification
- [ ] Server configurations are encrypted and stored securely.
- [ ] Passwords are never logged or exposed in error messages.
- [ ] SSL certificate verification works correctly.
- [ ] Path injection protection prevents malicious directory traversal.

### 7.6 Logging System Verification
- [ ] Default operation produces no log output or files.
- [ ] With `OPENLIST_LOG_LEVEL=on`, all debug information is captured.
- [ ] Log files are created in `logs/` directory with proper rotation.
- [ ] Console logging respects `OPENLIST_CONSOLE_LEVEL` setting.
- [ ] Application runs silently without logging overhead when disabled.

---

## 8. Documentation Map
- `README.md` — complete project documentation (includes user guide, logging system, troubleshooting)
- `CLAUDE.md` — (this document) engineering conventions
- `AUDIO_PLAYER_UPDATE_SUMMARY.md` — playback change log

**Current version**: v1.1.5 (Status bar optimization for audio-only display)
**Last update**: 23 Oct 2025
**Highlights**: status bar dedicated exclusively to audio playback functionality, removed all non-audio status display

---

## 9. Code Review Focus
1. **Accessibility First**: All changes must maintain or improve screen reader support and keyboard navigation.
2. **Navigation Consistency**: Directory navigation should preserve user context and provide predictable behavior.
3. **Audio Integration**: Ensure audio playback is not interrupted by directory operations.
4. **Security Compliance**: Configuration data must remain encrypted and secure.
5. **Performance Impact**: Changes should not affect the silent-by-default logging performance.
6. **Documentation Update**: New features must be documented in this guide before merge.

When proposing a new convention or shortcut, update this guide in the same pull request. Thanks!
