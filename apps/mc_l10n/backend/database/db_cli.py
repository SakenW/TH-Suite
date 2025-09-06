#!/usr/bin/env python
"""
数据库管理CLI工具
提供命令行界面管理本地数据库
"""

import click
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from tabulate import tabulate
import asyncio

# 导入服务模块
from init_local_db import LocalDatabaseInitializer
from scan_service import ScanDatabaseService
from sync_service import DataSyncService, SyncDirection
from offline_tracker import OfflineChangeTracker, EntityType, ChangeOperation


@click.group()
@click.option('--db', default='mc_l10n_local.db', help='数据库文件路径')
@click.pass_context
def cli(ctx, db):
    """MC L10n 数据库管理工具"""
    ctx.ensure_object(dict)
    ctx.obj['db_path'] = db


@cli.command()
@click.option('--reset', is_flag=True, help='重置数据库')
@click.pass_context
def init(ctx, reset):
    """初始化数据库"""
    db_path = ctx.obj['db_path']
    
    click.echo(f"初始化数据库: {db_path}")
    
    if reset and click.confirm("⚠️ 这将删除所有现有数据，确定继续？"):
        initializer = LocalDatabaseInitializer(db_path)
        initializer.initialize(reset=True)
    else:
        initializer = LocalDatabaseInitializer(db_path)
        initializer.initialize(reset=False)
        
    click.echo("✅ 数据库初始化完成")


@cli.command()
@click.argument('path')
@click.option('--recursive', is_flag=True, help='递归扫描')
@click.pass_context
def scan(ctx, path, recursive):
    """扫描MOD文件或目录"""
    db_path = ctx.obj['db_path']
    service = ScanDatabaseService(db_path)
    
    scan_path = Path(path)
    if not scan_path.exists():
        click.echo(f"❌ 路径不存在: {path}", err=True)
        return
        
    click.echo(f"开始扫描: {scan_path}")
    
    if scan_path.is_file():
        # 扫描单个文件
        result = service.discover_mod(scan_path)
        if result:
            click.echo(f"✅ 成功扫描: {result['mod_name']}")
            click.echo(f"  - MOD ID: {result['mod_id']}")
            click.echo(f"  - 版本: {result['version']}")
            click.echo(f"  - 语言文件: {result['language_count']}")
            click.echo(f"  - 翻译键: {result['total_keys']}")
        else:
            click.echo("❌ 扫描失败")
    else:
        # 扫描目录
        with click.progressbar(length=100, label='扫描进度') as bar:
            def progress_callback(current, total, name):
                percent = int((current / total) * 100)
                bar.update(percent - bar.pos)
                
            results = service.scan_directory(scan_path, progress_callback)
            
        click.echo(f"\n扫描完成:")
        click.echo(f"  - 总文件: {results['total_files']}")
        click.echo(f"  - 成功: {results['successful']}")
        click.echo(f"  - 失败: {results['failed']}")
        
    service.close()


@cli.command()
@click.pass_context
def stats(ctx):
    """显示数据库统计信息"""
    db_path = ctx.obj['db_path']
    service = ScanDatabaseService(db_path)
    
    stats = service.get_statistics()
    
    click.echo("\n📊 数据库统计:")
    click.echo(f"\nMOD统计:")
    click.echo(f"  总数: {stats['mods']['total']}")
    click.echo(f"  已上传: {stats['mods']['uploaded']}")
    click.echo(f"  待上传: {stats['mods']['pending']}")
    
    click.echo(f"\n语言文件: {stats['language_files']}")
    
    click.echo(f"\n翻译条目:")
    click.echo(f"  总数: {stats['translation_entries']['total']}")
    if stats['translation_entries']['by_status']:
        click.echo("  按状态:")
        for status, count in stats['translation_entries']['by_status'].items():
            click.echo(f"    - {status}: {count}")
            
    if stats.get('work_queue'):
        click.echo(f"\n工作队列:")
        for status, count in stats['work_queue'].items():
            click.echo(f"  - {status}: {count}")
            
    service.close()


@cli.command()
@click.option('--limit', default=10, help='显示数量')
@click.pass_context
def mods(ctx, limit):
    """列出MOD"""
    db_path = ctx.obj['db_path']
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT mod_id, mod_name, version, mod_loader, 
               language_count, total_keys, discovered_at
        FROM mod_discoveries
        ORDER BY discovered_at DESC
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    
    if rows:
        headers = ['MOD ID', '名称', '版本', '加载器', '语言', '翻译键', '发现时间']
        table = []
        
        for row in rows:
            table.append([
                row['mod_id'][:20],
                row['mod_name'][:30],
                row['version'][:10] if row['version'] else 'N/A',
                row['mod_loader'],
                row['language_count'],
                row['total_keys'],
                row['discovered_at'][:19]
            ])
            
        click.echo(tabulate(table, headers=headers, tablefmt='grid'))
    else:
        click.echo("没有找到MOD")
        
    conn.close()


@cli.command()
@click.argument('mod_id')
@click.pass_context
def mod_detail(ctx, mod_id):
    """显示MOD详细信息"""
    db_path = ctx.obj['db_path']
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM mod_discoveries WHERE mod_id = ?", (mod_id,))
    row = cursor.fetchone()
    
    if not row:
        click.echo(f"❌ 未找到MOD: {mod_id}")
        return
        
    click.echo(f"\n📦 MOD信息:")
    click.echo(f"  ID: {row['mod_id']}")
    click.echo(f"  名称: {row['mod_name']}")
    click.echo(f"  显示名: {row['display_name'] or 'N/A'}")
    click.echo(f"  版本: {row['version'] or 'N/A'}")
    click.echo(f"  MC版本: {row['minecraft_version'] or 'N/A'}")
    click.echo(f"  加载器: {row['mod_loader']}")
    click.echo(f"  文件路径: {row['file_path']}")
    click.echo(f"  文件哈希: {row['file_hash'][:16]}...")
    click.echo(f"  文件大小: {row['file_size'] / 1024 / 1024:.2f} MB")
    click.echo(f"  语言文件: {row['language_count']}")
    click.echo(f"  翻译键: {row['total_keys']}")
    click.echo(f"  已上传: {'是' if row['is_uploaded'] else '否'}")
    click.echo(f"  发现时间: {row['discovered_at']}")
    
    # 显示语言文件
    cursor.execute("""
        SELECT language_code, entry_count, cached_at
        FROM language_file_cache
        WHERE mod_id = ?
    """, (mod_id,))
    
    lang_rows = cursor.fetchall()
    if lang_rows:
        click.echo(f"\n📝 语言文件:")
        for lang in lang_rows:
            click.echo(f"  - {lang['language_code']}: {lang['entry_count']} 条目")
            
    conn.close()


@cli.command()
@click.option('--type', 'sync_type', type=click.Choice(['projects', 'mods', 'translations']), 
              default='mods', help='同步类型')
@click.option('--direction', type=click.Choice(['upload', 'download', 'bidirectional']),
              default='upload', help='同步方向')
@click.pass_context
def sync(ctx, sync_type, direction):
    """同步数据到服务器"""
    db_path = ctx.obj['db_path']
    
    async def run_sync():
        service = DataSyncService(db_path)
        await service.initialize()
        
        try:
            direction_map = {
                'upload': SyncDirection.UPLOAD,
                'download': SyncDirection.DOWNLOAD,
                'bidirectional': SyncDirection.BIDIRECTIONAL
            }
            
            dir_enum = direction_map[direction]
            
            click.echo(f"开始同步 {sync_type} ({direction})...")
            
            if sync_type == 'projects':
                await service.sync_projects(dir_enum)
            elif sync_type == 'mods':
                await service.sync_mod_discoveries()
            elif sync_type == 'translations':
                # 需要项目ID，这里使用默认项目
                await service.sync_translations('default-project')
                
            click.echo("✅ 同步完成")
            
        except Exception as e:
            click.echo(f"❌ 同步失败: {e}", err=True)
        finally:
            await service.close()
            
    asyncio.run(run_sync())


@cli.command()
@click.pass_context
def changes(ctx):
    """显示离线变更"""
    db_path = ctx.obj['db_path']
    tracker = OfflineChangeTracker(db_path)
    
    summary = tracker.get_change_summary()
    
    click.echo("\n📝 离线变更摘要:")
    click.echo(f"  待同步总数: {summary['total_pending']}")
    
    if summary['by_entity']:
        click.echo("\n按实体类型:")
        for entity_type, stats in summary['by_entity'].items():
            click.echo(f"  {entity_type}:")
            click.echo(f"    - 待同步: {stats['pending']}")
            click.echo(f"    - 已同步: {stats['synced']}")
            click.echo(f"    - 总计: {stats['total']}")
            
    if summary['by_operation']:
        click.echo("\n按操作类型:")
        for operation, count in summary['by_operation'].items():
            click.echo(f"  - {operation}: {count}")
            
    if summary['recent_changes']:
        click.echo("\n最近变更:")
        headers = ['类型', '实体ID', '操作', '时间', '状态']
        table = []
        
        for change in summary['recent_changes'][:5]:
            table.append([
                change['entity_type'],
                change['entity_id'][:20],
                change['operation'],
                change['created_at'][:19],
                '已同步' if change['is_synced'] else '待同步'
            ])
            
        click.echo(tabulate(table, headers=headers, tablefmt='simple'))


@cli.command()
@click.pass_context
def cleanup(ctx):
    """清理过期缓存"""
    db_path = ctx.obj['db_path']
    service = ScanDatabaseService(db_path)
    
    click.echo("清理过期缓存...")
    service.cleanup_expired_cache()
    
    # 清理旧的离线变更
    tracker = OfflineChangeTracker(db_path)
    tracker.cleanup_old_changes(days=30)
    
    click.echo("✅ 清理完成")
    service.close()


@cli.command()
@click.argument('file_path')
@click.pass_context
def export_changes(ctx, file_path):
    """导出离线变更"""
    db_path = ctx.obj['db_path']
    tracker = OfflineChangeTracker(db_path)
    
    tracker.export_changes(file_path)
    click.echo(f"✅ 变更已导出到: {file_path}")


@cli.command()
@click.argument('file_path')
@click.pass_context
def import_changes(ctx, file_path):
    """导入离线变更"""
    db_path = ctx.obj['db_path']
    tracker = OfflineChangeTracker(db_path)
    
    if not Path(file_path).exists():
        click.echo(f"❌ 文件不存在: {file_path}", err=True)
        return
        
    tracker.import_changes(file_path)
    click.echo(f"✅ 变更已导入")


@cli.command()
@click.pass_context
def settings(ctx):
    """显示本地设置"""
    db_path = ctx.obj['db_path']
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM local_settings ORDER BY setting_key")
    rows = cursor.fetchall()
    
    if rows:
        headers = ['设置键', '值', '类型', '描述']
        table = []
        
        for row in rows:
            table.append([
                row['setting_key'],
                row['setting_value'],
                row['setting_type'],
                row['description'][:40] if row['description'] else ''
            ])
            
        click.echo(tabulate(table, headers=headers, tablefmt='grid'))
    else:
        click.echo("没有设置项")
        
    conn.close()


@cli.command()
@click.argument('key')
@click.argument('value')
@click.pass_context
def set_config(ctx, key, value):
    """更新设置"""
    db_path = ctx.obj['db_path']
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE local_settings
        SET setting_value = ?, updated_at = CURRENT_TIMESTAMP
        WHERE setting_key = ?
    """, (value, key))
    
    if cursor.rowcount > 0:
        conn.commit()
        click.echo(f"✅ 设置已更新: {key} = {value}")
    else:
        click.echo(f"❌ 未找到设置: {key}", err=True)
        
    conn.close()


if __name__ == '__main__':
    cli(obj={})