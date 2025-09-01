"""
项目名称值对象

项目名称的值对象表示
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectName:
    """项目名称值对象"""
    
    value: str
    
    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("项目名称不能为空")
        
        if len(self.value) > 100:
            raise ValueError("项目名称不能超过100个字符")
        
        # 检查无效字符
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in invalid_chars:
            if char in self.value:
                raise ValueError(f"项目名称不能包含无效字符: {char}")