#!/usr/bin/env python3
"""
数据库查看工具
用于查看和分析MC L10n扫描数据库的内容
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import argparse
from tabulate import tabulate


class DatabaseViewer:
    """数据库查看器"""
    
    def __init__(self, db_path: str = "mc_l10n_unified.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()
    
    def get_tables(self) -> List[str]:
        """获取所有表名"""
        self.cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
        """)
        return [row[0] for row in self.cursor.fetchall()]
    
    def get_table_info(self, table_name: str) -> List[Dict]:
        """获取表结构信息"""
        self.cursor.execute(f"PRAGMA table_info({table_name})")
        columns = []
        for row in self.cursor.fetchall():
            columns.append({
                'id': row[0],
                'name': row[1],
                'type': row[2],
                'notnull': row[3],
                'default': row[4],
                'primary_key': row[5]
            })
        return columns
    
    def get_row_count(self, table_name: str) -> int:
        """获取表的行数"""
        self.cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        return self.cursor.fetchone()[0]
    
    def show_database_overview(self):
        """显示数据库概览"""
        print("\n" + "="*60)
        print(f"📊 数据库概览: {self.db_path}")
        print("="*60)
        
        # 获取文件大小
        db_size = Path(self.db_path).stat().st_size / 1024  # KB
        print(f"📁 文件大小: {db_size:.2f} KB")
        
        # 显示所有表
        tables = self.get_tables()
        print(f"\n📋 表数量: {len(tables)}")
        
        table_data = []
        for table in tables:
            row_count = self.get_row_count(table)
            table_data.append([table, row_count])
        
        print("\n" + tabulate(table_data, headers=['表名', '记录数'], tablefmt='grid'))
    
    def show_scan_sessions(self, limit: int = 10):
        """显示扫描会话"""
        print("\n" + "="*60)
        print("🔍 最近的扫描会话")
        print("="*60)
        
        self.cursor.execute("""
            SELECT 
                scan_id,
                status,
                path,
                target_path,
                scan_mode,
                started_at,
                completed_at,
                total_mods,
                total_language_files,
                total_keys,
                progress_percent
            FROM scan_sessions 
            ORDER BY started_at DESC 
            LIMIT ?
        """, (limit,))
        
        sessions = self.cursor.fetchall()
        
        for session in sessions:
            print(f"\n📦 扫描ID: {session['scan_id'][:12]}...")
            print(f"   状态: {session['status']}")
            print(f"   路径: {session['target_path'] or session['path']}")
            print(f"   模式: {session['scan_mode']}")
            print(f"   进度: {session['progress_percent']:.1f}%")
            print(f"   统计: {session['total_mods']} 模组, "
                  f"{session['total_language_files']} 语言文件, "
                  f"{session['total_keys']} 翻译键")
            
            # 计算耗时
            if session['started_at'] and session['completed_at']:
                try:
                    start = datetime.fromisoformat(session['started_at'])
                    end = datetime.fromisoformat(session['completed_at'])
                    duration = (end - start).total_seconds()
                    print(f"   耗时: {duration:.2f} 秒")
                except:
                    pass
    
    def show_scan_results(self, scan_id: str = None, limit: int = 20):
        """显示扫描结果"""
        print("\n" + "="*60)
        print("📊 扫描结果详情")
        print("="*60)
        
        if scan_id:
            where_clause = "WHERE scan_id = ?"
            params = (scan_id, limit)
        else:
            where_clause = ""
            params = (limit,)
        
        self.cursor.execute(f"""
            SELECT 
                scan_id,
                mod_id,
                mod_name,
                mod_version,
                file_path,
                language_code,
                keys_count
            FROM scan_results 
            {where_clause}
            ORDER BY keys_count DESC 
            LIMIT ?
        """, params)
        
        results = self.cursor.fetchall()
        
        if results:
            table_data = []
            for r in results:
                table_data.append([
                    r['mod_name'] or r['mod_id'] or 'Unknown',
                    r['mod_version'] or 'N/A',
                    r['language_code'] or 'en_us',
                    r['keys_count'] or 0,
                    Path(r['file_path']).name if r['file_path'] else 'N/A'
                ])
            
            print("\n" + tabulate(
                table_data, 
                headers=['模组名称', '版本', '语言', '键数', '文件'],
                tablefmt='grid'
            ))
    
    def show_top_mods(self, limit: int = 10):
        """显示翻译键最多的模组"""
        print("\n" + "="*60)
        print("🏆 翻译键最多的模组 TOP " + str(limit))
        print("="*60)
        
        self.cursor.execute("""
            SELECT 
                mod_name,
                mod_version,
                MAX(keys_count) as max_keys,
                COUNT(DISTINCT language_code) as lang_count
            FROM scan_results 
            WHERE mod_name IS NOT NULL
            GROUP BY mod_name, mod_version
            ORDER BY max_keys DESC
            LIMIT ?
        """, (limit,))
        
        results = self.cursor.fetchall()
        
        if results:
            table_data = []
            for i, r in enumerate(results, 1):
                table_data.append([
                    i,
                    r['mod_name'],
                    r['mod_version'] or 'N/A',
                    r['max_keys'],
                    r['lang_count']
                ])
            
            print("\n" + tabulate(
                table_data,
                headers=['排名', '模组名称', '版本', '翻译键数', '语言数'],
                tablefmt='grid'
            ))
    
    def export_to_json(self, output_file: str = "scan_data.json"):
        """导出数据为JSON格式"""
        print(f"\n📤 导出数据到 {output_file}...")
        
        # 获取最新的扫描会话
        self.cursor.execute("""
            SELECT * FROM scan_sessions 
            ORDER BY started_at DESC 
            LIMIT 1
        """)
        session = self.cursor.fetchone()
        
        if not session:
            print("❌ 没有找到扫描数据")
            return
        
        scan_id = session['scan_id']
        
        # 获取该会话的所有结果
        self.cursor.execute("""
            SELECT * FROM scan_results 
            WHERE scan_id = ?
        """, (scan_id,))
        results = self.cursor.fetchall()
        
        # 构建导出数据
        export_data = {
            'scan_session': dict(session),
            'results': [dict(r) for r in results],
            'summary': {
                'total_mods': session['total_mods'],
                'total_language_files': session['total_language_files'],
                'total_keys': session['total_keys'],
                'scan_date': session['started_at']
            }
        }
        
        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 数据已导出到 {output_file}")
        print(f"   包含 {len(results)} 条扫描结果")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='MC L10n 数据库查看工具')
    parser.add_argument('--db', default='mc_l10n_unified.db', help='数据库文件路径')
    parser.add_argument('--export', help='导出数据到JSON文件')
    parser.add_argument('--scan-id', help='指定扫描ID查看详情')
    parser.add_argument('--limit', type=int, default=10, help='显示记录数限制')
    parser.add_argument('--top-mods', action='store_true', help='显示翻译键最多的模组')
    
    args = parser.parse_args()
    
    # 检查数据库文件是否存在
    if not Path(args.db).exists():
        print(f"❌ 数据库文件不存在: {args.db}")
        return
    
    with DatabaseViewer(args.db) as viewer:
        # 显示数据库概览
        viewer.show_database_overview()
        
        # 显示扫描会话
        viewer.show_scan_sessions(limit=args.limit)
        
        # 显示扫描结果
        if args.scan_id:
            viewer.show_scan_results(scan_id=args.scan_id, limit=args.limit)
        
        # 显示TOP模组
        if args.top_mods:
            viewer.show_top_mods(limit=args.limit)
        
        # 导出数据
        if args.export:
            viewer.export_to_json(args.export)


if __name__ == "__main__":
    main()