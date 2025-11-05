"""审计日志 API"""
import time
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from app.db.database import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.api.auth import get_current_user
from app.schemas.audit import AuditLogResponse, AuditLogCreate

router = APIRouter()


@router.get("/")
async def list_audit_logs(
    action: Optional[str] = Query(None, description="操作类型"),
    resource_type: Optional[str] = Query(None, description="资源类型"),
    username: Optional[str] = Query(None, description="用户名"),
    ip_address: Optional[str] = Query(None, description="IP地址"),
    status: Optional[str] = Query(None, description="状态"),
    start_time: Optional[int] = Query(None, description="开始时间戳"),
    end_time: Optional[int] = Query(None, description="结束时间戳"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取审计日志列表"""
    # 构建查询条件
    conditions = [AuditLog.tenant_id == current_user.tenant_id]
    
    if action:
        conditions.append(AuditLog.action == action)
    if resource_type:
        conditions.append(AuditLog.resource_type == resource_type)
    if username:
        conditions.append(AuditLog.username.like(f'%{username}%'))
    if ip_address:
        conditions.append(AuditLog.ip_address == ip_address)
    if status:
        conditions.append(AuditLog.status == status)
    if start_time:
        conditions.append(AuditLog.timestamp >= start_time)
    if end_time:
        conditions.append(AuditLog.timestamp <= end_time)
    
    # 查询总数
    count_stmt = select(func.count(AuditLog.id)).where(and_(*conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar()
    
    # 查询数据
    offset = (page - 1) * page_size
    stmt = select(AuditLog).where(
        and_(*conditions)
    ).order_by(desc(AuditLog.timestamp)).offset(offset).limit(page_size)
    
    result = await db.execute(stmt)
    logs = result.scalars().all()
    
    # 转换为字典列表
    log_data = []
    for log in logs:
        log_data.append({
            "id": log.id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "resource_name": log.resource_name,
            "user_id": log.user_id,
            "username": log.username,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "request_method": log.request_method,
            "request_path": log.request_path,
            "changes": log.changes,
            "status": log.status,
            "error_message": log.error_message,
            "timestamp": log.timestamp,
            "tenant_id": log.tenant_id,
            "created_at": log.created_at
        })
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": log_data
    }


@router.get("/{log_id}")
async def get_audit_log(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取审计日志详情"""
    stmt = select(AuditLog).where(
        and_(
            AuditLog.id == log_id,
            AuditLog.tenant_id == current_user.tenant_id
        )
    )
    result = await db.execute(stmt)
    log = result.scalar_one_or_none()
    
    if not log:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="日志不存在")
    
    return {
        "id": log.id,
        "action": log.action,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
        "resource_name": log.resource_name,
        "user_id": log.user_id,
        "username": log.username,
        "ip_address": log.ip_address,
        "user_agent": log.user_agent,
        "request_method": log.request_method,
        "request_path": log.request_path,
        "changes": log.changes,
        "status": log.status,
        "error_message": log.error_message,
        "timestamp": log.timestamp,
        "tenant_id": log.tenant_id,
        "created_at": log.created_at
    }


@router.get("/stats/summary")
async def get_audit_stats(
    start_time: Optional[int] = Query(None, description="开始时间戳"),
    end_time: Optional[int] = Query(None, description="结束时间戳"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取审计日志统计"""
    from sqlalchemy import case
    
    conditions = [AuditLog.tenant_id == current_user.tenant_id]
    if start_time:
        conditions.append(AuditLog.timestamp >= start_time)
    if end_time:
        conditions.append(AuditLog.timestamp <= end_time)
    
    # 按操作类型统计
    action_stmt = select(
        AuditLog.action,
        func.count(AuditLog.id).label('count')
    ).where(and_(*conditions)).group_by(AuditLog.action)
    
    action_result = await db.execute(action_stmt)
    action_stats = [{"action": row[0], "count": row[1]} for row in action_result]
    
    # 按资源类型统计
    resource_stmt = select(
        AuditLog.resource_type,
        func.count(AuditLog.id).label('count')
    ).where(and_(*conditions)).group_by(AuditLog.resource_type)
    
    resource_result = await db.execute(resource_stmt)
    resource_stats = [{"resource_type": row[0], "count": row[1]} for row in resource_result]
    
    # 按状态统计
    status_stmt = select(
        AuditLog.status,
        func.count(AuditLog.id).label('count')
    ).where(and_(*conditions)).group_by(AuditLog.status)
    
    status_result = await db.execute(status_stmt)
    status_stats = [{"status": row[0], "count": row[1]} for row in status_result]
    
    return {
        "action_stats": action_stats,
        "resource_stats": resource_stats,
        "status_stats": status_stats
    }


async def create_audit_log(
    db: AsyncSession,
    action: str,
    resource_type: str,
    user: Optional[User] = None,
    resource_id: Optional[int] = None,
    resource_name: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_method: Optional[str] = None,
    request_path: Optional[str] = None,
    changes: Optional[dict] = None,
    status: str = "success",
    error_message: Optional[str] = None
):
    """创建审计日志（工具函数）"""
    log = AuditLog(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        user_id=user.id if user else None,
        username=user.username if user else None,
        ip_address=ip_address,
        user_agent=user_agent,
        request_method=request_method,
        request_path=request_path,
        changes=changes,
        status=status,
        error_message=error_message,
        timestamp=int(time.time()),
        tenant_id=user.tenant_id if user else None
    )
    
    db.add(log)
    await db.commit()
    return log
