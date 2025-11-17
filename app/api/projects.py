"""项目管理 API"""
from typing import List, Optional
import time
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_, delete
from loguru import logger

from app.db.database import get_db
from app.models.project import Project, project_user
from app.models.user import User
from app.models.alert import AlertRule
from app.models.datasource import DataSource
from app.api.auth import get_current_user
from app.schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse,
    ProjectMemberAdd, ProjectMemberUpdate, ProjectMemberResponse
)

router = APIRouter()


@router.post("/", status_code=201, response_model=ProjectResponse)
@router.post("", status_code=201, response_model=ProjectResponse)  # 支持不带斜杠的路径
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建项目（仅超级管理员）"""
    # 检查是否为超级管理员
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="只有全局管理员可以创建项目"
        )
    # 检查项目代码是否已存在
    stmt = select(Project).where(
        and_(
            Project.tenant_id == current_user.tenant_id,
            Project.code == project_data.code
        )
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"项目代码 '{project_data.code}' 已存在")
    
    # 创建项目
    new_project = Project(
        **project_data.model_dump(),
        tenant_id=current_user.tenant_id
    )
    
    db.add(new_project)
    await db.flush()  # 获取 project ID
    
    # 将创建者添加为 admin
    stmt = project_user.insert().values(
        project_id=new_project.id,
        user_id=current_user.id,
        role='admin',
        created_at=int(time.time())
    )
    await db.execute(stmt)
    
    await db.commit()
    await db.refresh(new_project)
    
    logger.info(f"用户 {current_user.username} 创建项目: {new_project.name}")
    
    return ProjectResponse(**new_project.to_dict(), member_count=1, alert_rule_count=0, user_role='admin')


@router.get("/", response_model=ProjectListResponse)
@router.get("", response_model=ProjectListResponse)  # 支持不带斜杠的路径
async def list_projects(
    is_active: Optional[bool] = Query(None, description="是否激活"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取项目列表（超级管理员看所有项目，普通用户只看有权限的项目）"""
    
    if current_user.is_superuser:
        # 超级管理员查看所有项目
        stmt = select(Project).where(Project.tenant_id == current_user.tenant_id)
        
        if is_active is not None:
            stmt = stmt.where(Project.is_active == is_active)
        
        stmt = stmt.order_by(Project.is_default.desc(), Project.created_at.desc())
        
        result = await db.execute(stmt)
        all_projects = result.scalars().all()
        project_role_pairs = [(project, 'admin') for project in all_projects]
    else:
        # 普通用户查询参与的项目及其角色
        stmt = select(Project, project_user.c.role).join(
            project_user,
            Project.id == project_user.c.project_id
        ).where(
            and_(
                Project.tenant_id == current_user.tenant_id,
                project_user.c.user_id == current_user.id
            )
        )
        
        if is_active is not None:
            stmt = stmt.where(Project.is_active == is_active)
        
        stmt = stmt.order_by(Project.is_default.desc(), Project.created_at.desc())
        
        result = await db.execute(stmt)
        project_role_pairs = result.all()
    
    # 查询每个项目的统计信息
    project_responses = []
    for project, user_role in project_role_pairs:
        # 成员数量
        member_count_stmt = select(func.count()).select_from(project_user).where(
            project_user.c.project_id == project.id
        )
        member_count = await db.scalar(member_count_stmt)
        
        # 告警规则数量
        alert_count_stmt = select(func.count()).select_from(AlertRule).where(
            AlertRule.project_id == project.id
        )
        alert_count = await db.scalar(alert_count_stmt)
        
        project_responses.append(
            ProjectResponse(
                **project.to_dict(),
                member_count=member_count,
                alert_rule_count=alert_count,
                user_role=user_role
            )
        )
    
    return ProjectListResponse(total=len(project_responses), projects=project_responses)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取项目详情"""
    # 检查用户是否有权限访问该项目
    if current_user.is_superuser:
        # 超级管理员可以访问所有项目
        stmt = select(Project).where(
            and_(
                Project.id == project_id,
                Project.tenant_id == current_user.tenant_id
            )
        )
    else:
        # 普通用户只能访问参与的项目
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
        raise HTTPException(status_code=404, detail="项目不存在或无权限访问")
    
    # 统计信息
    member_count_stmt = select(func.count()).select_from(project_user).where(
        project_user.c.project_id == project_id
    )
    member_count = await db.scalar(member_count_stmt)
    
    alert_count_stmt = select(func.count()).select_from(AlertRule).where(
        AlertRule.project_id == project_id
    )
    alert_count = await db.scalar(alert_count_stmt)
    
    return ProjectResponse(
        **project.to_dict(),
        member_count=member_count,
        alert_rule_count=alert_count
    )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新项目"""
    # 检查权限（超级管理员或项目 admin）
    if current_user.is_superuser:
        # 超级管理员直接获取项目
        stmt = select(Project).where(
            and_(
                Project.id == project_id,
                Project.tenant_id == current_user.tenant_id
            )
        )
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
    else:
        # 普通用户需要是项目 admin
        stmt = select(Project, project_user.c.role).join(
            project_user,
            Project.id == project_user.c.project_id
        ).where(
            and_(
                Project.id == project_id,
                Project.tenant_id == current_user.tenant_id,
                project_user.c.user_id == current_user.id,
                project_user.c.role == 'admin'
            )
        )
        
        result = await db.execute(stmt)
        row = result.first()
        
        if not row:
            raise HTTPException(status_code=403, detail="无权限更新项目")
        
        project = row[0]
    
    # 更新项目信息
    update_data = project_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)
    
    project.updated_at = int(time.time())
    
    await db.commit()
    await db.refresh(project)
    
    logger.info(f"用户 {current_user.username} 更新项目: {project.name}")
    
    return ProjectResponse(**project.to_dict())


@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除项目"""
    # 检查权限（超级管理员或项目 admin）
    if current_user.is_superuser:
        # 超级管理员直接获取项目
        stmt = select(Project).where(
            and_(
                Project.id == project_id,
                Project.tenant_id == current_user.tenant_id
            )
        )
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
    else:
        # 普通用户需要是项目 admin
        stmt = select(Project, project_user.c.role).join(
            project_user,
            Project.id == project_user.c.project_id
        ).where(
            and_(
                Project.id == project_id,
                Project.tenant_id == current_user.tenant_id,
                project_user.c.user_id == current_user.id,
                project_user.c.role == 'admin'
            )
        )
        
        result = await db.execute(stmt)
        row = result.first()
        
        if not row:
            raise HTTPException(status_code=403, detail="只有项目管理员可以删除项目")
        
        project = row[0]
    
    # 不允许删除默认项目
    if project.is_default:
        raise HTTPException(status_code=400, detail="不能删除默认项目")
    
    await db.delete(project)
    await db.commit()
    
    logger.info(f"用户 {current_user.username} 删除项目: {project.name}")
    
    return {"message": "项目已删除"}


# ========== 项目成员管理 ==========

@router.get("/{project_id}/members", response_model=List[ProjectMemberResponse])
async def list_project_members(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取项目成员列表"""
    # 检查用户是否有权限访问该项目（超级管理员跳过检查）
    if not current_user.is_superuser:
        stmt = select(project_user.c.role).where(
            and_(
                project_user.c.project_id == project_id,
                project_user.c.user_id == current_user.id
            )
        )
        user_role = await db.scalar(stmt)
        
        if not user_role:
            raise HTTPException(status_code=403, detail="无权限访问该项目")
    
    # 查询所有成员
    stmt = select(
        User.id,
        User.username,
        User.email,
        project_user.c.role,
        project_user.c.created_at
    ).join(
        project_user,
        User.id == project_user.c.user_id
    ).where(
        project_user.c.project_id == project_id
    ).order_by(
        # admin 排最前面
        func.field(project_user.c.role, 'admin', 'maintainer', 'viewer'),
        User.username
    )
    
    result = await db.execute(stmt)
    members = []
    for row in result:
        members.append(ProjectMemberResponse(
            user_id=row[0],
            username=row[1],
            email=row[2],
            role=row[3],
            created_at=row[4]
        ))
    
    return members


@router.post("/{project_id}/members", status_code=201)
async def add_project_member(
    project_id: int,
    member_data: ProjectMemberAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """添加项目成员"""
    # 检查权限（只有 admin 可以添加成员）
    stmt = select(project_user.c.role).where(
        and_(
            project_user.c.project_id == project_id,
            project_user.c.user_id == current_user.id,
            project_user.c.role == 'admin'
        )
    )
    current_role = await db.scalar(stmt)
    
    if not current_role:
        raise HTTPException(status_code=403, detail="无权限添加成员")
    
    # 检查目标用户是否存在且属于同一租户
    target_user = await db.get(User, member_data.user_id)
    if not target_user or target_user.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 检查是否已经是成员
    stmt = select(project_user).where(
        and_(
            project_user.c.project_id == project_id,
            project_user.c.user_id == member_data.user_id
        )
    )
    result = await db.execute(stmt)
    if result.first():
        raise HTTPException(status_code=400, detail="用户已经是项目成员")
    
    # 添加成员
    stmt = project_user.insert().values(
        project_id=project_id,
        user_id=member_data.user_id,
        role=member_data.role,
        created_at=int(time.time())
    )
    await db.execute(stmt)
    await db.commit()
    
    logger.info(f"用户 {current_user.username} 添加 {target_user.username} 到项目 {project_id}，角色: {member_data.role}")
    
    return {"message": "成员已添加", "user_id": member_data.user_id, "role": member_data.role}


@router.put("/{project_id}/members/{user_id}")
async def update_project_member_role(
    project_id: int,
    user_id: int,
    role_data: ProjectMemberUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新项目成员角色"""
    # 检查权限（只有 admin 可以更新角色）
    stmt = select(project_user.c.role).where(
        and_(
            project_user.c.project_id == project_id,
            project_user.c.user_id == current_user.id,
            project_user.c.role == 'admin'
        )
    )
    current_role = await db.scalar(stmt)
    
    if not current_role:
        raise HTTPException(status_code=403, detail="无权限更新成员角色")
    
    # 检查目标成员是否存在
    stmt = select(project_user.c.role).where(
        and_(
            project_user.c.project_id == project_id,
            project_user.c.user_id == user_id
        )
    )
    target_role = await db.scalar(stmt)
    
    if not target_role:
        raise HTTPException(status_code=404, detail="成员不存在")
    
    # 更新角色
    stmt = project_user.update().where(
        and_(
            project_user.c.project_id == project_id,
            project_user.c.user_id == user_id
        )
    ).values(role=role_data.role)
    
    await db.execute(stmt)
    await db.commit()
    
    logger.info(f"用户 {current_user.username} 更新项目 {project_id} 成员 {user_id} 角色为: {role_data.role}")
    
    return {"message": "成员角色已更新", "user_id": user_id, "role": role_data.role}


@router.delete("/{project_id}/members/{user_id}")
async def remove_project_member(
    project_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """移除项目成员"""
    # 检查权限（只有 admin 可以移除成员）
    stmt = select(project_user.c.role).where(
        and_(
            project_user.c.project_id == project_id,
            project_user.c.user_id == current_user.id
        )
    )
    current_role = await db.scalar(stmt)
    
    if current_role != 'admin':
        raise HTTPException(status_code=403, detail="无权限移除成员")
    
    # 检查目标成员
    stmt = select(project_user.c.role).where(
        and_(
            project_user.c.project_id == project_id,
            project_user.c.user_id == user_id
        )
    )
    target_role = await db.scalar(stmt)
    
    if not target_role:
        raise HTTPException(status_code=404, detail="成员不存在")
    
    # 检查是否是最后一个 admin
    if target_role == 'admin':
        stmt = select(func.count()).select_from(project_user).where(
            and_(
                project_user.c.project_id == project_id,
                project_user.c.role == 'admin'
            )
        )
        admin_count = await db.scalar(stmt)
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="不能移除最后一个管理员")
    
    # 移除成员
    stmt = delete(project_user).where(
        and_(
            project_user.c.project_id == project_id,
            project_user.c.user_id == user_id
        )
    )
    await db.execute(stmt)
    await db.commit()
    
    logger.info(f"用户 {current_user.username} 从项目 {project_id} 移除成员 {user_id}")
    
    return {"message": "成员已移除"}
