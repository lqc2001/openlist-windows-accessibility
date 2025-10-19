#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的OpenList管理器主窗口
专门用于服务器连接管理
"""

import wx
import wx.lib.newevent
import threading
from src.core.logger import get_logger
from src.core.config_manager import ConfigManager
from src.ui.server_dialog import ServerDialog
from src.api.openlist_client import OpenListClient
from src.core.version import get_about_text, get_version_info
from src.ui.audio_player_controller import AudioPlayerController
from src.ui.audio_player_controller import EVT_PLAYER_STATUS, EVT_PLAYER_PROGRESS
from src.media.playlist_manager import PlaylistManager

# 定义连接事件
ConnectionEvent, EVT_CONNECTION = wx.lib.newevent.NewEvent()


class MainFrame(wx.Frame):
    """简化的主窗口类"""

    def __init__(self, config_manager):
        """
        初始化主窗口

        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
        self.logger = get_logger()

        # 连接状态
        self.current_server = None
        self.current_client = None
        self.connection_status = "未连接"

        # 创建主窗口
        style = wx.DEFAULT_FRAME_STYLE
        super().__init__(None, title="OpenList管理器", size=(700, 450), style=style)

        # 初始化音频播放控制器
        self.audio_controller = AudioPlayerController(self)

        # 初始化播放列表管理器
        self.playlist_manager = PlaylistManager()
        self._setup_playlist_callbacks()

        # 初始化UI
        self._create_ui()
        self._create_menu()
        self._create_status_bar()
        self._setup_accelerators()

        # 绑定连接事件
        self.Bind(EVT_CONNECTION, self._on_connection_result)

        # 加载服务器列表
        self._load_servers()

        # 设置焦点到组合框
        self.server_combo.SetFocus()

        # 初始化音频设备菜单
        self._initialize_audio_device_menu()

        self.logger.info("主窗口初始化完成")

    def _create_ui(self):
        """创建用户界面"""
        # 创建主Panel，所有控件都放在Panel上以支持正确的Tab导航
        main_panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # 第一行：服务器选择
        row1_sizer = wx.BoxSizer(wx.HORIZONTAL)

        server_label = wx.StaticText(main_panel, label="服务器选择:")
        server_label.SetMinSize((80, -1))  # 固定标签宽度

        self.server_combo = wx.Choice(main_panel)
        self.server_combo.SetMinSize((300, -1))
        self.server_combo.SetName("服务器选择")
        self.server_combo.SetHelpText("选择要连接的OpenList服务器，按回车连接")

        row1_sizer.Add(server_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row1_sizer.Add(self.server_combo, 1, wx.EXPAND)
        main_sizer.Add(row1_sizer, 0, wx.ALL | wx.EXPAND, 10)

        # 第二行：按钮
        row2_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # 添加空白占位，与标签对齐
        row2_sizer.Add((80, 1))  # 占位符

        # 按钮容器
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.connect_btn = wx.Button(main_panel, label="连接(&L)")
        self.connect_btn.SetName("连接服务器")
        self.connect_btn.SetHelpText("连接到选中的OpenList服务器 (Alt+L)")
        button_sizer.Add(self.connect_btn, 0, wx.RIGHT, 5)

        self.add_btn = wx.Button(main_panel, label="添加(&A)")
        self.add_btn.SetName("添加服务器")
        self.add_btn.SetHelpText("添加新的OpenList服务器 (Alt+A)")
        button_sizer.Add(self.add_btn, 0, wx.RIGHT, 5)

        self.edit_btn = wx.Button(main_panel, label="编辑(&E)")
        self.edit_btn.SetName("编辑服务器")
        self.edit_btn.SetHelpText("编辑选中的服务器配置 (Alt+E)")
        # 保持启用状态以支持Tab导航
        button_sizer.Add(self.edit_btn, 0, wx.RIGHT, 5)

        self.delete_btn = wx.Button(main_panel, label="删除(&D)")
        self.delete_btn.SetName("删除服务器")
        self.delete_btn.SetHelpText("删除选中的服务器 (Alt+D)")
        # 保持启用状态以支持Tab导航
        button_sizer.Add(self.delete_btn, 0)

        row2_sizer.Add(button_sizer, 1, wx.EXPAND)
        main_sizer.Add(row2_sizer, 0, wx.ALL | wx.EXPAND, 10)

        # 分隔线
        main_sizer.Add(wx.StaticLine(main_panel), 0, wx.ALL | wx.EXPAND, 5)

        # 添加空白区域（为将来的文件列表预留）
        main_sizer.AddStretchSpacer()

        main_panel.SetSizer(main_sizer)

        # 绑定事件
        self._bind_events()

        # 在窗口显示时设置初始焦点
        self.Bind(wx.EVT_SHOW, self.on_show)

    def _create_status_bar(self):
        """创建状态栏"""
        # 创建5字段状态栏，所有字段宽度-1（自动调整）
        self.status_bar = self.CreateStatusBar(5)
        self.status_bar.SetStatusWidths([-1, -1, -1, -1, -1])

        # 设置初始状态栏文本
        self.status_bar.SetStatusText("停止", 0)      # 播放状态
        self.status_bar.SetStatusText("00:00/00:00", 1)  # 播放时间
        self.status_bar.SetStatusText("0%", 2)       # 进度百分比
        self.status_bar.SetStatusText("音量:75%", 3)  # 音量
        self.status_bar.SetStatusText("1.0x", 4)     # 倍速

        # 设置状态栏到音频控制器
        self.audio_controller.set_status_bar(self.status_bar)

        # 绑定音频播放器事件
        self.Bind(EVT_PLAYER_STATUS, self.on_player_status)
        self.Bind(EVT_PLAYER_PROGRESS, self.on_player_progress)

    def _create_menu(self):
        """创建菜单栏"""
        menubar = wx.MenuBar()

        # 文件菜单
        file_menu = wx.Menu()
        switch_item = file_menu.Append(wx.ID_ANY, "切换服务器\tCtrl+Tab", "切换到服务器选择")
        file_menu.AppendSeparator()
        exit_item = file_menu.Append(wx.ID_EXIT, "退出\tAlt+F4", "退出程序")

        # 播放菜单
        play_menu = wx.Menu()

        # 音频设备子菜单 - 将在初始化后动态创建
        self.device_menu_placeholder = play_menu.Append(wx.ID_ANY, "音频设备(&D)", "选择音频输出设备")
        play_menu.AppendSeparator()

        # 播放控制
        play_pause_item = play_menu.Append(wx.ID_ANY, "播放/暂停\tCtrl+Home", "播放或暂停当前音频")
        stop_item = play_menu.Append(wx.ID_ANY, "停止\tCtrl+End", "停止播放")
        play_menu.AppendSeparator()

        # 播放列表控制
        previous_item = play_menu.Append(wx.ID_ANY, "上一个\tCtrl+PageUp", "播放上一首音频")
        next_item = play_menu.Append(wx.ID_ANY, "下一个\tCtrl+PageDown", "播放下一首音频")
        play_menu.AppendSeparator()

        # 播放控制
        seek_backward_item = play_menu.Append(wx.ID_ANY, "快退\tCtrl+Left", "快退5秒")
        seek_forward_item = play_menu.Append(wx.ID_ANY, "快进\tCtrl+Right", "快进5秒")
        volume_up_item = play_menu.Append(wx.ID_ANY, "音量加\tCtrl+Up", "增加音量")
        volume_down_item = play_menu.Append(wx.ID_ANY, "音量减\tCtrl+Down", "减少音量")
        play_menu.AppendSeparator()

        # 倍速子菜单
        speed_menu = wx.Menu()
        speed_0_5 = speed_menu.Append(wx.ID_ANY, "0.5x", "设置播放倍速为0.5倍")
        speed_1_0 = speed_menu.Append(wx.ID_ANY, "1.0x", "设置播放倍速为1.0倍")
        speed_1_5 = speed_menu.Append(wx.ID_ANY, "1.5x", "设置播放倍速为1.5倍")
        speed_2_0 = speed_menu.Append(wx.ID_ANY, "2.0x", "设置播放倍速为2.0倍")
        speed_2_5 = speed_menu.Append(wx.ID_ANY, "2.5x", "设置播放倍速为2.5倍")
        speed_3_0 = speed_menu.Append(wx.ID_ANY, "3.0x", "设置播放倍速为3.0倍")

        play_menu.AppendSubMenu(speed_menu, "播放倍速(&P)")

        # 帮助菜单
        help_menu = wx.Menu()
        about_item = help_menu.Append(wx.ID_ABOUT, "关于\tF1", "关于程序")

        # 添加到菜单栏
        menubar.Append(file_menu, "文件(&F)")
        menubar.Append(play_menu, "播放(&P)")
        menubar.Append(help_menu, "帮助(&H)")

        self.SetMenuBar(menubar)

        # 存储菜单项ID以便后续使用
        self.play_menu_items = {
            'play_pause': play_pause_item,
            'stop': stop_item,
            'previous': previous_item,
            'next': next_item,
            'seek_backward': seek_backward_item,
            'seek_forward': seek_forward_item,
            'volume_up': volume_up_item,
            'volume_down': volume_down_item,
            'speed_0_5': speed_0_5,
            'speed_1_0': speed_1_0,
            'speed_1_5': speed_1_5,
            'speed_2_0': speed_2_0,
            'speed_2_5': speed_2_5,
            'speed_3_0': speed_3_0
        }

        # 绑定菜单事件
        self.Bind(wx.EVT_MENU, self.on_switch_server, switch_item)
        self.Bind(wx.EVT_MENU, self.on_exit, exit_item)
        self.Bind(wx.EVT_MENU, self.on_about, about_item)

        # 绑定播放菜单事件
        self.Bind(wx.EVT_MENU, self.on_play_pause, play_pause_item)
        self.Bind(wx.EVT_MENU, self.on_stop, stop_item)
        self.Bind(wx.EVT_MENU, self.on_previous, previous_item)
        self.Bind(wx.EVT_MENU, self.on_next, next_item)
        self.Bind(wx.EVT_MENU, self.on_seek_backward, seek_backward_item)
        self.Bind(wx.EVT_MENU, self.on_seek_forward, seek_forward_item)
        self.Bind(wx.EVT_MENU, self.on_volume_up, volume_up_item)
        self.Bind(wx.EVT_MENU, self.on_volume_down, volume_down_item)

        # 绑定倍速菜单事件
        self.Bind(wx.EVT_MENU, self.on_speed_0_5, speed_0_5)
        self.Bind(wx.EVT_MENU, self.on_speed_1_0, speed_1_0)
        self.Bind(wx.EVT_MENU, self.on_speed_1_5, speed_1_5)
        self.Bind(wx.EVT_MENU, self.on_speed_2_0, speed_2_0)
        self.Bind(wx.EVT_MENU, self.on_speed_2_5, speed_2_5)
        self.Bind(wx.EVT_MENU, self.on_speed_3_0, speed_3_0)

        # 绑定音频设备占位符事件
        self.Bind(wx.EVT_MENU, self.on_device_menu_placeholder, self.device_menu_placeholder)

        # wxPython菜单项不支持SetName和SetHelpText
        # 无障碍功能主要通过菜单项的标签文本来实现

    def _setup_accelerators(self):
        """设置快捷键"""
        accel_tbl = wx.AcceleratorTable([
            # 原有快捷键
            (wx.ACCEL_ALT, ord('L'), wx.ID_HIGHEST + 1),      # Alt+L 连接
            (wx.ACCEL_ALT, ord('A'), wx.ID_HIGHEST + 2),      # Alt+A 添加
            (wx.ACCEL_ALT, ord('E'), wx.ID_HIGHEST + 3),      # Alt+E 编辑
            (wx.ACCEL_ALT, ord('D'), wx.ID_HIGHEST + 4),      # Alt+D 删除
            (wx.ACCEL_NORMAL, wx.WXK_F1, wx.ID_ABOUT),       # F1 关于

            # 播放控制快捷键
            (wx.ACCEL_CTRL, wx.WXK_HOME, wx.ID_HIGHEST + 10),     # Ctrl+Home 播放/暂停
            (wx.ACCEL_CTRL, wx.WXK_END, wx.ID_HIGHEST + 11),       # Ctrl+End 停止
            (wx.ACCEL_CTRL, wx.WXK_PAGEUP, wx.ID_HIGHEST + 12),    # Ctrl+PageUp 上一个
            (wx.ACCEL_CTRL, wx.WXK_PAGEDOWN, wx.ID_HIGHEST + 13),  # Ctrl+PageDown 下一个
            (wx.ACCEL_CTRL, wx.WXK_LEFT, wx.ID_HIGHEST + 14),      # Ctrl+Left 快退
            (wx.ACCEL_CTRL, wx.WXK_RIGHT, wx.ID_HIGHEST + 15),     # Ctrl+Right 快进
            (wx.ACCEL_CTRL, wx.WXK_UP, wx.ID_HIGHEST + 16),        # Ctrl+Up 音量加
            (wx.ACCEL_CTRL, wx.WXK_DOWN, wx.ID_HIGHEST + 17),      # Ctrl+Down 音量减
        ])
        self.SetAcceleratorTable(accel_tbl)

        # 绑定原有快捷键事件
        self.Bind(wx.EVT_MENU, self.on_connect_hotkey, id=wx.ID_HIGHEST + 1)
        self.Bind(wx.EVT_MENU, self.on_add_server, id=wx.ID_HIGHEST + 2)
        self.Bind(wx.EVT_MENU, self.on_edit_server, id=wx.ID_HIGHEST + 3)
        self.Bind(wx.EVT_MENU, self.on_delete_server, id=wx.ID_HIGHEST + 4)

        # 绑定播放控制快捷键事件
        self.Bind(wx.EVT_MENU, self.on_play_pause_hotkey, id=wx.ID_HIGHEST + 10)
        self.Bind(wx.EVT_MENU, self.on_stop_hotkey, id=wx.ID_HIGHEST + 11)
        self.Bind(wx.EVT_MENU, self.on_previous_hotkey, id=wx.ID_HIGHEST + 12)
        self.Bind(wx.EVT_MENU, self.on_next_hotkey, id=wx.ID_HIGHEST + 13)
        self.Bind(wx.EVT_MENU, self.on_seek_backward_hotkey, id=wx.ID_HIGHEST + 14)
        self.Bind(wx.EVT_MENU, self.on_seek_forward_hotkey, id=wx.ID_HIGHEST + 15)
        self.Bind(wx.EVT_MENU, self.on_volume_up_hotkey, id=wx.ID_HIGHEST + 16)
        self.Bind(wx.EVT_MENU, self.on_volume_down_hotkey, id=wx.ID_HIGHEST + 17)

    def _bind_events(self):
        """绑定事件"""
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_BUTTON, self.on_add_server, self.add_btn)
        self.Bind(wx.EVT_BUTTON, self.on_edit_server, self.edit_btn)
        self.Bind(wx.EVT_BUTTON, self.on_delete_server, self.delete_btn)
        self.Bind(wx.EVT_BUTTON, self.on_connect_server, self.connect_btn)

        # 组合框事件
        self.server_combo.Bind(wx.EVT_CHOICE, self.on_server_selected)
        self.server_combo.Bind(wx.EVT_COMBOBOX, self.on_server_text_changed)
        self.server_combo.Bind(wx.EVT_TEXT_ENTER, self.on_server_enter)

    def _load_servers(self):
        """加载服务器列表"""
        servers = self.config_manager.get_servers()
        self.server_combo.Clear()
        self.server_data = {}  # 存储服务器数据，键为显示名称，值为服务器对象

        for server in servers:
            display_name = server.get('name', '未命名服务器')
            self.server_combo.Append(display_name)
            self.server_data[display_name] = server

        # 恢复上次选中的服务器
        last_selected = self.config_manager.get_last_selected()
        if last_selected:
            for i, server in enumerate(servers):
                if server.get('id') == last_selected:
                    self.server_combo.SetSelection(i)
                    self._update_button_states()
                    break

        self.logger.debug(f"加载了{len(servers)}个服务器")

    def _update_button_states(self):
        """更新按钮状态"""
        has_selection = self.server_combo.GetSelection() != wx.NOT_FOUND
        self.connect_btn.Enable(has_selection)
        # 保持编辑和删除按钮可用，这样Tab可以导航到它们
        # 当用户点击时会显示提示信息
        self.edit_btn.Enable(True)
        self.delete_btn.Enable(True)

    def _update_status(self, message, color=None):
        """更新状态显示"""
        self.connection_status = message

        # 更新组合框的描述信息，集成状态信息
        selection = self.server_combo.GetSelection()
        if selection != wx.NOT_FOUND:
            server_name = self.server_combo.GetString(selection)
            self.server_combo.SetHelpText(f"服务器选择：{server_name}，状态：{message}")

        self.logger.info(f"状态更新: {message}")

    def _connect_to_server(self, server):
        """连接到指定服务器（异步）"""
        if self.current_client:
            self._disconnect()

        # 立即更新状态，让用户知道连接开始
        self._update_status("连接中...")
        self.logger.info(f"开始连接到服务器: {server.get('name')}")

        # 禁用连接按钮，防止重复点击
        if hasattr(self, 'connect_btn'):
            self.connect_btn.Enable(False)

        # 在后台线程中执行连接操作
        threading.Thread(
            target=self._connect_in_background,
            args=(server,),
            daemon=True
        ).start()

    def _connect_in_background(self, server):
        """在后台线程中执行连接操作"""
        result = {
            'success': False,
            'message': '',
            'client': None,
            'server_name': server.get('name', '未知服务器')
        }

        try:
            # 构建完整URL
            url = server['url']
            port = server.get('port', '')

            # 如果有端口，添加到URL
            if port:
                if url.endswith('/'):
                    url = url[:-1]
                url += f":{port}"

            # 验证服务器地址格式
            if not url or not url.startswith(('http://', 'https://')):
                result['message'] = "服务器地址格式无效"
                self._post_connection_event(result)
                return

            # 创建客户端
            try:
                client = OpenListClient(
                    url,
                    server['username'],
                    server['password'],
                    server.get('ignore_ssl_errors', False)
                )
            except Exception as e:
                result['message'] = f"创建客户端失败: {str(e)}"
                self._post_connection_event(result)
                return

            # 测试连接
            try:
                success, message = client.test_connection()
                if not success:
                    result['message'] = message
                    self._post_connection_event(result)
                    return
            except Exception as e:
                result['message'] = f"连接测试异常: {str(e)}"
                self._post_connection_event(result)
                return

            # 登录
            try:
                client.login()
                result['success'] = True
                result['message'] = "连接成功"
                result['client'] = client
            except Exception as e:
                result['message'] = f"登录失败: {str(e)}"

        except Exception as e:
            result['message'] = f"连接过程中发生未知错误: {str(e)}"

        # 发送结果到主线程
        self._post_connection_event(result)

    def _post_connection_event(self, result):
        """发送连接结果事件到主线程"""
        try:
            wx.PostEvent(self, ConnectionEvent(**result))
        except Exception as e:
            self.logger.error(f"发送连接事件失败: {e}")

    def _on_connection_result(self, event):
        """处理连接结果"""
        # 重新启用连接按钮
        if hasattr(self, 'connect_btn'):
            self.connect_btn.Enable(True)

        if event.success:
            # 连接成功
            self.current_client = event.client
            self.current_server = event.server_name
            self.connection_status = "已连接"
            self._update_status(f"已连接: {event.server_name}")

            self.logger.info(f"成功连接到服务器: {event.server_name}")

            # 显示成功消息
            wx.MessageBox(
                f"已成功连接到 {event.server_name}",
                "连接成功",
                wx.OK | wx.ICON_INFORMATION
            )
        else:
            # 连接失败
            self.current_client = None
            self.current_server = None
            self.connection_status = "未连接"
            self._update_status(f"连接失败: {event.message}")

            self.logger.error(f"连接服务器失败: {event.message}")

            # 显示错误消息
            wx.MessageBox(
                f"连接失败: {event.message}",
                "连接错误",
                wx.OK | wx.ICON_ERROR
            )

    def _disconnect(self):
        """断开连接"""
        if self.current_client:
            try:
                self.current_client.close()
            except:
                pass
            self.current_client = None

        self.current_server = None
        self._update_status("已断开连接")

    def _normalize_url(self, url):
        """规范化URL"""
        if not url:
            return ""

        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'

        return url

    # 事件处理函数
    def on_server_selected(self, event):
        """服务器选择事件"""
        self._update_button_states()

    def on_server_text_changed(self, event):
        """服务器文本变化事件"""
        self._update_button_states()

    def on_server_enter(self, event):
        """组合框回车事件"""
        selection = self.server_combo.GetSelection()
        if selection != wx.NOT_FOUND:
            display_name = self.server_combo.GetStringSelection()
            server = self.server_data.get(display_name)
            if server:
                self._connect_to_server(server)

    def on_connect_server(self, event):
        """连接服务器按钮事件"""
        selection = self.server_combo.GetSelection()
        if selection == wx.NOT_FOUND:
            wx.MessageBox("请先选择要连接的服务器", "提示", wx.OK | wx.ICON_INFORMATION)
            return

        display_name = self.server_combo.GetStringSelection()
        server = self.server_data.get(display_name)
        if server:
            self._connect_to_server(server)

    def on_add_server(self, event):
        """添加服务器事件"""
        dlg = ServerDialog(self, self.config_manager)
        if dlg.ShowModal() == wx.ID_OK:
            self._load_servers()
        dlg.Destroy()

    def on_edit_server(self, event):
        """编辑服务器事件"""
        selection = self.server_combo.GetSelection()
        if selection == wx.NOT_FOUND:
            wx.MessageBox("请先选择要编辑的服务器", "提示", wx.OK | wx.ICON_INFORMATION)
            return

        display_name = self.server_combo.GetStringSelection()
        server = self.server_data.get(display_name)
        if server:
            dlg = ServerDialog(self, self.config_manager, server)
            if dlg.ShowModal() == wx.ID_OK:
                self._load_servers()
            dlg.Destroy()

    def on_delete_server(self, event):
        """删除服务器事件"""
        selection = self.server_combo.GetSelection()
        if selection == wx.NOT_FOUND:
            wx.MessageBox("请先选择要删除的服务器", "提示", wx.OK | wx.ICON_INFORMATION)
            return

        display_name = self.server_combo.GetStringSelection()
        server = self.server_data.get(display_name)
        if server:
            dlg = wx.MessageDialog(
                self,
                f"确定要删除服务器 \"{server.get('name', '未命名')}\" 吗？\n\n"
                "此操作不可撤销。",
                "确认删除",
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION
            )

            if dlg.ShowModal() == wx.ID_YES:
                try:
                    self.config_manager.delete_server(server.get('id'))
                    self._load_servers()
                    self.logger.info(f"删除服务器: {server.get('name')}")
                except Exception as e:
                    self.logger.error(f"删除服务器失败: {e}")
                    wx.MessageBox(f"删除服务器失败: {e}", "错误", wx.OK | wx.ICON_ERROR)

            dlg.Destroy()

    def on_connect_hotkey(self, event):
        """连接快捷键事件"""
        selection = self.server_combo.GetSelection()
        if selection == wx.NOT_FOUND:
            wx.MessageBox("请先添加服务器", "提示", wx.OK | wx.ICON_INFORMATION)
            self.on_add_server(event)
        else:
            self.on_server_enter(event)

    def on_switch_server(self, event):
        """切换服务器事件"""
        self.server_combo.SetFocus()

    def _setup_playlist_callbacks(self):
        """设置播放列表回调"""
        self.playlist_manager.on_current_track_changed = self._on_current_track_changed

    def _on_current_track_changed(self):
        """当前曲目变化回调"""
        item = self.playlist_manager.get_current_item()
        if item and self.audio_controller.is_available():
            # 播放新的曲目
            success = self.audio_controller.play_file(item.file_path, item.display_name)
            if not success:
                self.logger.error(f"播放曲目失败: {item.display_name}")

    def add_to_playlist(self, file_path: str, display_name: str = None) -> bool:
        """添加文件到播放列表"""
        return self.playlist_manager.add_item(file_path, display_name)

    def play_file_with_playlist(self, file_path: str, display_name: str = None) -> bool:
        """播放文件并添加到播放列表"""
        # 添加到播放列表
        self.add_to_playlist(file_path, display_name)

        # 设置为当前曲目
        for i, item in enumerate(self.playlist_manager.get_playlist()):
            if item.file_path == file_path:
                self.playlist_manager.set_current_index(i)
                break

        return self.audio_controller.play_file(file_path, display_name)

    def on_about(self, event):
        """关于对话框事件"""
        version_info = get_version_info()
        about_text = get_about_text()

        wx.MessageBox(
            f"{about_text}\n\n"
            "一个简单的OpenList服务器连接管理工具\n\n"
            "功能：\n"
            "• 添加、编辑、删除OpenList服务器\n"
            "• 快捷连接到服务器\n"
            "• 密码加密存储",
            f"关于 {version_info['software_name']}",
            wx.OK | wx.ICON_INFORMATION
        )

    def on_exit(self, event):
        """退出事件"""
        self.Close(True)

    def on_show(self, event):
        """窗口显示事件"""
        if event.IsShown():
            # 窗口显示时设置初始焦点
            wx.CallAfter(self.server_combo.SetFocus)
        event.Skip()

    def on_close(self, event):
        """窗口关闭事件"""
        # 断开连接
        self._disconnect()

        # 清理音频播放控制器
        if hasattr(self, 'audio_controller'):
            self.audio_controller.cleanup()

        event.Skip()

    # 播放控制事件处理方法
    def on_play_pause(self, event):
        """播放/暂停菜单事件"""
        if self.audio_controller.is_available():
            self.audio_controller.play_pause()

    def on_stop(self, event):
        """停止播放菜单事件"""
        if self.audio_controller.is_available():
            self.audio_controller.stop()

    def on_previous(self, event):
        """上一个菜单事件"""
        if not self.audio_controller.is_available():
            wx.MessageBox("音频播放器不可用", "提示", wx.OK | wx.ICON_INFORMATION)
            return

        previous_item = self.playlist_manager.previous_track()
        if previous_item:
            # 播放上一首
            self.logger.info(f"播放上一首: {previous_item.display_name}")
        else:
            # 没有上一首
            current_item = self.playlist_manager.get_current_item()
            if current_item:
                wx.MessageBox(f"已经是第一首: {current_item.display_name}", "提示", wx.OK | wx.ICON_INFORMATION)
            else:
                wx.MessageBox("播放列表为空", "提示", wx.OK | wx.ICON_INFORMATION)

    def on_next(self, event):
        """下一个菜单事件"""
        if not self.audio_controller.is_available():
            wx.MessageBox("音频播放器不可用", "提示", wx.OK | wx.ICON_INFORMATION)
            return

        next_item = self.playlist_manager.next_track()
        if next_item:
            # 播放下一首
            self.logger.info(f"播放下一首: {next_item.display_name}")
        else:
            # 没有下一首
            current_item = self.playlist_manager.get_current_item()
            if current_item:
                wx.MessageBox(f"已经是最后一首: {current_item.display_name}", "提示", wx.OK | wx.ICON_INFORMATION)
            else:
                wx.MessageBox("播放列表为空", "提示", wx.OK | wx.ICON_INFORMATION)

    def on_seek_backward(self, event):
        """快退菜单事件"""
        if self.audio_controller.is_available():
            self.audio_controller.seek_backward(5)

    def on_seek_forward(self, event):
        """快进菜单事件"""
        if self.audio_controller.is_available():
            self.audio_controller.seek_forward(5)

    def on_volume_up(self, event):
        """音量增加菜单事件"""
        if self.audio_controller.is_available():
            self.audio_controller.volume_up(5)

    def on_volume_down(self, event):
        """音量减少菜单事件"""
        if self.audio_controller.is_available():
            self.audio_controller.volume_down(5)

    # 倍速控制事件
    def on_speed_0_5(self, event):
        """0.5倍速"""
        if self.audio_controller.is_available():
            self.audio_controller.set_playback_rate(0.5)

    def on_speed_1_0(self, event):
        """1.0倍速"""
        if self.audio_controller.is_available():
            self.audio_controller.set_playback_rate(1.0)

    def on_speed_1_5(self, event):
        """1.5倍速"""
        if self.audio_controller.is_available():
            self.audio_controller.set_playback_rate(1.5)

    def on_speed_2_0(self, event):
        """2.0倍速"""
        if self.audio_controller.is_available():
            self.audio_controller.set_playback_rate(2.0)

    def on_speed_2_5(self, event):
        """2.5倍速"""
        if self.audio_controller.is_available():
            self.audio_controller.set_playback_rate(2.5)

    def on_speed_3_0(self, event):
        """3.0倍速"""
        if self.audio_controller.is_available():
            self.audio_controller.set_playback_rate(3.0)

    # 音频设备控制事件
    def _initialize_audio_device_menu(self):
        """初始化音频设备菜单"""
        try:
            if not self.audio_controller.is_available():
                self.logger.warning("音频控制器不可用，跳过设备菜单初始化")
                return

            # 获取菜单栏中的播放菜单
            menubar = self.GetMenuBar()
            if not menubar:
                return

            # 找到播放菜单（索引1）
            play_menu = menubar.GetMenu(1)
            if not play_menu:
                return

            # 创建动态设备菜单
            device_menu = self.audio_controller.create_device_menu(play_menu)

            # 找到并删除占位符菜单项
            placeholder_pos = None
            for i in range(play_menu.GetMenuItemCount()):
                item = play_menu.FindItemByPosition(i)
                if item and item.GetId() == self.device_menu_placeholder.GetId():
                    placeholder_pos = i
                    break

            if placeholder_pos is not None:
                # 删除占位符
                play_menu.Remove(self.device_menu_placeholder)

                # 在原位置插入设备子菜单
                play_menu.InsertSubMenu(placeholder_pos, device_menu, "音频设备(&D)")

                # 保存设备菜单引用
                self.device_menu = device_menu

                self.logger.info("音频设备菜单初始化完成")
            else:
                self.logger.warning("未找到设备菜单占位符")

        except Exception as e:
            self.logger.error(f"初始化音频设备菜单失败: {e}")

    def on_device_menu_placeholder(self, event):
        """设备菜单占位符点击事件"""
        # 这个事件应该不会触发，因为占位符会被替换
        self.logger.info("设备菜单占位符被点击")
        pass

    def refresh_device_menu(self):
        """刷新音频设备菜单"""
        try:
            if not hasattr(self, 'device_menu') or not self.device_menu:
                return

            # 清空当前设备菜单
            self.device_menu.Clear()

            # 重新创建设备菜单项
            devices = self.audio_controller.get_available_devices()
            current_device = self.audio_controller.get_current_device()

            for device in devices:
                device_name = device['name']
                device_desc = device['description']

                # 创建菜单项标签
                if device_name == current_device:
                    label = f"✓ {device_name} - {device_desc}"
                else:
                    label = f"{device_name} - {device_desc}"

                # 创建菜单项
                menu_item = self.device_menu.Append(
                    wx.ID_ANY,
                    label,
                    f"切换到 {device_name}"
                )

                # 绑定事件
                self.Bind(
                    wx.EVT_MENU,
                    lambda event, name=device_name: self._on_device_selected(name),
                    menu_item
                )

            # 如果没有设备，添加默认选项
            if not devices:
                self.device_menu.Append(wx.ID_SEPARATOR)
                no_device_item = self.device_menu.Append(
                    wx.ID_ANY,
                    "无可用设备",
                    "未检测到音频输出设备"
                )
                no_device_item.Enable(False)

            self.logger.info("音频设备菜单已刷新")

        except Exception as e:
            self.logger.error(f"刷新音频设备菜单失败: {e}")

    def _on_device_selected(self, device_name: str):
        """设备选择事件处理"""
        try:
            success = self.audio_controller.set_audio_device(device_name)
            if success:
                # 刷新设备菜单以显示新的选中状态
                self.refresh_device_menu()
                self.logger.info(f"已切换到音频设备: {device_name}")
            else:
                wx.MessageBox(
                    f"切换音频设备失败: {device_name}",
                    "错误",
                    wx.OK | wx.ICON_ERROR
                )
        except Exception as e:
            self.logger.error(f"处理设备选择事件失败: {e}")
            wx.MessageBox(
                f"设备切换时发生错误: {str(e)}",
                "错误",
                wx.OK | wx.ICON_ERROR
            )

    # 快捷键事件处理
    def on_play_pause_hotkey(self, event):
        """播放/暂停快捷键事件"""
        self.on_play_pause(event)

    def on_stop_hotkey(self, event):
        """停止快捷键事件"""
        self.on_stop(event)

    def on_previous_hotkey(self, event):
        """上一个快捷键事件"""
        self.on_previous(event)

    def on_next_hotkey(self, event):
        """下一个快捷键事件"""
        self.on_next(event)

    def on_seek_backward_hotkey(self, event):
        """快退快捷键事件"""
        self.on_seek_backward(event)

    def on_seek_forward_hotkey(self, event):
        """快进快捷键事件"""
        self.on_seek_forward(event)

    def on_volume_up_hotkey(self, event):
        """音量增加快捷键事件"""
        self.on_volume_up(event)

    def on_volume_down_hotkey(self, event):
        """音量减少快捷键事件"""
        self.on_volume_down(event)

    # 音频播放器事件处理
    def on_player_status(self, event):
        """播放器状态变化事件"""
        status = event.status
        filename = event.filename

        # 更新菜单项状态
        if hasattr(self, 'play_menu_items'):
            if status == "播放":
                self.play_menu_items['play_pause'].SetItemLabel("暂停\tCtrl+Home")
                self.play_menu_items['play_pause'].SetHelpText("暂停当前音频播放 (Ctrl+Home)")
            elif status == "暂停":
                self.play_menu_items['play_pause'].SetItemLabel("播放\tCtrl+Home")
                self.play_menu_items['play_pause'].SetHelpText("播放当前音频文件 (Ctrl+Home)")
            elif status == "停止":
                self.play_menu_items['play_pause'].SetItemLabel("播放\tCtrl+Home")
                self.play_menu_items['play_pause'].SetHelpText("播放当前音频文件 (Ctrl+Home)")

        # 记录日志
        self.logger.info(f"播放器状态: {status} - {filename}")

    def on_player_progress(self, event):
        """播放器进度变化事件"""
        # 这里可以添加进度相关的处理逻辑
        # 例如更新进度条等
        pass

    def test_audio_playback(self):
        """测试音频播放功能"""
        # 创建一个测试音频文件的路径
        # 这里可以是一个实际的音频文件路径用于测试
        test_file = "test.mp3"  # 替换为实际测试文件

        if self.audio_controller.is_available():
            success = self.audio_controller.play_file(test_file, "测试音频")
            if success:
                self.logger.info("测试音频播放开始")
            else:
                self.logger.error("测试音频播放失败")
        else:
            self.logger.error("音频播放器不可用")

    
    