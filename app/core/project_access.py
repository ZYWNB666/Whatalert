"""项目权限检查工具"""
from typing import Optional
from fastapi import HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.user import User
from app.models.project import Project, project_user
from app.db.database import get_db
from app.api.auth import get_current_user


async def get_project_id_from_request(
    project_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> int:
    """
    从请求中获取并验证 project_id
    
    规则:
    1. 如果请求中提供了 project_id,验证用户是否有权限访问该项目
    2. 如果没有提供,返回用户的默认项目或第一个项目
    """
    if project_id is not None:
        # 验证用户是否有权限访问该项目
        stmt = select(Project).join(
            project_user,
            Project.id == project_user.c.project_id
        ).where(
            and_(
                Project.id == project_id,
                Project.tenant_id == current_user.tenant_id,
                project_user.c.user_id == current_user.id
            )
        )
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=403, detail="无权限访问该项目")
        
        return project_id
    
    # 如果没有提供 project_id,获取默认项目
    stmt = select(Project).join(
        project_user,
        Project.id == project_user.c.project_id
    ).where(
        and_(
            Project.tenant_id == current_user.tenant_id,
            project_user.c.user_id == current_user.id
        )
    ).order_by(Project.is_default.desc(), Project.created_at.asc())
    
    result = await db.execute(stmt)
    project = result.scalars().first()
    
    if not project:
        raise HTTPException(status_code=400, detail="用户未分配任何项目")
    
    return project.id


async def check_project_access(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Project:
    """
    检查用户是否有权限访问指定项目
    返回项目对象
    """
    stmt = select(Project).join(
        project_user,
        Project.id == project_user.c.project_id
    ).where(
        and_(
            Project.id == project_id,
            Project.tenant_id == current_user.tenant_id,
            project_user.c.user_id == current_user.id
        )
    )
    
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=403, detail="无权限访问该项目")
    
    return project


async def get_user_role_in_project(
    project_id: int,
    user_id: int,
    db: AsyncSession
) -> Optional[str]:
    """获取用户在项目中的角色"""
    stmt = select(project_user.c.role).where(
        and_(
            project_user.c.project_id == project_id,
            project_user.c.user_id == user_id
        )
    )
    
    result = await db.execute(stmt)
    role = result.scalar_one_or_none()
    
    return role
