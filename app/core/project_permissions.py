"""项目成员权限检查"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.database import get_db
from app.models.user import User
from app.models.project import project_user, Project
from app.api.auth import get_current_user


async def check_project_member(
    project_id: int,
    current_user: User,
    db: AsyncSession,
    required_role: Optional[str] = None
) -> str:
    """
    检查用户是否是项目成员，并返回用户在项目中的角色
    
    Args:
        project_id: 项目ID
        current_user: 当前用户
        db: 数据库会话
        required_role: 需要的最低角色，可选值: 'viewer', 'maintainer', 'admin'
    
    Returns:
        用户在项目中的角色
    
    Raises:
        HTTPException: 如果用户不是项目成员或角色不足
    """
    # 超级管理员拥有所有项目的所有权限
    if current_user.is_superuser:
        return 'admin'
    
    # 查询用户在项目中的角色
    stmt = select(project_user.c.role).where(
        and_(
            project_user.c.project_id == project_id,
            project_user.c.user_id == current_user.id
        )
    )
    result = await db.execute(stmt)
    user_role = result.scalar_one_or_none()
    
    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"您不是项目 {project_id} 的成员"
        )
    
    # 检查角色权限等级
    if required_role:
        role_hierarchy = {
            'viewer': 1,       # 查看者：只读
            'maintainer': 2,   # 维护者：增改查
            'admin': 3         # 管理员：增删改查
        }
        
        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要 {required_role} 或更高权限，您的角色是 {user_role}"
            )
    
    return user_role


async def require_project_member(
    project_id: int = Query(..., description="项目ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> tuple[User, str]:
    """
    要求用户是项目成员（任意角色）
    返回 (用户, 角色)
    """
    role = await check_project_member(project_id, current_user, db)
    return current_user, role


async def require_project_viewer(
    project_id: int = Query(..., description="项目ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> tuple[User, str]:
    """要求用户至少是项目的 viewer"""
    role = await check_project_member(project_id, current_user, db, required_role='viewer')
    return current_user, role


async def require_project_developer(
    project_id: int = Query(..., description="项目ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> tuple[User, str]:
    """要求用户至少是项目的 maintainer（维护者）"""
    role = await check_project_member(project_id, current_user, db, required_role='maintainer')
    return current_user, role


async def require_project_maintainer(
    project_id: int = Query(..., description="项目ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> tuple[User, str]:
    """要求用户至少是项目的 maintainer（维护者）"""
    role = await check_project_member(project_id, current_user, db, required_role='maintainer')
    return current_user, role


async def require_project_admin(
    project_id: int = Query(..., description="项目ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> tuple[User, str]:
    """要求用户至少是项目的 admin"""
    role = await check_project_member(project_id, current_user, db, required_role='admin')
    return current_user, role


async def require_project_owner(
    project_id: int = Query(..., description="项目ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> tuple[User, str]:
    """要求用户是项目的 admin（管理员）"""
    role = await check_project_member(project_id, current_user, db, required_role='admin')
    return current_user, role


def can_read_resource(role: str) -> bool:
    """检查角色是否可以读取资源 - 所有角色都可以读"""
    return role in ['viewer', 'maintainer', 'admin']


def can_create_resource(role: str) -> bool:
    """检查角色是否可以创建资源 - 维护者和管理员"""
    return role in ['maintainer', 'admin']


def can_update_resource(role: str) -> bool:
    """检查角色是否可以更新资源 - 维护者和管理员"""
    return role in ['maintainer', 'admin']


def can_delete_resource(role: str) -> bool:
    """检查角色是否可以删除资源 - 只有管理员"""
    return role in ['admin']


def can_manage_members(role: str) -> bool:
    """检查角色是否可以管理成员 - 只有管理员"""
    return role in ['admin']
