#!/usr/bin/env python3
"""验证扫描数据是否存储到数据库中"""
import sqlite3
from pathlib import Path

def main():
    db_path = Path("data/mc_l10n.db")
    if not db_path.exists():
        print("❌ 数据库文件不存在:", db_path)
        return
    
    conn = sqlite3.connect(str(db_path))
    
    print("=== 语言文件 ===")
    files = conn.execute("""
        SELECT uid, locale, rel_path, format, size 
        FROM core_language_files
    """).fetchall()
    
    print(f"找到 {len(files)} 个语言文件:")
    for f in files:
        print(f"  {f[0]} | {f[1]} | {f[2]} | {f[3]} | {f[4]}")
    
    print("\n=== 翻译条目 ===")
    entries = conn.execute("""
        SELECT uid, language_file_uid, key, src_text, status 
        FROM core_translation_entries
    """).fetchall()
    
    print(f"找到 {len(entries)} 个翻译条目:")
    for e in entries:
        print(f"  {e[0]} | {e[1]} | {e[2]} | {e[3]} | {e[4]}")
    
    print("\n=== 事件日志 ===")
    events = conn.execute("""
        SELECT event_type, entity_ref, created_at 
        FROM ops_event_log 
        ORDER BY created_at DESC 
        LIMIT 10
    """).fetchall()
    
    print(f"最近 {len(events)} 个事件:")
    for e in events:
        print(f"  {e[0]} | {e[1]} | {e[2]}")
    
    conn.close()

if __name__ == "__main__":
    main()