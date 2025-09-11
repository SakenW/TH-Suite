"""
路径智能转换工具
支持Windows路径到Linux路径的智能转换，特别适用于WSL环境
"""
import os
import platform
import re
from pathlib import Path
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class PathConverter:
    """智能路径转换器"""
    
    # Windows驱动器映射到WSL路径
    WSL_DRIVE_MAPPING = {
        'C:': '/mnt/c',
        'D:': '/mnt/d',
        'E:': '/mnt/e',
        'F:': '/mnt/f',
        'G:': '/mnt/g',
    }
    
    # 常见的Minecraft路径映射
    MINECRAFT_PATH_PATTERNS = [
        # Curseforge路径
        {
            'pattern': r'([C-G]):(\\|\/)Games(\\|\/)Curseforge(\\|\/)Minecraft',
            'linux_template': '/mnt/{drive}/Games/Curseforge/Minecraft'
        },
        # 官方启动器路径
        {
            'pattern': r'([C-G]):(\\|\/)Users(\\|\/)([^\\\/]+)(\\|\/)AppData(\\|\/)Roaming(\\|\/)\.minecraft',
            'linux_template': '/mnt/{drive}/Users/{user}/AppData/Roaming/.minecraft'
        },
        # MultiMC路径
        {
            'pattern': r'([C-G]):(\\|\/)MultiMC(\\|\/)instances',
            'linux_template': '/mnt/{drive}/MultiMC/instances'
        },
        # Prism Launcher路径
        {
            'pattern': r'([C-G]):(\\|\/)PrismLauncher(\\|\/)instances',
            'linux_template': '/mnt/{drive}/PrismLauncher/instances'
        }
    ]
    
    @staticmethod
    def normalize_path_separators(path: str) -> str:
        """统一路径分隔符为正斜杠"""
        return path.replace('\\', '/')
    
    @staticmethod
    def is_windows_path(path: str) -> bool:
        """检测是否为Windows路径"""
        # Windows路径特征：盘符开头如 C:\ 或 C:/
        return bool(re.match(r'^[A-Za-z]:[\\\/]', path))
    
    @staticmethod
    def is_wsl_environment() -> bool:
        """检测是否在WSL环境中"""
        try:
            # 检查 /proc/version 是否包含 Microsoft 或 WSL
            if Path('/proc/version').exists():
                with open('/proc/version', 'r') as f:
                    version_info = f.read().lower()
                    return 'microsoft' in version_info or 'wsl' in version_info
        except:
            pass
        
        # 检查环境变量
        wsl_distro = os.environ.get('WSL_DISTRO_NAME')
        return bool(wsl_distro)
    
    @classmethod
    def convert_windows_to_wsl(cls, windows_path: str) -> Optional[str]:
        """将Windows路径转换为WSL路径"""
        if not cls.is_windows_path(windows_path):
            return None
            
        # 统一分隔符
        normalized_path = cls.normalize_path_separators(windows_path)
        
        # 提取驱动器字母
        drive_match = re.match(r'^([A-Za-z]):', normalized_path)
        if not drive_match:
            return None
            
        drive_letter = drive_match.group(1).upper()
        drive_key = f"{drive_letter}:"
        
        # 检查驱动器映射
        if drive_key not in cls.WSL_DRIVE_MAPPING:
            logger.warning(f"未知驱动器: {drive_key}")
            return None
        
        # 转换路径
        wsl_drive = cls.WSL_DRIVE_MAPPING[drive_key]
        # 移除驱动器部分，保留后续路径
        path_without_drive = normalized_path[2:]  # 移除 "C:"
        if path_without_drive.startswith('/'):
            path_without_drive = path_without_drive[1:]  # 移除开头的斜杠
            
        wsl_path = f"{wsl_drive}/{path_without_drive}" if path_without_drive else wsl_drive
        
        return wsl_path
    
    @classmethod
    def smart_convert_path(cls, input_path: str) -> str:
        """
        智能路径转换
        
        Args:
            input_path: 输入路径（可能是Windows或Linux路径）
            
        Returns:
            转换后的适合当前环境的路径
        """
        if not input_path:
            return input_path
            
        # 如果已经是Linux路径且存在，直接返回
        if not cls.is_windows_path(input_path):
            return input_path
        
        # 如果是Windows路径
        if cls.is_windows_path(input_path):
            # 在WSL环境中，尝试转换为WSL路径
            if cls.is_wsl_environment():
                converted_path = cls.convert_windows_to_wsl(input_path)
                if converted_path:
                    logger.info(f"路径转换: {input_path} -> {converted_path}")
                    return converted_path
            
            # 如果在Windows环境中，保持原路径
            if platform.system() == 'Windows':
                return input_path
        
        # 默认返回原路径
        return input_path
    
    @classmethod
    def suggest_minecraft_paths(cls) -> List[str]:
        """建议可能的Minecraft路径"""
        suggestions = []
        
        # WSL环境下的建议路径
        if cls.is_wsl_environment():
            common_paths = [
                '/mnt/c/Users/{user}/AppData/Roaming/.minecraft',
                '/mnt/d/Games/Curseforge/Minecraft',
                '/mnt/c/Games/Curseforge/Minecraft',
                '/mnt/d/MultiMC/instances', 
                '/mnt/c/MultiMC/instances',
                '/mnt/d/PrismLauncher/instances',
                '/mnt/c/PrismLauncher/instances'
            ]
            
            # 尝试获取用户名
            try:
                import subprocess
                result = subprocess.run(['whoami'], capture_output=True, text=True)
                if result.returncode == 0:
                    username = result.stdout.strip()
                    suggestions.extend([
                        path.replace('{user}', username) for path in common_paths
                        if '{user}' in path
                    ])
                
                # 添加不包含用户名的路径
                suggestions.extend([
                    path for path in common_paths if '{user}' not in path
                ])
            except:
                pass
        
        # Linux环境下的建议路径
        home_dir = os.path.expanduser('~')
        suggestions.extend([
            f"{home_dir}/.minecraft",
            f"{home_dir}/minecraft",
            f"{home_dir}/Games/minecraft",
            "/opt/minecraft",
            "/usr/games/minecraft"
        ])
        
        # 过滤存在的路径
        existing_paths = []
        for path in suggestions:
            if os.path.exists(path):
                existing_paths.append(path)
        
        return existing_paths[:10]  # 返回前10个建议
    
    @classmethod
    def validate_and_convert_path(cls, input_path: str) -> tuple[str, bool, str]:
        """
        验证并转换路径
        
        Returns:
            tuple: (转换后的路径, 是否存在, 状态消息)
        """
        if not input_path:
            return "", False, "路径为空"
        
        # 智能转换路径
        converted_path = cls.smart_convert_path(input_path)
        
        # 检查路径是否存在
        path_exists = os.path.exists(converted_path)
        
        if path_exists:
            status_msg = f"路径有效: {converted_path}"
            if converted_path != input_path:
                status_msg += f" (已转换自: {input_path})"
        else:
            status_msg = f"路径不存在: {converted_path}"
            if not path_exists and converted_path != input_path:
                # 提供建议
                suggestions = cls.suggest_minecraft_paths()
                if suggestions:
                    status_msg += f"\\n建议路径: {', '.join(suggestions[:3])}"
        
        return converted_path, path_exists, status_msg


# 便捷函数
def convert_path(path: str) -> str:
    """便捷的路径转换函数"""
    return PathConverter.smart_convert_path(path)


def validate_path(path: str) -> tuple[str, bool, str]:
    """便捷的路径验证函数"""
    return PathConverter.validate_and_convert_path(path)