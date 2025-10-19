#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
媒体播放器测试
测试修复后的媒体播放器界面
"""

import wx
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

class TestApp(wx.App):
    def OnInit(self):
        try:
            # 导入媒体播放器
            from src.ui.media_player_window import MediaPlayerWindow

            # 创建播放器窗口
            frame = MediaPlayerWindow()
            frame.Show()

            self.SetTopWindow(frame)
            print("媒体播放器测试启动成功")
            return True

        except Exception as e:
            print(f"媒体播放器测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """主函数"""
    print("开始媒体播放器测试...")

    app = TestApp()
    if app.MainLoop() == 0:
        print("媒体播放器测试完成")
    else:
        print("媒体播放器测试异常退出")

if __name__ == "__main__":
    main()