#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复运行时问题
解决VLC插件加载和存储路径问题
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

def fix_vlc_plugin_loading():
    """修复VLC插件加载问题"""
    print("修复VLC插件加载问题")
    print("=" * 40)

    try:
        # 检查当前VLC运行时环境
        vlc_runtime_dir = project_root / "src" / "media" / "vlc_runtime"
        lib_dir = vlc_runtime_dir / "lib"
        plugins_dir = lib_dir / "plugins"

        print(f"VLC运行时目录: {vlc_runtime_dir}")
        print(f"插件目录: {plugins_dir}")

        # 检查插件文件数量
        if plugins_dir.exists():
            plugin_files = list(plugins_dir.glob("**/*.dll"))
            print(f"插件文件数量: {len(plugin_files)}")

            if len(plugin_files) > 0:
                print("   [成功] 插件文件存在")

                # 检查关键插件类型
                plugin_types = set()
                for plugin_file in plugin_files:
                    parent_dir = plugin_file.parent.name
                    plugin_types.add(parent_dir)

                required_types = ['audio_output', 'video_output', 'codec', 'access']
                missing_types = [ptype for ptype in required_types if ptype not in plugin_types]

                if missing_types:
                    print(f"   [警告] 缺少插件类型: {missing_types}")
                else:
                    print("   [成功] 关键插件类型完整")

                # 设置环境变量
                vlc_path = str(lib_dir)
                plugins_path = str(plugins_dir)

                os.environ['VLC_PLUGIN_PATH'] = plugins_path
                os.environ['PATH'] = vlc_path + ';' + os.environ.get('PATH', '')

                print(f"   环境变量设置:")
                print(f"     VLC_PLUGIN_PATH={plugins_path}")
                print(f"     PATH更新={vlc_path}")

                return True
            else:
                print("   [错误] 插件目录为空")
                return False
        else:
            print(f"   [错误] 插件目录不存在: {plugins_dir}")
            return False

    except Exception as e:
        print(f"   [错误] VLC插件修复失败: {e}")
        return False

def create_fallback_url_strategy():
    """创建回退URL策略"""
    print("\n\n创建回退URL策略")
    print("=" * 40)

    try:
        # 分析日志中的路径问题
        original_path = "/opt/czzyfx_openlist_file/歌曲库/扶苏/程响--长街万象.flac"
        print(f"原始路径: {original_path}")

        # 尝试不同的URL构建策略
        base_url = "http://j.yzfycz.cn:5244"

        import urllib.parse

        fallback_urls = [
            # 直接访问
            f"{base_url}{original_path}",
            # 下载路径
            f"{base_url}/d{original_path}",
            # 预览路径
            f"{base_url}/p{original_path}",
            # 相对路径
            f"{base_url}/歌曲库/扶苏/程响--长街万象.flac",
        ]

        # 添加URL编码版本
        encoded_path = urllib.parse.quote(original_path, safe='/')
        fallback_urls.append(f"{base_url}{encoded_path}")

        print("回退URL策略:")
        for i, url in enumerate(fallback_urls, 1):
            print(f"   {i}. {url}")

        # 创建增强的URL获取函数
        enhanced_get_media_url_code = '''
def enhanced_get_media_url(self, file_path):
    """增强的媒体URL获取，包含多种回退策略"""

    # 存储路径映射（根据实际服务器配置调整）
    path_mappings = {
        "/opt/czzyfx_openlist_file/": "/",  # 映射到根目录
        "/opt/czzyfx_openlist_file": "",   # 移除前缀
    }

    # 尝试路径映射
    mapped_path = file_path
    for old_prefix, new_prefix in path_mappings.items():
        if file_path.startswith(old_prefix):
            mapped_path = file_path.replace(old_prefix, new_prefix, 1)
            break

    # URL构建策略
    base_url = self.base_url
    strategies = [
        # 1. 使用原始API（如果可用）
        lambda: self._get_api_url(file_path),
        # 2. 使用映射路径的直接访问
        lambda: f"{base_url}{mapped_path}",
        # 3. 下载链接
        lambda: f"{base_url}/d{mapped_path}",
        # 4. 预览链接
        lambda: f"{base_url}/p{mapped_path}",
        # 5. URL编码版本
        lambda: f"{base_url}{urllib.parse.quote(mapped_path, safe='/')}",
    ]

    # 尝试每个策略
    for i, strategy in enumerate(strategies, 1):
        try:
            url = strategy()
            self.logger.debug(f"策略{i}: {url}")

            # 简单验证URL可访问性（可选）
            if self._test_url_accessible(url):
                self.logger.info(f"使用策略{i}成功: {url}")
                return url

        except Exception as e:
            self.logger.debug(f"策略{i}失败: {e}")
            continue

    # 如果所有策略都失败，返回最简单的直接访问URL
    self.logger.warning("所有策略失败，使用直接访问")
    return f"{base_url}{file_path}"

def _get_api_url(self, file_path):
    """获取API URL（原有逻辑）"""
    try:
        data = {'path': file_path}
        response = self._make_request('POST', '/api/fs/get', data=data)
        if response.get('code') == 200:
            file_data = response.get('data', {})
            raw_url = file_data.get('raw_url')
            if raw_url:
                return raw_url
            file_url = file_data.get('url')
            if file_url:
                return file_url if file_url.startswith('http') else f"{self.base_url}{file_url}"
    except Exception as e:
        self.logger.debug(f"API URL获取失败: {e}")
    raise Exception("API获取失败")

def _test_url_accessible(self, url):
    """测试URL是否可访问（简单HEAD请求）"""
    try:
        import requests
        response = requests.head(url, timeout=5, verify=False)
        return response.status_code == 200
    except:
        return False
'''

        # 保存增强的代码到文件
        enhanced_code_file = project_root / "enhanced_media_url.py"
        with open(enhanced_code_file, 'w', encoding='utf-8') as f:
            f.write(enhanced_get_media_url_code)

        print(f"   增强的URL获取代码已保存到: {enhanced_code_file}")
        return True

    except Exception as e:
        print(f"   [错误] 创建回退策略失败: {e}")
        return False

def test_current_vlc_status():
    """测试当前VLC状态"""
    print("\n\n测试当前VLC状态")
    print("=" * 40)

    try:
        from src.media.vlc_loader import VLCLoader

        loader = VLCLoader(prefer_embedded=True)
        load_info = loader.get_load_info()

        print(f"加载状态: {load_info.get('is_loaded', False)}")
        print(f"加载源: {load_info.get('load_source', '未知')}")

        # 测试播放器创建
        try:
            from src.media.media_player_core import MediaPlayerCore
            player = MediaPlayerCore()
            print("播放器创建: 成功")

            state = player.state
            print(f"播放器状态: {state}")

            player.cleanup()
            print("播放器清理: 成功")
            return True

        except Exception as e:
            print(f"播放器创建失败: {e}")
            return False

    except Exception as e:
        print(f"VLC状态测试失败: {e}")
        return False

def main():
    """主函数"""
    print("修复运行时问题")
    print("=" * 50)

    # 1. 修复VLC插件加载
    vlc_ok = fix_vlc_plugin_loading()

    # 2. 创建回退URL策略
    url_ok = create_fallback_url_strategy()

    # 3. 测试当前VLC状态
    status_ok = test_current_vlc_status()

    print("\n" + "=" * 50)
    print("修复结果:")
    print(f"   VLC插件修复: {'成功' if vlc_ok else '失败'}")
    print(f"   URL策略创建: {'成功' if url_ok else '失败'}")
    print(f"   VLC状态测试: {'成功' if status_ok else '失败'}")

    if vlc_ok and status_ok:
        print("\n[成功] 运行时问题修复完成!")
        print("\n现在可以:")
        print("1. 重新测试媒体文件播放")
        print("2. 验证FLAC文件播放")
        print("3. 检查URL回退策略效果")
    else:
        print("\n[需要进一步调试]")
        print("建议:")
        print("1. 检查VLC环境变量设置")
        print("2. 验证插件文件权限")
        print("3. 测试不同的URL构建策略")

if __name__ == "__main__":
    main()