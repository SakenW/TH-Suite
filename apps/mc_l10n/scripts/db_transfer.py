#!/usr/bin/env python3
"""
数据库传输工具
用于导入、导出和迁移数据库数据
"""

import sqlite3
import json
import csv
import sys
import os
from pathlib import Path
from typing import Dict, List, Any
import argparse
from datetime import datetime
import zipfile
import shutil


class DatabaseTransfer:
    """数据库传输工具"""
    
    def __init__(self, db_path: str = None):
        """初始化"""
        if db_path is None:
            db_path = Path(__file__).parent.parent / "backend" / "mc_l10n.db"
        
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"数据库文件不存在: {db_path}")
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
    
    def export_to_json(self, output_file: str = None):
        """导出整个数据库到JSON"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"mc_l10n_export_{timestamp}.json"
        
        output_path = Path(output_file)
        
        print(f"📦 导出数据库到JSON: {output_path}")
        
        data = {}
        
        # 获取所有表
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in self.cursor.fetchall()]
        
        for table in tables:
            if table.startswith('sqlite_'):
                continue
            
            print(f"  导出表: {table}")
            self.cursor.execute(f"SELECT * FROM {table}")
            rows = self.cursor.fetchall()
            
            # 转换为字典列表
            data[table] = []
            for row in rows:
                data[table].append(dict(row))
        
        # 写入JSON文件
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"✅ 导出完成: {len(data)} 个表")
        print(f"   文件大小: {output_path.stat().st_size / 1024:.1f} KB")
        
        return str(output_path)
    
    def import_from_json(self, input_file: str, merge: bool = False):
        """从JSON导入数据"""
        input_path = Path(input_file)
        
        if not input_path.exists():
            raise FileNotFoundError(f"输入文件不存在: {input_file}")
        
        print(f"📥 从JSON导入数据: {input_path}")
        
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not merge:
            # 清空现有数据
            print("⚠️ 清空现有数据...")
            for table in data.keys():
                try:
                    self.cursor.execute(f"DELETE FROM {table}")
                except sqlite3.Error as e:
                    print(f"  警告: 无法清空表 {table}: {e}")
        
        # 导入数据
        for table, rows in data.items():
            print(f"  导入表 {table}: {len(rows)} 行")
            
            if not rows:
                continue
            
            # 获取列名
            columns = list(rows[0].keys())
            placeholders = ','.join(['?' for _ in columns])
            
            # 插入数据
            for row in rows:
                values = [row.get(col) for col in columns]
                
                if merge:
                    # 使用INSERT OR REPLACE进行合并
                    query = f"INSERT OR REPLACE INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
                else:
                    query = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
                
                try:
                    self.cursor.execute(query, values)
                except sqlite3.Error as e:
                    print(f"    错误: 插入失败 - {e}")
        
        self.conn.commit()
        print("✅ 导入完成")
    
    def export_translations_csv(self, output_dir: str = None):
        """导出翻译到CSV文件（便于编辑）"""
        if output_dir is None:
            output_dir = Path.cwd() / "translations_export"
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📊 导出翻译到CSV: {output_dir}")
        
        # 获取所有模组
        self.cursor.execute("""
            SELECT DISTINCT m.mod_id, m.display_name
            FROM mods m
            JOIN language_files lf ON m.mod_id = lf.mod_id
        """)
        
        mods = self.cursor.fetchall()
        
        for mod_id, display_name in mods:
            # 创建模组目录
            mod_dir = output_dir / f"{mod_id}"
            mod_dir.mkdir(exist_ok=True)
            
            # 获取该模组的所有语言
            self.cursor.execute("""
                SELECT DISTINCT locale_code
                FROM language_files
                WHERE mod_id = ?
            """, (mod_id,))
            
            locales = [row[0] for row in self.cursor.fetchall()]
            
            # 获取所有翻译键
            self.cursor.execute("""
                SELECT DISTINCT te.entry_key
                FROM translation_entries te
                JOIN language_files lf ON te.file_id = lf.file_id
                WHERE lf.mod_id = ?
                ORDER BY te.entry_key
            """, (mod_id,))
            
            keys = [row[0] for row in self.cursor.fetchall()]
            
            if not keys:
                continue
            
            # 创建CSV文件
            csv_file = mod_dir / f"{mod_id}_translations.csv"
            
            with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                
                # 写入标题行
                header = ['key'] + locales
                writer.writerow(header)
                
                # 写入翻译数据
                for key in keys:
                    row = [key]
                    
                    for locale in locales:
                        # 获取该键在该语言的翻译
                        self.cursor.execute("""
                            SELECT te.entry_value
                            FROM translation_entries te
                            JOIN language_files lf ON te.file_id = lf.file_id
                            WHERE lf.mod_id = ? AND lf.locale_code = ? AND te.entry_key = ?
                        """, (mod_id, locale, key))
                        
                        result = self.cursor.fetchone()
                        row.append(result[0] if result else '')
                    
                    writer.writerow(row)
            
            print(f"  导出: {csv_file.name} ({len(keys)} 键, {len(locales)} 语言)")
        
        print(f"✅ 导出完成: {len(mods)} 个模组")
    
    def import_translations_csv(self, csv_file: str):
        """从CSV导入翻译"""
        csv_path = Path(csv_file)
        
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV文件不存在: {csv_file}")
        
        print(f"📝 从CSV导入翻译: {csv_path}")
        
        # 从文件名提取模组ID
        mod_id = csv_path.stem.replace('_translations', '')
        
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            # 获取语言列表（除了key列）
            locales = [col for col in reader.fieldnames if col != 'key']
            
            print(f"  模组ID: {mod_id}")
            print(f"  语言: {', '.join(locales)}")
            
            imported_count = 0
            
            for row in reader:
                key = row['key']
                
                for locale in locales:
                    value = row.get(locale, '')
                    
                    if not value:
                        continue
                    
                    # 查找或创建语言文件
                    self.cursor.execute("""
                        SELECT file_id FROM language_files
                        WHERE mod_id = ? AND locale_code = ?
                        LIMIT 1
                    """, (mod_id, locale))
                    
                    result = self.cursor.fetchone()
                    
                    if result:
                        file_id = result[0]
                        
                        # 更新或插入翻译
                        self.cursor.execute("""
                            INSERT OR REPLACE INTO translation_entries
                            (entry_id, file_id, entry_key, entry_value)
                            VALUES (
                                (SELECT entry_id FROM translation_entries 
                                 WHERE file_id = ? AND entry_key = ?),
                                ?, ?, ?
                            )
                        """, (file_id, key, file_id, key, value))
                        
                        imported_count += 1
        
        self.conn.commit()
        print(f"✅ 导入完成: {imported_count} 个翻译条目")
    
    def backup_database(self, backup_dir: str = None):
        """备份数据库"""
        if backup_dir is None:
            backup_dir = self.db_path.parent / "backups"
        else:
            backup_dir = Path(backup_dir)
        
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"mc_l10n_backup_{timestamp}.db"
        
        print(f"💾 备份数据库到: {backup_file}")
        
        # 复制数据库文件
        shutil.copy2(self.db_path, backup_file)
        
        # 创建压缩包
        zip_file = backup_dir / f"mc_l10n_backup_{timestamp}.zip"
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(backup_file, backup_file.name)
            
            # 同时导出JSON
            json_file = self.export_to_json(backup_dir / f"mc_l10n_backup_{timestamp}.json")
            zf.write(json_file, Path(json_file).name)
        
        # 删除临时文件
        backup_file.unlink()
        Path(json_file).unlink()
        
        print(f"✅ 备份完成: {zip_file}")
        print(f"   文件大小: {zip_file.stat().st_size / 1024:.1f} KB")
        
        return str(zip_file)
    
    def restore_database(self, backup_file: str):
        """恢复数据库"""
        backup_path = Path(backup_file)
        
        if not backup_path.exists():
            raise FileNotFoundError(f"备份文件不存在: {backup_file}")
        
        print(f"♻️ 恢复数据库从: {backup_path}")
        
        if backup_path.suffix == '.zip':
            # 解压备份
            temp_dir = backup_path.parent / "temp_restore"
            temp_dir.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(backup_path, 'r') as zf:
                zf.extractall(temp_dir)
            
            # 查找数据库文件
            db_files = list(temp_dir.glob("*.db"))
            if db_files:
                # 使用数据库文件恢复
                print("  使用数据库文件恢复...")
                self.conn.close()
                shutil.copy2(db_files[0], self.db_path)
                self.conn = sqlite3.connect(str(self.db_path))
                self.conn.row_factory = sqlite3.Row
                self.cursor = self.conn.cursor()
            else:
                # 使用JSON文件恢复
                json_files = list(temp_dir.glob("*.json"))
                if json_files:
                    print("  使用JSON文件恢复...")
                    self.import_from_json(json_files[0], merge=False)
            
            # 清理临时目录
            shutil.rmtree(temp_dir)
            
        elif backup_path.suffix == '.db':
            # 直接使用数据库文件
            self.conn.close()
            shutil.copy2(backup_path, self.db_path)
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            
        elif backup_path.suffix == '.json':
            # 使用JSON文件
            self.import_from_json(backup_path, merge=False)
        
        else:
            raise ValueError(f"不支持的备份文件格式: {backup_path.suffix}")
        
        print("✅ 恢复完成")
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'conn'):
            self.conn.close()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='MC L10n 数据库传输工具')
    parser.add_argument('--db', type=str, help='数据库文件路径')
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 导出JSON
    export_json_parser = subparsers.add_parser('export-json', help='导出数据库到JSON')
    export_json_parser.add_argument('--output', help='输出文件名')
    
    # 导入JSON
    import_json_parser = subparsers.add_parser('import-json', help='从JSON导入数据')
    import_json_parser.add_argument('input_file', help='输入文件')
    import_json_parser.add_argument('--merge', action='store_true', help='合并而不是替换')
    
    # 导出CSV
    export_csv_parser = subparsers.add_parser('export-csv', help='导出翻译到CSV')
    export_csv_parser.add_argument('--output', help='输出目录')
    
    # 导入CSV
    import_csv_parser = subparsers.add_parser('import-csv', help='从CSV导入翻译')
    import_csv_parser.add_argument('csv_file', help='CSV文件路径')
    
    # 备份
    backup_parser = subparsers.add_parser('backup', help='备份数据库')
    backup_parser.add_argument('--dir', help='备份目录')
    
    # 恢复
    restore_parser = subparsers.add_parser('restore', help='恢复数据库')
    restore_parser.add_argument('backup_file', help='备份文件')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        transfer = DatabaseTransfer(args.db)
        
        if args.command == 'export-json':
            transfer.export_to_json(args.output)
        
        elif args.command == 'import-json':
            transfer.import_from_json(args.input_file, args.merge)
        
        elif args.command == 'export-csv':
            transfer.export_translations_csv(args.output)
        
        elif args.command == 'import-csv':
            transfer.import_translations_csv(args.csv_file)
        
        elif args.command == 'backup':
            transfer.backup_database(args.dir)
        
        elif args.command == 'restore':
            transfer.restore_database(args.backup_file)
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()