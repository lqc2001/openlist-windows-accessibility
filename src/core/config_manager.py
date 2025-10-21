#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的配置管理器
专门用于服务器配置管理，支持密码加密存储
"""

import json
import os
import time
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
from src.core.logger import get_logger


class ConfigManager:
    """简化的配置管理器"""

    def __init__(self):
        """初始化配置管理器"""
        self.logger = get_logger()
        self.config_dir = "config"
        self.servers_file = os.path.join(self.config_dir, "servers.json")
        self.last_selected_file = os.path.join(self.config_dir, "last_selected.json")

        # 确保配置目录存在
        os.makedirs(self.config_dir, exist_ok=True)

        # 初始化加密
        self._init_encryption()

        # 初始化配置文件
        self._init_config_files()

        self.logger.info("配置管理器初始化完成")

    def _init_encryption(self):
        """初始化加密功能"""
        key_file = os.path.join(self.config_dir, ".key")

        if os.path.exists(key_file):
            # 读取现有密钥
            with open(key_file, 'rb') as f:
                self.key = f.read()

            # 验证密钥是否安全（不是旧的硬编码密钥）
            if self._is_legacy_key(self.key):
                self.logger.warning("检测到旧的硬编码密钥，正在生成新的安全密钥...")

                # 生成新密钥
                new_key = self._generate_secure_key()

                # 备份旧密钥
                backup_file = key_file + '.legacy'
                try:
                    with open(backup_file, 'wb') as f:
                        f.write(self.key)
                    self.logger.info(f"旧密钥已备份到: {backup_file}")
                except Exception as e:
                    self.logger.warning(f"备份旧密钥失败: {e}")

                # 保存新密钥
                with open(key_file, 'wb') as f:
                    f.write(new_key)

                # 设置文件权限
                try:
                    import stat
                    os.chmod(key_file, stat.S_IRUSR | stat.S_IWUSR)
                except:
                    self.logger.warning("无法设置密钥文件权限")

                # 使用新密钥，但保留旧密钥用于解密
                self.key = new_key
                self.legacy_key = legacy_key  # 使用备份的旧密钥
                self.logger.info("已将旧密钥替换为新的安全密钥")
                self.logger.warning("由于密钥已更改，您可能需要重新输入服务器密码")
            else:
                self.key = self.key  # 保持现有密钥
                self.legacy_key = None
        else:
            # 生成新的安全密钥
            self.key = self._generate_secure_key()

            # 保存密钥
            with open(key_file, 'wb') as f:
                f.write(self.key)

            # 设置文件权限（仅所有者可读写）
            try:
                import stat
                os.chmod(key_file, stat.S_IRUSR | stat.S_IWUSR)
            except:
                # 如果无法设置权限，记录警告但不影响功能
                self.logger.warning("无法设置密钥文件权限")

            self.logger.info("已生成新的加密密钥")
            self.legacy_key = None

        self.cipher = Fernet(self.key)
        self.logger.debug("加密功能初始化完成")

    def _generate_secure_key(self):
        """生成安全的加密密钥"""
        try:
            # 方法1：使用系统特定的熵源生成密钥
            import platform
            import uuid

            # 收集系统特定的熵
            system_info = {
                'platform': platform.platform(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'node': platform.node(),
                'user': os.environ.get('USERNAME', os.environ.get('USER', 'unknown')),
                'temp': os.environ.get('TEMP', os.environ.get('TMP', 'unknown')),
                'uuid': str(uuid.uuid1())
            }

            # 组合熵源
            entropy = '|'.join(system_info.values()).encode()

            # 生成随机盐值
            salt = os.urandom(32)

            # 使用PBKDF2从系统熵生成密钥
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=200000,  # 增加迭代次数以提高安全性
            )
            key = base64.urlsafe_b64encode(kdf.derive(entropy))

            self.logger.debug("使用系统特定熵生成了安全密钥")
            return key

        except Exception as e:
            self.logger.warning(f"使用系统熵生成密钥失败，使用随机密钥: {e}")

            # 方法2：回退到完全随机密钥
            try:
                # Fernet自动生成安全密钥
                key = Fernet.generate_key()
                self.logger.debug("使用随机数生成器生成了安全密钥")
                return key
            except Exception as e2:
                self.logger.error(f"生成随机密钥也失败: {e2}")
                # 方法3：最后的回退方案
                import secrets
                key = base64.urlsafe_b64encode(secrets.token_bytes(32))
                self.logger.warning("使用secrets模块生成了回退密钥")
                return key

    def _is_legacy_key(self, key):
        """检查是否是旧的硬编码密钥"""
        try:
            # 尝试使用旧的硬编码参数生成密钥
            password = "OpenListManager_Default_Password".encode()
            salt = b'OpenListManager_Salt_2024'

            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            legacy_key = base64.urlsafe_b64encode(kdf.derive(password))

            # 比较密钥
            return key == legacy_key
        except:
            return False

    def _encrypt_password(self, password):
        """加密密码"""
        if not password:
            return ""
        encrypted = self.cipher.encrypt(password.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def _decrypt_password(self, encrypted_password):
        """解密密码（支持新旧密钥）"""
        if not encrypted_password:
            return ""

        # 首先尝试用新密钥解密
        try:
            encrypted = base64.urlsafe_b64decode(encrypted_password.encode())
            decrypted = self.cipher.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            self.logger.debug(f"新密钥解密失败: {e}")

        # 如果新密钥解密失败，尝试用旧密钥解密
        if self.legacy_key:
            try:
                legacy_cipher = Fernet(self.legacy_key)
                encrypted = base64.urlsafe_b64decode(encrypted_password.encode())
                decrypted = legacy_cipher.decrypt(encrypted)
                return decrypted.decode()
            except Exception as e:
                self.logger.debug(f"旧密钥解密也失败: {e}")

        # 如果都失败了，返回空字符串
        self.logger.error("密码解密失败，可能需要重新输入")
        return ""

    def _init_config_files(self):
        """初始化配置文件"""
        # 初始化服务器配置文件
        if not os.path.exists(self.servers_file):
            self._save_servers([])

        # 初始化最后选中配置文件
        if not os.path.exists(self.last_selected_file):
            self._save_last_selected(None)

    def _save_servers(self, servers):
        """保存服务器配置"""
        # 加密密码
        encrypted_servers = []
        for server in servers:
            encrypted_server = server.copy()
            if 'password' in encrypted_server:
                encrypted_server['password'] = self._encrypt_password(encrypted_server['password'])
            encrypted_servers.append(encrypted_server)

        data = {
            'servers': encrypted_servers,
            'version': '1.0'
        }

        try:
            with open(self.servers_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.logger.debug(f"保存了{len(servers)}个服务器配置")
        except Exception as e:
            self.logger.error(f"保存服务器配置失败: {e}")

    def _load_json(self, file_path):
        """加载JSON文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"加载配置文件失败 {file_path}: {e}")
            return {}

    def _save_json(self, file_path, data):
        """保存JSON文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存配置文件失败 {file_path}: {e}")

    def _save_last_selected(self, server_id):
        """保存最后选中的服务器ID"""
        data = {
            'last_selected_server_id': server_id,
            'version': '1.0'
        }
        self._save_json(self.last_selected_file, data)

    def get_servers(self):
        """获取服务器列表"""
        try:
            data = self._load_json(self.servers_file)
            servers = data.get('servers', [])

            # 解密密码
            decrypted_servers = []
            for server in servers:
                decrypted_server = server.copy()
                if 'password' in decrypted_server:
                    decrypted_server['password'] = self._decrypt_password(decrypted_server['password'])
                decrypted_servers.append(decrypted_server)

            return decrypted_servers
        except Exception as e:
            self.logger.error(f"获取服务器列表失败: {e}")
            return []

    def save_server(self, server_data):
        """保存服务器配置"""
        try:
            servers = self.get_servers()

            # 检查是否已存在
            existing_index = None
            for i, server in enumerate(servers):
                if server.get('id') == server_data.get('id'):
                    existing_index = i
                    break

            if existing_index is not None:
                # 更新现有服务器
                servers[existing_index] = server_data
                self.logger.info(f"更新服务器配置: {server_data.get('name')}")
            else:
                # 添加新服务器
                if not server_data.get('id'):
                    server_data['id'] = f"server_{len(servers) + 1}"
                servers.append(server_data)
                self.logger.info(f"添加新服务器配置: {server_data.get('name')}")

            self._save_servers(servers)
            return True

        except Exception as e:
            self.logger.error(f"保存服务器配置失败: {e}")
            return False

    def delete_server(self, server_id):
        """删除服务器配置"""
        try:
            servers = self.get_servers()
            servers = [server for server in servers if server.get('id') != server_id]
            self._save_servers(servers)
            self.logger.info(f"删除服务器配置: {server_id}")
            return True

        except Exception as e:
            self.logger.error(f"删除服务器配置失败: {e}")
            return False

    def get_last_selected(self):
        """获取最后选中的服务器ID"""
        try:
            data = self._load_json(self.last_selected_file)
            return data.get('last_selected_server_id')
        except Exception as e:
            self.logger.error(f"获取最后选中服务器失败: {e}")
            return None

    def set_last_selected(self, server_id):
        """设置最后选中的服务器ID"""
        self._save_last_selected(server_id)