"""
MYPC-MCP 配置加载工具

提供配置文件读取和环境变量扩展功能
仅支持 JSON 格式，保持配置结构简单清晰
"""

import os
import json
import re
from typing import Any, Dict, List, Optional


def expand_env_vars(path: str) -> str:
    """扩展路径中的环境变量 (支持 Windows %VAR% 和 Unix $VAR)"""
    if not path or not isinstance(path, str):
        return path
    # Windows 风格: %USERPROFILE%
    path = re.sub(r'%([^%]+)%', lambda m: os.environ.get(m.group(1), m.group(0)), path)
    # Unix 风格和 ~ 展开
    path = os.path.expandvars(os.path.expanduser(path))
    return path


def expand_env_in_config(config: Any) -> Any:
    """递归扩展配置中的所有环境变量"""
    if isinstance(config, dict):
        return {k: expand_env_in_config(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [expand_env_in_config(i) for i in config]
    elif isinstance(config, str):
        return expand_env_vars(config)
    return config


def expand_env_in_list(paths: List[str]) -> List[str]:
    """扩展路径列表中的环境变量"""
    return [expand_env_vars(path) for path in paths]


def load_config(config_file: str = "config.json") -> Dict[str, Any]:
    """加载 JSON 配置文件"""
    config_path = os.path.join(os.path.dirname(__file__), "..", config_file)
    config_path = os.path.normpath(os.path.abspath(config_path))

    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"Successfully loaded config from {config_file}")
            return expand_env_in_config(config)
        except Exception as e:
            print(f"Error loading {config_file}: {e}")
    
    print(f"Warning: {config_file} not found or invalid, using empty defaults")
    return {}


def get_config_value(config: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """使用点号路径获取配置值，如 'server.port'"""
    keys = key_path.split('.')
    value = config
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    return value


def get_safe_zones(config: Dict[str, Any]) -> List[str]:
    """获取安全区列表"""
    # 优先尝试从 safe_zones 根键找，再尝试从 paths.safe_zones 找
    zones = config.get("safe_zones")
    if not zones:
        zones = get_config_value(config, "paths.safe_zones")
    return zones if isinstance(zones, list) else []


def get_workspace(config: Dict[str, Any]) -> str:
    """获取默认工作区路径"""
    # 按照你的 config.json 结构，优先从 paths.workspace 找
    workspace = get_config_value(config, "paths.workspace")
    if not workspace:
        # 兼容旧版或 files 节下的配置
        workspace = get_config_value(config, "files.default_workspace")
    
    if not workspace:
        # 最终保底
        workspace = os.path.join(os.path.expanduser("~"), "ALICE")
        
    return os.path.abspath(expand_env_vars(workspace))


def find_executable(paths: List[str]) -> Optional[str]:
    """
    在路径列表中查找第一个存在的可执行文件

    Args:
        paths: 可执行文件路径列表

    Returns:
        第一个存在的可执行文件路径, 如果都不存在则返回 None
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
        驱动器列表, 如 ["C:", "D:", "E:"]
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
