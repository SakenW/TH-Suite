#!/usr/bin/env python
"""
清理重复文件脚本
安全删除所有重复的代码文件
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

# 要删除的文件列表
FILES_TO_DELETE = [
    # 重复的扫描器
    "ddd_scanner.py",
    "simple_scanner.py", 
    "fixed_scanner.py",
    "full_scanner.py",
    "upsert_scanner.py",
    "enterprise_upsert_scanner.py",
    "scanner_service.py",
    "test_real_scan.py",
    
    # 旧的数据库初始化
    "init_db.py",
    "init_db_ddd.py",
    "init_clean_db.py",
    "check_db.py",
    
    # 重复的数据库工具
    "tools/db_viewer/db_web_viewer.py",
    "tools/db_viewer/view_database.py", 
    "tools/db_viewer/view_db_simple.py",
]

# 要删除的目录
DIRS_TO_DELETE = [
    "infrastructure/scanners",  # 旧的扫描器目录
]

def create_backup_dir():
    """创建备份目录"""
    backup_dir = Path(f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    backup_dir.mkdir(exist_ok=True)
    return backup_dir

def backup_file(file_path: Path, backup_dir: Path):
    """备份文件"""
    if file_path.exists():
        # 使用文件名作为备份路径
        backup_path = backup_dir / file_path.name
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, backup_path)
        print(f"  ✅ 备份: {file_path} -> {backup_path}")
        return True
    return False

def delete_file(file_path: Path):
    """删除文件"""
    if file_path.exists():
        file_path.unlink()
        print(f"  🗑️ 删除: {file_path}")
        return True
    else:
        print(f"  ⚠️ 文件不存在: {file_path}")
        return False

def delete_directory(dir_path: Path):
    """删除目录"""
    if dir_path.exists() and dir_path.is_dir():
        shutil.rmtree(dir_path)
        print(f"  🗑️ 删除目录: {dir_path}")
        return True
    else:
        print(f"  ⚠️ 目录不存在: {dir_path}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("MC L10n 重复文件清理工具")
    print("=" * 60)
    
    # 创建备份目录
    backup_dir = create_backup_dir()
    print(f"\n📁 备份目录: {backup_dir}")
    
    # 统计
    backed_up = 0
    deleted_files = 0
    deleted_dirs = 0
    
    # 处理文件
    print("\n📝 处理文件:")
    for file_name in FILES_TO_DELETE:
        file_path = Path(file_name)
        if backup_file(file_path, backup_dir):
            backed_up += 1
            if delete_file(file_path):
                deleted_files += 1
    
    # 处理目录
    print("\n📁 处理目录:")
    for dir_name in DIRS_TO_DELETE:
        dir_path = Path(dir_name)
        if dir_path.exists():
            # 备份目录中的所有文件
            for file in dir_path.rglob("*.py"):
                if backup_file(file, backup_dir):
                    backed_up += 1
            # 删除整个目录
            if delete_directory(dir_path):
                deleted_dirs += 1
    
    # 清理__pycache__
    print("\n🧹 清理__pycache__目录:")
    pycache_count = 0
    for pycache in Path(".").rglob("__pycache__"):
        if pycache.is_dir():
            shutil.rmtree(pycache)
            pycache_count += 1
    print(f"  删除了 {pycache_count} 个__pycache__目录")
    
    # 报告
    print("\n" + "=" * 60)
    print("📊 清理报告:")
    print(f"  - 备份文件数: {backed_up}")
    print(f"  - 删除文件数: {deleted_files}")
    print(f"  - 删除目录数: {deleted_dirs}")
    print(f"  - 清理缓存数: {pycache_count}")
    print(f"\n💡 提示: 备份文件保存在 {backup_dir}")
    print("=" * 60)

if __name__ == "__main__":
    # 确认操作
    print("⚠️ 警告: 此操作将删除重复文件！")
    print("文件将被备份到backup_目录中。")
    response = input("\n确定要继续吗? (yes/no): ")
    
    if response.lower() == "yes":
        main()
        print("\n✅ 清理完成！")
    else:
        print("\n❌ 操作已取消。")