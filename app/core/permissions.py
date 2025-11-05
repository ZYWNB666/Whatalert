"""权限检查"""
from typing import List, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.models.user import User, Permission
from app.api.auth import get_current_user


async def check_permission(
    resource: str,
    action: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    """检查用户是否有指定权限"""
    # 超级管理员拥有所有权限
    if current_user.is_superuser:
        return current_user
    
    # 直接使用预加载的角色和权限数据（get_current_user已经加载了）
    if not current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户没有任何角色"
        )
    
    # 检查用户的角色是否有对应权限
    for role in current_user.roles:
        for permission in role.permissions:
            if permission.resource == resource and permission.action == action:
                return current_user
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"没有权限执行此操作: {resource}.{action}"
    )


def require_permission(resource: str, action: str):
    """权限检查装饰器工厂"""
    async def permission_checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        return await check_permission(resource, action, current_user, db)
    return permission_checker


def require_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """要求超级管理员权限"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要超级管理员权限"
        )
    return current_user


# 预定义的权限检查依赖
RequireAlertRuleRead = Depends(require_permission("alert_rule", "read"))
RequireAlertRuleCreate = Depends(require_permission("alert_rule", "create"))
RequireAlertRuleUpdate = Depends(require_permission("alert_rule", "update"))
RequireAlertRuleDelete = Depends(require_permission("alert_rule", "delete"))

RequireDatasourceRead = Depends(require_permission("datasource", "read"))
RequireDatasourceCreate = Depends(require_permission("datasource", "create"))
RequireDatasourceUpdate = Depends(require_permission("datasource", "update"))
RequireDatasourceDelete = Depends(require_permission("datasource", "delete"))

RequireNotificationRead = Depends(require_permission("notification", "read"))
RequireNotificationCreate = Depends(require_permission("notification", "create"))
RequireNotificationUpdate = Depends(require_permission("notification", "update"))
RequireNotificationDelete = Depends(require_permission("notification", "delete"))

RequireUserRead = Depends(require_permission("user", "read"))
RequireUserCreate = Depends(require_permission("user", "create"))
RequireUserUpdate = Depends(require_permission("user", "update"))
RequireUserDelete = Depends(require_permission("user", "delete"))

RequireSuperuser = Depends(require_superuser)
