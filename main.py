#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenList Windows管理工具
主程序入口文件
"""

import wx
import sys
import os
from src.ui.server_select_dialog import ServerSelectDialog
from src.ui.file_manager_window import FileManagerWindow
from src.core.logger import setup_logger


class OpenListManagerApp(wx.App):
    """OpenList管理器应用类"""

    def OnInit(self):
        """应用初始化"""
        # 设置应用名称
        self.SetAppName("OpenList管理器")

        # 初始化日志系统
        self.logger = setup_logger()
        self.logger.info("OpenList管理器启动")

        # 显示服务器选择对话框
        self.show_server_select_dialog()

        return True

    def show_server_select_dialog(self):
        """显示服务器选择窗口"""
        try:
            # 创建服务器选择窗口
            server_dialog = ServerSelectDialog()
            server_dialog.Show()
            server_dialog.Center()

            # 绑定窗口关闭事件
            server_dialog.Bind(wx.EVT_CLOSE, lambda event: self.on_server_dialog_closed(event, server_dialog))

            self.server_dialog = server_dialog

        except Exception as e:
            self.logger.error(f"启动过程中发生错误: {e}")
            wx.MessageBox(f"启动失败: {e}", "错误", wx.OK | wx.ICON_ERROR)
            self.Exit()

    def on_server_dialog_closed(self, event, server_dialog):
        """服务器选择窗口关闭事件"""
        event.Skip()  # 允许窗口关闭

        # 获取认证结果
        server_info, client = server_dialog.get_authenticated_server()

        if server_info and client:
            self.logger.info(f"成功登录到服务器: {server_info.get('name')}")

            # 创建并显示文件管理窗口
            self.file_manager_window = FileManagerWindow(server_info, client)
            self.file_manager_window.Show()
            self.file_manager_window.Center()
        else:
            # 用户取消或登录失败
            self.logger.info("用户取消了服务器选择或登录失败")
            self.Exit()

        # 销毁服务器选择窗口
        server_dialog.Destroy()

    def OnExit(self):
        """应用退出"""
        if hasattr(self, 'logger'):
            self.logger.info("OpenList管理器退出")
        return 0


def main():
    """主函数"""
    # 抑制libpng警告（可选）
    os.environ['LIBPNG_WARNINGS'] = '0'

    # 设置工作目录为程序所在目录
    if getattr(sys, 'frozen', False):
        # 打包后的可执行文件
        application_path = os.path.dirname(sys.executable)
    else:
        # 开发环境
        application_path = os.path.dirname(os.path.abspath(__file__))

    os.chdir(application_path)

    # 创建并运行应用
    app = OpenListManagerApp()
    app.MainLoop()


if __name__ == "__main__":
    main()