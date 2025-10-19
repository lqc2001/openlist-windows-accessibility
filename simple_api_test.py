#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的API测试
避免编码问题，专注于核心功能
"""

import requests
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

def test_server():
    """测试服务器"""
    print("OpenList服务器测试")
    print("=" * 30)

    base_url = "http://j.yzfycz.cn:5244"

    try:
        response = requests.get(base_url, timeout=10, verify=False)
        print(f"连接状态: {response.status_code}")

        if response.status_code == 200:
            print("服务器类型: OpenList")

            # 检查API端点
            api_endpoints = [
                "/api/public/info",
                "/api/fs/list",
                "/api/auth/login"
            ]

            for endpoint in api_endpoints:
                try:
                    api_response = requests.get(base_url + endpoint, timeout=5, verify=False)
                    print(f"API {endpoint}: {api_response.status_code}")
                except:
                    print(f"API {endpoint}: 失败")

        else:
            print(f"连接失败: {response.status_code}")

    except Exception as e:
        print(f"测试失败: {e}")

def test_login():
    """测试登录"""
    print("\n登录测试")
    print("=" * 30)

    base_url = "http://j.yzfycz.cn:5244"
    login_url = base_url + "/api/auth/login"

    # 常见的默认凭据
    test_creds = [
        ("admin", "admin"),
        ("test", "test"),
        ("guest", "guest")
    ]

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    for username, password in test_creds:
        try:
            data = {"username": username, "password": password}
            response = requests.post(
                login_url,
                json=data,
                headers=headers,
                timeout=10,
                verify=False
            )
            print(f"登录 {username}: {response.status_code}")

            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get('data', {}).get('token'):
                        print(f"  成功获得token")
                        return True
                except:
                    print(f"  响应格式异常")

        except Exception as e:
            print(f"登录 {username}: 失败")

    return False

def main():
    """主函数"""
    print("OpenList API简单测试")
    print("=" * 40)

    # 测试服务器连接
    test_server()

    # 测试登录
    success = test_login()

    print("\n" + "=" * 40)
    if success:
        print("API测试成功 - 可以使用OpenList功能")
        print("\n下一步:")
        print("1. 使用正确的凭据登录")
        print("2. 测试文件列表获取")
        print("3. 测试媒体文件播放")
    else:
        print("API测试失败 - 需要检查配置")
        print("\n建议:")
        print("1. 确认服务器地址正确")
        print("2. 检查用户名密码")
        print("3. 确认API端点路径")

if __name__ == "__main__":
    main()