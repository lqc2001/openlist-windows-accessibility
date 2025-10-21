#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境配置管理器
借鉴ForumAssist的环境自动配置功能，智能管理VLC环境
"""

import os
import sys
import platform
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from src.core.logger import get_logger


class EnvironmentSetup:
    """环境配置管理器

    功能：
    1. 自动检测开发/打包环境
    2. 智能配置VLC环境变量
    3. VLC组件完整性检查
    4. 依赖项验证
    5. 环境问题诊断
    """

    def __init__(self):
        """初始化环境配置管理器"""
        self.logger = get_logger()

        # 环境信息
        self.is_development = not getattr(sys, 'frozen', False)
        self.is_windows = platform.system() == 'Windows'
        self.is_64bit = sys.maxsize > 2**32
        self.python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

        # 路径信息
        self.project_root = self._get_project_root()
        self.executable_dir = Path(sys.executable).parent
        self.script_dir = Path(__file__).parent.parent.parent

        # VLC配置
        self.vlc_paths = self._get_vlc_paths()
        self.selected_vlc_path = None
        self.vlc_available = False

        # 诊断信息
        self.diagnostics = {}

        # 初始化
        self._diagnose_environment()
        self._setup_vlc_environment()

    def _get_project_root(self) -> Path:
        """获取项目根目录"""
        if self.is_development:
            # 开发环境：脚本所在目录的上上级目录
            return Path(__file__).parent.parent.parent
        else:
            # 打包环境：可执行文件所在目录
            return Path(sys.executable).parent

    def _get_vlc_paths(self) -> List[Path]:
        """获取VLC可能的位置列表"""
        paths = []

        if self.is_development:
            # 开发环境可能的VLC位置
            vlc_candidates = [
                self.project_root / 'vlc',
                self.project_root / 'vlc_portable',
                self.project_root / 'dependencies' / 'vlc',
                self.script_dir / 'vlc',
                self.script_dir / 'vlc_portable',
            ]

            # Windows系统VLC安装位置
            if self.is_windows:
                system_vlc_paths = [
                    Path(os.environ.get('ProgramFiles', 'C:\\Program Files')) / 'VideoLAN' / 'VLC',
                    Path(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')) / 'VideoLAN' / 'VLC',
                    Path('C:\\Program Files\\VideoLAN\\VLC'),
                    Path('C:\\Program Files (x86)\\VideoLAN\\VLC'),
                ]
                vlc_candidates.extend(system_vlc_paths)

            paths = [p for p in vlc_candidates if p.exists()]

        else:
            # 打包环境可能的VLC位置
            packed_vlc_paths = [
                self.executable_dir / 'vlc',
                self.executable_dir / 'vlc_portable',
                self.executable_dir / 'dependencies' / 'vlc',
            ]

            paths = [p for p in packed_vlc_paths if p.exists()]

        return paths

    def _diagnose_environment(self):
        """诊断环境配置"""
        self.logger.info("开始环境诊断...")
        self.diagnostics = {
            'platform': platform.platform(),
            'architecture': platform.architecture()[0],
            'python_version': self.python_version,
            'is_development': self.is_development,
            'is_windows': self.is_windows,
            'is_64bit': self.is_64bit,
            'project_root': str(self.project_root),
            'executable_dir': str(self.executable_dir),
            'script_dir': str(self.script_dir),
            'vlc_paths_found': len(self.vlc_paths),
            'vlc_paths': [str(p) for p in self.vlc_paths],
        }

        # 检查Python依赖
        missing_deps = self._check_dependencies()
        self.diagnostics['missing_dependencies'] = missing_deps

        # 检查VLC
        vlc_status = self._check_v_installations()
        self.diagnostics['vlc_status'] = vlc_status

        # 记录诊断结果
        self.logger.info(f"环境诊断完成: {len(self.vlc_paths)}个VLC路径")
        if missing_deps:
            self.logger.warning(f"缺少依赖: {missing_deps}")

    def _check_dependencies(self) -> List[str]:
        """检查Python依赖"""
        required_modules = ['wx', 'pathlib']
        optional_modules = ['vlc', 'pythoncom']

        missing = []

        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing.append(module)

        for module in optional_modules:
            try:
                __import__(module)
            except ImportError:
                self.logger.debug(f"可选模块不可用: {module}")

        return missing

    def _check_v_installations(self) -> Dict[str, any]:
        """检查VLC安装"""
        vlc_status = {
            'available': False,
            'selected_path': None,
            'installations': [],
            'issues': []
        }

        for vlc_path in self.vlc_paths:
            install_info = self._verify_vlc_installation(vlc_path)
            vlc_status['installations'].append(install_info)

            if install_info['valid'] and not vlc_status['available']:
                vlc_status['available'] = True
                vlc_status['selected_path'] = str(vlc_path)

        if not vlc_status['available']:
            vlc_status['issues'].append('未找到有效的VLC安装')

        return vlc_status

    def _verify_vlc_installation(self, vlc_path: Path) -> Dict[str, any]:
        """验证VLC安装的完整性"""
        install_info = {
            'path': str(vlc_path),
            'valid': False,
            'core_files': [],
            'missing_core': [],
            'plugin_count': 0,
            'issues': []
        }

        try:
            if not vlc_path.exists():
                install_info['issues'].append('路径不存在')
                return install_info

            # 检查核心文件
            if self.is_windows:
                core_files = ['libvlc.dll', 'libvlccore.dll']
            elif platform.system() == 'Linux':
                core_files = ['libvlc.so', 'libvlccore.so']
            else:
                core_files = ['libvlc.dylib', 'libvlccore.dylib']

            found_core = []
            missing_core = []

            for core_file in core_files:
                core_path = vlc_path / core_file
                if core_path.exists():
                    found_core.append(core_file)
                else:
                    missing_core.append(core_file)

            install_info['core_files'] = found_core
            install_info['missing_core'] = missing_core

            # 检查插件目录
            plugin_path = vlc_path / 'plugins'
            if plugin_path.exists():
                # 统计插件文件数量
                plugin_files = list(plugin_path.rglob('*.dll')) if self.is_windows else list(plugin_path.rglob('*.so'))
                install_info['plugin_count'] = len(plugin_files)

                if len(plugin_files) < 20:
                    install_info['issues'].append(f'插件文件数量不足: {len(plugin_files)}个')
            else:
                install_info['issues'].append('插件目录不存在')

            # 判断安装是否有效
            install_info['valid'] = (len(found_core) == len(core_files) and
                                   install_info['plugin_count'] >= 20)

        except Exception as e:
            install_info['issues'].append(f'验证失败: {str(e)}')

        return install_info

    def _setup_vlc_environment(self):
        """设置VLC环境"""
        if not self.diagnostics['vlc_status']['available']:
            self.logger.error("没有可用的VLC安装")
            self.vlc_available = False
            return

        # 选择最佳的VLC路径
        selected_path = self._select_best_vlc_path()
        if not selected_path:
            self.logger.error("无法选择合适的VLC路径")
            self.vlc_available = False
            return

        self.selected_vlc_path = selected_path

        # 设置环境变量
        success = self._configure_vlc_environment(selected_path)

        if success:
            self.vlc_available = True
            self.logger.info(f"VLC环境配置成功: {selected_path}")
        else:
            self.vlc_available = False
            self.logger.error("VLC环境配置失败")

    def _select_best_vlc_path(self) -> Optional[Path]:
        """选择最佳的VLC路径"""
        if not self.vlc_paths:
            return None

        # 优先级评分系统
        scored_paths = []

        for vlc_path in self.vlc_paths:
            score = 0
            install_info = self._verify_vlc_installation(vlc_path)

            if not install_info['valid']:
                continue

            # 基础分数
            score += 100

            # 开发环境优先使用项目目录下的VLC
            if self.is_development and vlc_path.is_relative_to(self.project_root):
                score += 50

            # 打包环境优先使用可执行文件目录下的VLC
            if not self.is_development and vlc_path.is_relative_to(self.executable_dir):
                score += 50

            # 插件数量加分
            score += min(install_info['plugin_count'] // 10, 30)

            # 路径深度惩罚（太深的路径可能有问题）
            depth_penalty = len(vlc_path.parts) * 2
            score -= depth_penalty

            scored_paths.append((score, vlc_path, install_info))

        if not scored_paths:
            return None

        # 选择得分最高的路径
        scored_paths.sort(key=lambda x: x[0], reverse=True)
        best_score, best_path, best_info = scored_paths[0]

        self.logger.info(f"选择VLC路径: {best_path} (评分: {best_score})")
        return best_path

    def _configure_vlc_environment(self, vlc_path: Path) -> bool:
        """配置VLC环境变量"""
        try:
            # 设置VLC插件路径
            plugin_path = vlc_path / 'plugins'
            if plugin_path.exists():
                os.environ['VLC_PLUGIN_PATH'] = str(plugin_path)
                self.logger.debug(f"VLC插件路径: {plugin_path}")

            # 添加VLC路径到系统PATH
            vlc_path_str = str(vlc_path)
            current_path = os.environ.get('PATH', '')

            if vlc_path_str not in current_path:
                os.environ['PATH'] = vlc_path_str + os.pathsep + current_path
                self.logger.debug(f"VLC路径已添加到PATH: {vlc_path_str}")

            # Windows特定配置
            if self.is_windows:
                # 检查并设置Windows特定的环境变量
                self._setup_windows_environment(vlc_path)

            return True

        except Exception as e:
            self.logger.error(f"配置VLC环境失败: {e}")
            return False

    def _setup_windows_environment(self, vlc_path: Path):
        """设置Windows特定环境"""
        try:
            # 检查Visual C++ Redistributable
            self._check_visual_cpp_redistributable()

            # 设置Windows媒体格式支持
            self._setup_windows_media_support()

        except Exception as e:
            self.logger.debug(f"Windows环境设置失败: {e}")

    def _check_visual_cpp_redistributable(self):
        """检查Visual C++ Redistributable"""
        try:
            # 检查常见的Visual C++ Redistributable安装
            redistributable_paths = [
                Path(os.environ.get('SystemRoot', 'C:\\Windows')) / 'System32' / 'msvcp140.dll',
                Path(os.environ.get('SystemRoot', 'C:\\Windows')) / 'SysWOW64' / 'msvcp140.dll',
            ]

            found = any(path.exists() for path in redistributable_paths)

            if found:
                self.logger.debug("Visual C++ Redistributable 可用")
            else:
                self.logger.warning("可能缺少Visual C++ Redistributable")

        except Exception as e:
            self.logger.debug(f"检查Visual C++ Redistributable失败: {e}")

    def _setup_windows_media_support(self):
        """设置Windows媒体支持"""
        try:
            # 检查Windows Media Foundation
            wmf_path = Path(os.environ.get('SystemRoot', 'C:\\Windows')) / 'System32' / 'mf.dll'
            if wmf_path.exists():
                self.logger.debug("Windows Media Foundation 可用")
            else:
                self.logger.debug("Windows Media Foundation 不可用")

        except Exception as e:
            self.logger.debug(f"检查Windows媒体支持失败: {e}")

    def is_vlc_available(self) -> bool:
        """检查VLC是否可用"""
        return self.vlc_available

    def get_selected_vlc_path(self) -> Optional[Path]:
        """获取选择的VLC路径"""
        return self.selected_vlc_path

    def get_diagnostics(self) -> Dict[str, any]:
        """获取诊断信息"""
        return self.diagnostics.copy()

    def get_environment_info(self) -> Dict[str, any]:
        """获取环境信息摘要"""
        return {
            'is_development': self.is_development,
            'is_windows': self.is_windows,
            'is_64bit': self.is_64bit,
            'python_version': self.python_version,
            'vlc_available': self.vlc_available,
            'selected_vlc_path': str(self.selected_vlc_path) if self.selected_vlc_path else None,
            'vlc_paths_count': len(self.vlc_paths),
            'missing_dependencies': self.diagnostics.get('missing_dependencies', []),
        }

    def test_vlc_import(self) -> Tuple[bool, str]:
        """测试VLC导入"""
        try:
            import vlc
            version = vlc.libvlc_get_version()
            version_str = version.decode('utf-8') if isinstance(version, bytes) else str(version)
            return True, f"VLC导入成功，版本: {version_str}"
        except ImportError as e:
            return False, f"VLC导入失败: {str(e)}"
        except Exception as e:
            return False, f"VLC测试失败: {str(e)}"

    def create_environment_report(self) -> str:
        """创建环境报告"""
        report = []
        report.append("=" * 60)
        report.append("OpenList Windows 环境报告")
        report.append("=" * 60)
        report.append(f"平台: {self.diagnostics['platform']}")
        report.append(f"架构: {self.diagnostics['architecture']}")
        report.append(f"Python版本: {self.diagnostics['python_version']}")
        report.append(f"运行模式: {'开发环境' if self.is_development else '打包环境'}")
        report.append(f"项目根目录: {self.diagnostics['project_root']}")
        report.append("")

        # VLC状态
        vlc_status = self.diagnostics['vlc_status']
        report.append("VLC状态:")
        report.append(f"  可用: {'是' if vlc_status['available'] else '否'}")
        if vlc_status['selected_path']:
            report.append(f"  选中路径: {vlc_status['selected_path']}")
        report.append(f"  找到安装: {len(vlc_status['installations'])}个")

        if vlc_status['issues']:
            report.append("  问题:")
            for issue in vlc_status['issues']:
                report.append(f"    - {issue}")

        report.append("")

        # 依赖状态
        missing_deps = self.diagnostics['missing_dependencies']
        report.append("Python依赖:")
        if missing_deps:
            report.append("  缺少:")
            for dep in missing_deps:
                report.append(f"    - {dep}")
        else:
            report.append("  所有必需依赖已安装")

        report.append("")

        # VLC测试
        vlc_test, vlc_test_msg = self.test_vlc_import()
        report.append("VLC导入测试:")
        report.append(f"  结果: {vlc_test_msg}")

        report.append("=" * 60)

        return "\n".join(report)

    def repair_environment(self) -> Dict[str, bool]:
        """尝试修复环境问题"""
        results = {
            'dependencies_fixed': False,
            'vlc_environment_fixed': False,
            'path_issues_fixed': False
        }

        try:
            # 修复依赖问题
            if self.diagnostics['missing_dependencies']:
                self.logger.info("尝试修复依赖问题...")
                # 这里可以添加自动安装依赖的逻辑
                results['dependencies_fixed'] = False  # 暂不实现自动安装

            # 修复VLC环境
            if not self.vlc_available and self.vlc_paths:
                self.logger.info("尝试修复VLC环境...")
                self._setup_vlc_environment()
                results['vlc_environment_fixed'] = self.vlc_available

            # 修复路径问题
            path_issues = self._check_path_issues()
            if path_issues:
                self.logger.info("尝试修复路径问题...")
                self._fix_path_issues(path_issues)
                results['path_issues_fixed'] = True

        except Exception as e:
            self.logger.error(f"环境修复失败: {e}")

        return results

    def _check_path_issues(self) -> List[str]:
        """检查路径问题"""
        issues = []

        if not self.selected_vlc_path:
            issues.append("未选择VLC路径")
            return issues

        # 检查路径权限
        try:
            test_file = self.selected_vlc_path / 'test_access.tmp'
            test_file.touch()
            test_file.unlink()
        except PermissionError:
            issues.append("VLC路径没有写入权限")
        except Exception:
            issues.append("VLC路径访问异常")

        return issues

    def _fix_path_issues(self, issues: List[str]):
        """修复路径问题"""
        for issue in issues:
            if "权限" in issue:
                self.logger.warning("VLC路径权限问题需要手动解决")
            elif "访问" in issue:
                self.logger.warning("VLC路径访问问题需要手动解决")

    def __str__(self) -> str:
        """字符串表示"""
        return f"EnvironmentSetup(vlc_available={self.vlc_available}, path={self.selected_vlc_path})"

    def __repr__(self) -> str:
        """详细字符串表示"""
        return f"EnvironmentSetup(development={self.is_development}, windows={self.is_windows}, vlc={self.vlc_available})"