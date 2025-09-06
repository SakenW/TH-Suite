"""
简单的日志工厂模块
提供基本的日志功能，替代packages.core.framework.logging
"""

import logging
import sys
from typing import Optional


class SimpleStructLogFactory:
    """简单的结构化日志工厂"""
    
    _initialized = False
    
    @classmethod
    def initialize(cls):
        """初始化日志系统"""
        if cls._initialized:
            return
            
        # 配置基本日志格式
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        cls._initialized = True
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        获取日志器实例
        
        Args:
            name: 日志器名称
            
        Returns:
            日志器实例
        """
        cls.initialize()
        return logging.getLogger(name)


# 兼容性别名
StructLogFactory = SimpleStructLogFactory