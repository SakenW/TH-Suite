#!/usr/bin/env python3
"""
简单的数据库查看工具（无外部依赖）
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime


def format_table(headers, rows, widths=None):
    """简单的表格格式化"""
    if not widths:
        widths = [max(len(str(h)), max(len(str(r[i]) if i < len(r) else '') for r in rows)) 
                  for i, h in enumerate(headers)]
    
    # 打印表头
    header_line = " | ".join(str(h).ljust(w) for h, w in zip(headers, widths))
    print(header_line)
    print("-" * len(header_line))
    
    # 打印数据行
    for row in rows:
        row_line = " | ".join(str(row[i] if i < len(row) else '').ljust(w) 
                             for i, w in enumerate(widths))
        print(row_line)


def view_database(db_path="mc_l10n_unified.db"):
    """查看数据库内容"""
    
    if not Path(db_path).exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print(f"📊 MC L10n 数据库分析")
    print(f"📁 文件: {db_path}")
    print(f"📏 大小: {Path(db_path).stat().st_size / 1024:.2f} KB")
    print("="*80)
    
    # 1. 数据库概览
    print("\n### 📋 数据库表概览 ###\n")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    
    table_info = []
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        table_info.append([table_name, count])
    
    format_table(["表名", "记录数"], table_info)
    
    # 2. 扫描会话
    print("\n### 🔍 最近的扫描会话 ###\n")
    cursor.execute("""
        SELECT 
            substr(scan_id, 1, 8) || '...' as scan_id,
            status,
            substr(COALESCE(target_path, path), -40) as path,
            progress_percent,
            total_mods,
            total_language_files,
            total_keys
        FROM scan_sessions 
        ORDER BY started_at DESC 
        LIMIT 5
    """)
    
    sessions = cursor.fetchall()
    if sessions:
        headers = ["扫描ID", "状态", "路径", "进度%", "模组", "语言", "键"]
        rows = [[s[0], s[1], s[2], f"{s[3]:.1f}", s[4], s[5], s[6]] for s in sessions]
        format_table(headers, rows)
    else:
        print("没有扫描会话记录")
    
    # 3. TOP 模组
    print("\n### 🏆 翻译键最多的模组 TOP 10 ###\n")
    cursor.execute("""
        SELECT 
            ROW_NUMBER() OVER (ORDER BY MAX(keys_count) DESC) as rank,
            COALESCE(mod_name, mod_id, 'Unknown') as name,
            COALESCE(mod_version, 'N/A') as version,
            MAX(keys_count) as keys,
            COUNT(DISTINCT language_code) as langs
        FROM scan_results 
        WHERE keys_count > 0
        GROUP BY mod_name, mod_version
        ORDER BY keys DESC
        LIMIT 10
    """)
    
    top_mods = cursor.fetchall()
    if top_mods:
        headers = ["排名", "模组名称", "版本", "翻译键", "语言数"]
        rows = [[m[0], m[1][:30], m[2][:10], m[3], m[4]] for m in top_mods]
        format_table(headers, rows)
    else:
        print("没有模组数据")
    
    # 4. 统计汇总
    print("\n### 📈 统计汇总 ###\n")
    
    # 获取总计
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT scan_id) as total_scans,
            SUM(total_mods) as total_mods,
            SUM(total_language_files) as total_langs,
            SUM(total_keys) as total_keys
        FROM scan_sessions 
        WHERE status = 'completed'
    """)
    
    stats = cursor.fetchone()
    if stats:
        print(f"✅ 完成扫描: {stats[0]} 次")
        print(f"📦 模组总数: {stats[1] or 0}")
        print(f"🌐 语言文件: {stats[2] or 0}")
        print(f"🔑 翻译键数: {stats[3] or 0}")
    
    # 5. 最新扫描详情
    print("\n### 📝 最新扫描详情 ###\n")
    cursor.execute("""
        SELECT scan_id, status, started_at, completed_at 
        FROM scan_sessions 
        ORDER BY started_at DESC 
        LIMIT 1
    """)
    
    latest = cursor.fetchone()
    if latest:
        print(f"扫描ID: {latest[0]}")
        print(f"状态: {latest[1]}")
        print(f"开始时间: {latest[2]}")
        print(f"完成时间: {latest[3]}")
        
        # 显示该扫描的一些结果
        cursor.execute("""
            SELECT COUNT(*) as count, SUM(keys_count) as total_keys
            FROM scan_results 
            WHERE scan_id = ?
        """, (latest[0],))
        
        result_stats = cursor.fetchone()
        if result_stats:
            print(f"扫描结果: {result_stats[0]} 条记录, 共 {result_stats[1] or 0} 个翻译键")
    
    conn.close()
    print("\n" + "="*80)
    print("✅ 数据库分析完成")
    print("="*80 + "\n")


def export_json(db_path="mc_l10n_unified.db", output="scan_data.json"):
    """导出数据为JSON"""
    
    if not Path(db_path).exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print(f"📤 正在导出数据到 {output}...")
    
    # 获取最新扫描
    cursor.execute("""
        SELECT * FROM scan_sessions 
        ORDER BY started_at DESC 
        LIMIT 1
    """)
    session = cursor.fetchone()
    
    if not session:
        print("❌ 没有找到扫描数据")
        return
    
    scan_id = session['scan_id']
    
    # 获取扫描结果
    cursor.execute("""
        SELECT * FROM scan_results 
        WHERE scan_id = ?
        ORDER BY keys_count DESC
    """, (scan_id,))
    results = cursor.fetchall()
    
    # 构建导出数据
    export_data = {
        'scan_session': dict(session),
        'summary': {
            'scan_id': scan_id,
            'status': session['status'],
            'path': session['target_path'] or session['path'],
            'total_mods': session['total_mods'],
            'total_language_files': session['total_language_files'],
            'total_keys': session['total_keys'],
            'started_at': session['started_at'],
            'completed_at': session['completed_at']
        },
        'results': [dict(r) for r in results],
        'export_time': datetime.now().isoformat()
    }
    
    # 写入文件
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
    
    conn.close()
    
    print(f"✅ 数据已导出到 {output}")
    print(f"   包含 {len(results)} 条扫描结果")
    file_size = Path(output).stat().st_size / 1024
    print(f"   文件大小: {file_size:.2f} KB")


if __name__ == "__main__":
    import sys
    
    # 简单的命令行参数处理
    if len(sys.argv) > 1:
        if sys.argv[1] == '--export':
            output = sys.argv[2] if len(sys.argv) > 2 else "scan_data.json"
            export_json(output=output)
        elif sys.argv[1] == '--help':
            print("用法:")
            print("  python view_db_simple.py           # 查看数据库")
            print("  python view_db_simple.py --export  # 导出为JSON")
            print("  python view_db_simple.py --export output.json  # 导出到指定文件")
        else:
            view_database(sys.argv[1])
    else:
        view_database()