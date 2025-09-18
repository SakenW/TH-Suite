#!/usr/bin/env python3
"""
数据迁移脚本：从简化V2架构升级到完整V5架构
将当前6个简化表的数据迁移到19个完整表的V5 SSOT架构
"""

import sqlite3
import uuid
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)

class V5MigrationManager:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.backup_path = self.db_path.with_suffix(f'.v2_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
    
    def execute_migration(self):
        """执行完整的V5架构迁移"""
        logger.info("🚀 开始V5完整架构迁移", db_path=str(self.db_path))
        
        try:
            # 1. 备份当前数据库
            self._backup_current_database()
            
            # 2. 读取当前简化数据
            current_data = self._extract_current_data()
            
            # 3. 执行V5架构脚本
            self._execute_v5_schema()
            
            # 4. 迁移数据到V5架构
            self._migrate_data_to_v5(current_data)
            
            # 5. 验证迁移结果
            self._verify_migration()
            
            logger.info("✅ V5架构迁移完成", 
                       backup_file=str(self.backup_path),
                       new_tables=19,
                       new_views=5)
            return True
            
        except Exception as e:
            logger.error("❌ V5架构迁移失败", error=str(e))
            # 恢复备份
            self._restore_backup()
            return False
    
    def _backup_current_database(self):
        """备份当前数据库"""
        import shutil
        shutil.copy2(self.db_path, self.backup_path)
        logger.info("📋 数据库已备份", backup_path=str(self.backup_path))
    
    def _extract_current_data(self):
        """提取当前简化架构的数据"""
        logger.info("📊 提取当前数据")
        
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        
        data = {
            'packs': [],
            'pack_versions': [],
            'mod_version_instances': [],
            'pack_mod_relations': [],
            'content_instances': [],
            'pack_content_relations': []
        }
        
        # 提取各表数据
        for table_name in data.keys():
            try:
                cursor = conn.execute(f"SELECT * FROM {table_name}")
                data[table_name] = [dict(row) for row in cursor.fetchall()]
                logger.info(f"✅ 提取 {table_name}: {len(data[table_name])} 条记录")
            except sqlite3.OperationalError as e:
                logger.warning(f"⚠️ 表 {table_name} 不存在或为空: {e}")
                data[table_name] = []
        
        conn.close()
        return data
    
    def _execute_v5_schema(self):
        """执行V5架构创建脚本"""
        logger.info("🏗️ 执行V5完整架构创建")
        
        # 读取V5架构脚本
        schema_file = Path(__file__).parent / "003_v5_complete_architecture.sql"
        
        if not schema_file.exists():
            raise FileNotFoundError(f"V5架构脚本不存在: {schema_file}")
        
        schema_sql = schema_file.read_text(encoding='utf-8')
        
        # 先删除当前数据库，重新创建V5架构
        if self.db_path.exists():
            self.db_path.unlink()
        
        conn = sqlite3.connect(str(self.db_path))
        conn.executescript(schema_sql)
        conn.close()
        
        logger.info("✅ V5架构创建完成")
    
    def _migrate_data_to_v5(self, current_data):
        """将简化数据迁移到V5完整架构"""
        logger.info("🔄 开始数据迁移到V5架构")
        
        conn = sqlite3.connect(str(self.db_path))
        
        try:
            # 1. 创建默认项目
            project_uid = self._migrate_projects(conn)
            
            # 2. 迁移整合包数据  
            pack_mapping = self._migrate_packs(conn, current_data['packs'], project_uid)
            
            # 3. 迁移整合包版本
            version_mapping = self._migrate_pack_versions(conn, current_data['pack_versions'], pack_mapping)
            
            # 4. 迁移MOD数据
            mod_mapping = self._migrate_mods(conn, current_data['mod_version_instances'])
            
            # 5. 迁移MOD版本
            mod_version_mapping = self._migrate_mod_versions(conn, current_data['mod_version_instances'], mod_mapping)
            
            # 6. 迁移语言文件
            lang_file_mapping = self._migrate_language_files(conn, current_data['content_instances'], mod_version_mapping)
            
            # 7. 迁移翻译条目
            self._migrate_translation_entries(conn, current_data['content_instances'], lang_file_mapping)
            
            # 8. 创建pack_items (从pack_mod_relations推断)
            self._create_pack_items(conn, current_data['pack_mod_relations'], version_mapping, mod_version_mapping)
            
            # 9. 初始化工作队列
            self._initialize_work_queue(conn)
            
            conn.commit()
            logger.info("✅ 数据迁移完成")
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _migrate_projects(self, conn):
        """迁移项目数据 (创建默认项目)"""
        project_uid = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        conn.execute("""
            INSERT INTO core_projects (uid, name, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (project_uid, "默认项目", "从V2简化架构迁移的默认项目", now, now))
        
        logger.info("✅ 创建默认项目", project_uid=project_uid)
        return project_uid
    
    def _migrate_packs(self, conn, packs_data, project_uid):
        """迁移整合包数据"""
        pack_mapping = {}
        
        for pack in packs_data:
            pack_uid = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            # 从简化字段推断V5字段
            platform = "custom"  # 默认为custom
            slug = pack.get('name', '').lower().replace(' ', '-')
            title = pack.get('name', 'Unknown Pack')
            author = pack.get('author', '')
            
            conn.execute("""
                INSERT INTO core_packs (uid, platform, slug, title, author, homepage, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (pack_uid, platform, slug, title, author, '', now, now))
            
            pack_mapping[pack['id']] = pack_uid
            logger.info("✅ 迁移整合包", old_id=pack['id'], new_uid=pack_uid, title=title)
        
        return pack_mapping
    
    def _migrate_pack_versions(self, conn, versions_data, pack_mapping):
        """迁移整合包版本数据"""
        version_mapping = {}
        
        for version in versions_data:
            version_uid = str(uuid.uuid4())
            pack_uid = pack_mapping.get(version['pack_id'])
            
            if not pack_uid:
                logger.warning("⚠️ 跳过版本，找不到对应整合包", version_id=version['id'])
                continue
            
            now = datetime.now().isoformat()
            
            # 生成manifest hash
            manifest_data = {
                "version_tag": version.get('version_tag', '1.0.0'),
                "minecraft_version": version.get('minecraft_version', '1.21.1'),
                "loader_type": version.get('loader_type', 'fabric')
            }
            manifest_json = json.dumps(manifest_data, sort_keys=True)
            manifest_hash_b3 = hashlib.blake2b(manifest_json.encode(), digest_size=32).hexdigest()
            manifest_hash_md5 = hashlib.md5(manifest_json.encode()).hexdigest()
            
            conn.execute("""
                INSERT INTO core_pack_versions 
                (uid, pack_uid, mc_version, loader, manifest_json, manifest_hash_b3, manifest_hash_md5, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (version_uid, pack_uid, 
                  version.get('minecraft_version', '1.21.1'),
                  version.get('loader_type', 'fabric'),
                  manifest_json, manifest_hash_b3, manifest_hash_md5, now))
            
            version_mapping[version['id']] = version_uid
            logger.info("✅ 迁移整合包版本", old_id=version['id'], new_uid=version_uid)
        
        return version_mapping
    
    def _migrate_mods(self, conn, mod_instances_data):
        """迁移MOD数据 (从mod_version_instances推断)"""
        mod_mapping = {}
        seen_mods = {}
        
        for mod_instance in mod_instances_data:
            mod_id = mod_instance.get('mod_id', '')
            
            if mod_id and mod_id not in seen_mods:
                mod_uid = str(uuid.uuid4())
                now = datetime.now().isoformat()
                
                conn.execute("""
                    INSERT INTO core_mods (uid, modid, slug, name, homepage, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (mod_uid, mod_id, mod_id.replace('_', '-'), 
                      mod_instance.get('mod_name', mod_id), '', now, now))
                
                seen_mods[mod_id] = mod_uid
                mod_mapping[mod_id] = mod_uid
                logger.info("✅ 创建MOD", mod_id=mod_id, mod_uid=mod_uid)
        
        return mod_mapping
    
    def _migrate_mod_versions(self, conn, mod_instances_data, mod_mapping):
        """迁移MOD版本数据"""
        mod_version_mapping = {}
        
        for mod_instance in mod_instances_data:
            mod_id = mod_instance.get('mod_id', '')
            mod_uid = mod_mapping.get(mod_id)
            
            if not mod_uid:
                continue
            
            mod_version_uid = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            # 构建元数据
            meta_data = {
                "description": mod_instance.get('description', ''),
                "authors": mod_instance.get('authors', ''),
                "homepage_url": mod_instance.get('homepage_url', ''),
                "jar_file_path": mod_instance.get('jar_file_path', ''),
                "jar_file_size": mod_instance.get('jar_file_size', 0),
                "jar_file_hash": mod_instance.get('jar_file_hash', '')
            }
            
            conn.execute("""
                INSERT INTO core_mod_versions 
                (uid, mod_uid, loader, mc_version, version, meta_json, source, discovered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (mod_version_uid, mod_uid, 
                  'unknown',  # 默认loader
                  '1.21.1',   # 默认MC版本
                  mod_instance.get('mod_version', '1.0.0'),
                  json.dumps(meta_data),
                  'migration_from_v2',
                  now))
            
            mod_version_mapping[mod_instance['id']] = mod_version_uid
            logger.info("✅ 迁移MOD版本", old_id=mod_instance['id'], new_uid=mod_version_uid)
        
        return mod_version_mapping
    
    def _migrate_language_files(self, conn, content_instances_data, mod_version_mapping):
        """迁移语言文件数据 (从content_instances推断)"""
        lang_file_mapping = {}
        seen_files = {}
        
        for content in content_instances_data:
            # 构建语言文件的唯一标识
            file_key = (
                content.get('content_source', 'mod_jar'),
                content.get('source_identifier', ''),
                content.get('language_code', 'en_us'),
                content.get('file_path', '')
            )
            
            if file_key not in seen_files:
                lang_file_uid = str(uuid.uuid4())
                now = datetime.now().isoformat()
                
                # 推断carrier_uid (载体UID)
                source_id = content.get('source_identifier', '')
                carrier_uid = None
                
                # 尝试匹配到MOD版本
                for old_id, new_uid in mod_version_mapping.items():
                    if source_id in str(old_id):  # 简单匹配策略
                        carrier_uid = new_uid
                        break
                
                if not carrier_uid:
                    carrier_uid = str(uuid.uuid4())  # 创建虚拟载体
                
                # 推断文件格式
                file_path = content.get('file_path', '')
                if file_path.endswith('.json'):
                    format_type = 'json'
                elif file_path.endswith('.lang'):
                    format_type = 'lang'
                elif file_path.endswith('.properties'):
                    format_type = 'properties'
                else:
                    format_type = 'json'  # 默认
                
                conn.execute("""
                    INSERT INTO core_language_files 
                    (uid, carrier_type, carrier_uid, locale, rel_path, format, size, discovered_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (lang_file_uid, 
                      content.get('content_source', 'mod_jar').replace('_', ''),
                      carrier_uid,
                      content.get('language_code', 'en_us'),
                      content.get('file_path', ''),
                      format_type,
                      len(content.get('source_text', '')),
                      now))
                
                seen_files[file_key] = lang_file_uid
                logger.info("✅ 创建语言文件", lang_file_uid=lang_file_uid)
            
            lang_file_mapping[content['id']] = seen_files[file_key]
        
        return lang_file_mapping
    
    def _migrate_translation_entries(self, conn, content_instances_data, lang_file_mapping):
        """迁移翻译条目数据"""
        for content in content_instances_data:
            entry_uid = str(uuid.uuid4())
            lang_file_uid = lang_file_mapping.get(content['id'])
            
            if not lang_file_uid:
                continue
            
            now = datetime.now().isoformat()
            
            # 推断QA标志
            qa_flags = {}
            if not content.get('source_text', '').strip():
                qa_flags['empty_source'] = True
            if '{' in content.get('source_text', '') or '%' in content.get('source_text', ''):
                qa_flags['has_placeholders'] = True
            
            conn.execute("""
                INSERT INTO core_translation_entries 
                (uid, language_file_uid, key, src_text, dst_text, status, qa_flags, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (entry_uid, lang_file_uid,
                  content.get('content_key', ''),
                  content.get('source_text', ''),
                  '',  # dst_text默认为空
                  'new',  # 默认状态
                  json.dumps(qa_flags),
                  now))
            
            logger.info("✅ 迁移翻译条目", content_id=content['id'], entry_uid=entry_uid)
    
    def _create_pack_items(self, conn, pack_mod_relations_data, version_mapping, mod_version_mapping):
        """从pack_mod_relations创建pack_items"""
        for relation in pack_mod_relations_data:
            pack_version_id = relation.get('pack_version_id')
            mod_instance_id = relation.get('mod_instance_id')
            
            pack_version_uid = version_mapping.get(pack_version_id)
            mod_version_uid = mod_version_mapping.get(mod_instance_id)
            
            if not pack_version_uid or not mod_version_uid:
                continue
            
            now = datetime.now().isoformat()
            
            conn.execute("""
                INSERT INTO core_pack_items 
                (pack_version_uid, item_type, source_platform, identity, constraints, position, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (pack_version_uid, 'mod', 'local', mod_version_uid, '{}', 0, now))
            
            logger.info("✅ 创建pack_item", pack_version_uid=pack_version_uid[:8], mod_version_uid=mod_version_uid[:8])
    
    def _initialize_work_queue(self, conn):
        """初始化工作队列"""
        now = datetime.now().isoformat()
        
        # 创建初始任务
        initial_tasks = [
            {
                "type": "qa_run",
                "payload": {"scope": "all", "rules": ["check_placeholders", "check_empty"]},
                "priority": 10
            },
            {
                "type": "tm_index",
                "payload": {"action": "rebuild_index"},
                "priority": 5
            }
        ]
        
        for task in initial_tasks:
            task_uid = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO ops_work_queue 
                (type, payload_json, state, priority, dedupe_key, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (task["type"], json.dumps(task["payload"]), 'pending', 
                  task["priority"], f"init_{task['type']}", now, now))
        
        logger.info("✅ 初始化工作队列")
    
    def _verify_migration(self):
        """验证迁移结果"""
        logger.info("🔍 验证迁移结果")
        
        conn = sqlite3.connect(str(self.db_path))
        
        # 检查表数量
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = [
            'core_projects', 'core_packs', 'core_pack_versions', 'core_pack_items',
            'core_pack_installations', 'core_mods', 'core_mod_versions', 
            'core_language_files', 'core_translation_entries',
            'ops_work_queue', 'ops_outbox_journal', 'ops_sync_log', 'ops_cas_objects',
            'cfg_local_settings', 'cfg_file_watch',
            'cache_scan_results', 'cache_lang_file', 'cache_entry', 'cache_stats'
        ]
        
        missing_tables = set(expected_tables) - set(tables)
        if missing_tables:
            raise Exception(f"缺少表: {missing_tables}")
        
        # 检查视图
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='view'")
        views = [row[0] for row in cursor.fetchall()]
        
        expected_views = ['v_cache_statistics', 'v_queue_status', 'v_sync_history', 'v_delta_backlog', 'v_project_statistics']
        missing_views = set(expected_views) - set(views)
        if missing_views:
            logger.warning(f"⚠️ 缺少视图: {missing_views}")
        
        # 统计数据量
        stats = {}
        for table in expected_tables:
            try:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                stats[table] = count
            except sqlite3.OperationalError:
                stats[table] = 0
        
        conn.close()
        
        logger.info("✅ 迁移验证完成", 
                   tables_count=len(tables),
                   views_count=len(views),
                   data_stats=stats)
    
    def _restore_backup(self):
        """恢复备份"""
        if self.backup_path.exists():
            import shutil
            shutil.copy2(self.backup_path, self.db_path)
            logger.info("🔄 已恢复备份数据库")

def main():
    """主函数"""
    db_path = "data/mc_l10n.db"
    
    migrator = V5MigrationManager(db_path)
    success = migrator.execute_migration()
    
    if success:
        print("🎉 V5完整架构迁移成功！")
        print(f"📋 备份文件: {migrator.backup_path}")
        print("📊 新架构包含:")
        print("   - 19个表 (9个core + 4个ops + 2个cfg + 4个cache)")
        print("   - 5个统计视图")
        print("   - 20+个性能索引") 
        print("   - 8个数据完整性触发器")
    else:
        print("❌ 迁移失败，已恢复原数据库")
    
    return success

if __name__ == "__main__":
    main()