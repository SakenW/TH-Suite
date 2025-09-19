"""
版本差异计算引擎 - TH-Suite MC L10n
实现高效的版本间差异计算、对比和应用功能
"""

import json
import logging
import hashlib
import uuid
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


class DiffType(Enum):
    """差异类型枚举"""
    FORWARD = "forward"      # 正向差异: A -> B
    REVERSE = "reverse"      # 反向差异: B -> A
    THREE_WAY = "three_way"  # 三路差异: Base + A + B


class OperationType(Enum):
    """操作类型枚举"""
    ADD = "add"
    REMOVE = "remove"
    REPLACE = "replace"
    MOVE = "move"
    COPY = "copy"
    TEST = "test"


@dataclass
class DiffOperation:
    """差异操作数据类"""
    op: OperationType
    path: str
    value: Any = None
    old_value: Any = None
    from_path: str = None


@dataclass
class VersionDiff:
    """版本差异数据类"""
    uid: str
    from_commit_uid: Optional[str]
    to_commit_uid: str
    diff_type: DiffType
    operations: List[DiffOperation]
    metadata: Dict[str, Any] = None
    created_at: Optional[datetime] = None


class VersionDiffEngine:
    """版本差异计算引擎"""
    
    def __init__(self):
        self.config = {
            "max_diff_size": 10000,  # 最大差异操作数
            "deep_compare": True,    # 深度比较
            "ignore_whitespace": False,  # 忽略空白字符
            "case_sensitive": True,  # 大小写敏感
            "array_diff_mode": "smart",  # 数组差异模式: smart/simple
            "text_diff_granularity": "line"  # 文本差异粒度: char/word/line
        }
    
    # ============================================================
    # 1. 核心差异计算
    # ============================================================
    
    def calculate_diff(self, old_data: Dict[str, Any], new_data: Dict[str, Any],
                      diff_type: DiffType = DiffType.FORWARD) -> VersionDiff:
        """
        计算两个版本间的差异
        
        Args:
            old_data: 旧版本数据
            new_data: 新版本数据
            diff_type: 差异类型
        
        Returns:
            VersionDiff: 差异对象
        """
        try:
            operations = []
            
            if diff_type == DiffType.FORWARD:
                operations = self._calculate_forward_diff(old_data, new_data)
            elif diff_type == DiffType.REVERSE:
                operations = self._calculate_forward_diff(new_data, old_data)
            elif diff_type == DiffType.THREE_WAY:
                # 三路差异需要额外的base数据
                operations = self._calculate_three_way_diff(old_data, new_data, {})
            
            # 生成差异对象
            diff_uid = str(uuid.uuid4())
            version_diff = VersionDiff(
                uid=diff_uid,
                from_commit_uid=None,  # 由调用方设置
                to_commit_uid=None,    # 由调用方设置
                diff_type=diff_type,
                operations=operations,
                metadata={
                    "operations_count": len(operations),
                    "algorithm": "json_patch",
                    "config": self.config.copy()
                },
                created_at=datetime.now()
            )
            
            return version_diff
            
        except Exception as e:
            logger.error(f"计算差异失败: {e}")
            raise
    
    def _calculate_forward_diff(self, old_data: Dict[str, Any], 
                              new_data: Dict[str, Any]) -> List[DiffOperation]:
        """计算正向差异 (A -> B)"""
        operations = []
        
        # 递归比较对象
        self._diff_objects(old_data, new_data, "", operations)
        
        return operations
    
    def _diff_objects(self, old_obj: Any, new_obj: Any, path: str, 
                     operations: List[DiffOperation]) -> None:
        """递归比较对象差异"""
        
        # 处理不同类型的对象
        if type(old_obj) != type(new_obj):
            operations.append(DiffOperation(
                op=OperationType.REPLACE,
                path=path,
                value=new_obj,
                old_value=old_obj
            ))
            return
        
        # 处理字典
        if isinstance(old_obj, dict) and isinstance(new_obj, dict):
            self._diff_dicts(old_obj, new_obj, path, operations)
        
        # 处理列表
        elif isinstance(old_obj, list) and isinstance(new_obj, list):
            self._diff_arrays(old_obj, new_obj, path, operations)
        
        # 处理基本类型
        elif old_obj != new_obj:
            operations.append(DiffOperation(
                op=OperationType.REPLACE,
                path=path,
                value=new_obj,
                old_value=old_obj
            ))
    
    def _diff_dicts(self, old_dict: Dict[str, Any], new_dict: Dict[str, Any], 
                   path: str, operations: List[DiffOperation]) -> None:
        """比较字典差异"""
        
        old_keys = set(old_dict.keys())
        new_keys = set(new_dict.keys())
        
        # 删除的键
        for key in old_keys - new_keys:
            key_path = f"{path}/{key}" if path else key
            operations.append(DiffOperation(
                op=OperationType.REMOVE,
                path=key_path,
                old_value=old_dict[key]
            ))
        
        # 新增的键
        for key in new_keys - old_keys:
            key_path = f"{path}/{key}" if path else key
            operations.append(DiffOperation(
                op=OperationType.ADD,
                path=key_path,
                value=new_dict[key]
            ))
        
        # 修改的键
        for key in old_keys & new_keys:
            key_path = f"{path}/{key}" if path else key
            self._diff_objects(old_dict[key], new_dict[key], key_path, operations)
    
    def _diff_arrays(self, old_array: List[Any], new_array: List[Any], 
                    path: str, operations: List[DiffOperation]) -> None:
        """比较数组差异"""
        
        if self.config["array_diff_mode"] == "smart":
            self._diff_arrays_smart(old_array, new_array, path, operations)
        else:
            self._diff_arrays_simple(old_array, new_array, path, operations)
    
    def _diff_arrays_simple(self, old_array: List[Any], new_array: List[Any], 
                           path: str, operations: List[DiffOperation]) -> None:
        """简单数组差异比较"""
        
        min_len = min(len(old_array), len(new_array))
        
        # 比较共同部分
        for i in range(min_len):
            item_path = f"{path}/{i}"
            self._diff_objects(old_array[i], new_array[i], item_path, operations)
        
        # 处理长度差异
        if len(new_array) > len(old_array):
            # 新增元素
            for i in range(len(old_array), len(new_array)):
                item_path = f"{path}/{i}"
                operations.append(DiffOperation(
                    op=OperationType.ADD,
                    path=item_path,
                    value=new_array[i]
                ))
        elif len(new_array) < len(old_array):
            # 删除元素 (从后往前删除)
            for i in range(len(old_array) - 1, len(new_array) - 1, -1):
                item_path = f"{path}/{i}"
                operations.append(DiffOperation(
                    op=OperationType.REMOVE,
                    path=item_path,
                    old_value=old_array[i]
                ))
    
    def _diff_arrays_smart(self, old_array: List[Any], new_array: List[Any], 
                          path: str, operations: List[DiffOperation]) -> None:
        """智能数组差异比较 (基于LCS算法)"""
        
        # 使用最长公共子序列算法来优化数组差异
        lcs_matrix = self._calculate_lcs_matrix(old_array, new_array)
        
        # 从LCS矩阵回溯生成差异操作
        i, j = len(old_array), len(new_array)
        
        while i > 0 or j > 0:
            if i > 0 and j > 0 and self._items_equal(old_array[i-1], new_array[j-1]):
                # 元素相同，继续回溯
                i -= 1
                j -= 1
            elif j > 0 and (i == 0 or lcs_matrix[i][j-1] >= lcs_matrix[i-1][j]):
                # 新增元素
                item_path = f"{path}/{j-1}"
                operations.insert(0, DiffOperation(
                    op=OperationType.ADD,
                    path=item_path,
                    value=new_array[j-1]
                ))
                j -= 1
            elif i > 0 and (j == 0 or lcs_matrix[i][j-1] < lcs_matrix[i-1][j]):
                # 删除元素
                item_path = f"{path}/{i-1}"
                operations.insert(0, DiffOperation(
                    op=OperationType.REMOVE,
                    path=item_path,
                    old_value=old_array[i-1]
                ))
                i -= 1
    
    def _calculate_lcs_matrix(self, array1: List[Any], array2: List[Any]) -> List[List[int]]:
        """计算最长公共子序列矩阵"""
        m, n = len(array1), len(array2)
        matrix = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if self._items_equal(array1[i-1], array2[j-1]):
                    matrix[i][j] = matrix[i-1][j-1] + 1
                else:
                    matrix[i][j] = max(matrix[i-1][j], matrix[i][j-1])
        
        return matrix
    
    def _items_equal(self, item1: Any, item2: Any) -> bool:
        """比较两个项目是否相等"""
        if self.config["deep_compare"]:
            return self._deep_equal(item1, item2)
        else:
            return item1 == item2
    
    def _deep_equal(self, obj1: Any, obj2: Any) -> bool:
        """深度比较两个对象"""
        if type(obj1) != type(obj2):
            return False
        
        if isinstance(obj1, dict) and isinstance(obj2, dict):
            if set(obj1.keys()) != set(obj2.keys()):
                return False
            return all(self._deep_equal(obj1[k], obj2[k]) for k in obj1.keys())
        
        elif isinstance(obj1, list) and isinstance(obj2, list):
            if len(obj1) != len(obj2):
                return False
            return all(self._deep_equal(obj1[i], obj2[i]) for i in range(len(obj1)))
        
        else:
            return obj1 == obj2
    
    def _calculate_three_way_diff(self, base_data: Dict[str, Any], 
                                 data_a: Dict[str, Any], 
                                 data_b: Dict[str, Any]) -> List[DiffOperation]:
        """计算三路差异 (用于合并场景)"""
        # TODO: 实现三路差异算法
        # 这是一个复杂的算法，需要考虑：
        # 1. Base -> A 的变更
        # 2. Base -> B 的变更
        # 3. 冲突检测和解决
        
        operations = []
        # 简化实现：先计算base->A的差异，再计算base->B的差异
        # 实际应该实现更复杂的三路合并算法
        
        return operations
    
    # ============================================================
    # 2. 差异应用
    # ============================================================
    
    def apply_diff(self, base_data: Dict[str, Any], 
                  diff: VersionDiff) -> Dict[str, Any]:
        """
        将差异应用到基础数据上
        
        Args:
            base_data: 基础数据
            diff: 差异对象
        
        Returns:
            应用差异后的数据
        """
        try:
            # 深拷贝基础数据
            result_data = json.loads(json.dumps(base_data))
            
            # 按顺序应用所有操作
            for operation in diff.operations:
                result_data = self._apply_operation(result_data, operation)
            
            return result_data
            
        except Exception as e:
            logger.error(f"应用差异失败: {e}")
            raise
    
    def _apply_operation(self, data: Dict[str, Any], 
                        operation: DiffOperation) -> Dict[str, Any]:
        """应用单个差异操作"""
        
        path_parts = operation.path.split("/") if operation.path else []
        
        if operation.op == OperationType.ADD:
            return self._apply_add_operation(data, path_parts, operation.value)
        
        elif operation.op == OperationType.REMOVE:
            return self._apply_remove_operation(data, path_parts)
        
        elif operation.op == OperationType.REPLACE:
            return self._apply_replace_operation(data, path_parts, operation.value)
        
        elif operation.op == OperationType.MOVE:
            return self._apply_move_operation(data, path_parts, operation.from_path)
        
        elif operation.op == OperationType.COPY:
            return self._apply_copy_operation(data, path_parts, operation.from_path)
        
        elif operation.op == OperationType.TEST:
            # 测试操作，验证值是否匹配
            current_value = self._get_value_at_path(data, path_parts)
            if current_value != operation.value:
                raise ValueError(f"测试失败: 路径 {operation.path} 的值不匹配")
            return data
        
        return data
    
    def _apply_add_operation(self, data: Dict[str, Any], path_parts: List[str], 
                           value: Any) -> Dict[str, Any]:
        """应用添加操作"""
        if not path_parts:
            return value
        
        current = data
        
        # 导航到父对象
        for part in path_parts[:-1]:
            if isinstance(current, dict):
                if part not in current:
                    current[part] = {}
                current = current[part]
            elif isinstance(current, list):
                index = int(part)
                while len(current) <= index:
                    current.append(None)
                if current[index] is None:
                    current[index] = {}
                current = current[index]
        
        # 添加值
        last_part = path_parts[-1]
        if isinstance(current, dict):
            current[last_part] = value
        elif isinstance(current, list):
            index = int(last_part)
            if index == len(current):
                current.append(value)
            else:
                current.insert(index, value)
        
        return data
    
    def _apply_remove_operation(self, data: Dict[str, Any], 
                              path_parts: List[str]) -> Dict[str, Any]:
        """应用删除操作"""
        if not path_parts:
            return {}
        
        current = data
        
        # 导航到父对象
        for part in path_parts[:-1]:
            if isinstance(current, dict):
                current = current[part]
            elif isinstance(current, list):
                current = current[int(part)]
        
        # 删除值
        last_part = path_parts[-1]
        if isinstance(current, dict):
            if last_part in current:
                del current[last_part]
        elif isinstance(current, list):
            index = int(last_part)
            if 0 <= index < len(current):
                current.pop(index)
        
        return data
    
    def _apply_replace_operation(self, data: Dict[str, Any], path_parts: List[str], 
                               value: Any) -> Dict[str, Any]:
        """应用替换操作"""
        if not path_parts:
            return value
        
        current = data
        
        # 导航到父对象
        for part in path_parts[:-1]:
            if isinstance(current, dict):
                current = current[part]
            elif isinstance(current, list):
                current = current[int(part)]
        
        # 替换值
        last_part = path_parts[-1]
        if isinstance(current, dict):
            current[last_part] = value
        elif isinstance(current, list):
            current[int(last_part)] = value
        
        return data
    
    def _apply_move_operation(self, data: Dict[str, Any], path_parts: List[str], 
                            from_path: str) -> Dict[str, Any]:
        """应用移动操作"""
        # 获取源值
        from_parts = from_path.split("/") if from_path else []
        value = self._get_value_at_path(data, from_parts)
        
        # 删除源位置
        data = self._apply_remove_operation(data, from_parts)
        
        # 添加到目标位置
        data = self._apply_add_operation(data, path_parts, value)
        
        return data
    
    def _apply_copy_operation(self, data: Dict[str, Any], path_parts: List[str], 
                            from_path: str) -> Dict[str, Any]:
        """应用复制操作"""
        # 获取源值
        from_parts = from_path.split("/") if from_path else []
        value = self._get_value_at_path(data, from_parts)
        
        # 添加到目标位置
        data = self._apply_add_operation(data, path_parts, value)
        
        return data
    
    def _get_value_at_path(self, data: Dict[str, Any], path_parts: List[str]) -> Any:
        """获取指定路径的值"""
        current = data
        
        for part in path_parts:
            if isinstance(current, dict):
                current = current[part]
            elif isinstance(current, list):
                current = current[int(part)]
            else:
                raise KeyError(f"无法导航到路径: {'/'.join(path_parts)}")
        
        return current
    
    # ============================================================
    # 3. 差异优化和压缩
    # ============================================================
    
    def optimize_diff(self, diff: VersionDiff) -> VersionDiff:
        """优化差异，减少操作数量"""
        
        optimized_operations = []
        
        # 合并连续的操作
        i = 0
        while i < len(diff.operations):
            operation = diff.operations[i]
            
            # 尝试合并后续操作
            merged_ops = [operation]
            j = i + 1
            
            while j < len(diff.operations):
                next_op = diff.operations[j]
                if self._can_merge_operations(operation, next_op):
                    merged_ops.append(next_op)
                    j += 1
                else:
                    break
            
            # 生成合并后的操作
            if len(merged_ops) > 1:
                merged_op = self._merge_operations(merged_ops)
                optimized_operations.append(merged_op)
            else:
                optimized_operations.append(operation)
            
            i = j
        
        # 创建优化后的差异对象
        optimized_diff = VersionDiff(
            uid=str(uuid.uuid4()),
            from_commit_uid=diff.from_commit_uid,
            to_commit_uid=diff.to_commit_uid,
            diff_type=diff.diff_type,
            operations=optimized_operations,
            metadata={
                **diff.metadata,
                "optimized": True,
                "original_operations_count": len(diff.operations),
                "optimized_operations_count": len(optimized_operations)
            },
            created_at=datetime.now()
        )
        
        return optimized_diff
    
    def _can_merge_operations(self, op1: DiffOperation, op2: DiffOperation) -> bool:
        """判断两个操作是否可以合并"""
        # 简化实现：只合并相同路径前缀的连续操作
        return (op1.path.startswith(op2.path) or op2.path.startswith(op1.path))
    
    def _merge_operations(self, operations: List[DiffOperation]) -> DiffOperation:
        """合并多个操作为单个操作"""
        # 简化实现：返回第一个操作
        # 实际应该实现更复杂的合并逻辑
        return operations[0]