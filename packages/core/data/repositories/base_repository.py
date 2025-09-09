#!/usr/bin/env python
"""
通用Repository基类
提供CRUD操作的抽象接口和通用实现
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Generic, TypeVar, Union
import sqlite3
import json
import uuid
from datetime import datetime

T = TypeVar('T')  # 实体类型
ID = TypeVar('ID')  # ID类型


class IRepository(ABC, Generic[T, ID]):
    """Repository接口定义"""
    
    @abstractmethod
    async def create(self, entity: T) -> ID:
        """创建实体"""
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: ID) -> Optional[T]:
        """根据ID获取实体"""
        pass
    
    @abstractmethod
    async def get_by_uid(self, uid: str) -> Optional[T]:
        """根据UID获取实体"""
        pass
    
    @abstractmethod
    async def update(self, entity: T) -> bool:
        """更新实体"""
        pass
    
    @abstractmethod
    async def delete(self, entity_id: ID) -> bool:
        """删除实体"""
        pass
    
    @abstractmethod
    async def list_all(self, limit: int = None, offset: int = 0) -> List[T]:
        """列出所有实体"""
        pass
    
    @abstractmethod
    async def count(self) -> int:
        """统计实体数量"""
        pass


class BaseRepository(IRepository[T, ID]):
    """通用Repository基类实现"""
    
    def __init__(self, db_manager, table_name: str, entity_class=None):
        self.db_manager = db_manager
        self.table_name = table_name
        self.entity_class = entity_class
    
    def _generate_uid(self) -> str:
        """生成唯一标识符"""
        return str(uuid.uuid4())
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        return datetime.now().isoformat()
    
    def _dict_to_entity(self, data: Dict[str, Any]) -> T:
        """将字典转换为实体对象"""
        if self.entity_class:
            return self.entity_class(**data)
        return data
    
    def _entity_to_dict(self, entity: T) -> Dict[str, Any]:
        """将实体对象转换为字典"""
        if hasattr(entity, '__dict__'):
            return entity.__dict__
        elif hasattr(entity, 'to_dict'):
            return entity.to_dict()
        else:
            return dict(entity) if isinstance(entity, dict) else entity
    
    async def create(self, entity: T) -> ID:
        """创建实体"""
        data = self._entity_to_dict(entity)
        
        # 生成UID和时间戳
        if 'uid' not in data or not data['uid']:
            data['uid'] = self._generate_uid()
        
        now = self._get_timestamp()
        if 'created_at' not in data:
            data['created_at'] = now
        if 'updated_at' not in data:
            data['updated_at'] = now
        
        # 构建插入SQL
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        values = list(data.values())
        
        sql = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(sql, values)
            return cursor.lastrowid
    
    async def get_by_id(self, entity_id: ID) -> Optional[T]:
        """根据ID获取实体"""
        sql = f"SELECT * FROM {self.table_name} WHERE id = ?"
        
        with self.db_manager.get_connection() as conn:
            result = conn.execute(sql, (entity_id,)).fetchone()
            if result:
                return self._dict_to_entity(dict(result))
            return None
    
    async def get_by_uid(self, uid: str) -> Optional[T]:
        """根据UID获取实体"""
        sql = f"SELECT * FROM {self.table_name} WHERE uid = ?"
        
        with self.db_manager.get_connection() as conn:
            result = conn.execute(sql, (uid,)).fetchone()
            if result:
                return self._dict_to_entity(dict(result))
            return None
    
    async def update(self, entity: T) -> bool:
        """更新实体"""
        data = self._entity_to_dict(entity)
        
        # 更新时间戳
        data['updated_at'] = self._get_timestamp()
        
        # 提取ID/UID作为条件
        entity_id = data.pop('id', None)
        uid = data.get('uid')
        
        if not entity_id and not uid:
            raise ValueError("实体必须有id或uid字段")
        
        # 构建更新SQL
        set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
        values = list(data.values())
        
        if entity_id:
            sql = f"UPDATE {self.table_name} SET {set_clause} WHERE id = ?"
            values.append(entity_id)
        else:
            sql = f"UPDATE {self.table_name} SET {set_clause} WHERE uid = ?"
            values.append(uid)
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(sql, values)
            return cursor.rowcount > 0
    
    async def delete(self, entity_id: ID) -> bool:
        """删除实体"""
        sql = f"DELETE FROM {self.table_name} WHERE id = ?"
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(sql, (entity_id,))
            return cursor.rowcount > 0
    
    async def delete_by_uid(self, uid: str) -> bool:
        """根据UID删除实体"""
        sql = f"DELETE FROM {self.table_name} WHERE uid = ?"
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(sql, (uid,))
            return cursor.rowcount > 0
    
    async def list_all(self, limit: int = None, offset: int = 0) -> List[T]:
        """列出所有实体"""
        sql = f"SELECT * FROM {self.table_name} ORDER BY created_at DESC"
        
        if limit:
            sql += f" LIMIT {limit} OFFSET {offset}"
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql).fetchall()
            return [self._dict_to_entity(dict(row)) for row in results]
    
    async def count(self) -> int:
        """统计实体数量"""
        sql = f"SELECT COUNT(*) as cnt FROM {self.table_name}"
        
        with self.db_manager.get_connection() as conn:
            result = conn.execute(sql).fetchone()
            return result['cnt']
    
    async def find_by(self, **conditions) -> List[T]:
        """根据条件查找实体"""
        if not conditions:
            return await self.list_all()
        
        # 构建WHERE条件
        where_clauses = []
        values = []
        
        for key, value in conditions.items():
            if value is None:
                where_clauses.append(f"{key} IS NULL")
            else:
                where_clauses.append(f"{key} = ?")
                values.append(value)
        
        where_clause = " AND ".join(where_clauses)
        sql = f"SELECT * FROM {self.table_name} WHERE {where_clause} ORDER BY created_at DESC"
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql, values).fetchall()
            return [self._dict_to_entity(dict(row)) for row in results]
    
    async def find_one_by(self, **conditions) -> Optional[T]:
        """根据条件查找单个实体"""
        results = await self.find_by(**conditions)
        return results[0] if results else None
    
    async def exists(self, entity_id: ID) -> bool:
        """检查实体是否存在"""
        sql = f"SELECT 1 FROM {self.table_name} WHERE id = ? LIMIT 1"
        
        with self.db_manager.get_connection() as conn:
            result = conn.execute(sql, (entity_id,)).fetchone()
            return result is not None
    
    async def exists_by_uid(self, uid: str) -> bool:
        """检查UID是否存在"""
        sql = f"SELECT 1 FROM {self.table_name} WHERE uid = ? LIMIT 1"
        
        with self.db_manager.get_connection() as conn:
            result = conn.execute(sql, (uid,)).fetchone()
            return result is not None
    
    async def batch_create(self, entities: List[T]) -> List[ID]:
        """批量创建实体"""
        if not entities:
            return []
        
        # 预处理实体数据
        processed_entities = []
        for entity in entities:
            data = self._entity_to_dict(entity)
            
            if 'uid' not in data or not data['uid']:
                data['uid'] = self._generate_uid()
            
            now = self._get_timestamp()
            if 'created_at' not in data:
                data['created_at'] = now
            if 'updated_at' not in data:
                data['updated_at'] = now
                
            processed_entities.append(data)
        
        # 构建批量插入SQL
        if not processed_entities:
            return []
        
        first_entity = processed_entities[0]
        columns = ', '.join(first_entity.keys())
        placeholders = ', '.join(['?' for _ in first_entity])
        sql = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"
        
        # 执行批量插入
        results = []
        with self.db_manager.get_connection() as conn:
            for data in processed_entities:
                cursor = conn.execute(sql, list(data.values()))
                results.append(cursor.lastrowid)
        
        return results
    
    async def batch_update(self, entities: List[T]) -> int:
        """批量更新实体"""
        if not entities:
            return 0
        
        updated_count = 0
        for entity in entities:
            success = await self.update(entity)
            if success:
                updated_count += 1
        
        return updated_count
    
    async def batch_delete(self, entity_ids: List[ID]) -> int:
        """批量删除实体"""
        if not entity_ids:
            return 0
        
        placeholders = ', '.join(['?' for _ in entity_ids])
        sql = f"DELETE FROM {self.table_name} WHERE id IN ({placeholders})"
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(sql, entity_ids)
            return cursor.rowcount


class JsonFieldRepository(BaseRepository[T, ID]):
    """支持JSON字段的Repository基类"""
    
    def __init__(self, db_manager, table_name: str, json_fields: List[str] = None, entity_class=None):
        super().__init__(db_manager, table_name, entity_class)
        self.json_fields = json_fields or []
    
    def _prepare_json_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理JSON字段"""
        processed = data.copy()
        
        for field in self.json_fields:
            if field in processed and processed[field] is not None:
                if not isinstance(processed[field], str):
                    processed[field] = json.dumps(processed[field], ensure_ascii=False)
        
        return processed
    
    def _parse_json_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """解析JSON字段"""
        processed = data.copy()
        
        for field in self.json_fields:
            if field in processed and processed[field] is not None:
                if isinstance(processed[field], str):
                    try:
                        processed[field] = json.loads(processed[field])
                    except json.JSONDecodeError:
                        pass  # 保持原值
        
        return processed
    
    def _entity_to_dict(self, entity: T) -> Dict[str, Any]:
        """将实体对象转换为字典并处理JSON字段"""
        data = super()._entity_to_dict(entity)
        return self._prepare_json_fields(data)
    
    def _dict_to_entity(self, data: Dict[str, Any]) -> T:
        """将字典转换为实体对象并解析JSON字段"""
        processed_data = self._parse_json_fields(data)
        return super()._dict_to_entity(processed_data)