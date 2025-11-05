"""用户管理 API"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from passlib.context import CryptContext
from app.db.database import get_db
from app.models.user import User, Role
from app.models.tenant import Tenant
from app.api.auth import get_current_user
from app.core.permissions import require_permission, require_superuser
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserWithRolesResponse,
    UserPasswordUpdate, RoleResponse
)

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.get("/")
async def list_users(
    current_user: User = Depends(require_permission("user", "read")),
    db: AsyncSession = Depends(get_db)
):
    """获取用户列表"""
    # 使用 selectinload 预加载角色数据
    stmt = select(User).options(selectinload(User.roles)).where(
        User.tenant_id == current_user.tenant_id
    )
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    # 转换为响应格式，添加角色信息
    response_users = []
    for user in users:
        user_dict = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "tenant_id": user.tenant_id,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "role_names": [role.name for role in user.roles],
            "roles": [{"id": role.id, "name": role.name, "code": role.code} for role in user.roles]
        }
        response_users.append(user_dict)
    
    return response_users


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户信息（包含权限）"""
    from app.models.user import Permission
    
    # 使用 selectinload 预加载角色和权限数据
    stmt = select(User).options(
        selectinload(User.roles).selectinload(Role.permissions)
    ).where(User.id == current_user.id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    # 收集所有权限
    permissions = set()
    roles = []
    
    if user:
        for role in user.roles:
            roles.append({
                "id": role.id,
                "name": role.name,
                "code": role.code
            })
            for perm in role.permissions:
                permissions.add(f"{perm.resource}.{perm.action}")
    
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "phone": current_user.phone,
        "is_superuser": current_user.is_superuser,
        "tenant_id": current_user.tenant_id,
        "roles": roles,
        "permissions": list(permissions)
    }


@router.get("/{user_id}")
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户详情"""
    # 使用 selectinload 预加载角色数据
    stmt = select(User).options(selectinload(User.roles)).where(
        and_(
            User.id == user_id,
            User.tenant_id == current_user.tenant_id
        )
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "tenant_id": user.tenant_id,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "role_names": [role.name for role in user.roles],
        "roles": [{"id": role.id, "name": role.name, "code": role.code} for role in user.roles]
    }


@router.post("/", status_code=201)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_permission("user", "create")),
    db: AsyncSession = Depends(get_db)
):
    """创建用户"""
    # 检查用户名是否已存在
    stmt = select(User).where(
        or_(
            User.username == user_data.username,
            User.email == user_data.email
        )
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名或邮箱已存在")
    
    # 创建用户
    hashed_password = pwd_context.hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name,
        phone=user_data.phone,
        is_active=user_data.is_active,
        is_superuser=user_data.is_superuser,
        tenant_id=current_user.tenant_id
    )
    
    # 分配角色
    if user_data.role_ids:
        stmt = select(Role).where(
            and_(
                Role.id.in_(user_data.role_ids),
                Role.tenant_id == current_user.tenant_id
            )
        )
        result = await db.execute(stmt)
        roles = result.scalars().all()
        new_user.roles = list(roles)
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return {
        "id": new_user.id,
        "username": new_user.username,
        "email": new_user.email,
        "full_name": new_user.full_name,
        "phone": new_user.phone,
        "is_active": new_user.is_active,
        "is_superuser": new_user.is_superuser,
        "tenant_id": new_user.tenant_id,
        "created_at": new_user.created_at,
        "updated_at": new_user.updated_at
    }


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新用户"""
    # 使用 selectinload 预加载角色数据
    stmt = select(User).options(selectinload(User.roles)).where(
        and_(
            User.id == user_id,
            User.tenant_id == current_user.tenant_id
        )
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 更新字段
    update_data = user_data.dict(exclude_unset=True, exclude={'role_ids'})
    for key, value in update_data.items():
        setattr(user, key, value)
    
    # 更新角色
    if user_data.role_ids is not None:
        stmt = select(Role).where(
            and_(
                Role.id.in_(user_data.role_ids),
                Role.tenant_id == current_user.tenant_id
            )
        )
        result = await db.execute(stmt)
        roles = result.scalars().all()
        user.roles = list(roles)
    
    await db.commit()
    await db.refresh(user)
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "tenant_id": user.tenant_id,
        "created_at": user.created_at,
        "updated_at": user.updated_at
    }


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_permission("user", "delete")),
    db: AsyncSession = Depends(get_db)
):
    """删除用户"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    
    stmt = select(User).where(
        and_(
            User.id == user_id,
            User.tenant_id == current_user.tenant_id
        )
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    await db.delete(user)
    await db.commit()
    
    return {"message": "用户已删除"}


@router.post("/{user_id}/password")
async def update_user_password(
    user_id: int,
    password_data: UserPasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """修改用户密码"""
    # 只能修改自己的密码或管理员修改其他人的密码
    if user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="没有权限")
    
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 验证旧密码
    if user_id == current_user.id:
        if not pwd_context.verify(password_data.old_password, user.password_hash):
            raise HTTPException(status_code=400, detail="旧密码错误")
    
    # 更新密码
    user.password_hash = pwd_context.hash(password_data.new_password)
    await db.commit()
    
    return {"message": "密码已更新"}


@router.get("/roles/list")
async def list_roles(
    current_user: User = Depends(require_permission("user", "read")),
    db: AsyncSession = Depends(get_db)
):
    """获取角色列表"""
    stmt = select(Role).where(Role.tenant_id == current_user.tenant_id)
    result = await db.execute(stmt)
    roles = result.scalars().all()
    
    return [
        {
            "id": role.id,
            "name": role.name,
            "code": role.code,
            "description": role.description,
            "tenant_id": role.tenant_id,
            "created_at": role.created_at,
            "updated_at": role.updated_at
        }
        for role in roles
    ]
