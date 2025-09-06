"""
简化的服务器启动脚本
设置正确的Python路径并启动FastAPI服务器
"""

import sys
import os
from pathlib import Path

# 设置路径
current_dir = Path(__file__).parent
root_dir = current_dir.parent.parent.parent
packages_dir = root_dir / "packages"

# 添加必要的路径
sys.path.insert(0, str(current_dir))  # backend目录
sys.path.insert(0, str(packages_dir / "core" / "src"))  # trans_hub_core所在目录
sys.path.insert(0, str(packages_dir / "universal-scanner"))  # universal-scanner
sys.path.insert(0, str(packages_dir / "game-parsers"))  # game-parsers

# 打印路径进行调试
print(f"Python路径已设置:")
print(f"  - Backend: {current_dir}")
print(f"  - Core: {packages_dir / 'core' / 'src'}")
print(f"  - Scanner: {packages_dir / 'universal-scanner'}")
print(f"  - Parsers: {packages_dir / 'game-parsers'}")

# 导入并运行main
if __name__ == "__main__":
    import uvicorn
    from main import app
    
    print(f"\n启动服务器在 http://localhost:18001")
    print(f"API文档: http://localhost:18001/docs")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=18001,
        reload=False,
        log_level="info"
    )