#!/usr/bin/env python
"""
启动脚本日志辅助工具
输出与应用程序一致的结构化日志格式
"""

import sys
import json
from datetime import datetime


def log(level: str, message: str, service: str = "mc-l10n-scripts", logger: str = "startup"):
    """输出结构化日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 构建结构化日志
    log_entry = {
        'event': message,
        'service': service,
        'logger': logger,
        'level': level.lower(),
        'timestamp': timestamp
    }
    
    # 输出格式：级别:     时间 JSON
    prefix = f"{level.upper()}:     {timestamp}"
    print(f"{prefix} {json.dumps(log_entry, ensure_ascii=False)}")


def main():
    """命令行接口"""
    if len(sys.argv) < 3:
        print("Usage: python log_helper.py <level> <message> [service] [logger]")
        sys.exit(1)
    
    level = sys.argv[1]
    message = sys.argv[2]
    service = sys.argv[3] if len(sys.argv) > 3 else "mc-l10n-scripts"
    logger = sys.argv[4] if len(sys.argv) > 4 else "startup"
    
    log(level, message, service, logger)


if __name__ == "__main__":
    main()