"""
启动MC L10n后端服务器
"""

import os
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# 设置环境变量
os.environ.setdefault('DATABASE_PATH', './mc_l10n_local.db')
os.environ.setdefault('SERVER_HOST', '0.0.0.0')
os.environ.setdefault('SERVER_PORT', '18000')
os.environ.setdefault('LOG_LEVEL', 'INFO')

# 导入并启动应用
try:
    from main import app
    import uvicorn
    
    print("🚀 Starting MC L10n Backend Server v6.0")
    print("📍 Server: http://localhost:18000")
    print("📚 API Docs: http://localhost:18000/docs")
    print("🔧 Press Ctrl+C to stop")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=18000,
        reload=True,
        log_level="info"
    )
except ImportError as e:
    print(f"Import error: {e}")
    print("\n尝试使用简单后端...")
    
    # 如果新架构有问题，使用简单后端
    from simple_backend import app
    import uvicorn
    
    print("🚀 Starting MC L10n Simple Backend")
    print("📍 Server: http://localhost:18000")
    print("📚 API Docs: http://localhost:18000/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=18000,
        reload=True,
        log_level="info"
    )