#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务器选择和登录对话框
程序启动时的第一个界面，用于选择服务器并登录
"""

import wx
from src.core.logger import get_logger
from src.core.config_manager import ConfigManager
from src.core.version import VERSION
from src.ui.server_dialog import ServerDialog
from src.api.openlist_client import OpenListClient


class ServerSelectDialog(wx.Frame):
    """服务器选择和登录窗口"""

    def __init__(self):
        """
        初始化服务器选择窗口
        """
        # 创建主窗口
        style = wx.DEFAULT_FRAME_STYLE
        title = "选择服务器登录 - OpenList管理器"
        super().__init__(None, title=title, size=(500, 400), style=style)

        self.logger = get_logger()
        self.config_manager = ConfigManager()
        self.authenticated_server = None
        self.authenticated_client = None

        # 创建主面板
        self.panel = wx.Panel(self)

        # 初始化UI
        self._create_ui()
        self._create_menu()
        self._setup_accelerators()

        # 加载服务器列表
        self._load_servers()

        # 居中显示
        self.Center()

        self.logger.debug("服务器选择对话框初始化完成")

    def _create_ui(self):
        """创建用户界面"""
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # 服务器选择区域
        server_sizer = wx.BoxSizer(wx.HORIZONTAL)

        server_label = wx.StaticText(self.panel, label="服务器选择:")
        server_label.SetMinSize((80, -1))

        self.server_combo = wx.Choice(self.panel)
        self.server_combo.SetMinSize((300, -1))
        self.server_combo.SetName("服务器选择")
        self.server_combo.SetHelpText("选择要连接的OpenList服务器，按回车连接")

        server_sizer.Add(server_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        server_sizer.Add(self.server_combo, 1, wx.EXPAND)
        main_sizer.Add(server_sizer, 0, wx.ALL | wx.EXPAND, 15)

        # 按钮区域
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.connect_btn = wx.Button(self.panel, label="连接(&L)")
        self.connect_btn.SetName("连接服务器")
        self.connect_btn.SetHelpText("连接到选中的OpenList服务器 (Alt+L)")
        button_sizer.Add(self.connect_btn, 0, wx.RIGHT, 5)

        self.add_btn = wx.Button(self.panel, label="添加(&A)")
        self.add_btn.SetName("添加服务器")
        self.add_btn.SetHelpText("添加新的OpenList服务器 (Alt+A)")
        button_sizer.Add(self.add_btn, 0, wx.RIGHT, 5)

        self.edit_btn = wx.Button(self.panel, label="编辑(&E)")
        self.edit_btn.SetName("编辑服务器")
        self.edit_btn.SetHelpText("编辑选中的服务器配置 (Alt+E)")
        button_sizer.Add(self.edit_btn, 0, wx.RIGHT, 5)

        self.delete_btn = wx.Button(self.panel, label="删除(&D)")
        self.delete_btn.SetName("删除服务器")
        self.delete_btn.SetHelpText("删除选中的服务器 (Alt+D)")
        button_sizer.Add(self.delete_btn, 0)

        main_sizer.Add(button_sizer, 0, wx.ALL | wx.EXPAND, 15)

        # 分隔线
        main_sizer.Add(wx.StaticLine(self.panel), 0, wx.ALL | wx.EXPAND, 10)

        # 连接状态区域
        status_label = wx.StaticText(self.panel, label="📊 服务器连接状态")
        status_label.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        main_sizer.Add(status_label, 0, wx.ALL | wx.LEFT, 15)

        self.status_text = wx.StaticText(self.panel, label="请选择服务器并点击连接")
        self.status_text.SetForegroundColour(wx.Colour(100, 100, 100))
        main_sizer.Add(self.status_text, 0, wx.ALL | wx.EXPAND | wx.LEFT, 15)

        # 添加空白区域
        main_sizer.AddStretchSpacer()

        self.panel.SetSizer(main_sizer)

        # 绑定事件
        self._bind_events()

    def _create_menu(self):
        """创建菜单栏"""
        menubar = wx.MenuBar()

        # 文件菜单
        file_menu = wx.Menu()
        connect_item = file_menu.Append(wx.ID_ANY, "连接(&L)\tAlt+L", "连接到选中的服务器")
        file_menu.AppendSeparator()
        add_item = file_menu.Append(wx.ID_ANY, "添加服务器(&A)\tAlt+A", "添加新的服务器")
        edit_item = file_menu.Append(wx.ID_ANY, "编辑服务器(&E)\tAlt+E", "编辑选中的服务器")
        delete_item = file_menu.Append(wx.ID_ANY, "删除服务器(&D)\tAlt+D", "删除选中的服务器")
        file_menu.AppendSeparator()
        exit_item = file_menu.Append(wx.ID_EXIT, "退出(&X)\tAlt+F4", "退出程序")

        # 帮助菜单
        help_menu = wx.Menu()
        about_item = help_menu.Append(wx.ID_ABOUT, "关于(&H)\tF1", "关于程序")

        # 添加到菜单栏
        menubar.Append(file_menu, "文件(&F)")
        menubar.Append(help_menu, "帮助(&H)")

        self.SetMenuBar(menubar)

        # 绑定菜单事件
        self.Bind(wx.EVT_MENU, self.on_connect, connect_item)
        self.Bind(wx.EVT_MENU, self.on_add_server, add_item)
        self.Bind(wx.EVT_MENU, self.on_edit_server, edit_item)
        self.Bind(wx.EVT_MENU, self.on_delete_server, delete_item)
        self.Bind(wx.EVT_MENU, self.on_exit, exit_item)
        self.Bind(wx.EVT_MENU, self.on_about, about_item)

    def _setup_accelerators(self):
        """设置快捷键"""
        accel_tbl = wx.AcceleratorTable([
            (wx.ACCEL_ALT, ord('L'), wx.ID_HIGHEST + 1),  # Alt+L 连接
            (wx.ACCEL_ALT, ord('A'), wx.ID_HIGHEST + 2),  # Alt+A 添加
            (wx.ACCEL_ALT, ord('E'), wx.ID_HIGHEST + 3),  # Alt+E 编辑
            (wx.ACCEL_ALT, ord('D'), wx.ID_HIGHEST + 4),  # Alt+D 删除
            (wx.ACCEL_NORMAL, wx.WXK_F1, wx.ID_ABOUT),   # F1 关于
        ])
        self.SetAcceleratorTable(accel_tbl)

        # 绑定快捷键事件
        self.Bind(wx.EVT_MENU, self.on_connect_hotkey, id=wx.ID_HIGHEST + 1)
        self.Bind(wx.EVT_MENU, self.on_add_server, id=wx.ID_HIGHEST + 2)
        self.Bind(wx.EVT_MENU, self.on_edit_server, id=wx.ID_HIGHEST + 3)
        self.Bind(wx.EVT_MENU, self.on_delete_server, id=wx.ID_HIGHEST + 4)

    def _bind_events(self):
        """绑定事件"""
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_BUTTON, self.on_connect, self.connect_btn)
        self.Bind(wx.EVT_BUTTON, self.on_add_server, self.add_btn)
        self.Bind(wx.EVT_BUTTON, self.on_edit_server, self.edit_btn)
        self.Bind(wx.EVT_BUTTON, self.on_delete_server, self.delete_btn)

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
        self.edit_btn.Enable(True)
        self.delete_btn.Enable(True)

    def _update_status(self, message, color=None):
        """更新状态显示"""
        self.status_text.SetLabel(message)
        if color:
            self.status_text.SetForegroundColour(color)
        else:
            self.status_text.SetForegroundColour(wx.Colour(100, 100, 100))

        # 强制更新显示
        self.Layout()
        self.Refresh()
        self.Update()

        self.logger.info(f"状态更新: {message}")

    def _authenticate_server(self, server):
        """认证并连接到服务器"""
        try:
            self._update_status("连接中...", wx.Colour(0, 100, 200))
            self.logger.info(f"开始连接到服务器: {server.get('name')}")

            # 强制UI更新
            self.Update()
            wx.Yield()

            # 构建完整URL
            url = server['url']
            port = server.get('port', '')

            if port:
                if url.endswith('/'):
                    url = url[:-1]
                url += f":{port}"

            # 验证服务器地址格式
            if not url or not url.startswith(('http://', 'https://')):
                error_msg = "服务器地址格式无效"
                self._update_status(f"连接失败: {error_msg}", wx.Colour(200, 0, 0))
                return False, None, error_msg

            # 创建客户端
            try:
                client = OpenListClient(
                    url,
                    server['username'],
                    server['password'],
                    server.get('ignore_ssl_errors', False)
                )
            except Exception as e:
                error_msg = f"创建客户端失败: {str(e)}"
                self._update_status(f"连接失败: {error_msg}", wx.Colour(200, 0, 0))
                return False, None, error_msg

            # 测试连接
            try:
                success, message = client.test_connection()
                if not success:
                    error_msg = f"连接测试失败: {message}"
                    self._update_status(error_msg, wx.Colour(200, 0, 0))
                    return False, None, error_msg
            except Exception as e:
                error_msg = f"连接测试异常: {str(e)}"
                self._update_status(error_msg, wx.Colour(200, 0, 0))
                return False, None, error_msg

            # 登录
            try:
                client.login()
            except Exception as e:
                error_msg = f"登录失败: {str(e)}"
                self._update_status(error_msg, wx.Colour(200, 0, 0))
                return False, None, error_msg

            # 连接成功
            self._update_status("连接成功，准备打开文件管理器...", wx.Colour(0, 150, 0))
            self.logger.info(f"成功连接到服务器: {server.get('name')}")

            # 保存最后选中的服务器
            self.config_manager.set_last_selected(server.get('id'))

            return True, client, "连接成功"

        except Exception as e:
            error_msg = f"连接过程中发生未知错误: {str(e)}"
            self.logger.error(f"连接失败: {e}")
            self._update_status(error_msg, wx.Colour(200, 0, 0))
            return False, None, error_msg

    def get_authenticated_server(self):
        """获取认证成功的服务器信息"""
        return self.authenticated_server, self.authenticated_client

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
            self.on_connect(event)

    def on_connect(self, event):
        """连接服务器事件"""
        selection = self.server_combo.GetSelection()
        if selection == wx.NOT_FOUND:
            wx.MessageBox("请先选择要连接的服务器", "提示", wx.OK | wx.ICON_INFORMATION)
            return

        display_name = self.server_combo.GetStringSelection()
        server = self.server_data.get(display_name)
        if server:
            success, client, message = self._authenticate_server(server)
            if success:
                self.authenticated_server = server
                self.authenticated_client = client
                self.Close()  # 关闭窗口
            else:
                wx.MessageBox(f"连接失败: {message}", "连接错误", wx.OK | wx.ICON_ERROR)

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
            self.on_connect(event)

    def on_about(self, event):
        """关于对话框事件"""
        wx.MessageBox(
            f"OpenList管理器 v{VERSION}\n\n"
            "一个简单的OpenList服务器连接管理工具\n\n"
            "功能：\n"
            "• 添加、编辑、删除OpenList服务器\n"
            "• 连接到服务器并管理文件\n"
            "• 密码加密存储",
            "关于 OpenList管理器",
            wx.OK | wx.ICON_INFORMATION
        )

    def on_exit(self, event):
        """退出事件"""
        self.Close(True)

    def on_close(self, event):
        """窗口关闭事件"""
        # 如果没有认证成功，清除认证信息
        if not self.authenticated_server or not self.authenticated_client:
            self.authenticated_server = None
            self.authenticated_client = None
        event.Skip()