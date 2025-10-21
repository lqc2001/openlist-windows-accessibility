#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VLC下载窗口
提供VLC便携包下载进度显示和管理功能
"""

import wx
import wx.lib.agw.pygauge as pygauge
import threading
import time
from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from media.vlc_downloader import VLCDownloader

class VLCDownloadWindow(wx.Dialog):
    """VLC下载窗口"""

    def __init__(self, parent, title="VLC便携版下载"):
        super().__init__(parent, title=title, size=(500, 350),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        # 初始化变量
        self.project_root = Path(__file__).parent.parent.parent
        self.downloader = VLCDownloader(self.project_root)
        self.download_thread = None
        self.is_downloading = False

        # 创建UI
        self.init_ui()
        self.Center()

        # 检查当前VLC状态
        self.check_vlc_status()

    def init_ui(self):
        """初始化用户界面"""
        # 主面板
        main_panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # 标题
        title_label = wx.StaticText(main_panel, label="VLC便携版下载管理")
        title_font = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        title_label.SetFont(title_font)
        main_sizer.Add(title_label, 0, wx.ALL | wx.CENTER, 10)

        # 状态面板
        status_box = wx.StaticBox(main_panel, label="VLC状态")
        status_box_sizer = wx.StaticBoxSizer(status_box, wx.VERTICAL)

        # VLC状态信息
        self.status_label = wx.StaticText(main_panel, label="检查中...")
        self.version_label = wx.StaticText(main_panel, label="")
        self.path_label = wx.StaticText(main_panel, label="")

        status_box_sizer.Add(self.status_label, 0, wx.ALL, 5)
        status_box_sizer.Add(self.version_label, 0, wx.ALL, 5)
        status_box_sizer.Add(self.path_label, 0, wx.ALL, 5)

        main_sizer.Add(status_box_sizer, 0, wx.ALL | wx.EXPAND, 10)

        # 下载进度面板
        progress_box = wx.StaticBox(main_panel, label="下载进度")
        progress_box_sizer = wx.StaticBoxSizer(progress_box, wx.VERTICAL)

        # 进度条
        self.progress_gauge = pygauge.PyGauge(main_panel, size=(450, 25))
        self.progress_gauge.SetBackgroundColour(wx.Colour(240, 240, 240))
        self.progress_gauge.SetBarColour(wx.Colour(0, 120, 215))
        progress_box_sizer.Add(self.progress_gauge, 0, wx.ALL | wx.EXPAND, 5)

        # 进度文本
        self.progress_text = wx.StaticText(main_panel, label="准备就绪")
        progress_box_sizer.Add(self.progress_text, 0, wx.ALL | wx.CENTER, 5)

        main_sizer.Add(progress_box_sizer, 0, wx.ALL | wx.EXPAND, 10)

        # 下载信息
        self.download_info_label = wx.StaticText(main_panel, label="")
        main_sizer.Add(self.download_info_label, 0, wx.ALL | wx.CENTER, 5)

        # 按钮面板
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.download_btn = wx.Button(main_panel, label="下载VLC便携版")
        self.download_btn.SetName("下载VLC便携版按钮")
        self.download_btn.SetHelpText("下载官方VLC便携版到项目目录")

        self.test_btn = wx.Button(main_panel, label="测试VLC")
        self.test_btn.SetName("测试VLC按钮")
        self.test_btn.SetHelpText("测试VLC播放器功能")
        self.test_btn.Enable(False)

        self.close_btn = wx.Button(main_panel, label="关闭")
        self.close_btn.SetName("关闭按钮")
        self.close_btn.SetHelpText("关闭下载窗口")

        button_sizer.Add(self.download_btn, 0, wx.ALL, 5)
        button_sizer.Add(self.test_btn, 0, wx.ALL, 5)
        button_sizer.Add(wx.StaticText(main_panel, label=""), 1, wx.EXPAND)  # 弹性空间
        button_sizer.Add(self.close_btn, 0, wx.ALL, 5)

        main_sizer.Add(button_sizer, 0, wx.ALL | wx.EXPAND, 10)

        main_panel.SetSizer(main_sizer)

        # 绑定事件
        self.download_btn.Bind(wx.EVT_BUTTON, self.on_download)
        self.test_btn.Bind(wx.EVT_BUTTON, self.on_test)
        self.close_btn.Bind(wx.EVT_BUTTON, self.on_close)

        # 设置无障碍属性
        self.SetName("VLC下载窗口")
        self.SetHelpText("下载和管理VLC便携版播放器")

    def check_vlc_status(self):
        """检查VLC状态"""
        info = self.downloader.get_vlc_info()

        if info['installed']:
            self.status_label.SetLabel("状态: ✅ 已安装")
            self.version_label.SetLabel(f"版本: {info['version']}")
            self.path_label.SetLabel(f"路径: {info['path']}")
            self.download_btn.SetLabel("重新下载")
            self.test_btn.Enable(True)

            # 读取文件大小信息
            try:
                vlc_exe = Path(info['exe_path'])
                if vlc_exe.exists():
                    size_mb = vlc_exe.stat().st_size / (1024 * 1024)
                    self.download_info_label.SetLabel(f"VLC.exe大小: {size_mb:.1f}MB")
            except:
                pass
        else:
            self.status_label.SetLabel("状态: ❌ 未安装")
            self.version_label.SetLabel("版本: 需要下载")
            self.path_label.SetLabel("路径: 未安装")
            self.download_btn.SetLabel("下载VLC便携版")
            self.test_btn.Enable(False)

            # 显示下载大小
            if info['download_size']:
                size_mb = info['download_size'] / (1024 * 1024)
                self.download_info_label.SetLabel(f"下载大小: {size_mb:.1f}MB")
            else:
                self.download_info_label.SetLabel("获取下载信息中...")

    def on_download(self, event):
        """下载按钮事件"""
        if self.is_downloading:
            # 正在下载中，显示取消确认
            dlg = wx.MessageDialog(self, "确定要取消下载吗？", "确认取消",
                                  wx.YES_NO | wx.ICON_QUESTION)
            if dlg.ShowModal() == wx.ID_YES:
                self.is_downloading = False
                self.download_btn.SetLabel("下载VLC便携版")
                self.progress_text.SetLabel("下载已取消")
            dlg.Destroy()
            return

        # 检查是否已安装
        info = self.downloader.get_vlc_info()
        if info['installed']:
            dlg = wx.MessageDialog(self,
                                  f"VLC便携版 {info['version']} 已安装。\n\n是否要重新下载？",
                                  "确认重新下载",
                                  wx.YES_NO | wx.ICON_QUESTION)
            if dlg.ShowModal() != wx.ID_YES:
                dlg.Destroy()
                return
            dlg.Destroy()

        # 开始下载
        self.start_download()

    def start_download(self):
        """开始下载"""
        self.is_downloading = True
        self.download_btn.SetLabel("取消下载")
        self.progress_gauge.SetValue(0)
        self.progress_text.SetLabel("准备下载...")

        # 在后台线程中下载
        self.download_thread = threading.Thread(target=self.download_worker)
        self.download_thread.daemon = True
        self.download_thread.start()

    def download_worker(self):
        """下载工作线程"""
        def progress_callback(progress, status):
            wx.CallAfter(self.update_progress, progress, status)

        success = self.downloader.download_vlc(progress_callback)

        # 下载完成
        wx.CallAfter(self.download_completed, success)

    def update_progress(self, progress, status):
        """更新下载进度"""
        if not self.is_downloading:
            return

        self.progress_gauge.SetValue(int(progress))
        self.progress_text.SetLabel(status)

        # 更新窗口标题显示进度
        self.SetTitle(f"VLC下载 - {progress:.1f}%")

    def download_completed(self, success):
        """下载完成处理"""
        self.is_downloading = False
        self.download_btn.SetLabel("下载VLC便携版")
        self.SetTitle("VLC便携版下载管理")

        if success:
            self.progress_text.SetLabel("✅ 下载完成!")
            wx.MessageBox("VLC便携版下载成功!\n\n现在可以使用媒体播放功能了。",
                         "下载成功", wx.OK | wx.ICON_INFORMATION)

            # 重新检查状态
            self.check_vlc_status()
        else:
            self.progress_text.SetLabel("❌ 下载失败")
            wx.MessageBox(f"VLC下载失败:\n{self.downloader.download_status}",
                         "下载失败", wx.OK | wx.ICON_ERROR)

    def on_test(self, event):
        """测试VLC功能"""
        info = self.downloader.get_vlc_info()
        if not info['installed']:
            wx.MessageBox("VLC未安装，无法测试", "错误", wx.OK | wx.ICON_ERROR)
            return

        try:
            # 测试导入VLC库
            vlc_path = info['dll_path']
            if vlc_path and Path(vlc_path).exists():
                # 添加VLC路径到环境变量
                import os
                vlc_dir = str(Path(vlc_path).parent)
                if vlc_dir not in os.environ['PATH']:
                    os.environ['PATH'] = vlc_dir + os.pathsep + os.environ['PATH']

                # 尝试导入VLC
                import vlc
                instance = vlc.Instance()
                player = instance.media_player_new()
                player.release()
                instance.release()

                wx.MessageBox("✅ VLC测试成功!\n\nVLC库可以正常加载，媒体播放功能可用。",
                             "测试成功", wx.OK | wx.ICON_INFORMATION)
            else:
                wx.MessageBox("❌ VLC测试失败\n\n找不到VLC库文件",
                             "测试失败", wx.OK | wx.ICON_ERROR)

        except Exception as e:
            wx.MessageBox(f"❌ VLC测试失败\n\n错误信息: {str(e)}",
                         "测试失败", wx.OK | wx.ICON_ERROR)

    def on_close(self, event):
        """关闭窗口"""
        if self.is_downloading:
            dlg = wx.MessageDialog(self, "正在下载中，确定要关闭吗？", "确认关闭",
                                  wx.YES_NO | wx.ICON_QUESTION)
            if dlg.ShowModal() != wx.ID_YES:
                dlg.Destroy()
                return
            dlg.Destroy()

            self.is_downloading = False

        self.Destroy()

def main():
    """测试VLC下载窗口"""
    print("VLC下载窗口测试")
    print("=" * 50)

    app = wx.App()
    frame = VLCDownloadWindow(None)
    frame.ShowModal()
    frame.Destroy()
    app.Destroy()

    print("测试完成")

if __name__ == "__main__":
    main()