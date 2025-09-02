import sqlite3

conn = sqlite3.connect('mc_l10n_unified.db')
cursor = conn.cursor()

# 获取总数
cursor.execute('SELECT COUNT(*) FROM content_items')
count = cursor.fetchone()[0]
print(f'Total content items: {count}')

# 按类型统计
cursor.execute('SELECT content_type, COUNT(*) FROM content_items GROUP BY content_type')
print('By type:')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]}')

# 查看最近的扫描
cursor.execute('SELECT scan_id, target_path, status, items_discovered FROM scan_sessions ORDER BY start_time DESC LIMIT 5')
print('\nRecent scans:')
for row in cursor.fetchall():
    print(f'  ID: {row[0][:8]}..., Path: {row[1]}, Status: {row[2]}, Items: {row[3]}')

# 查看前几个content items
cursor.execute('SELECT content_hash, content_type, name FROM content_items LIMIT 5')
print('\nSample content items:')
for row in cursor.fetchall():
    print(f'  Hash: {row[0][:8]}..., Type: {row[1]}, Name: {row[2]}')

conn.close()