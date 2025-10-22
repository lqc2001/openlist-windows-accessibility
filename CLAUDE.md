# OpenList Windows Management Tool – Developer Guide (Claude Edition)

> Keep the codebase accessibility-first while refining the audio experience. This guide summarizes coding standards, shortcut contracts, and regression checks. Treat it as the living reference before shipping changes.

---

## 1. Project Overview
- **Tech stack**: wxPython, requests, python-vlc  
- **Focus**: Screen-reader friendly UI, full keyboard navigation, integrated audio playback with device selection  
- **Directory layout**
  ```text
  src/
    ui/               # windowing & interaction
    media/            # VLC wrapper and playback control
    core/             # logging, configuration, utilities
    api/              # OpenList API client
    accessibility/    # light-weight accessibility helpers
  ```

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

## 3. Audio Playback Implementation Notes
1. **File detection** – always use `MediaFileDetector` to identify playable items.  
2. **Single controller** – UI code should speak only to `AudioPlayerController`.  
3. **State sync** – update status bar, selected list item, and controller state together (`_select_file_index` is the helper).  
4. **Pause semantics** – `AudioPlayerController.play_pause()` returns `False` when nothing is playing/paused; never reload media inside that method.  
5. **Shortcut parity** – Space bar and `Ctrl+Home` call the same pause/resume logic; when nothing is playing the UI just reports “no active audio”.  
6. **VLC management** – let `MediaPlayerCore` manage instance reuse, device enumeration, and teardown; no raw VLC calls in UI.  
7. **Error feedback** – log failures and surface them via the status bar instead of modal dialogs.
8. **Device persistence** – cache the selected audio device and call `_apply_audio_device()` before each play/resume; the `MediaPlayerPlaying` hook re-applies the device because LibVLC rebuilds the output chain after `stop()`.

---

## 4. Shortcut Contracts
### 4.1 General
- `Alt+letter` — primary actions in menus/dialogs  
- `Ctrl+Tab` — switch panes  
- `Alt+F4` — exit  
- `F1` — help

### 4.2 Audio Playback (global)
- `Ctrl+Home` — pause/resume, only when audio is currently playing or paused  
- `Ctrl+End` — stop playback and clear the active file reference  
- `Ctrl+PageUp / PageDown` — previous / next track  
- `Ctrl+Left / Right` — seek backward / forward  
- `Ctrl+Up / Down` — volume up / down  
- `Space` — identical to `Ctrl+Home`; works regardless of focus location  
- **Fallback behavior**: if neither playing nor paused, the shortcut simply updates the status bar with “no audio playing” (no implicit load).

---

## 5. Coding Standards
- Class names use **PascalCase**; functions & variables use **snake_case**; constants use **UPPER_SNAKE_CASE**.
- Every non-trivial method should include a short docstring with intent and caveats.
- Logging goes through `get_logger()`; never use `print`.
- API interaction funnels through `OpenListClient`; avoid stray `requests` calls.

## 5.1 Logging Control
- Set environment variable `OPENLIST_LOG_LEVEL=OFF` to disable all logging output
- When logging is disabled, both file logs and console output (including API debug info) are suppressed
- Default behavior maintains full logging for debugging and development

---

## 6. Regression Checklist (run before commit)
### 6.1 Core UX
- [ ] Application launches without errors.  
- [ ] Tab navigation covers all controls in logical order.  
- [ ] Screen reader announces names/help texts correctly.  
- [ ] Menu items and buttons include shortcut hints.

### 6.2 Audio Playback
- [ ] Play, pause, and stop update the status bar and current track name.  
- [ ] Space / `Ctrl+Home` only pause/resume active playback; no unintended restarts.  
- [ ] After stopping, repeated pause/resume commands return “no audio playing”.  
- [ ] Previous/next track updates the list selection to match the active file.  
- [ ] Device enumeration shows real outputs (no Dummy fallback); reselecting devices is applied before each playback.  
- [ ] Stopping playback preserves the cached device and the next play/replay uses the selected output without defaulting back.  
- [ ] Failure cases log a descriptive message and update the status bar without modal dialogs.

### 6.3 Suggested scripts
```bash
python test_startup.py
python test_tab_navigation.py
python test_accessibility.py
python test_audio_player.py
```

---

## 7. Documentation Map
- `README.md` — user quick start  
- `HELP_DOCUMENTATION.md` — full user manual  
- `CLAUDE.md` — (this document) engineering conventions  
- `AUDIO_PLAYER_UPDATE_SUMMARY.md` — playback change log  
- `DOCUMENTATION_INDEX.md` — doc hub

**Current version**: v1.1.2 (Audio device persistence)  
**Last update**: 21 Oct 2025  
**Highlights**: audio device reapplied across stop/replay, pause/resume logic standardized, list selection sync after track changes

---

## 8. Code Review Focus
1. Accessibility unchanged or improved (focus order, announcements, shortcuts).  
2. Audio controller state and UI state stay aligned; no hidden reloads.  
3. Logging/status messaging is informative yet non-intrusive.  
4. New shortcuts or behaviors are documented here before merge.

When proposing a new convention or shortcut, update this guide in the same pull request. Thanks!
