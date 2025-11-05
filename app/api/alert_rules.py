"""告警规则API"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc

from app.db.database import get_db
from app.models.alert import AlertRule, AlertEvent, AlertEventHistory
from app.models.user import User
from app.api.auth import get_current_user
from app.schemas.alert import (
    AlertRuleCreate, AlertRuleUpdate, AlertRuleResponse,
    AlertEventResponse, AlertEventHistoryResponse
)

router = APIRouter()


@router.post("/", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_alert_rule(
    rule_data: AlertRuleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建告警规则"""
    new_rule = AlertRule(
        **rule_data.dict(),
        tenant_id=current_user.tenant_id
    )
    
    db.add(new_rule)
    await db.commit()
    await db.refresh(new_rule)
    
    return new_rule


@router.get("/", response_model=List[AlertRuleResponse])
async def list_alert_rules(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取告警规则列表"""
    stmt = select(AlertRule).where(
        AlertRule.tenant_id == current_user.tenant_id
    ).offset(skip).limit(limit)
    
    result = await db.execute(stmt)
    rules = result.scalars().all()
    
    return rules


@router.get("/{rule_id}", response_model=AlertRuleResponse)
async def get_alert_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取告警规则详情"""
    stmt = select(AlertRule).where(
        and_(
            AlertRule.id == rule_id,
            AlertRule.tenant_id == current_user.tenant_id
        )
    )
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    
    return rule


@router.put("/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: int,
    rule_data: AlertRuleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新告警规则"""
    stmt = select(AlertRule).where(
        and_(
            AlertRule.id == rule_id,
            AlertRule.tenant_id == current_user.tenant_id
        )
    )
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    
    for key, value in rule_data.dict(exclude_unset=True).items():
        setattr(rule, key, value)
    
    await db.commit()
    await db.refresh(rule)
    
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除告警规则"""
    from sqlalchemy import text
    from loguru import logger
    
    stmt = select(AlertRule).where(
        and_(
            AlertRule.id == rule_id,
            AlertRule.tenant_id == current_user.tenant_id
        )
    )
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    
    try:
        # 方法1：手动清理关联数据（兼容旧数据库）
        # 删除告警规则通知渠道关联
        try:
            await db.execute(
                text("DELETE FROM alert_rule_notification_channels WHERE alert_rule_id = :rule_id"),
                {"rule_id": rule_id}
            )
        except Exception as e:
            logger.warning(f"清理关联表失败（可能不存在）: {e}")
        
        # 删除告警规则（如果外键正确配置，会自动级联删除 alert_event）
        await db.delete(rule)
        await db.commit()
        
        logger.info(f"成功删除告警规则: id={rule_id}, name={rule.name}")
        
    except Exception as e:
        await db.rollback()
        logger.error(f"删除告警规则失败: id={rule_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.get("/events/current", response_model=List[AlertEventResponse])
async def list_current_alerts(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前告警列表（平铺）- 不包含已恢复的告警"""
    stmt = select(AlertEvent).where(
        and_(
            AlertEvent.tenant_id == current_user.tenant_id,
            AlertEvent.status.in_(['pending', 'firing'])  # 只显示 pending 和 firing
        )
    ).offset(skip).limit(limit)
    
    result = await db.execute(stmt)
    events = result.scalars().all()
    
    return events


@router.get("/events/current/grouped")
async def list_current_alerts_grouped(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页分组数"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """获取按规则名称分组的当前告警列表 - 不包含已恢复的告警"""
    # 1. 获取所有当前告警（只包含 pending 和 firing 状态）
    stmt = select(AlertEvent).where(
        and_(
            AlertEvent.tenant_id == current_user.tenant_id,
            AlertEvent.status.in_(['pending', 'firing'])  # 只显示 pending 和 firing
        )
    ).order_by(AlertEvent.started_at.desc())
    
    result = await db.execute(stmt)
    all_events = result.scalars().all()
    
    # 2. 按规则名称分组
    groups = {}
    for event in all_events:
        rule_name = event.rule_name
        if rule_name not in groups:
            groups[rule_name] = {
                "rule_name": rule_name,
                "rule_id": event.rule_id,
                "count": 0,
                "severity": event.severity,
                "status": event.status,
                "latest_started_at": event.started_at,
                "alerts": []
            }
        
        groups[rule_name]["count"] += 1
        groups[rule_name]["alerts"].append({
            "id": event.id,
            "fingerprint": event.fingerprint,
            "rule_name": event.rule_name,
            "rule_id": event.rule_id,
            "status": event.status,
            "severity": event.severity,
            "started_at": event.started_at,
            "last_eval_at": event.last_eval_at,
            "last_sent_at": event.last_sent_at,
            "value": event.value,
            "labels": event.labels,
            "annotations": event.annotations,
            "expr": event.expr
        })
        
        # 更新最新触发时间和状态
        if event.started_at > groups[rule_name]["latest_started_at"]:
            groups[rule_name]["latest_started_at"] = event.started_at
            groups[rule_name]["severity"] = event.severity
            groups[rule_name]["status"] = event.status
    
    # 3. 转换为列表并按最新触发时间排序
    grouped_list = sorted(
        groups.values(),
        key=lambda x: x["latest_started_at"],
        reverse=True
    )
    
    # 4. 分页
    total = len(grouped_list)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_groups = grouped_list[start_idx:end_idx]
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        "groups": paginated_groups
    }


@router.get("/events/history", response_model=List[AlertEventHistoryResponse])
async def list_alert_history(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取历史告警列表（平铺）"""
    stmt = select(AlertEventHistory).where(
        AlertEventHistory.tenant_id == current_user.tenant_id
    ).offset(skip).limit(limit).order_by(AlertEventHistory.resolved_at.desc())
    
    result = await db.execute(stmt)
    events = result.scalars().all()
    
    return events


@router.get("/events/history/grouped")
async def list_alert_history_grouped(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页分组数"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """获取按规则名称分组的历史告警列表"""
    # 1. 获取所有历史告警
    stmt = select(AlertEventHistory).where(
        AlertEventHistory.tenant_id == current_user.tenant_id
    ).order_by(AlertEventHistory.resolved_at.desc())
    
    result = await db.execute(stmt)
    all_events = result.scalars().all()
    
    # 2. 按规则名称分组
    groups = {}
    for event in all_events:
        rule_name = event.rule_name
        if rule_name not in groups:
            groups[rule_name] = {
                "rule_name": rule_name,
                "rule_id": event.rule_id,
                "count": 0,
                "severity": event.severity,
                "latest_resolved_at": event.resolved_at,
                "total_duration": 0,
                "alerts": []
            }
        
        groups[rule_name]["count"] += 1
        groups[rule_name]["total_duration"] += event.duration
        groups[rule_name]["alerts"].append({
            "id": event.id,
            "fingerprint": event.fingerprint,
            "rule_name": event.rule_name,
            "rule_id": event.rule_id,
            "status": event.status,
            "severity": event.severity,
            "started_at": event.started_at,
            "resolved_at": event.resolved_at,
            "duration": event.duration,
            "value": event.value,
            "labels": event.labels,
            "annotations": event.annotations,
            "expr": event.expr
        })
        
        # 更新最新恢复时间和等级
        if event.resolved_at > groups[rule_name]["latest_resolved_at"]:
            groups[rule_name]["latest_resolved_at"] = event.resolved_at
            groups[rule_name]["severity"] = event.severity
    
    # 3. 计算平均持续时间
    for group in groups.values():
        if group["count"] > 0:
            group["avg_duration"] = group["total_duration"] // group["count"]
    
    # 4. 转换为列表并按最新恢复时间排序
    grouped_list = sorted(
        groups.values(),
        key=lambda x: x["latest_resolved_at"],
        reverse=True
    )
    
    # 5. 分页
    total = len(grouped_list)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_groups = grouped_list[start_idx:end_idx]
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        "groups": paginated_groups
    }


@router.get("/grouping/stats")
async def get_grouping_stats(
    current_user: User = Depends(get_current_user)
):
    """获取告警分组统计信息"""
    from app.main import alert_manager
    
    if not alert_manager:
        raise HTTPException(status_code=503, detail="Alert manager not initialized")
    
    stats = alert_manager.get_grouping_stats()
    return stats
