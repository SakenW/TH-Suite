"""
翻译权限控制服务
实现基于角色的访问控制 (RBAC) 和权限验证
"""

from typing import Any, Dict, List, Optional, Set
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

import structlog

logger = structlog.get_logger(__name__)


class UserRole(Enum):
    """用户角色"""
    GUEST = "guest"                    # 访客
    TRANSLATOR = "translator"          # 翻译者
    REVIEWER = "reviewer"              # 审核者
    SENIOR_TRANSLATOR = "senior_translator"  # 高级翻译者
    SENIOR_REVIEWER = "senior_reviewer"      # 高级审核者
    COORDINATOR = "coordinator"        # 协调员
    PROJECT_MANAGER = "project_manager"  # 项目经理
    ADMIN = "admin"                    # 管理员
    SUPER_ADMIN = "super_admin"        # 超级管理员


class Permission(Enum):
    """权限枚举"""
    # 基础权限
    READ_TRANSLATIONS = "read_translations"
    READ_STATISTICS = "read_statistics"
    
    # 翻译权限
    CREATE_TRANSLATION = "create_translation"
    EDIT_TRANSLATION = "edit_translation"
    DELETE_TRANSLATION = "delete_translation"
    SUBMIT_TRANSLATION = "submit_translation"
    
    # 审核权限
    REVIEW_TRANSLATION = "review_translation"
    APPROVE_TRANSLATION = "approve_translation"
    REJECT_TRANSLATION = "reject_translation"
    REQUEST_REVISION = "request_revision"
    
    # 状态管理权限
    CHANGE_STATE = "change_state"
    LOCK_TRANSLATION = "lock_translation"
    UNLOCK_TRANSLATION = "unlock_translation"
    
    # 分配权限
    ASSIGN_TRANSLATION = "assign_translation"
    REASSIGN_TRANSLATION = "reassign_translation"
    
    # 批量操作权限
    BATCH_STATE_CHANGE = "batch_state_change"
    BATCH_ASSIGNMENT = "batch_assignment"
    BATCH_REVIEW = "batch_review"
    BATCH_PUBLICATION = "batch_publication"
    BATCH_CLEANUP = "batch_cleanup"
    
    # 发布权限
    PUBLISH_TRANSLATION = "publish_translation"
    UNPUBLISH_TRANSLATION = "unpublish_translation"
    
    # 项目管理权限
    CREATE_PROJECT = "create_project"
    EDIT_PROJECT = "edit_project"
    DELETE_PROJECT = "delete_project"
    MANAGE_PROJECT_SETTINGS = "manage_project_settings"
    
    # 用户管理权限
    MANAGE_USERS = "manage_users"
    ASSIGN_ROLES = "assign_roles"
    VIEW_USER_ACTIVITIES = "view_user_activities"
    
    # 系统管理权限
    MANAGE_SYSTEM_SETTINGS = "manage_system_settings"
    VIEW_SYSTEM_LOGS = "view_system_logs"
    MANAGE_WORKFLOWS = "manage_workflows"
    MANAGE_TEMPLATES = "manage_templates"


@dataclass
class User:
    """用户信息"""
    user_id: str
    username: str
    email: str = ""
    roles: Set[UserRole] = field(default_factory=set)
    custom_permissions: Set[Permission] = field(default_factory=set)
    project_roles: Dict[str, Set[UserRole]] = field(default_factory=dict)  # 项目级角色
    is_active: bool = True
    
    def has_role(self, role: UserRole, project_id: str = None) -> bool:
        """检查用户是否有指定角色"""
        # 检查全局角色
        if role in self.roles:
            return True
        
        # 检查项目级角色
        if project_id and project_id in self.project_roles:
            return role in self.project_roles[project_id]
        
        return False
    
    def get_all_roles(self, project_id: str = None) -> Set[UserRole]:
        """获取用户的所有角色"""
        all_roles = set(self.roles)
        
        if project_id and project_id in self.project_roles:
            all_roles.update(self.project_roles[project_id])
        
        return all_roles


@dataclass
class RolePermissionMapping:
    """角色权限映射"""
    role: UserRole
    permissions: Set[Permission]
    inherits_from: Set[UserRole] = field(default_factory=set)


class PermissionResolver:
    """权限解析器"""
    
    def __init__(self):
        self.role_mappings = self._create_default_role_mappings()
        self.permission_hierarchy = self._create_permission_hierarchy()
    
    def _create_default_role_mappings(self) -> Dict[UserRole, RolePermissionMapping]:
        """创建默认的角色权限映射"""
        mappings = {}
        
        # 访客
        mappings[UserRole.GUEST] = RolePermissionMapping(
            role=UserRole.GUEST,
            permissions={
                Permission.READ_TRANSLATIONS,
                Permission.READ_STATISTICS
            }
        )
        
        # 翻译者
        mappings[UserRole.TRANSLATOR] = RolePermissionMapping(
            role=UserRole.TRANSLATOR,
            permissions={
                Permission.CREATE_TRANSLATION,
                Permission.EDIT_TRANSLATION,
                Permission.SUBMIT_TRANSLATION
            },
            inherits_from={UserRole.GUEST}
        )
        
        # 审核者
        mappings[UserRole.REVIEWER] = RolePermissionMapping(
            role=UserRole.REVIEWER,
            permissions={
                Permission.REVIEW_TRANSLATION,
                Permission.APPROVE_TRANSLATION,
                Permission.REJECT_TRANSLATION,
                Permission.REQUEST_REVISION,
                Permission.CHANGE_STATE
            },
            inherits_from={UserRole.TRANSLATOR}
        )
        
        # 高级翻译者
        mappings[UserRole.SENIOR_TRANSLATOR] = RolePermissionMapping(
            role=UserRole.SENIOR_TRANSLATOR,
            permissions={
                Permission.DELETE_TRANSLATION,
                Permission.ASSIGN_TRANSLATION,
                Permission.LOCK_TRANSLATION
            },
            inherits_from={UserRole.TRANSLATOR}
        )
        
        # 高级审核者
        mappings[UserRole.SENIOR_REVIEWER] = RolePermissionMapping(
            role=UserRole.SENIOR_REVIEWER,
            permissions={
                Permission.UNLOCK_TRANSLATION,
                Permission.BATCH_REVIEW,
                Permission.PUBLISH_TRANSLATION
            },
            inherits_from={UserRole.REVIEWER, UserRole.SENIOR_TRANSLATOR}
        )
        
        # 协调员
        mappings[UserRole.COORDINATOR] = RolePermissionMapping(
            role=UserRole.COORDINATOR,
            permissions={
                Permission.REASSIGN_TRANSLATION,
                Permission.BATCH_STATE_CHANGE,
                Permission.BATCH_ASSIGNMENT,
                Permission.VIEW_USER_ACTIVITIES
            },
            inherits_from={UserRole.SENIOR_REVIEWER}
        )
        
        # 项目经理
        mappings[UserRole.PROJECT_MANAGER] = RolePermissionMapping(
            role=UserRole.PROJECT_MANAGER,
            permissions={
                Permission.CREATE_PROJECT,
                Permission.EDIT_PROJECT,
                Permission.MANAGE_PROJECT_SETTINGS,
                Permission.BATCH_PUBLICATION,
                Permission.BATCH_CLEANUP,
                Permission.ASSIGN_ROLES
            },
            inherits_from={UserRole.COORDINATOR}
        )
        
        # 管理员
        mappings[UserRole.ADMIN] = RolePermissionMapping(
            role=UserRole.ADMIN,
            permissions={
                Permission.DELETE_PROJECT,
                Permission.UNPUBLISH_TRANSLATION,
                Permission.MANAGE_USERS,
                Permission.MANAGE_WORKFLOWS,
                Permission.MANAGE_TEMPLATES
            },
            inherits_from={UserRole.PROJECT_MANAGER}
        )
        
        # 超级管理员
        mappings[UserRole.SUPER_ADMIN] = RolePermissionMapping(
            role=UserRole.SUPER_ADMIN,
            permissions={
                Permission.MANAGE_SYSTEM_SETTINGS,
                Permission.VIEW_SYSTEM_LOGS
            },
            inherits_from={UserRole.ADMIN}
        )
        
        return mappings
    
    def _create_permission_hierarchy(self) -> Dict[Permission, Set[Permission]]:
        """创建权限层次结构"""
        hierarchy = {}
        
        # 一些高级权限包含低级权限
        hierarchy[Permission.MANAGE_USERS] = {
            Permission.VIEW_USER_ACTIVITIES,
            Permission.ASSIGN_ROLES
        }
        
        hierarchy[Permission.BATCH_PUBLICATION] = {
            Permission.PUBLISH_TRANSLATION,
            Permission.BATCH_STATE_CHANGE
        }
        
        hierarchy[Permission.MANAGE_PROJECT_SETTINGS] = {
            Permission.EDIT_PROJECT,
            Permission.MANAGE_WORKFLOWS
        }
        
        return hierarchy
    
    def resolve_permissions(self, user: User, project_id: str = None) -> Set[Permission]:
        """解析用户的所有权限"""
        all_permissions = set(user.custom_permissions)
        
        # 获取用户的所有角色
        user_roles = user.get_all_roles(project_id)
        
        # 解析每个角色的权限
        for role in user_roles:
            role_permissions = self._resolve_role_permissions(role)
            all_permissions.update(role_permissions)
        
        # 应用权限层次结构
        expanded_permissions = set(all_permissions)
        for permission in all_permissions:
            if permission in self.permission_hierarchy:
                expanded_permissions.update(self.permission_hierarchy[permission])
        
        return expanded_permissions
    
    def _resolve_role_permissions(self, role: UserRole) -> Set[Permission]:
        """解析角色的所有权限（包括继承的权限）"""
        all_permissions = set()
        visited_roles = set()
        
        def collect_permissions(current_role: UserRole):
            if current_role in visited_roles:
                return
            
            visited_roles.add(current_role)
            
            if current_role in self.role_mappings:
                mapping = self.role_mappings[current_role]
                all_permissions.update(mapping.permissions)
                
                # 递归收集继承的权限
                for inherited_role in mapping.inherits_from:
                    collect_permissions(inherited_role)
        
        collect_permissions(role)
        return all_permissions


class TranslationPermissionService:
    """翻译权限控制服务"""
    
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.permission_resolver = PermissionResolver()
        self._setup_default_users()
    
    def _setup_default_users(self):
        """设置默认用户（用于演示）"""
        # 管理员用户
        self.users["admin"] = User(
            user_id="admin",
            username="管理员",
            email="admin@example.com",
            roles={UserRole.ADMIN}
        )
        
        # 协调员用户
        self.users["coordinator1"] = User(
            user_id="coordinator1",
            username="协调员1",
            email="coordinator1@example.com",
            roles={UserRole.COORDINATOR}
        )
        
        # 高级审核者
        self.users["reviewer1"] = User(
            user_id="reviewer1",
            username="审核者1",
            email="reviewer1@example.com",
            roles={UserRole.SENIOR_REVIEWER}
        )
        
        # 翻译者
        self.users["translator1"] = User(
            user_id="translator1",
            username="翻译者1",
            email="translator1@example.com",
            roles={UserRole.TRANSLATOR}
        )
        
        self.users["translator2"] = User(
            user_id="translator2",
            username="翻译者2",
            email="translator2@example.com",
            roles={UserRole.SENIOR_TRANSLATOR}
        )
    
    def get_user(self, user_id: str) -> Optional[User]:
        """获取用户信息"""
        return self.users.get(user_id)
    
    def create_user(self, user: User) -> bool:
        """创建用户"""
        try:
            if user.user_id in self.users:
                return False
            
            self.users[user.user_id] = user
            logger.info(f"用户创建成功", user_id=user.user_id, username=user.username)
            return True
            
        except Exception as e:
            logger.error(f"创建用户失败", user_id=user.user_id, error=str(e))
            return False
    
    def update_user_roles(self, user_id: str, roles: Set[UserRole], project_id: str = None) -> bool:
        """更新用户角色"""
        try:
            user = self.users.get(user_id)
            if not user:
                return False
            
            if project_id:
                user.project_roles[project_id] = roles
            else:
                user.roles = roles
            
            logger.info(
                f"用户角色更新成功",
                user_id=user_id,
                roles=[role.value for role in roles],
                project_id=project_id
            )
            return True
            
        except Exception as e:
            logger.error(f"更新用户角色失败", user_id=user_id, error=str(e))
            return False
    
    def check_permission(
        self,
        user_id: str,
        permission: Permission,
        project_id: str = None,
        resource_context: Dict[str, Any] = None
    ) -> bool:
        """检查用户权限"""
        try:
            user = self.users.get(user_id)
            if not user or not user.is_active:
                return False
            
            # 解析用户权限
            user_permissions = self.permission_resolver.resolve_permissions(user, project_id)
            
            # 检查基础权限
            if permission in user_permissions:
                # 进行额外的上下文检查
                return self._check_context_permission(user, permission, resource_context)
            
            return False
            
        except Exception as e:
            logger.error(f"权限检查失败", user_id=user_id, permission=permission.value, error=str(e))
            return False
    
    def _check_context_permission(
        self,
        user: User,
        permission: Permission,
        context: Dict[str, Any] = None
    ) -> bool:
        """检查上下文相关的权限"""
        if not context:
            return True
        
        # 检查资源所有权
        resource_owner = context.get("owner_id")
        if resource_owner and resource_owner == user.user_id:
            # 用户可以操作自己的资源
            if permission in [
                Permission.EDIT_TRANSLATION,
                Permission.DELETE_TRANSLATION,
                Permission.SUBMIT_TRANSLATION
            ]:
                return True
        
        # 检查项目权限
        project_id = context.get("project_id")
        if project_id:
            project_roles = user.project_roles.get(project_id, set())
            
            # 项目经理可以管理项目内的所有资源
            if UserRole.PROJECT_MANAGER in project_roles or UserRole.ADMIN in user.roles:
                return True
        
        # 检查状态相关权限
        current_state = context.get("current_state")
        if current_state and permission == Permission.CHANGE_STATE:
            target_state = context.get("target_state")
            
            # 某些状态转换需要特殊权限
            if current_state == "locked" and target_state != "locked":
                return Permission.UNLOCK_TRANSLATION in self.permission_resolver.resolve_permissions(user, project_id)
        
        return True
    
    def get_user_permissions(self, user_id: str, project_id: str = None) -> Set[Permission]:
        """获取用户的所有权限"""
        user = self.users.get(user_id)
        if not user:
            return set()
        
        return self.permission_resolver.resolve_permissions(user, project_id)
    
    def get_users_with_permission(self, permission: Permission, project_id: str = None) -> List[User]:
        """获取拥有指定权限的用户"""
        users_with_permission = []
        
        for user in self.users.values():
            if not user.is_active:
                continue
            
            user_permissions = self.permission_resolver.resolve_permissions(user, project_id)
            if permission in user_permissions:
                users_with_permission.append(user)
        
        return users_with_permission
    
    def get_available_assignees(self, assignment_type: str, project_id: str = None) -> List[User]:
        """获取可分配的用户列表"""
        if assignment_type == "translate":
            required_permission = Permission.CREATE_TRANSLATION
        elif assignment_type == "review":
            required_permission = Permission.REVIEW_TRANSLATION
        elif assignment_type == "approve":
            required_permission = Permission.APPROVE_TRANSLATION
        else:
            return []
        
        return self.get_users_with_permission(required_permission, project_id)
    
    def check_workflow_permission(
        self,
        user_id: str,
        from_state: str,
        to_state: str,
        project_id: str = None
    ) -> bool:
        """检查工作流转换权限"""
        user = self.users.get(user_id)
        if not user:
            return False
        
        user_permissions = self.permission_resolver.resolve_permissions(user, project_id)
        
        # 基于状态转换的权限检查
        state_transition_permissions = {
            ("draft", "pending"): Permission.SUBMIT_TRANSLATION,
            ("pending", "translated"): Permission.CREATE_TRANSLATION,
            ("translated", "under_review"): Permission.SUBMIT_TRANSLATION,
            ("under_review", "reviewed"): Permission.REVIEW_TRANSLATION,
            ("under_review", "needs_revision"): Permission.REQUEST_REVISION,
            ("under_review", "rejected"): Permission.REJECT_TRANSLATION,
            ("reviewed", "approved"): Permission.APPROVE_TRANSLATION,
            ("approved", "published"): Permission.PUBLISH_TRANSLATION,
            ("published", "archived"): Permission.MANAGE_PROJECT_SETTINGS,
        }
        
        transition_key = (from_state, to_state)
        required_permission = state_transition_permissions.get(transition_key)
        
        if required_permission:
            return required_permission in user_permissions
        
        # 默认需要状态变更权限
        return Permission.CHANGE_STATE in user_permissions
    
    def get_role_hierarchy(self) -> Dict[str, Any]:
        """获取角色层次结构"""
        hierarchy = {}
        
        for role, mapping in self.permission_resolver.role_mappings.items():
            hierarchy[role.value] = {
                "permissions": [p.value for p in mapping.permissions],
                "inherits_from": [r.value for r in mapping.inherits_from]
            }
        
        return hierarchy
    
    def get_permission_matrix(self) -> Dict[str, Dict[str, bool]]:
        """获取权限矩阵"""
        matrix = {}
        
        all_permissions = list(Permission)
        all_roles = list(UserRole)
        
        for role in all_roles:
            role_permissions = self.permission_resolver._resolve_role_permissions(role)
            matrix[role.value] = {}
            
            for permission in all_permissions:
                matrix[role.value][permission.value] = permission in role_permissions
        
        return matrix