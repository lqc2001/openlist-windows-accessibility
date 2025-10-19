
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
