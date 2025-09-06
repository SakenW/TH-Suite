#!/usr/bin/env python3
"""
数据库读取工具
提供MC L10n数据库的查询和分析功能
"""

import sqlite3
import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
try:
    from tabulate import tabulate
except ImportError:
    # 简单的表格替代实现
    def tabulate(rows, headers=None, tablefmt=None):
        if headers:
            print(" | ".join(str(h) for h in headers))
            print("-" * (len(headers) * 15))
        for row in rows:
            print(" | ".join(str(cell) if cell else 'N/A' for cell in row))
        return ""
import argparse

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class DatabaseReader:
    """数据库读取器"""
    
    def __init__(self, db_path: str = None):
        """初始化数据库连接"""
        if db_path is None:
            db_path = Path(__file__).parent.parent / "backend" / "mc_l10n.db"
        
        self.db_path = db_path
        if not Path(db_path).exists():
            raise FileNotFoundError(f"数据库文件不存在: {db_path}")
        
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
    
    def __del__(self):
        """关闭数据库连接"""
        if hasattr(self, 'conn'):
            self.conn.close()
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        stats = {
            'total_mods': 0,
            'total_language_files': 0,
            'total_translation_entries': 0,
            'language_distribution': {},
            'mod_loaders': {},
            'largest_mods': [],
            'recent_scans': []
        }
        
        try:
            # 模组总数
            self.cursor.execute("SELECT COUNT(*) FROM mods")
            stats['total_mods'] = self.cursor.fetchone()[0]
            
            # 语言文件总数
            self.cursor.execute("SELECT COUNT(*) FROM language_files")
            stats['total_language_files'] = self.cursor.fetchone()[0]
            
            # 翻译条目总数
            self.cursor.execute("SELECT COUNT(*) FROM translation_entries")
            stats['total_translation_entries'] = self.cursor.fetchone()[0]
            
            # 语言分布
            self.cursor.execute("""
                SELECT locale_code, COUNT(*) as count 
                FROM language_files 
                GROUP BY locale_code 
                ORDER BY count DESC
            """)
            stats['language_distribution'] = dict(self.cursor.fetchall())
            
            # 模组加载器分布
            self.cursor.execute("""
                SELECT mod_loader, COUNT(*) as count 
                FROM mods 
                WHERE mod_loader IS NOT NULL 
                GROUP BY mod_loader
            """)
            stats['mod_loaders'] = dict(self.cursor.fetchall())
            
            # 最大的模组（按语言文件数）
            self.cursor.execute("""
                SELECT m.mod_id, m.display_name, COUNT(lf.file_id) as lang_count
                FROM mods m
                LEFT JOIN language_files lf ON m.mod_id = lf.mod_id
                GROUP BY m.mod_id, m.display_name
                ORDER BY lang_count DESC
                LIMIT 10
            """)
            stats['largest_mods'] = [dict(row) for row in self.cursor.fetchall()]
            
        except sqlite3.Error as e:
            print(f"查询统计信息时出错: {e}")
        
        return stats
    
    def list_mods(self, limit: int = 50) -> List[Dict[str, Any]]:
        """列出所有模组"""
        self.cursor.execute("""
            SELECT mod_id, display_name, version, mod_loader, file_path, file_size
            FROM mods
            ORDER BY display_name
            LIMIT ?
        """, (limit,))
        
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_mod_details(self, mod_id: str) -> Optional[Dict[str, Any]]:
        """获取模组详细信息"""
        # 获取模组基本信息
        self.cursor.execute("""
            SELECT * FROM mods WHERE mod_id = ?
        """, (mod_id,))
        
        mod = self.cursor.fetchone()
        if not mod:
            return None
        
        result = dict(mod)
        
        # 获取语言文件
        self.cursor.execute("""
            SELECT file_id, locale_code, namespace, key_count, file_path
            FROM language_files
            WHERE mod_id = ?
            ORDER BY locale_code
        """, (mod_id,))
        
        result['language_files'] = [dict(row) for row in self.cursor.fetchall()]
        
        # 获取翻译条目示例
        if result['language_files']:
            file_id = result['language_files'][0]['file_id']
            self.cursor.execute("""
                SELECT entry_key, entry_value
                FROM translation_entries
                WHERE file_id = ?
                LIMIT 10
            """, (file_id,))
            
            result['sample_entries'] = [dict(row) for row in self.cursor.fetchall()]
        
        return result
    
    def search_translations(self, keyword: str, locale: str = None) -> List[Dict[str, Any]]:
        """搜索翻译条目"""
        query = """
            SELECT 
                te.entry_key,
                te.entry_value,
                lf.locale_code,
                lf.namespace,
                m.display_name as mod_name
            FROM translation_entries te
            JOIN language_files lf ON te.file_id = lf.file_id
            JOIN mods m ON lf.mod_id = m.mod_id
            WHERE (te.entry_key LIKE ? OR te.entry_value LIKE ?)
        """
        
        params = [f'%{keyword}%', f'%{keyword}%']
        
        if locale:
            query += " AND lf.locale_code = ?"
            params.append(locale)
        
        query += " LIMIT 100"
        
        self.cursor.execute(query, params)
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_untranslated_keys(self, source_locale: str = 'en_us', target_locale: str = 'zh_cn') -> List[Dict[str, Any]]:
        """获取未翻译的键"""
        self.cursor.execute("""
            SELECT DISTINCT
                te1.entry_key,
                te1.entry_value as source_value,
                m.display_name as mod_name,
                lf1.namespace
            FROM translation_entries te1
            JOIN language_files lf1 ON te1.file_id = lf1.file_id
            JOIN mods m ON lf1.mod_id = m.mod_id
            WHERE lf1.locale_code = ?
            AND NOT EXISTS (
                SELECT 1 
                FROM translation_entries te2
                JOIN language_files lf2 ON te2.file_id = lf2.file_id
                WHERE lf2.mod_id = lf1.mod_id
                AND lf2.locale_code = ?
                AND te2.entry_key = te1.entry_key
            )
            LIMIT 100
        """, (source_locale, target_locale))
        
        return [dict(row) for row in self.cursor.fetchall()]
    
    def export_mod_translations(self, mod_id: str, output_dir: str = None) -> int:
        """导出模组的所有翻译文件"""
        if output_dir is None:
            output_dir = Path.cwd() / "exports" / mod_id
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 获取所有语言文件
        self.cursor.execute("""
            SELECT DISTINCT lf.locale_code, lf.namespace
            FROM language_files lf
            WHERE lf.mod_id = ?
        """, (mod_id,))
        
        files = self.cursor.fetchall()
        exported_count = 0
        
        for locale_code, namespace in files:
            # 获取该语言文件的所有条目
            self.cursor.execute("""
                SELECT te.entry_key, te.entry_value
                FROM translation_entries te
                JOIN language_files lf ON te.file_id = lf.file_id
                WHERE lf.mod_id = ? AND lf.locale_code = ? AND lf.namespace = ?
            """, (mod_id, locale_code, namespace))
            
            entries = dict(self.cursor.fetchall())
            
            if entries:
                # 导出为JSON文件
                output_file = output_dir / f"{namespace}_{locale_code}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(entries, f, ensure_ascii=False, indent=2)
                
                exported_count += 1
                print(f"导出: {output_file}")
        
        return exported_count
    
    def analyze_coverage(self) -> Dict[str, Any]:
        """分析翻译覆盖率"""
        self.cursor.execute("""
            SELECT 
                m.mod_id,
                m.display_name,
                COUNT(DISTINCT lf.locale_code) as lang_count,
                COUNT(DISTINCT te.entry_key) as unique_keys
            FROM mods m
            LEFT JOIN language_files lf ON m.mod_id = lf.mod_id
            LEFT JOIN translation_entries te ON lf.file_id = te.file_id
            GROUP BY m.mod_id, m.display_name
        """)
        
        coverage = []
        for row in self.cursor.fetchall():
            mod_data = dict(row)
            
            # 计算中文覆盖率
            self.cursor.execute("""
                SELECT COUNT(DISTINCT te.entry_key) as zh_keys
                FROM translation_entries te
                JOIN language_files lf ON te.file_id = lf.file_id
                WHERE lf.mod_id = ? AND lf.locale_code IN ('zh_cn', 'zh_tw')
            """, (mod_data['mod_id'],))
            
            zh_keys = self.cursor.fetchone()[0]
            
            if mod_data['unique_keys'] > 0:
                mod_data['zh_coverage'] = (zh_keys / mod_data['unique_keys']) * 100
            else:
                mod_data['zh_coverage'] = 0
            
            coverage.append(mod_data)
        
        # 按覆盖率排序
        coverage.sort(key=lambda x: x['zh_coverage'])
        
        return {
            'mods_coverage': coverage,
            'total_mods': len(coverage),
            'fully_translated': sum(1 for m in coverage if m['zh_coverage'] >= 100),
            'partially_translated': sum(1 for m in coverage if 0 < m['zh_coverage'] < 100),
            'not_translated': sum(1 for m in coverage if m['zh_coverage'] == 0)
        }
    
    def get_recent_scans(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的扫描记录"""
        # 尝试从scan_sessions表获取（如果存在）
        try:
            self.cursor.execute("""
                SELECT * FROM scan_sessions
                ORDER BY started_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error:
            # 如果表不存在，返回空列表
            return []


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='MC L10n 数据库读取工具')
    parser.add_argument('--db', type=str, help='数据库文件路径')
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 统计信息
    subparsers.add_parser('stats', help='显示数据库统计信息')
    
    # 列出模组
    list_parser = subparsers.add_parser('list', help='列出所有模组')
    list_parser.add_argument('--limit', type=int, default=50, help='限制数量')
    
    # 模组详情
    detail_parser = subparsers.add_parser('detail', help='显示模组详细信息')
    detail_parser.add_argument('mod_id', help='模组ID')
    
    # 搜索翻译
    search_parser = subparsers.add_parser('search', help='搜索翻译条目')
    search_parser.add_argument('keyword', help='搜索关键词')
    search_parser.add_argument('--locale', help='语言代码')
    
    # 未翻译键
    untrans_parser = subparsers.add_parser('untranslated', help='查找未翻译的键')
    untrans_parser.add_argument('--source', default='en_us', help='源语言')
    untrans_parser.add_argument('--target', default='zh_cn', help='目标语言')
    
    # 导出翻译
    export_parser = subparsers.add_parser('export', help='导出模组翻译')
    export_parser.add_argument('mod_id', help='模组ID')
    export_parser.add_argument('--output', help='输出目录')
    
    # 覆盖率分析
    subparsers.add_parser('coverage', help='分析翻译覆盖率')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        reader = DatabaseReader(args.db)
        
        if args.command == 'stats':
            stats = reader.get_statistics()
            print("\n=== 数据库统计信息 ===")
            print(f"模组总数: {stats['total_mods']}")
            print(f"语言文件总数: {stats['total_language_files']}")
            print(f"翻译条目总数: {stats['total_translation_entries']}")
            
            if stats['language_distribution']:
                print("\n语言分布:")
                for lang, count in stats['language_distribution'].items():
                    print(f"  {lang}: {count}")
            
            if stats['mod_loaders']:
                print("\n模组加载器:")
                for loader, count in stats['mod_loaders'].items():
                    print(f"  {loader}: {count}")
            
            if stats['largest_mods']:
                print("\n最大的模组（按语言文件数）:")
                for mod in stats['largest_mods'][:5]:
                    print(f"  {mod['display_name']}: {mod['lang_count']} 个语言文件")
        
        elif args.command == 'list':
            mods = reader.list_mods(args.limit)
            if mods:
                headers = ['模组ID', '显示名称', '版本', '加载器', '文件大小']
                rows = [[m['mod_id'], m['display_name'], m['version'], 
                        m['mod_loader'], f"{m['file_size']//1024}KB" if m['file_size'] else 'N/A'] 
                       for m in mods]
                print(tabulate(rows, headers=headers, tablefmt='grid'))
            else:
                print("没有找到模组")
        
        elif args.command == 'detail':
            details = reader.get_mod_details(args.mod_id)
            if details:
                print(f"\n=== 模组详情: {details['display_name']} ===")
                print(f"模组ID: {details['mod_id']}")
                print(f"版本: {details.get('version', 'N/A')}")
                print(f"加载器: {details.get('mod_loader', 'N/A')}")
                print(f"文件路径: {details.get('file_path', 'N/A')}")
                
                if details.get('language_files'):
                    print(f"\n语言文件 ({len(details['language_files'])} 个):")
                    for lf in details['language_files']:
                        print(f"  - {lf['locale_code']}: {lf['key_count']} 个键")
                
                if details.get('sample_entries'):
                    print("\n翻译条目示例:")
                    for entry in details['sample_entries'][:5]:
                        print(f"  {entry['entry_key']}: {entry['entry_value'][:50]}...")
            else:
                print(f"未找到模组: {args.mod_id}")
        
        elif args.command == 'search':
            results = reader.search_translations(args.keyword, args.locale)
            if results:
                print(f"\n找到 {len(results)} 个匹配项:")
                for r in results[:20]:
                    print(f"\n[{r['mod_name']}] {r['locale_code']}")
                    print(f"  键: {r['entry_key']}")
                    print(f"  值: {r['entry_value'][:100]}...")
            else:
                print("没有找到匹配的翻译")
        
        elif args.command == 'untranslated':
            results = reader.get_untranslated_keys(args.source, args.target)
            if results:
                print(f"\n找到 {len(results)} 个未翻译的键:")
                for r in results[:20]:
                    print(f"\n[{r['mod_name']}] {r['namespace']}")
                    print(f"  键: {r['entry_key']}")
                    print(f"  原文: {r['source_value'][:100]}...")
            else:
                print("所有键都已翻译")
        
        elif args.command == 'export':
            count = reader.export_mod_translations(args.mod_id, args.output)
            print(f"\n成功导出 {count} 个语言文件")
        
        elif args.command == 'coverage':
            coverage = reader.analyze_coverage()
            print("\n=== 翻译覆盖率分析 ===")
            print(f"总模组数: {coverage['total_mods']}")
            print(f"完全翻译: {coverage['fully_translated']}")
            print(f"部分翻译: {coverage['partially_translated']}")
            print(f"未翻译: {coverage['not_translated']}")
            
            print("\n覆盖率最低的模组:")
            for mod in coverage['mods_coverage'][:10]:
                print(f"  {mod['display_name']}: {mod['zh_coverage']:.1f}%")
    
    except FileNotFoundError as e:
        print(f"错误: {e}")
        print("请确保数据库文件存在，或使用 --db 参数指定路径")
    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()