#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件管理主窗口
登录成功后显示的文件管理界面
"""

import threading

import wx
import wx.lib.mixins.listctrl as listmix
from src.core.logger import get_logger
from src.ui.server_select_dialog import ServerSelectDialog
from src.core.version import get_about_text, get_version_info
from src.media.file_detector import MediaFileDetector
from src.ui.media_player_window import MediaPlayerWindow
from src.ui.audio_player_controller import AudioPlayerController


class FileManagerWindow(wx.Frame):
    """文件管理主窗口"""

    def __init__(self, server_info, client):
        """
        初始化文件管理窗口

        Args:
            server_info: 服务器信息
            client: 已认证的OpenList客户端
        """
        self.server_info = server_info
        self.client = client
        self.logger = get_logger()

        # 创建主窗口
        style = wx.DEFAULT_FRAME_STYLE
        title = f"文件管理 - {server_info.get('name')}"
        super().__init__(None, title=title, size=(800, 600), style=style)

        # 当前路径
        self.current_path = "/"
        self.file_list = []
        self._load_sequence = 0

        # 目录导航历史栈 (带路径验证的智能历史栈)
        # 每个元素包含: {'path': str, 'files': list, 'selected_index': int}
        self._navigation_history = []

        # 媒体播放器相关
        self.media_player_window = None

        # 音频播放控制器
        self.audio_controller = AudioPlayerController(self)

        # 记住最后通过回车键选择的文件（用于停止后恢复播放）
        self._last_selected_file = None

        # 初始化UI
        self._create_ui()
        self._create_menu()
        self._setup_accelerators()

        # 加载文件列表
        self._load_file_list()

        self.logger.info(f"文件管理窗口初始化完成: {server_info.get('name')}")

    def _create_ui(self):
        """创建用户界面"""
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # 创建文件列表
        self.file_list_ctrl = FileListCtrl(self)
        self.file_list_ctrl.SetMinSize((760, 500))

        main_sizer.Add(self.file_list_ctrl, 1, wx.ALL | wx.EXPAND, 10)

        # 状态栏（5字段专门用于音频播放显示）
        self.status_bar = self.CreateStatusBar(5)
        self.status_bar.SetStatusWidths([-2, -1, -1, -1, -1])  # 自适应宽度
        self.audio_controller.set_status_bar(self.status_bar)
        # 注意：状态栏现在只用于音频功能，不再显示连接状态等非音频信息

        self.SetSizer(main_sizer)

        # 绑定事件
        self._bind_events()

        # 绑定键盘事件
        self.Bind(wx.EVT_CHAR, self.on_char)

    def _create_menu(self):
        """创建菜单栏"""
        menubar = wx.MenuBar()

        # 文件菜单
        file_menu = wx.Menu()
        switch_item = file_menu.Append(wx.ID_ANY, "切换服务器(&Q)\tCtrl+Q", "切换到其他服务器")
        file_menu.AppendSeparator()
        refresh_item = file_menu.Append(wx.ID_ANY, "刷新(&R)\tF5", "刷新文件列表")
        exit_item = file_menu.Append(wx.ID_EXIT, "退出(&X)\tAlt+F4", "退出程序")

        # 编辑菜单
        edit_menu = wx.Menu()
        select_all_item = edit_menu.Append(wx.ID_ANY, "全选(&A)\tCtrl+A", "选择所有文件")
        edit_menu.AppendSeparator()
        copy_name_item = edit_menu.Append(wx.ID_ANY, "复制文件名(&C)\tCtrl+C", "复制选中文件的名称")
        copy_path_item = edit_menu.Append(wx.ID_ANY, "复制路径(&P)\tCtrl+Shift+C", "复制选中文件的完整路径")

        # 播放菜单
        play_menu = wx.Menu()

        # 音频设备子菜单（根据VLC实际输出设备动态生成）
        device_menu = self.audio_controller.create_device_menu(play_menu)
        play_menu.AppendSubMenu(device_menu, "音频设备(&D)", "选择音频输出设备")
        self.device_menu = device_menu
        play_menu.AppendSeparator()

        # 播放控制
        play_pause_item = play_menu.Append(wx.ID_ANY, "播放/暂停(&P)\tCtrl+Home", "播放或暂停音频")
        stop_item = play_menu.Append(wx.ID_ANY, "停止(&S)\tCtrl+End", "停止播放")
        play_menu.AppendSeparator()

        # 播放列表控制
        previous_item = play_menu.Append(wx.ID_ANY, "上一个(&B)\tCtrl+PageUp", "播放上一个音频文件")
        next_item = play_menu.Append(wx.ID_ANY, "下一个(&N)\tCtrl+PageDown", "播放下一个音频文件")
        play_menu.AppendSeparator()

        # 快进快退
        seek_backward_item = play_menu.Append(wx.ID_ANY, "快退5秒(&B)\tCtrl+Left", "快退5秒")
        seek_forward_item = play_menu.Append(wx.ID_ANY, "快进5秒(&F)\tCtrl+Right", "快进5秒")
        play_menu.AppendSeparator()

        # 音量控制
        volume_up_item = play_menu.Append(wx.ID_ANY, "音量增加(&U)\tCtrl+Up", "增加音量")
        volume_down_item = play_menu.Append(wx.ID_ANY, "音量减少(&D)\tCtrl+Down", "减少音量")
        play_menu.AppendSeparator()

        # 倍速选择
        speed_menu = wx.Menu()
        speed_0_5x = speed_menu.AppendRadioItem(wx.ID_ANY, "0.5倍速", "0.5倍播放速度")
        speed_1_0x = speed_menu.AppendRadioItem(wx.ID_ANY, "1.0倍速", "正常播放速度")
        speed_1_5x = speed_menu.AppendRadioItem(wx.ID_ANY, "1.5倍速", "1.5倍播放速度")
        speed_2_0x = speed_menu.AppendRadioItem(wx.ID_ANY, "2.0倍速", "2倍播放速度")
        speed_2_5x = speed_menu.AppendRadioItem(wx.ID_ANY, "2.5倍速", "2.5倍播放速度")
        speed_3_0x = speed_menu.AppendRadioItem(wx.ID_ANY, "3.0倍速", "3倍播放速度")

        # 默认选择1.0倍速
        speed_1_0x.Check(True)

        play_menu.AppendSubMenu(speed_menu, "播放倍速(&S)", "选择播放倍速")

        # 视图菜单
        view_menu = wx.Menu()
        sort_name_item = view_menu.AppendRadioItem(wx.ID_ANY, "按名称排序(&N)")
        sort_size_item = view_menu.AppendRadioItem(wx.ID_ANY, "按大小排序(&S)")
        sort_date_item = view_menu.AppendRadioItem(wx.ID_ANY, "按日期排序(&D)")

        # 帮助菜单
        help_menu = wx.Menu()
        about_item = help_menu.Append(wx.ID_ABOUT, "关于(&H)\tF1", "关于程序")

        # 添加到菜单栏
        menubar.Append(file_menu, "文件(&F)")
        menubar.Append(edit_menu, "编辑(&E)")
        menubar.Append(play_menu, "播放(&P)")
        menubar.Append(view_menu, "视图(&V)")
        menubar.Append(help_menu, "帮助(&H)")

        self.SetMenuBar(menubar)

        # 绑定菜单事件
        self.Bind(wx.EVT_MENU, self.on_switch_server, switch_item)
        self.Bind(wx.EVT_MENU, self.on_refresh, refresh_item)
        self.Bind(wx.EVT_MENU, self.on_exit, exit_item)
        self.Bind(wx.EVT_MENU, self.on_select_all, select_all_item)
        self.Bind(wx.EVT_MENU, self.on_copy_name, copy_name_item)
        self.Bind(wx.EVT_MENU, self.on_copy_path, copy_path_item)

        # 播放菜单事件
        self.Bind(wx.EVT_MENU, self.on_play_pause, play_pause_item)
        self.Bind(wx.EVT_MENU, self.on_stop_playback, stop_item)
        self.Bind(wx.EVT_MENU, self.on_previous_track, previous_item)
        self.Bind(wx.EVT_MENU, self.on_next_track, next_item)
        self.Bind(wx.EVT_MENU, self.on_seek_backward, seek_backward_item)
        self.Bind(wx.EVT_MENU, self.on_seek_forward, seek_forward_item)
        self.Bind(wx.EVT_MENU, self.on_volume_up, volume_up_item)
        self.Bind(wx.EVT_MENU, self.on_volume_down, volume_down_item)

        # 倍速事件
        self.Bind(wx.EVT_MENU, lambda e: self.on_set_playback_rate(0.5), speed_0_5x)
        self.Bind(wx.EVT_MENU, lambda e: self.on_set_playback_rate(1.0), speed_1_0x)
        self.Bind(wx.EVT_MENU, lambda e: self.on_set_playback_rate(1.5), speed_1_5x)
        self.Bind(wx.EVT_MENU, lambda e: self.on_set_playback_rate(2.0), speed_2_0x)
        self.Bind(wx.EVT_MENU, lambda e: self.on_set_playback_rate(2.5), speed_2_5x)
        self.Bind(wx.EVT_MENU, lambda e: self.on_set_playback_rate(3.0), speed_3_0x)

        self.Bind(wx.EVT_MENU, self.on_sort_name, sort_name_item)
        self.Bind(wx.EVT_MENU, self.on_sort_size, sort_size_item)
        self.Bind(wx.EVT_MENU, self.on_sort_date, sort_date_item)
        self.Bind(wx.EVT_MENU, self.on_about, about_item)

    def _setup_accelerators(self):
        """设置快捷键"""
        self.logger.info("正在设置快捷键表...")
        accel_tbl = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord('Q'), wx.ID_HIGHEST + 1),  # Ctrl+Q 切换服务器
            (wx.ACCEL_NORMAL, wx.WXK_F5, wx.ID_HIGHEST + 2),  # F5 刷新
            (wx.ACCEL_CTRL, ord('A'), wx.ID_HIGHEST + 3),  # Ctrl+A 全选
            (wx.ACCEL_CTRL, ord('C'), wx.ID_HIGHEST + 4),  # Ctrl+C 复制文件名
            (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('C'), wx.ID_HIGHEST + 5),  # Ctrl+Shift+C 复制路径
            (wx.ACCEL_CTRL, ord('W'), wx.ID_HIGHEST + 6),  # Ctrl+W 网页打开
            (wx.ACCEL_SHIFT, wx.WXK_RETURN, wx.ID_HIGHEST + 7),  # Shift+Enter 查看说明
            (wx.ACCEL_ALT | wx.ACCEL_SHIFT, wx.WXK_RETURN, wx.ID_HIGHEST + 8),  # Alt+Shift+Enter 批量下载
            (wx.ACCEL_NORMAL, ord('O'), wx.ID_HIGHEST + 9),  # O 打开
            (wx.ACCEL_NORMAL, wx.WXK_F1, wx.ID_ABOUT),   # F1 关于

            # 音频播放快捷键
            (wx.ACCEL_CTRL, wx.WXK_HOME, wx.ID_HIGHEST + 20),  # Ctrl+Home 播放/暂停
            (wx.ACCEL_CTRL, wx.WXK_END, wx.ID_HIGHEST + 21),   # Ctrl+End 停止
            (wx.ACCEL_CTRL, wx.WXK_PAGEUP, wx.ID_HIGHEST + 22), # Ctrl+PageUp 上一个
            (wx.ACCEL_CTRL, wx.WXK_PAGEDOWN, wx.ID_HIGHEST + 23), # Ctrl+PageDown 下一个
            (wx.ACCEL_CTRL, wx.WXK_LEFT, wx.ID_HIGHEST + 24),   # Ctrl+Left 快退
            (wx.ACCEL_CTRL, wx.WXK_RIGHT, wx.ID_HIGHEST + 25),  # Ctrl+Right 快进
            (wx.ACCEL_CTRL, wx.WXK_UP, wx.ID_HIGHEST + 26),     # Ctrl+Up 音量增加
            (wx.ACCEL_CTRL, wx.WXK_DOWN, wx.ID_HIGHEST + 27),   # Ctrl+Down 音量减少
            (wx.ACCEL_NORMAL, wx.WXK_SPACE, wx.ID_HIGHEST + 28),      # 空格键 - 播放/暂停
        ])
        self.SetAcceleratorTable(accel_tbl)
        self.logger.info("快捷键表设置完成")

        # 绑定快捷键事件
        self.Bind(wx.EVT_MENU, self.on_switch_server_hotkey, id=wx.ID_HIGHEST + 1)
        self.Bind(wx.EVT_MENU, self.on_refresh_hotkey, id=wx.ID_HIGHEST + 2)
        self.Bind(wx.EVT_MENU, self.on_select_all_hotkey, id=wx.ID_HIGHEST + 3)
        self.Bind(wx.EVT_MENU, self.on_copy_name_hotkey, id=wx.ID_HIGHEST + 4)
        self.Bind(wx.EVT_MENU, self.on_copy_path_hotkey, id=wx.ID_HIGHEST + 5)
        self.Bind(wx.EVT_MENU, self.on_web_open_hotkey, id=wx.ID_HIGHEST + 6)
        self.Bind(wx.EVT_MENU, self.on_view_info_hotkey, id=wx.ID_HIGHEST + 7)
        self.Bind(wx.EVT_MENU, self.on_batch_download_hotkey, id=wx.ID_HIGHEST + 8)
        self.Bind(wx.EVT_MENU, self.on_open_hotkey, id=wx.ID_HIGHEST + 9)

        # 音频播放快捷键事件
        self.logger.info("正在绑定音频快捷键事件...")
        self.Bind(wx.EVT_MENU, self.on_play_pause_hotkey, id=wx.ID_HIGHEST + 20)
        self.Bind(wx.EVT_MENU, self.on_stop_playback_hotkey, id=wx.ID_HIGHEST + 21)
        self.Bind(wx.EVT_MENU, self.on_previous_track_hotkey, id=wx.ID_HIGHEST + 22)
        self.Bind(wx.EVT_MENU, self.on_next_track_hotkey, id=wx.ID_HIGHEST + 23)
        self.Bind(wx.EVT_MENU, self.on_seek_backward_hotkey, id=wx.ID_HIGHEST + 24)
        self.Bind(wx.EVT_MENU, self.on_seek_forward_hotkey, id=wx.ID_HIGHEST + 25)
        self.Bind(wx.EVT_MENU, self.on_volume_up_hotkey, id=wx.ID_HIGHEST + 26)
        self.Bind(wx.EVT_MENU, self.on_volume_down_hotkey, id=wx.ID_HIGHEST + 27)
        self.Bind(wx.EVT_MENU, self.on_space_hotkey, id=wx.ID_HIGHEST + 28)
        self.logger.info("音频快捷键事件绑定完成")

    def _show_error_dialog(self, error_message, retry_callback=None):
        """
        显示错误对话框

        Args:
            error_message: 错误信息
            retry_callback: 重试回调函数，可选
        """
        # 创建自定义对话框
        dialog = wx.Dialog(self, title="错误", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        # 设置对话框在屏幕中央显示
        dialog.SetSize((400, 200))
        dialog.CenterOnScreen()

        # 创建垂直布局
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # 添加错误图标和消息
        message_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # 错误图标
        icon = wx.ArtProvider.GetBitmap(wx.ART_ERROR, wx.ART_MESSAGE_BOX)
        icon_ctrl = wx.StaticBitmap(dialog, bitmap=icon)
        message_sizer.Add(icon_ctrl, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 10)

        # 错误消息
        message_text = wx.StaticText(dialog, label=str(error_message))
        message_text.Wrap(350)  # 设置文本换行宽度
        message_sizer.Add(message_text, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 10)

        main_sizer.Add(message_sizer, 1, wx.EXPAND | wx.ALL, 10)

        # 添加按钮
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # 重试按钮（如果提供了重试回调）
        if retry_callback:
            retry_btn = wx.Button(dialog, wx.ID_RETRY, "重试")
            retry_btn.SetName("重试按钮")
            retry_btn.SetHelpText("重新尝试加载文件列表")
            retry_btn.Bind(wx.EVT_BUTTON, lambda evt: self._on_retry(dialog, retry_callback))
            button_sizer.Add(retry_btn, 0, wx.ALL, 5)

        # 确定按钮
        ok_btn = wx.Button(dialog, wx.ID_OK, "确定")
        ok_btn.SetName("确定按钮")
        ok_btn.SetHelpText("关闭错误对话框")
        ok_btn.SetDefault()  # 设置为默认按钮
        button_sizer.Add(ok_btn, 0, wx.ALL, 5)

        main_sizer.Add(button_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        dialog.SetSizer(main_sizer)

        # 设置为窗口级模态
        dialog.SetWindowModality(wx.WINDOW_MODAL)

        # 显示对话框
        dialog.ShowModal()
        dialog.Destroy()

    def _on_retry(self, dialog, retry_callback):
        """重试按钮点击处理"""
        dialog.Close()  # 先关闭对话框
        if retry_callback:
            retry_callback()  # 执行重试回调

        # 注意：所有快捷键事件绑定已移动到 _setup_accelerators 方法中
        # 这里不再需要重复绑定

    def _bind_events(self):
        """绑定事件"""
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_item_activated, self.file_list_ctrl)
        # 绑定文件列表控件的键盘事件
        self.file_list_ctrl.Bind(wx.EVT_CHAR, self.on_char)
        # 在父窗口级别也捕获键盘事件，以确保上下文菜单键能被识别
        self.Bind(wx.EVT_KEY_DOWN, self.on_main_key_down)



    def _load_file_list(self):
        """加载文件列表"""
        self._load_sequence += 1
        load_id = self._load_sequence
        target_path = self.current_path

        self.logger.info("正在加载文件列表...")  # 只记录日志，不更新状态栏

        worker = threading.Thread(
            target=self._load_file_list_worker,
            args=(target_path, load_id),
            daemon=True,
        )
        worker.start()

    def _load_file_list_worker(self, path, load_id):
        """后台线程：请求文件列表并格式化数据"""
        files = []
        total = 0
        error = None

        try:
            response = self.client.get_file_list(path)

            raw_files = response.get('files', [])
            for file_data in raw_files:
                file_item = {
                    "name": file_data.get('name', ''),
                    "size": self._format_file_size(file_data.get('size', 0)),
                    "date": self._format_date(file_data.get('modified_time')),
                    "type": self._get_file_type(
                        file_data.get('mime_type', ''),
                        file_data.get('name', '')
                    ),
                    "mime_type": file_data.get('mime_type', ''),
                    "path": file_data.get('path', ''),
                    "sign": file_data.get('sign', ''),
                    "id": file_data.get('id', '')
                }
                files.append(file_item)

            total = response.get('total', len(files))

        except Exception as exc:
            error = exc
            self.logger.error(f"加载文件列表失败: {exc}")

        wx.CallAfter(
            self._apply_file_list_result,
            path,
            files,
            total,
            error,
            load_id
        )

    def _apply_file_list_result(self, path, files, total, error, load_id):
        """在UI线程中应用文件列表加载结果"""
        if load_id != self._load_sequence or path != self.current_path:
            # 过期的加载请求，忽略结果
            return

        if error is not None:
            message = f"加载文件列表失败: {error}"
            self.logger.error(message)  # 记录错误日志

            # 清空文件列表显示空白
            self.file_list = []
            self.file_list_ctrl.load_files([])

            # 显示错误对话框，提供重试功能
            retry_callback = lambda: self._load_file_list()
            wx.CallAfter(self._show_error_dialog, error, retry_callback)
            return

        self.file_list = files
        self.file_list_ctrl.load_files(files)
        self.logger.info(f"已加载 {len(files)} 个项目，总计 {total} 个")  # 只记录日志

        # 自动选择第一项（新目录加载完成时）
        self._auto_select_first_item()
    def _format_file_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes == 0:
            return "-"

        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def _format_date(self, date_str):
        """格式化日期"""
        if not date_str:
            return "-"

        try:
            # 尝试解析ISO格式的日期
            if 'T' in date_str:
                # ISO格式: 2025-10-15T10:30:00Z
                from datetime import datetime
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                return dt.strftime("%Y-%m-%d %H:%M")
            else:
                return date_str
        except:
            return date_str

    def _get_file_type(self, mime_type, filename=None):
        """根据MIME类型获取文件类型"""
        mime_type = mime_type.lower()

        type_mapping = {
            'directory': 'folder',
            'inode/directory': 'folder',
            'application/pdf': 'pdf',
            'application/vnd.ms-excel': 'excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'excel',
            'application/msword': 'word',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'word',
            'image/jpeg': 'image',
            'image/png': 'image',
            'image/gif': 'image',
            'text/plain': 'text',
            'application/zip': 'archive',
            'application/x-zip-compressed': 'archive',
            'application/x-rar-compressed': 'archive',
        }

        # 首先检查是否为媒体文件
        if filename and MediaFileDetector.is_media_file(filename):
            media_type = MediaFileDetector.get_media_type(filename)
            if media_type == 'audio':
                return 'audio'
            elif media_type == 'video':
                return 'video'

        return type_mapping.get(mime_type, 'default')

    def _update_status(self, message):
        """更新状态 - 仅记录日志，状态栏只用于音频信息"""
        self.logger.info(f"状态更新: {message}")
        # 注意：状态栏现在专门用于音频播放显示，不再显示其他状态信息

    def _get_user_base_path(self):
        """
        获取用户基础路径

        Returns:
            str: 用户基础路径，如果获取失败返回None

        Raises:
            Exception: 当用户信息不存在或base_path字段缺失时
        """
        try:
            # 检查客户端是否有用户信息
            if not hasattr(self.client, 'user_info') or not self.client.user_info:
                raise Exception("用户信息不存在，请重新登录")

            base_path = self.client.user_info.get('base_path')
            if not base_path:
                raise Exception("用户信息中缺少base_path字段，请联系管理员")

            # 确保路径以/开头
            if not base_path.startswith('/'):
                base_path = '/' + base_path

            # 确保路径以/结尾（方便后续处理）
            if not base_path.endswith('/'):
                base_path = base_path + '/'

            self.logger.debug(f"获取用户基础路径: {base_path}")
            return base_path

        except Exception as e:
            self.logger.error(f"获取用户基础路径失败: {e}")
            raise

    def on_item_activated(self, event):
        """文件项双击事件"""
        index = event.GetIndex()
        if index >= 0 and index < len(self.file_list):
            file_item = self.file_list[index]
            if file_item["mime_type"] == "inode/directory":
                # 进入文件夹
                self.logger.info(f"进入文件夹: {file_item['name']}")
                self._navigate_to_folder(file_item)
            else:
                # 打开文件
                self.logger.info(f"打开文件: {file_item['name']}")
                self._open_file(file_item)

    def _navigate_to_folder(self, folder_item):
        """导航到文件夹"""
        try:
            # 保存当前状态到历史栈
            self._save_current_state_to_history()

            # 构建新的路径
            if self.current_path == "/":
                new_path = f"/{folder_item['name']}"
            else:
                new_path = f"{self.current_path}/{folder_item['name']}".replace("//", "/")

            self.logger.info(f"导航到路径: {new_path}")
            self.current_path = new_path

            # 更新窗口标题
            self.SetTitle(f"文件管理 - {self.server_info.get('name')} - {new_path}")

            # 重新加载文件列表
            self._load_file_list()

        except Exception as e:
            self.logger.error(f"文件夹导航失败: {e}")
            wx.MessageBox(f"文件夹导航失败: {e}", "错误", wx.OK | wx.ICON_ERROR)

    def _open_file(self, file_item):
        """打开文件"""
        try:
            self.logger.info(f"准备打开文件: {file_item['name']}")

            # 检查是否为媒体文件
            if MediaFileDetector.is_media_file(file_item['name']):
                self._play_media_file(file_item)
            else:
                # 非媒体文件的默认处理
                wx.MessageBox(f"文件操作功能待实现\n\n文件名: {file_item['name']}\n大小: {file_item['size']}\n类型: {file_item['mime_type']}",
                             "文件信息", wx.OK | wx.ICON_INFORMATION)
        except Exception as e:
            self.logger.error(f"打开文件失败: {e}")
            wx.MessageBox(f"打开文件失败: {e}", "错误", wx.OK | wx.ICON_ERROR)

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

    def on_main_key_down(self, event):
        """主窗口键盘事件处理"""
        key_code = event.GetKeyCode()
        raw_key_code = event.GetRawKeyCode()

        # 调试：记录特殊按键
        if event.ControlDown():
            ctrl_name = {
                wx.WXK_HOME: "Home",
                wx.WXK_END: "End",
                wx.WXK_PAGEUP: "PageUp",
                wx.WXK_PAGEDOWN: "PageDown",
                wx.WXK_LEFT: "Left",
                wx.WXK_RIGHT: "Right",
                wx.WXK_UP: "Up",
                wx.WXK_DOWN: "Down",
                wx.WXK_F5: "F5",
                wx.WXK_SPACE: "Space"
            }.get(key_code, f"KeyCode_{key_code}")

            if ctrl_name != f"KeyCode_{key_code}":
                self.logger.info(f"检测到 Ctrl+{ctrl_name} 按键")

        # 检查是否按下了 Shift+F10 (标准上下文菜单快捷键)
        if key_code == wx.WXK_F10 and event.ShiftDown():
            # 确保焦点在文件列表上
            self.file_list_ctrl.SetFocus()

            # 确保有选中项，如果没有则选中第一项
            if self.file_list_ctrl.GetFirstSelected() == -1 and self.file_list_ctrl.GetItemCount() > 0:
                self.file_list_ctrl.Select(0, True)

            # 直接触发右键菜单
            self._show_context_menu_at_selection()
            return  # 不继续处理事件

        # 检查上下文菜单键（根据调试信息，Application键是 key_code=395, raw_key_code=93）
        if key_code == 395 or raw_key_code == 93:
            # 确保焦点在文件列表上
            self.file_list_ctrl.SetFocus()

            # 确保有选中项，如果没有则选中第一项
            if self.file_list_ctrl.GetFirstSelected() == -1 and self.file_list_ctrl.GetItemCount() > 0:
                self.file_list_ctrl.Select(0, True)

            # 直接触发右键菜单
            self._show_context_menu_at_selection()
            return  # 不继续处理事件

        # 其他按键交给默认处理
        event.Skip()

    def _show_context_menu_at_selection(self):
        """在当前选中项位置显示上下文菜单"""
        try:
            # 获取当前选中项
            selected_index = self.file_list_ctrl.GetFirstSelected()
            if selected_index != -1:
                # 获取选中项的位置
                pos = self.file_list_ctrl.GetItemPosition(selected_index)
            else:
                # 如果没有选中项，使用列表控件的中心位置
                rect = self.file_list_ctrl.GetClientRect()
                pos = (rect.width // 2, rect.height // 2)

            # 创建并显示上下文菜单
            context_menu = ContextMenu(self.file_list_ctrl, self)
            self.file_list_ctrl.PopupMenu(context_menu, pos)
            context_menu.Destroy()

        except Exception as e:
            self.logger.error(f"显示上下文菜单时出错: {e}")
            # 如果出错，尝试简单的方式
            try:
                context_menu = ContextMenu(self.file_list_ctrl, self)
                self.file_list_ctrl.PopupMenu(context_menu, (10, 10))
                context_menu.Destroy()
            except Exception as e2:
                self.logger.error(f"备用方式也失败: {e2}")

    def _go_back(self):
        """返回上级目录"""
        try:
            # 如果不在根目录，则返回上级目录
            if self.current_path != "/":
                # 计算上级目录路径
                path_parts = self.current_path.strip("/").split("/")
                if len(path_parts) > 1:
                    # 返回上一级
                    new_path = "/" + "/".join(path_parts[:-1])
                else:
                    # 返回根目录
                    new_path = "/"

                self.logger.info(f"返回上级目录: {self.current_path} -> {new_path}")
                self.current_path = new_path

                # 更新窗口标题
                self.SetTitle(f"文件管理 - {self.server_info.get('name')} - {new_path}")

                # 尝试从历史栈恢复状态
                if not self._try_restore_from_history(new_path):
                    # 历史栈中没有对应状态，重新加载
                    self._load_file_list()
            else:
                # 已经在根目录，显示提示
                self.logger.info("已经在根目录")
                # 不再更新状态栏，状态栏仅用于音频信息

        except Exception as e:
            self.logger.error(f"返回上级目录失败: {e}")
            wx.MessageBox(f"返回上级目录失败: {e}", "错误", wx.OK | wx.ICON_ERROR)

    def _save_current_state_to_history(self):
        """保存当前目录状态到历史栈"""
        if self.file_list:  # 只有当文件列表不为空时才保存
            current_selected = self.file_list_ctrl.GetFirstSelected()
            history_entry = {
                'path': self.current_path,
                'files': self.file_list.copy(),
                'selected_index': current_selected if current_selected != -1 else 0
            }
            self._navigation_history.append(history_entry)
            self.logger.debug(f"已保存目录状态到历史栈: {self.current_path}, 选中项: {history_entry['selected_index']}")

    def _try_restore_from_history(self, expected_path):
        """尝试从历史栈恢复目录状态

        Args:
            expected_path: 期望恢复的路径

        Returns:
            bool: 是否成功恢复
        """
        if not self._navigation_history:
            self.logger.debug("历史栈为空，无法恢复")
            return False

        # 检查栈顶是否匹配期望的路径
        top_entry = self._navigation_history[-1]
        if top_entry['path'] == expected_path:
            # 恢复状态
            self.file_list = top_entry['files']
            self.file_list_ctrl.load_files(top_entry['files'])

            # 恢复选中状态
            if top_entry['files'] and 0 <= top_entry['selected_index'] < len(top_entry['files']):
                self._select_file_index(top_entry['selected_index'])
                self.logger.debug(f"从历史栈恢复目录状态: {expected_path}, 选中项: {top_entry['selected_index']}")
            else:
                # 如果文件列表为空或索引无效，设置焦点到列表但不选中任何项
                self.file_list_ctrl.SetFocus()
                self.logger.debug(f"从历史栈恢复目录状态: {expected_path}, 无选中项")

            self.logger.info(f"已恢复 {len(top_entry['files'])} 个项目")
            self._navigation_history.pop()  # 移除已使用的条目
            return True
        else:
            # 路径不匹配，历史栈不可用
            self.logger.debug(f"历史栈路径不匹配: 期望 {expected_path}, 实际 {top_entry['path']}")
            # 清空历史栈，因为状态不一致
            self._navigation_history.clear()
            return False

    def _select_file_index(self, index: int):
        """更新文件列表的选中项并设置焦点"""
        try:
            total = self.file_list_ctrl.GetItemCount()
            if total == 0:
                # 空列表，只设置焦点
                self.file_list_ctrl.SetFocus()
                return

            for i in range(total):
                self.file_list_ctrl.Select(i, on=(i == index))

            if 0 <= index < total:
                self.file_list_ctrl.Focus(index)
                self.file_list_ctrl.EnsureVisible(index)
                self.logger.debug(f"已选择文件列表项: {index}")
        except Exception as e:
            self.logger.debug(f"更新文件列表选中项失败: {e}")

    def _auto_select_first_item(self):
        """自动选择第一项并设置焦点"""
        if self.file_list and len(self.file_list) > 0:
            self._select_file_index(0)
            self.logger.debug(f"已自动选择第一项: {self.file_list[0]['name']}")
        else:
            # 空目录，只设置焦点到列表控件
            self.file_list_ctrl.SetFocus()
            self.logger.debug("空目录，只设置焦点到列表控件")

    def _play_media_file(self, file_item):
        """播放媒体文件"""
        try:
            self.logger.info(f"开始播放媒体文件: {file_item['name']}")
            # 不再更新状态栏，状态栏仅用于音频播放器控制器

            # 构建文件URL（用于播放器）
            file_url = self._build_file_url(file_item)

            # 创建或显示播放器窗口
            if self.media_player_window is None:
                self.media_player_window = MediaPlayerWindow(self, file_url)
                self.media_player_window.Show()
            else:
                # 播放器已存在，加载新文件
                self.media_player_window.load_and_play_file(file_url)
                self.media_player_window.Show()
                self.media_player_window.Raise()

            # 不再更新状态栏，状态栏仅用于音频播放器控制器

        except Exception as e:
            self.logger.error(f"播放媒体文件失败: {e}")
            # 不再更新状态栏，状态栏仅用于音频播放器控制器
            wx.MessageBox(f"播放媒体文件失败: {e}", "播放错误", wx.OK | wx.ICON_ERROR)

    def _build_file_url(self, file_item):
        """构建文件URL - 使用AList签名下载格式"""
        try:
            import urllib.parse

            # 构建文件路径：使用用户当前浏览路径 + 文件名
            if self.current_path == "/":
                file_path = f"/{file_item['name']}"
            else:
                file_path = f"{self.current_path}/{file_item['name']}"

            self.logger.debug(f"构建文件URL，文件路径: {file_path}")

            # 获取签名信息
            sign = file_item.get('sign', '')

            if sign:
                # 使用签名构建下载URL
                self.logger.debug(f"使用签名构建下载URL")

                # 获取用户基础路径并构建完整播放路径
                try:
                    user_base_path = self._get_user_base_path()
                    if not user_base_path:
                        raise Exception("无法获取用户基础路径，请检查用户配置")

                    # 构建完整播放路径：用户基础路径 + 文件相对路径
                    # 如果文件路径已经是绝对路径（以/开头），移除开头的斜杠
                    if file_path.startswith('/'):
                        relative_path = file_path[1:]  # 移除开头的斜杠
                    else:
                        relative_path = file_path

                    # 最终播放路径：用户基础路径 + 文件相对路径
                    final_file_path = user_base_path.rstrip('/') + '/' + relative_path
                    clean_path = final_file_path[1:]  # 移除开头的斜杠用于URL构建

                    self.logger.debug(f"构建播放路径: 用户基础路径={user_base_path}, 文件路径={file_path}, 最终路径={final_file_path}")

                except Exception as e:
                    # 获取用户基础路径失败，使用原始文件路径
                    self.logger.error(f"构建播放路径失败，使用原始路径: {e}")
                    clean_path = file_path.lstrip('/')  # 移除开头的斜杠

                # URL编码路径
                encoded_path = urllib.parse.quote(clean_path, safe='')

                # 构建完整URL
                server_url = self.server_info.get('url', '').rstrip('/')
                port = self.server_info.get('port', '')

                if port:
                    if server_url.endswith('/'):
                        server_url = server_url[:-1]
                    base_url = f"{server_url}:{port}"
                else:
                    base_url = server_url

                # 构建最终URL：http://server:port/d/encoded_path?sign=signature
                final_url = f"{base_url}/d/{encoded_path}?sign={sign}"

                self.logger.debug(f"构建的签名URL: {final_url}")
                print(f"[URL构建] 使用签名URL: {final_url}")
                return final_url
            else:
                # 没有签名，回退到API客户端方法
                self.logger.debug(f"没有签名信息，使用API客户端方法")
                print(f"[URL构建] 没有签名，使用API客户端方法")

                try:
                    media_url = self.client.get_media_url(file_path)
                    self.logger.debug(f"API返回的媒体URL: {media_url}")
                    print(f"[URL构建] API返回URL: {media_url}")
                    return media_url
                except Exception as api_error:
                    self.logger.warning(f"API获取URL失败，回退到手动构建: {api_error}")
                    print(f"[URL构建] API获取失败，回退到手动构建")

                    # 最后的回退：直接URL
                    server_url = self.server_info.get('url', '').rstrip('/')
                    port = self.server_info.get('port', '')

                    if port:
                        if server_url.endswith('/'):
                            server_url = server_url[:-1]
                        full_url = f"{server_url}:{port}{file_path}"
                    else:
                        full_url = f"{server_url}{file_path}"

                    print(f"[URL构建] 手动构建URL: {full_url}")
                    return full_url

        except Exception as e:
            self.logger.error(f"构建文件URL失败: {e}")
            print(f"[URL构建] 构建失败: {e}")
            return file_item.get('name', '')

    # 菜单事件处理
    def on_switch_server(self, event):
        """切换服务器"""
        self.switch_server()

    def on_refresh(self, event):
        """刷新文件列表"""
        self._load_file_list()

    def on_exit(self, event):
        """退出程序"""
        self.Close(True)

    def on_select_all(self, event):
        """全选"""
        self.file_list_ctrl.select_all()

  
    def on_copy_name(self, event):
        """复制文件名"""
        selected_items = self.file_list_ctrl.get_selected_items()
        if selected_items:
            names = [item["name"] for item in selected_items]
            text = "\n".join(names)
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(text))
                wx.TheClipboard.Close()
                wx.MessageBox(f"已复制 {len(names)} 个文件名", "复制成功")
        else:
            wx.MessageBox("请先选择文件", "提示", wx.OK | wx.ICON_INFORMATION)

    def on_copy_path(self, event):
        """复制路径"""
        selected_items = self.file_list_ctrl.get_selected_items()
        if selected_items:
            paths = [item["path"] for item in selected_items]
            text = "\n".join(paths)
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(text))
                wx.TheClipboard.Close()
                wx.MessageBox(f"已复制 {len(paths)} 个文件路径", "复制成功")
        else:
            wx.MessageBox("请先选择文件", "提示", wx.OK | wx.ICON_INFORMATION)

    def on_sort_name(self, event):
        """按名称排序"""
        self.file_list_ctrl.sort_by_name()

    def on_sort_size(self, event):
        """按大小排序"""
        self.file_list_ctrl.sort_by_size()

    def on_sort_date(self, event):
        """按日期排序"""
        self.file_list_ctrl.sort_by_date()

    def on_about(self, event):
        """关于对话框"""
        version_info = get_version_info()
        about_text = get_about_text()

        wx.MessageBox(
            f"{about_text}\n\n"
            "一个简单的OpenList服务器文件管理工具\n\n"
            "功能：\n"
            "• 服务器文件管理\n"
            "• 文件操作和查看\n"
            "• 右键菜单支持\n"
            "• 密码加密存储",
            f"关于 {version_info['software_name']}",
            wx.OK | wx.ICON_INFORMATION
        )

    # 快捷键事件处理
    def on_switch_server_hotkey(self, event):
        """切换服务器快捷键"""
        self.on_switch_server(event)

    def on_refresh_hotkey(self, event):
        """刷新快捷键"""
        self.on_refresh(event)

    def on_select_all_hotkey(self, event):
        """全选快捷键"""
        self.on_select_all(event)

    
    def on_copy_name_hotkey(self, event):
        """复制文件名快捷键"""
        self.on_copy_name(event)

    def on_copy_path_hotkey(self, event):
        """复制路径快捷键"""
        self.on_copy_path(event)

    def on_web_open_hotkey(self, event):
        """网页打开快捷键"""
        selected_items = self.file_list_ctrl.get_selected_items()
        if selected_items:
            self.on_context_web_open(selected_items[0])
        else:
            wx.MessageBox("请先选择要网页打开的文件", "提示", wx.OK | wx.ICON_INFORMATION)

    def on_view_info_hotkey(self, event):
        """查看说明快捷键"""
        selected_items = self.file_list_ctrl.get_selected_items()
        if selected_items:
            self.on_context_view_info(selected_items[0])
        else:
            wx.MessageBox("请先选择要查看说明的文件", "提示", wx.OK | wx.ICON_INFORMATION)

    def on_batch_download_hotkey(self, event):
        """批量下载快捷键"""
        selected_items = self.file_list_ctrl.get_selected_items()
        if selected_items:
            self.on_context_batch_download(selected_items)
        else:
            wx.MessageBox("请先选择要批量下载的文件", "提示", wx.OK | wx.ICON_INFORMATION)

    def on_open_hotkey(self, event):
        """打开快捷键"""
        selected_items = self.file_list_ctrl.get_selected_items()
        if selected_items:
            self.on_context_open(selected_items[0])
        else:
            wx.MessageBox("请先选择要打开的文件或文件夹", "提示", wx.OK | wx.ICON_INFORMATION)

    def switch_server(self):
        """切换到其他服务器"""
        try:
            # 关闭客户端连接
            if self.client:
                self.client.close()

            # 关闭当前窗口
            self.Close()

            # 显示服务器选择对话框
            server_dialog = ServerSelectDialog()
            server_dialog.Show()
            server_dialog.Center()

            # 绑定窗口关闭事件
            def on_server_dialog_closed(event):
                event.Skip()
                # 获取认证结果
                server_info, client = server_dialog.get_authenticated_server()

                if server_info and client:
                    # 创建新的文件管理窗口
                    new_window = FileManagerWindow(server_info, client)
                    new_window.Show()
                    new_window.Center()

                server_dialog.Destroy()

            server_dialog.Bind(wx.EVT_CLOSE, on_server_dialog_closed)

        except Exception as e:
            self.logger.error(f"切换服务器失败: {e}")
            wx.MessageBox(f"切换服务器失败: {e}", "错误", wx.OK | wx.ICON_ERROR)

    def on_close(self, event):
        """窗口关闭事件"""
        try:
            # 关闭媒体播放器
            if self.media_player_window:
                self.media_player_window.Close()
                self.media_player_window = None

            # 清理音频播放控制器
            if hasattr(self, 'audio_controller'):
                self.audio_controller.cleanup()

            # 关闭客户端连接
            if self.client:
                self.client.close()
        except:
            pass

        event.Skip()

    # 右键菜单事件处理
    def on_context_open(self, file_item):
        """右键菜单：打开文件或文件夹"""
        if file_item["mime_type"] == "inode/directory":
            # 进入文件夹
            self.logger.info(f"右键进入文件夹: {file_item['name']}")
            self._navigate_to_folder(file_item)
        else:
            # 打开文件
            self.logger.info(f"右键打开文件: {file_item['name']}")
            self._open_file(file_item)

    def on_context_play_media(self, file_item):
        """右键菜单：播放媒体文件"""
        try:
            if MediaFileDetector.is_media_file(file_item['name']):
                self._play_media_file(file_item)
            else:
                wx.MessageBox(f"这不是媒体文件: {file_item['name']}", "提示", wx.OK | wx.ICON_INFORMATION)
        except Exception as e:
            self.logger.error(f"播放媒体文件失败: {e}")
            wx.MessageBox(f"播放失败: {e}", "错误", wx.OK | wx.ICON_ERROR)

    def on_context_web_open(self, file_item):
        """右键菜单：在浏览器中打开文件"""
        try:
            import webbrowser
            import urllib.parse

            # 构建完整的文件URL：使用用户当前浏览路径 + 文件名
            if self.current_path == "/":
                file_path = f"/{file_item['name']}"
            else:
                file_path = f"{self.current_path}/{file_item['name']}"

            # 构建完整的URL，包含端口
            server_url = self.server_info.get('url', '').rstrip('/')
            port = self.server_info.get('port', '')

            # 如果有端口，添加到URL
            if port:
                if server_url.endswith('/'):
                    server_url = server_url[:-1]
                full_url = f"{server_url}:{port}{file_path}"
            else:
                full_url = f"{server_url}{file_path}"

            # 对URL进行编码
            encoded_url = urllib.parse.quote(full_url, safe=':/?#[]@!$&\'()*+,;=')

            self.logger.info(f"在浏览器中打开: {encoded_url}")
            webbrowser.open(encoded_url)

            # 不再更新状态栏，状态栏仅用于音频信息
            self.logger.info(f"已在浏览器中打开: {file_item['name']}")

        except Exception as e:
            self.logger.error(f"网页打开失败: {e}")
            wx.MessageBox(f"网页打开失败: {e}", "错误", wx.OK | wx.ICON_ERROR)

    def on_context_view_info(self, file_item):
        """右键菜单：查看文件详细信息"""
        try:
            # 构建详细信息文本
            info_text = f"文件名: {file_item['name']}\n"
            info_text += f"大小: {file_item['size']}\n"
            info_text += f"修改时间: {file_item['date']}\n"

            if file_item["path"]:
                info_text += f"路径: {file_item['path']}\n"
            else:
                if self.current_path == "/":
                    info_text += f"路径: /{file_item['name']}\n"
                else:
                    info_text += f"路径: {self.current_path}/{file_item['name']}\n"

            info_text += f"文件类型: {file_item['mime_type']}\n"
            info_text += f"文件ID: {file_item.get('id', 'N/A')}\n"

            # 如果是文件夹，添加特殊说明
            if file_item["mime_type"] == "inode/directory":
                info_text += "\n这是一个文件夹"
            else:
                info_text += "\n这是一个文件"

            # 显示详细信息对话框
            dlg = wx.MessageDialog(
                self,
                info_text,
                f"文件详细信息 - {file_item['name']}",
                wx.OK | wx.ICON_INFORMATION
            )
            dlg.ShowModal()
            dlg.Destroy()

        except Exception as e:
            self.logger.error(f"查看文件信息失败: {e}")
            wx.MessageBox(f"查看文件信息失败: {e}", "错误", wx.OK | wx.ICON_ERROR)

    def on_context_batch_download(self, selected_items):
        """右键菜单：批量下载"""
        try:
            # 暂时显示开发中提示
            file_names = [item['name'] for item in selected_items]
            files_text = "\n".join(file_names[:5])  # 只显示前5个文件名
            if len(file_names) > 5:
                files_text += f"\n... 等共{len(file_names)}个文件"

            wx.MessageBox(
                f"选中的文件:\n{files_text}\n\n批量下载功能正在开发中，敬请期待！",
                "批量下载",
                wx.OK | wx.ICON_INFORMATION
            )

        except Exception as e:
            self.logger.error(f"批量下载失败: {e}")
            wx.MessageBox(f"批量下载失败: {e}", "错误", wx.OK | wx.ICON_ERROR)

    # 音频播放相关方法
    def _handle_space_key_playback(self):
        """处理空格键播放/暂停"""
        try:
            # 只控制当前播放，不切换到选中文件
            self._control_current_playback()

        except Exception as e:
            self.logger.error(f"空格键播放控制失败: {e}")

    def on_play_pause(self, event):
        """播放/暂停菜单事件"""
        # 只控制当前播放，不切换到选中文件
        self._control_current_playback()

    def on_stop_playback(self, event):
        """停止播放菜单事件"""
        self.audio_controller.stop()

    def on_space_hotkey(self, event):
        """空格键全局播放/暂停"""
        self.logger.info("空格键播放/暂停快捷键被触发")
        self._handle_space_key_playback()

    def on_previous_track(self, event):
        """上一个曲目菜单事件"""
        self._play_previous_audio()

    def on_next_track(self, event):
        """下一个曲目菜单事件"""
        self._play_next_audio()

    def on_seek_backward(self, event):
        """快退菜单事件"""
        self.audio_controller.seek_backward(5)

    def on_seek_forward(self, event):
        """快进菜单事件"""
        self.audio_controller.seek_forward(5)

    def on_volume_up(self, event):
        """音量增加菜单事件"""
        self.audio_controller.volume_up(5)

    def on_volume_down(self, event):
        """音量减少菜单事件"""
        self.audio_controller.volume_down(5)

    def on_set_playback_rate(self, rate):
        """设置播放倍速事件"""
        self.audio_controller.set_playback_rate(rate)
        # 不再更新状态栏，状态栏由音频控制器自动更新
        self.logger.info(f"播放倍速已设置为: {rate}x")

    # 播放快捷键事件处理
    def on_play_pause_hotkey(self, event):
        """播放/暂停快捷键事件"""
        self.logger.info("播放/暂停快捷键被触发")
        # 只控制当前播放，不切换到选中文件
        self._control_current_playback()

    def on_stop_playback_hotkey(self, event):
        """停止播放快捷键事件"""
        self.logger.info("停止播放快捷键被触发")
        self.audio_controller.stop()

    def on_previous_track_hotkey(self, event):
        """上一个曲目快捷键事件"""
        self.logger.info("上一曲快捷键被触发")
        self._play_previous_audio()

    def on_next_track_hotkey(self, event):
        """下一个曲目快捷键事件"""
        self.logger.info("下一曲快捷键被触发")
        self._play_next_audio()

    def on_seek_backward_hotkey(self, event):
        """快退快捷键事件"""
        self.logger.info("快退快捷键被触发")
        self.audio_controller.seek_backward(5)

    def on_seek_forward_hotkey(self, event):
        """快进快捷键事件"""
        self.logger.info("快进快捷键被触发")
        self.audio_controller.seek_forward(5)

    def on_volume_up_hotkey(self, event):
        """音量增加快捷键事件"""
        self.logger.info("音量增加快捷键被触发")
        self.audio_controller.volume_up(5)

    def on_volume_down_hotkey(self, event):
        """音量减少快捷键事件"""
        self.logger.info("音量减少快捷键被触发")
        self.audio_controller.volume_down(5)

    # 辅助方法
    def _control_current_playback(self):
        """控制当前播放（用于快捷键和菜单，不切换到选中文件）"""
        try:
            if self.audio_controller.current_file:
                # 有当前播放文件，直接控制播放/暂停
                self.audio_controller.play_pause()
                self.logger.info("控制当前播放文件")
            else:
                # 没有当前播放文件，优先播放最后选择的文件
                target_file = None
                target_index = -1

                if self._last_selected_file:
                    # 优先使用最后通过回车键选择的文件
                    target_file = self._last_selected_file
                    # 在文件列表中找到这个文件的索引
                    for idx, item in enumerate(self.file_list):
                        if item['name'] == target_file['name']:
                            target_index = idx
                            break
                    self.logger.info(f"恢复播放最后选择的文件: {target_file['name']}")
                else:
                    # 没有最后选择的文件，播放列表中的第一个音频文件
                    for idx, item in enumerate(self.file_list):
                        if MediaFileDetector.is_media_file(item['name']):
                            media_type = MediaFileDetector.get_media_type(item['name'])
                            if media_type == 'audio':
                                target_file = item
                                target_index = idx
                                break
                    if target_file:
                        self.logger.info(f"自动播放第一个音频文件: {target_file['name']}")

                if target_file:
                    file_url = self._build_file_url(target_file)
                    self.audio_controller.play_file(file_url, target_file['name'])
                    if target_index >= 0:
                        self._select_file_index(target_index)
                else:
                    self.logger.info("当前目录没有音频文件")
                    wx.MessageBox("当前目录没有音频文件", "提示", wx.OK | wx.ICON_INFORMATION)

        except Exception as e:
            self.logger.error(f"播放控制失败: {e}")
            wx.MessageBox(f"播放控制失败: {e}", "错误", wx.OK | wx.ICON_ERROR)

    def _play_selected_or_current(self):
        """播放选中文件或控制当前播放"""
        try:
            selected_items = self.file_list_ctrl.get_selected_items()

            if selected_items and len(selected_items) == 1:
                file_item = selected_items[0]

                if MediaFileDetector.is_media_file(file_item['name']):
                    media_type = MediaFileDetector.get_media_type(file_item['name'])

                    if media_type == 'audio':
                        file_url = self._build_file_url(file_item)
                        current_url = getattr(self.audio_controller, 'current_file', None)
                        if current_url and current_url == file_url:
                            self.audio_controller.play_pause()
                        else:
                            self.audio_controller.play_file(file_url, file_item['name'])
                    else:
                        wx.MessageBox("只能播放音频文件", "提示", wx.OK | wx.ICON_INFORMATION)
                else:
                    wx.MessageBox("选中的不是媒体文件", "提示", wx.OK | wx.ICON_INFORMATION)
            else:
                # 没有选中文件或选中多个，控制当前播放
                if self.audio_controller.current_file:
                    # 控制当前播放
                    self.audio_controller.play_pause()
                else:
                    # 没有播放文件，自动播放列表中的第一个音频文件
                    first_audio = None
                    first_index = -1
                    for idx, item in enumerate(self.file_list):
                        if MediaFileDetector.is_media_file(item['name']):
                            media_type = MediaFileDetector.get_media_type(item['name'])
                            if media_type == 'audio':
                                first_audio = item
                                first_index = idx
                                break

                    if first_audio:
                        file_url = self._build_file_url(first_audio)
                        self.audio_controller.play_file(file_url, first_audio['name'])
                        self._select_file_index(first_index)
                    else:
                        self.logger.info("当前目录没有音频文件")

        except Exception as e:
            self.logger.error(f"播放操作失败: {e}")
            wx.MessageBox(f"播放操作失败: {e}", "错误", wx.OK | wx.ICON_ERROR)

    
    def _play_previous_audio(self):
        """播放上一个音频文件"""
        try:
            # 获取当前音频文件在列表中的位置
            current_filename = self.audio_controller.get_current_filename()
            if not current_filename:
                # 没有当前播放文件，播放第一个音频文件
                self._play_first_audio_file()
                return

            # 查找当前文件在列表中的索引
            current_index = -1
            audio_files = []  # 当前目录的所有音频文件

            for i, file_item in enumerate(self.file_list):
                if MediaFileDetector.is_media_file(file_item['name']):
                    media_type = MediaFileDetector.get_media_type(file_item['name'])
                    if media_type == 'audio':
                        audio_files.append((i, file_item))
                        if file_item['name'] == current_filename:
                            current_index = len(audio_files) - 1

            if not audio_files:
                self.logger.info("当前目录没有音频文件")
                return

            if current_index > 0:
                # 播放上一个音频文件
                prev_index, prev_file = audio_files[current_index - 1]
                file_url = self._build_file_url(prev_file)
                self.audio_controller.play_file(file_url, prev_file['name'])
                self._select_file_index(prev_index)
            elif current_index == 0:
                # 已经是第一个，播放最后一个
                last_index, last_file = audio_files[-1]
                file_url = self._build_file_url(last_file)
                self.audio_controller.play_file(file_url, last_file['name'])
                self._select_file_index(last_index)
            else:
                # 没找到当前文件，播放第一个
                first_index, first_file = audio_files[0]
                file_url = self._build_file_url(first_file)
                self.audio_controller.play_file(file_url, first_file['name'])
                self._select_file_index(first_index)

        except Exception as e:
            self.logger.error(f"播放上一个音频文件失败: {e}")

    def _play_next_audio(self):
        """播放下一个音频文件"""
        try:
            # 获取当前音频文件在列表中的位置
            current_filename = self.audio_controller.get_current_filename()
            if not current_filename:
                # 没有当前播放文件，播放第一个音频文件
                self._play_first_audio_file()
                return

            # 查找当前文件在列表中的索引
            current_index = -1
            audio_files = []  # 当前目录的所有音频文件

            for i, file_item in enumerate(self.file_list):
                if MediaFileDetector.is_media_file(file_item['name']):
                    media_type = MediaFileDetector.get_media_type(file_item['name'])
                    if media_type == 'audio':
                        audio_files.append((i, file_item))
                        if file_item['name'] == current_filename:
                            current_index = len(audio_files) - 1

            if not audio_files:
                self.logger.info("当前目录没有音频文件")
                return

            if current_index >= 0 and current_index < len(audio_files) - 1:
                # 播放下一个音频文件
                next_index, next_file = audio_files[current_index + 1]
                file_url = self._build_file_url(next_file)
                self.audio_controller.play_file(file_url, next_file['name'])
                self._select_file_index(next_index)
            elif current_index == len(audio_files) - 1:
                # 已经是最后一个，播放第一个
                first_index, first_file = audio_files[0]
                file_url = self._build_file_url(first_file)
                self.audio_controller.play_file(file_url, first_file['name'])
                self._select_file_index(first_index)
            else:
                # 没找到当前文件，播放第一个
                first_index, first_file = audio_files[0]
                file_url = self._build_file_url(first_file)
                self.audio_controller.play_file(file_url, first_file['name'])
                self._select_file_index(first_index)

        except Exception as e:
            self.logger.error(f"播放下一个音频文件失败: {e}")

    def _play_first_audio_file(self):
        """播放第一个音频文件"""
        try:
            for index, file_item in enumerate(self.file_list):
                if MediaFileDetector.is_media_file(file_item['name']):
                    media_type = MediaFileDetector.get_media_type(file_item['name'])
                    if media_type == 'audio':
                        file_url = self._build_file_url(file_item)
                        self.audio_controller.play_file(file_url, file_item['name'])
                        self._select_file_index(index)
                        return

            self._update_status("当前目录没有音频文件")

        except Exception as e:
            self.logger.error(f"播放第一个音频文件失败: {e}")

    # 重写播放媒体文件方法，优先使用音频控制器
    def _play_media_file(self, file_item):
        """播放媒体文件 - 优先使用音频控制器"""
        try:
            if MediaFileDetector.is_media_file(file_item['name']):
                media_type = MediaFileDetector.get_media_type(file_item['name'])

                if media_type == 'audio':
                    # 音频文件使用音频控制器
                    self.logger.info(f"使用音频控制器播放: {file_item['name']}")
                    file_url = self._build_file_url(file_item)
                    self.audio_controller.play_file(file_url, file_item['name'])
                    # 记住最后通过回车键选择的文件
                    self._last_selected_file = file_item
                    self.logger.info(f"已记住最后选择的文件: {file_item['name']}")
                    # 不再更新状态栏，状态栏由音频控制器自动更新
                else:
                    # 视频文件使用原来的播放器窗口
                    self.logger.info(f"使用视频播放器播放: {file_item['name']}")
                    self._play_video_file(file_item)
            else:
                wx.MessageBox(f"不支持的媒体文件: {file_item['name']}", "提示", wx.OK | wx.ICON_INFORMATION)

        except Exception as e:
            self.logger.error(f"播放媒体文件失败: {e}")
            wx.MessageBox(f"播放失败: {e}", "错误", wx.OK | wx.ICON_ERROR)

    def _play_video_file(self, file_item):
        """播放视频文件（使用原来的播放器窗口）"""
        try:
            self.logger.info(f"开始播放视频文件: {file_item['name']}")
            # 不再更新状态栏，状态栏仅用于音频播放器控制器

            # 构建文件URL
            file_url = self._build_file_url(file_item)

            # 创建或显示播放器窗口
            if self.media_player_window is None:
                self.media_player_window = MediaPlayerWindow(self, file_url)
                self.media_player_window.Show()
            else:
                self.media_player_window.load_and_play_file(file_url)
                self.media_player_window.Show()
                self.media_player_window.Raise()

            # 不再更新状态栏，状态栏仅用于音频播放器控制器

        except Exception as e:
            self.logger.error(f"播放视频文件失败: {e}")
            # 不再更新状态栏，状态栏仅用于音频播放器控制器
            wx.MessageBox(f"播放视频文件失败: {e}", "播放错误", wx.OK | wx.ICON_ERROR)


class FileListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
    """文件列表控件"""

    def __init__(self, parent):
        """初始化文件列表控件"""
        wx.ListCtrl.__init__(
            self,
            parent,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_VIRTUAL
        )
        listmix.ListCtrlAutoWidthMixin.__init__(self)

        # 设置列
        self.InsertColumn(0, "名称", width=250)
        self.InsertColumn(1, "类型", width=100)
        self.InsertColumn(2, "大小", width=100)
        self.InsertColumn(3, "修改时间", width=150)

        self.files = []
        self.sort_column = 0
        self.sort_ascending = True

        # 绑定右键菜单事件
        self.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)
        # 绑定键盘事件以处理上下文菜单键
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

    def load_files(self, files):
        """加载文件列表"""
        self.Freeze()
        try:
            data = files if files is not None else []
            self.files = data
            count = len(self.files)
            self.SetItemCount(count)
            self.Refresh()
        finally:
            self.Thaw()

        # 自动调整列宽
        self._autosize_columns()

    def OnGetItemText(self, item, column):
        """虚拟列表项文本回调"""
        if item < 0 or item >= len(self.files):
            return ""

        file_item = self.files[item]

        if column == 0:
            return file_item.get("name", "")
        if column == 1:
            return self._get_type_display_name(file_item.get("type", "default"))
        if column == 2:
            return file_item.get("size", "")
        if column == 3:
            return file_item.get("date", "")

        return ""

    def _autosize_columns(self):
        """自动调整列宽"""
        for col in range(self.GetColumnCount()):
            self.SetColumnWidth(col, wx.LIST_AUTOSIZE_USEHEADER)
            # 如果自动调整后的宽度太小，设置最小宽度
            if self.GetColumnWidth(col) < 100:
                self.SetColumnWidth(col, 100)

    def _get_file_icon(self, file_type):
        """获取文件图标"""
        icons = {
            "folder": "📁",
            "audio": "🎵",
            "video": "🎬",
            "pdf": "📄",
            "excel": "📊",
            "word": "📝",
            "image": "🖼️",
            "text": "📄",
            "default": "❓"
        }
        return icons.get(file_type, icons["default"])

    def _get_type_display_name(self, file_type):
        """获取文件类型的显示名称"""
        type_names = {
            "folder": "文件夹",
            "file": "文件",
            "video": "视频",
            "audio": "音频",
            "text": "文本",
            "image": "图片"
        }
        return type_names.get(file_type, "文件")

    def get_selected_items(self):
        """获取选中的文件"""
        selected_items = []
        index = self.GetFirstSelected()

        while index != -1:
            if index < len(self.files):
                selected_items.append(self.files[index])
            index = self.GetNextSelected(index)

        return selected_items

    def select_all(self):
        """全选"""
        self.Freeze()
        try:
            for i in range(self.GetItemCount()):
                self.Select(i, True)
        finally:
            self.Thaw()

    
    def sort_by_name(self):
        """按名称排序"""
        self.sort_column = 0
        self.sort_ascending = not self.sort_ascending
        self.files.sort(key=lambda x: x["name"], reverse=not self.sort_ascending)
        self._refresh_display()

    def sort_by_size(self):
        """按大小排序"""
        self.sort_column = 1
        self.sort_ascending = not self.sort_ascending
        # 简单的大小转换，用于排序
        def size_key(item):
            size = item["size"]
            if size == "-":
                return -1  # 文件夹排在前面
            # 移除单位并转换为数字
            if "KB" in size:
                return float(size.replace("KB", "").strip())
            elif "MB" in size:
                return float(size.replace("MB", "").strip()) * 1024
            elif "GB" in size:
                return float(size.replace("GB", "").strip()) * 1024 * 1024
            return 0

        self.files.sort(key=size_key, reverse=not self.sort_ascending)
        self._refresh_display()

    def sort_by_date(self):
        """按日期排序"""
        self.sort_column = 2
        self.sort_ascending = not self.sort_ascending
        self.files.sort(key=lambda x: x["date"], reverse=not self.sort_ascending)
        self._refresh_display()

    def _refresh_display(self):
        """刷新显示"""
        count = len(self.files)
        self.SetItemCount(count)
        self.Refresh()

    def on_context_menu(self, event):
        """右键菜单事件"""
        # 获取右键点击的位置
        pos = event.GetPosition()
        if pos == wx.DefaultPosition:
            # 如果是键盘触发的右键菜单，使用当前选中项
            item_index = self.GetFirstSelected()
            if item_index != -1:
                pos = self.GetItemPosition(item_index)
            else:
                pos = (0, 0)

        # 弹出右键菜单
        self.PopupMenu(ContextMenu(self, self.GetParent()), pos)

    def on_key_down(self, event):
        """键盘按下事件处理"""
        key_code = event.GetKeyCode()
        raw_key_code = event.GetRawKeyCode()

        # 检查是否按下了 Shift+F10 (标准上下文菜单快捷键)
        if key_code == wx.WXK_F10 and event.ShiftDown():
            # 确保有选中项，如果没有则选中第一项
            if self.GetFirstSelected() == -1 and self.GetItemCount() > 0:
                self.Select(0, True)
                self.SetFocus()

            # 触发上下文菜单事件
            menu_event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU)
            menu_event.SetPosition(wx.DefaultPosition)
            self.GetEventHandler().ProcessEvent(menu_event)
            return  # 不继续处理事件

        # 检查上下文菜单键（Application键）
        if key_code == 395 or raw_key_code == 93:
            # 确保有选中项，如果没有则选中第一项
            if self.GetFirstSelected() == -1 and self.GetItemCount() > 0:
                self.Select(0, True)
                self.SetFocus()

            # 触发上下文菜单事件
            menu_event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU)
            menu_event.SetPosition(wx.DefaultPosition)
            self.GetEventHandler().ProcessEvent(menu_event)
            return  # 不继续处理事件

        # 其他按键交给默认处理
        event.Skip()


class ContextMenu(wx.Menu):
    """文件右键菜单"""

    def __init__(self, file_list_ctrl, parent_window):
        """
        初始化右键菜单

        Args:
            file_list_ctrl: 文件列表控件
            parent_window: 父窗口
        """
        super().__init__()
        self.file_list_ctrl = file_list_ctrl
        self.parent_window = parent_window

        # 创建菜单项
        self._create_menu_items()

    def _create_menu_items(self):
        """创建菜单项"""
        selected_items = self.file_list_ctrl.get_selected_items()
        has_selection = len(selected_items) > 0

        # 打开(O)
        open_item = self.Append(wx.ID_ANY, "打开(&O)\tO", "打开文件或进入文件夹")
        self.Bind(wx.EVT_MENU, self.on_open, open_item)

        # 播放媒体文件
        if has_selection and len(selected_items) == 1 and MediaFileDetector.is_media_file(selected_items[0]['name']):
            play_item = self.Append(wx.ID_ANY, "播放媒体(&P)\tP", "播放选中的媒体文件")
            self.Bind(wx.EVT_MENU, self.on_play_media, play_item)
            self.AppendSeparator()

        # 网页打开(W)
        web_open_item = self.Append(wx.ID_ANY, "网页打开(&W)\tCtrl+W", "在浏览器中打开文件")
        self.Bind(wx.EVT_MENU, self.on_web_open, web_open_item)

        self.AppendSeparator()

        # 查看说明(R)
        view_info_item = self.Append(wx.ID_ANY, "查看说明(&R)\tShift+Enter", "查看文件详细信息")
        self.Bind(wx.EVT_MENU, self.on_view_info, view_info_item)

        # 批量下载
        batch_download_item = self.Append(wx.ID_ANY, "批量下载(&B)\tAlt+Shift+Enter", "批量下载选中的文件")
        self.Bind(wx.EVT_MENU, self.on_batch_download, batch_download_item)

        # 根据选中项启用/禁用菜单项
        self._update_menu_states()

    def _update_menu_states(self):
        """更新菜单项状态"""
        selected_items = self.file_list_ctrl.get_selected_items()
        has_selection = len(selected_items) > 0

        # 获取菜单项并转换为列表以支持切片操作
        menu_items = list(self.GetMenuItems())

        # 检查菜单项数量，避免索引错误
        if len(menu_items) >= 5:
            # 打开和网页打开：需要选中项
            for item in menu_items[:2]:  # 前两个菜单项
                item.Enable(has_selection)

            # 查看说明：需要选中项（第4个菜单项，索引3）
            menu_items[3].Enable(has_selection)

            # 批量下载：需要选中项（暂时启用，点击提示开发中）
            menu_items[4].Enable(has_selection)

    def on_open(self, event):
        """打开文件或文件夹"""
        selected_items = self.file_list_ctrl.get_selected_items()
        if selected_items:
            file_item = selected_items[0]  # 只处理第一个选中项
            self.parent_window.on_context_open(file_item)

    def on_play_media(self, event):
        """播放媒体文件"""
        selected_items = self.file_list_ctrl.get_selected_items()
        if selected_items:
            file_item = selected_items[0]  # 只处理第一个选中项
            self.parent_window.on_context_play_media(file_item)

    def on_web_open(self, event):
        """在浏览器中打开文件"""
        selected_items = self.file_list_ctrl.get_selected_items()
        if selected_items:
            file_item = selected_items[0]  # 只处理第一个选中项
            self.parent_window.on_context_web_open(file_item)

    def on_view_info(self, event):
        """查看文件信息"""
        selected_items = self.file_list_ctrl.get_selected_items()
        if selected_items:
            file_item = selected_items[0]  # 只处理第一个选中项
            self.parent_window.on_context_view_info(file_item)

    def on_batch_download(self, event):
        """批量下载"""
        selected_items = self.file_list_ctrl.get_selected_items()
        if selected_items:
            self.parent_window.on_context_batch_download(selected_items)
