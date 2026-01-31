"""
MYPC-MCP 配置加载工具

提供配置文件读取和环境变量扩展功能
支持 JSON 和 .env 两种格式
"""

import os
import json
import re
from typing import Any, Dict, List, Optional


def expand_env_vars(path: str) -> str:
    """
    扩展路径中的环境变量

    支持以下格式:
    - Windows 风格: %USERPROFILE%, %APPDATA%
    - Unix 风格: $HOME, ${HOME}
    - 波浪号: ~ (用户主目录)

    Args:
        path: 可能包含环境变量的路径

    Returns:
        扩展后的绝对路径
    """
    if not path:
        return path

    # Windows 风格: %USERPROFILE%
    path = re.sub(r'%([^%]+)%', lambda m: os.environ.get(m.group(1), m.group(0)), path)

    # Unix 风格: $HOME, ${HOME}
    path = os.path.expandvars(path)

    # ~ 展开
    path = os.path.expanduser(path)

    return path


def expand_env_in_list(paths: List[str]) -> List[str]:
    """
    扩展列表中的所有路径的环境变量

    Args:
        paths: 路径列表

    Returns:
        扩展后的路径列表
    """
    return [expand_env_vars(p) for p in paths] if paths else []


def expand_env_in_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    递归扩展配置中的所有环境变量

    Args:
        config: 配置字典

    Returns:
        环境变量扩展后的配置
    """
    if not isinstance(config, dict):
        return config

    result = {}
    for key, value in config.items():
        if isinstance(value, str):
            result[key] = expand_env_vars(value)
        elif isinstance(value, list):
            # 处理列表中的字符串
            result[key] = [
                expand_env_vars(item) if isinstance(item, str) else item
                for item in value
            ]
        elif isinstance(value, dict):
            # 递归处理嵌套字典
            result[key] = expand_env_in_config(value)
        else:
            result[key] = value

    return result


def parse_bool(value: str) -> bool:
    """解析布尔值字符串"""
    return value.lower() in ('true', '1', 'yes', 'on')


def parse_list(value: str, sep: str = '|') -> List[str]:
    """解析列表字符串"""
    if not value:
        return []
    return [item.strip() for item in value.split(sep) if item.strip()]


def load_env_config(env_file: str = "config.env") -> Dict[str, Any]:
    """
    加载 .env 格式配置文件

    Args:
        env_file: .env 配置文件路径

    Returns:
        配置字典
    """
    config: Dict[str, Any] = {}

    env_path = os.path.join(os.path.dirname(__file__), "..", env_file)
    env_path = os.path.abspath(env_path)

    if not os.path.exists(env_path):
        return config

    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            # 跳过空行和注释
            if not line or line.startswith('#'):
                continue

            # 解析 KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                # 设置到配置字典
                config[key] = value

    # 将扁平的 .env 配置转换为嵌套的 JSON 格式
    return convert_env_to_json_format(config)


def convert_env_to_json_format(env_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    将 .env 格式的配置转换为 JSON 嵌套格式

    例如: SERVER_PORT=9999 -> {"server": {"port": 9999}}
    """
    result: Dict[str, Any] = {}

    for key, value in env_config.items():
        # 分割键名，例如: SERVER_PORT -> ["SERVER", "PORT"]
        parts = key.lower().split('_')

        # 根据前缀确定配置节
        section_map = {
            'server': 'server',
            'safe': 'safe_zones',
            'paths': 'paths',
            'vlm': 'vlm',
            'screen': 'screen',
            'system': 'system',
            'files': 'files',
            'window': 'window',
            'search': 'search',
            'keyboard': 'keyboard_mouse',
            'detector': 'detector',
            'ssh': 'ssh',
        }

        # 确定配置节
        section = None
        for part in parts:
            if part in section_map:
                section = section_map[part]
                # 移除节名前缀
                idx = parts.index(part)
                parts = parts[idx + 1:]
                break

        if not section:
            continue

        # 构建嵌套结构
        if section not in result:
            result[section] = {}

        # 处理特殊字段
        if section == 'safe_zones':
            result['safe_zones'] = parse_list(value)
            continue

        # 处理其他配置
        if len(parts) == 0:
            continue

        # 转换键名（例如: workspace -> workspace）
        config_key = '_'.join(parts)

        # 类型转换
        # 处理带下划线的特殊字段，转换为驼峰命名
        if config_key == 'screenshots_dir':
            result[section]['screenshots_dir'] = value
        elif config_key == 'local_host_header':
            result[section]['local_host_header'] = value
        elif config_key.endswith('_dir'):
            result[section][config_key] = value
        elif config_key in ('enabled', 'failsafe'):
            result[section][config_key] = parse_bool(value)
        elif config_key in ('port', 'max_screenshots', 'llm_max_dim', 'llm_quality',
                           'vlm_max_dim', 'vlm_quality', 'vlm_timeout', 'cpu_interval',
                           'default_read_lines', 'grep_max_results', 'notification_duration',
                           'process_list_limit', 'window_list_limit', 'delay_min_seconds',
                           'delay_max_seconds', 'default_limit', 'search_depth'):
            result[section][config_key] = int(value)
        elif config_key in ('pause', 'type_interval'):
            result[section][config_key] = float(value)
        elif config_key in ('everything', 'git_bash', 'download_dirs', 'drives',
                           'common_dirs', 'allowed_commands'):
            result[section][config_key] = parse_list(value)
        elif config_key == 'hosts':
            # SSH hosts 是 JSON 格式
            try:
                result[section][config_key] = json.loads(value)
            except json.JSONDecodeError:
                result[section][config_key] = {}
        else:
            result[section][config_key] = value

    return result


def load_config(config_file: str = "config.json") -> Dict[str, Any]:
    """
    加载配置文件

    优先加载 JSON 格式配置，如果不存在则尝试加载 .env 格式

    Args:
        config_file: 配置文件路径

    Returns:
        配置字典，如果加载失败返回空字典
    """
    # 首先尝试加载 JSON 格式
    config_path = os.path.join(os.path.dirname(__file__), "..", config_file)
    config_path = os.path.abspath(config_path)

    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            # 展开环境变量
            return expand_env_in_config(config)
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse {config_file}: {e}")
        except Exception as e:
            print(f"Warning: Failed to load {config_file}: {e}")

    # 尝试加载 .env 格式
    env_file = config_file.replace('.json', '.env')
    env_config = load_env_config(env_file)
    if env_config:
        print(f"Loaded configuration from {env_file}")
        return expand_env_in_config(env_config)

    print(f"Warning: No valid configuration file found, using defaults")
    return {}


def get_config_value(config: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """
    获取嵌套配置值

    Args:
        config: 配置字典
        key_path: 配置键路径，使用点号分隔，如 "server.port"
        default: 默认值

    Returns:
        配置值，如果不存在则返回默认值
    """
    keys = key_path.split('.')
    value = config

    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default

    return value


def get_safe_zones(config: Dict[str, Any]) -> List[str]:
    """
    获取安全区列表，展开环境变量

    Args:
        config: 配置字典

    Returns:
        安全区路径列表
    """
    safe_zones = config.get("safe_zones", [])
    if not safe_zones:
        # 默认安全区
        safe_zones = [
            "~/Documents",
            "~/Downloads",
            "~/Desktop"
        ]

    return expand_env_in_list(safe_zones)


def find_executable(paths: List[str]) -> Optional[str]:
    """
    在路径列表中查找第一个存在的可执行文件

    Args:
        paths: 可执行文件路径列表

    Returns:
        第一个存在的可执行文件路径，如果都不存在则返回 None
    """
    for path in paths:
        expanded = expand_env_vars(path)
        if os.path.exists(expanded):
            return expanded

    return None


def get_drives(config: Dict[str, Any]) -> List[str]:
    """
    获取驱动器列表

    Args:
        config: 配置字典

    Returns:
        驱动器列表，如 ["C:", "D:", "E:"]
    """
    drives = config.get("paths", {}).get("drives", [])

    if not drives:
        # 自动检测驱动器
        drives = []
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            drive = f"{letter}:"
            if os.path.exists(drive):
                drives.append(drive)

    return drives


def get_workspace(config: Dict[str, Any]) -> str:
    """
    获取工作区目录

    Args:
        config: 配置字典

    Returns:
        工作区路径，默认为用户目录下的 Workspace
    """
    workspace = config.get("paths", {}).get("workspace") or config.get("files", {}).get("default_workspace")

    if workspace:
        return expand_env_vars(workspace)

    # 默认工作区
    return os.path.expanduser("~/Workspace")
