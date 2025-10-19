#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务器添加/编辑对话框
用于添加或编辑OpenList服务器配置
"""

import wx
from src.core.logger import get_logger


class ServerDialog(wx.Dialog):
    """服务器配置对话框"""

    def __init__(self, parent, config_manager, server=None):
        """
        初始化服务器配置对话框

        Args:
            parent: 父窗口
            config_manager: 配置管理器
            server: 要编辑的服务器配置，None表示新建
        """
        self.config_manager = config_manager
        self.server = server  # None表示新建，否则表示编辑
        self.is_editing = server is not None

        # 创建对话框
        style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        title = "编辑服务器" if self.is_editing else "添加服务器"
        super().__init__(parent, title=title, size=(450, 350), style=style)

        self.logger = get_logger()

        # 初始化UI
        self._create_ui()

        # 如果是编辑模式，加载数据
        if self.is_editing:
            self._load_server_data()

        # 居中显示
        self.Center()

        self.logger.debug(f"{'编辑' if self.is_editing else '添加'}服务器对话框初始化完成")

    def _create_ui(self):
        """创建用户界面"""
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # 表单区域
        form_sizer = wx.FlexGridSizer(rows=0, cols=2, vgap=10, hgap=10)

        # 服务器名称
        name_label = wx.StaticText(self, label="服务器名称:")
        self.name_ctrl = wx.TextCtrl(self)
        self.name_ctrl.SetName("服务器名称")
        self.name_ctrl.SetHelpText("输入在服务器列表中显示的名称，如：我的OpenList服务器")

        # 服务器地址
        url_label = wx.StaticText(self, label="服务器地址:")
        self.url_ctrl = wx.TextCtrl(self)
        self.url_ctrl.SetName("服务器地址")
        self.url_ctrl.SetHelpText("输入OpenList服务器的完整地址，如：example.com 或 https://example.com")

        # 端口
        port_label = wx.StaticText(self, label="端口:")
        self.port_ctrl = wx.TextCtrl(self)
        self.port_ctrl.SetName("端口")
        self.port_ctrl.SetHelpText("输入服务器端口号，留空则使用默认端口（80/443）")

        # 用户名
        username_label = wx.StaticText(self, label="用户名:")
        self.username_ctrl = wx.TextCtrl(self)
        self.username_ctrl.SetName("用户名")
        self.username_ctrl.SetHelpText("输入用于登录OpenList服务器的用户名")

        # 密码
        password_label = wx.StaticText(self, label="密码:")
        self.password_ctrl = wx.TextCtrl(self, style=wx.TE_PASSWORD)
        self.password_ctrl.SetName("密码")
        self.password_ctrl.SetHelpText("输入用于登录OpenList服务器的密码")

        # SSL选项
        ssl_label = wx.StaticText(self, label="SSL选项:")
        self.ssl_checkbox = wx.CheckBox(self, label="忽略SSL证书错误")
        self.ssl_checkbox.SetName("SSL选项")
        self.ssl_checkbox.SetHelpText("如果服务器使用自签名证书，请勾选此项")

        # 添加到表单
        form_sizer.Add(name_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        form_sizer.Add(self.name_ctrl, 1, wx.EXPAND)

        form_sizer.Add(url_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        form_sizer.Add(self.url_ctrl, 1, wx.EXPAND)

        form_sizer.Add(port_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        form_sizer.Add(self.port_ctrl, 1, wx.EXPAND)

        form_sizer.Add(username_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        form_sizer.Add(self.username_ctrl, 1, wx.EXPAND)

        form_sizer.Add(password_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        form_sizer.Add(self.password_ctrl, 1, wx.EXPAND)

        form_sizer.Add(ssl_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_TOP)
        form_sizer.Add(self.ssl_checkbox, 1, wx.ALIGN_CENTER_VERTICAL)

        form_sizer.AddGrowableCol(1)
        main_sizer.Add(form_sizer, 0, wx.ALL | wx.EXPAND, 20)

        # 提示信息
        if self.is_editing:
            hint_text = wx.StaticText(self, label="提示：如果不想修改密码，请留空密码字段")
            hint_text.SetForegroundColour(wx.Colour(128, 128, 128))
            main_sizer.Add(hint_text, 0, wx.ALL | wx.CENTER, 5)

        # 按钮区域
        button_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        if button_sizer:
            main_sizer.Add(button_sizer, 0, wx.ALL | wx.EXPAND, 10)

        self.SetSizer(main_sizer)

        # 绑定事件
        self.Bind(wx.EVT_TEXT, self.on_text_changed)
        self.Bind(wx.EVT_BUTTON, self.on_ok, id=wx.ID_OK)

        # 设置初始焦点
        self.name_ctrl.SetFocus()

        # 初始验证
        self._validate_form()

    def _load_server_data(self):
        """加载服务器数据（编辑模式）"""
        if self.server:
            self.name_ctrl.SetValue(self.server.get('name', ''))
            self.url_ctrl.SetValue(self.server.get('url', ''))
            self.port_ctrl.SetValue(str(self.server.get('port', '')))
            self.username_ctrl.SetValue(self.server.get('username', ''))
            self.password_ctrl.SetValue('')  # 编辑模式下密码为空
            self.ssl_checkbox.SetValue(self.server.get('ignore_ssl_errors', False))

    def _validate_form(self):
        """验证表单数据"""
        name = self.name_ctrl.GetValue().strip()
        url = self.url_ctrl.GetValue().strip()
        username = self.username_ctrl.GetValue().strip()

        is_valid = False

        if name and url and username:
            # 验证端口格式
            port = self.port_ctrl.GetValue().strip()
            if port:
                try:
                    port_num = int(port)
                    if port_num < 1 or port_num > 65535:
                        is_valid = False
                    else:
                        is_valid = True
                except ValueError:
                    is_valid = False
            else:
                is_valid = True

        # 启用/禁用OK按钮
        ok_button = self.FindWindowById(wx.ID_OK)
        if ok_button:
            ok_button.Enable(is_valid)

        return is_valid

    def on_text_changed(self, event):
        """文本变化事件"""
        self._validate_form()
        event.Skip()

    def on_ok(self, event):
        """确定按钮事件"""
        if not self._validate_form():
            if self.is_editing:
                wx.MessageBox("请检查输入的服务器信息", "提示", wx.OK | wx.ICON_WARNING)
            else:
                wx.MessageBox("请填写完整的服务器信息", "提示", wx.OK | wx.ICON_WARNING)
            return

        # 验证服务器名称格式
        name = self.name_ctrl.GetValue().strip()
        if len(name) < 2:
            wx.MessageBox("服务器名称至少需要2个字符", "提示", wx.OK | wx.ICON_WARNING)
            return

        # 验证URL格式
        url = self.url_ctrl.GetValue().strip()
        if not self._is_valid_url(url):
            wx.MessageBox("服务器地址格式无效", "提示", wx.OK | wx.ICON_WARNING)
            return

        # 验证用户名格式
        username = self.username_ctrl.GetValue().strip()
        if len(username) < 2:
            wx.MessageBox("用户名至少需要2个字符", "提示", wx.OK | wx.ICON_WARNING)
            return

        # 验证密码格式
        password = self.password_ctrl.GetValue()
        if not self.is_editing and len(password) < 3:  # 新建模式下密码必须填写
            wx.MessageBox("密码至少需要3个字符", "提示", wx.OK | wx.ICON_WARNING)
            return

        # 获取服务器数据
        server_data = self.get_server_data()

        # 如果是编辑模式，保持原有ID
        if self.is_editing and self.server:
            server_data['id'] = self.server.get('id')

        # 保存服务器配置
        try:
            success = self.config_manager.save_server(server_data)
            if not success:
                wx.MessageBox("保存服务器配置失败", "错误", wx.OK | wx.ICON_ERROR)
                return

            self.logger.info(f"{'编辑' if self.is_editing else '添加'}服务器配置成功: {server_data.get('name')}")

        except Exception as e:
            self.logger.error(f"{'编辑' if self.is_editing else '添加'}服务器配置失败: {e}")
            wx.MessageBox(f"保存服务器配置时发生错误: {e}", "错误", wx.OK | wx.ICON_ERROR)
            return

        event.Skip()  # 关闭对话框

    def _is_valid_url(self, url):
        """验证URL格式"""
        if not url:
            return False

        # 简单的URL验证
        url = self._normalize_url(url)
        return url.startswith(('http://', 'https://'))

    def _normalize_url(self, url):
        """规范化URL"""
        if not url:
            return ""

        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'

        return url

    def get_server_data(self):
        """获取服务器配置数据"""
        url = self._normalize_url(self.url_ctrl.GetValue().strip())
        port = self.port_ctrl.GetValue().strip()

        # 如果没有端口，使用默认端口
        if not port:
            port = 443 if url.startswith('https://') else 80
        else:
            port = int(port)

        data = {
            'name': self.name_ctrl.GetValue().strip(),
            'url': url,
            'port': port,
            'username': self.username_ctrl.GetValue().strip(),
            'ignore_ssl_errors': self.ssl_checkbox.GetValue(),
        }

        # 只有在编辑模式下且输入了密码时才包含密码
        password = self.password_ctrl.GetValue()
        if password:
            data['password'] = password

        return data