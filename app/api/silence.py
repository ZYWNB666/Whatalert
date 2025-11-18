"""静默规则 API"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.db.database import get_db
from app.models.silence import SilenceRule
from app.models.alert import AlertEvent
from app.models.user import User
from app.api.auth import get_current_user
from app.services.silence_matcher import validate_matchers, check_silence_match
from app.services.cache_service import CacheService
import time

router = APIRouter()


@router.post("/", status_code=201)
async def create_silence_rule(
    rule_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建静默规则"""
    # 验证 matchers
    matchers = rule_data.get('matchers', [])
    is_valid, error_msg = validate_matchers(matchers)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"matchers 配置无效: {error_msg}")
    
    # 提取 project_id（如果有）
    project_id = rule_data.get('project_id')
    
    # 创建静默规则
    new_rule = SilenceRule(
        name=rule_data.get('name'),
        description=rule_data.get('description'),
        matchers=matchers,
        starts_at=rule_data.get('starts_at'),
        ends_at=rule_data.get('ends_at'),
        is_enabled=rule_data.get('is_enabled', True),
        comment=rule_data.get('comment'),
        tenant_id=current_user.tenant_id,
        project_id=project_id,
        created_by=current_user.username
    )
    
    db.add(new_rule)
    await db.commit()
    await db.refresh(new_rule)
    
    # 清除缓存
    await CacheService.delete_pattern(f"silence:list:tenant:{current_user.tenant_id}:*")
    
    return new_rule.to_dict()


@router.get("/")
async def list_silence_rules(
    project_id: int = Query(None, description="项目ID,不传则显示所有项目"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取静默规则列表 - 带动态缓存"""
    # 生成缓存键
    cache_key = f"silence:list:tenant:{current_user.tenant_id}"
    if project_id is not None:
        cache_key += f":project:{project_id}"
    
    # 尝试从缓存获取（30秒TTL，静默规则变化较频繁）
    cached_data = await CacheService.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    conditions = [SilenceRule.tenant_id == current_user.tenant_id]
    if project_id is not None:
        conditions.append(SilenceRule.project_id == project_id)
    
    stmt = select(SilenceRule).where(and_(*conditions))
    result = await db.execute(stmt)
    rules = result.scalars().all()
    
    rules_data = [rule.to_dict() for rule in rules]
    
    # 存入缓存（30秒TTL）
    await CacheService.set(cache_key, rules_data, 30)
    
    return rules_data


@router.put("/{rule_id}")
async def update_silence_rule(
    rule_id: int,
    rule_data: dict,
    project_id: int = Query(None, description="项目ID,不传则不校验项目"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新静默规则"""
    conditions = [
        SilenceRule.id == rule_id,
        SilenceRule.tenant_id == current_user.tenant_id
    ]
    if project_id is not None:
        conditions.append(SilenceRule.project_id == project_id)
    
    stmt = select(SilenceRule).where(and_(*conditions))
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Silence rule not found")
    
    # 验证 matchers（如果提供）
    if 'matchers' in rule_data:
        is_valid, error_msg = validate_matchers(rule_data['matchers'])
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"matchers 配置无效: {error_msg}")
    
    # 更新规则
    for key, value in rule_data.items():
        setattr(rule, key, value)
    
    await db.commit()
    await db.refresh(rule)
    
    # 清除缓存
    await CacheService.delete_pattern(f"silence:list:tenant:{current_user.tenant_id}:*")
    await CacheService.delete(f"silence:detail:{rule_id}")
    
    return rule.to_dict()


@router.delete("/{rule_id}")
async def delete_silence_rule(
    rule_id: int,
    project_id: int = Query(None, description="项目ID,不传则不校验项目"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除静默规则"""
    conditions = [
        SilenceRule.id == rule_id,
        SilenceRule.tenant_id == current_user.tenant_id
    ]
    if project_id is not None:
        conditions.append(SilenceRule.project_id == project_id)
    
    stmt = select(SilenceRule).where(and_(*conditions))
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Silence rule not found")
    
    await db.delete(rule)
    await db.commit()
    
    # 清除缓存
    await CacheService.delete_pattern(f"silence:list:tenant:{current_user.tenant_id}:*")
    await CacheService.delete(f"silence:detail:{rule_id}")
    
    return {"message": "Silence rule deleted"}


@router.get("/{rule_id}/silenced-alerts")
async def get_silenced_alerts(
    rule_id: int,
    project_id: int = Query(None, description="项目ID,不传则不校验项目"),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取被该静默规则匹配的告警列表"""
    # 查询静默规则
    conditions = [
        SilenceRule.id == rule_id,
        SilenceRule.tenant_id == current_user.tenant_id
    ]
    if project_id is not None:
        conditions.append(SilenceRule.project_id == project_id)
    
    stmt = select(SilenceRule).where(and_(*conditions))
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Silence rule not found")
    
    # 检查规则是否在有效期内
    current_time = int(time.time())
    is_active = rule.is_enabled and rule.starts_at <= current_time <= rule.ends_at
    
    # 查询当前所有 firing 和 pending 状态的告警
    alert_conditions = [
        AlertEvent.tenant_id == current_user.tenant_id,
        AlertEvent.status.in_(['pending', 'firing'])
    ]
    if project_id is not None:
        alert_conditions.append(AlertEvent.project_id == project_id)
    
    stmt = select(AlertEvent).where(and_(*alert_conditions)).offset(skip).limit(limit)
    result = await db.execute(stmt)
    all_alerts = result.scalars().all()
    
    # 过滤出被该规则匹配的告警
    silenced_alerts = []
    for alert in all_alerts:
        if check_silence_match(alert.labels, rule.matchers):
            silenced_alerts.append({
                "id": alert.id,
                "fingerprint": alert.fingerprint,
                "rule_id": alert.rule_id,
                "rule_name": alert.rule_name,
                "status": alert.status,
                "severity": alert.severity,
                "started_at": alert.started_at,
                "last_eval_at": alert.last_eval_at,
                "value": alert.value,
                "labels": alert.labels,
                "annotations": alert.annotations,
                "is_silence_active": is_active  # 标记静默规则当前是否生效
            })
    
    return {
        "silence_rule": {
            "id": rule.id,
            "name": rule.name,
            "is_enabled": rule.is_enabled,
            "is_active": is_active,
            "starts_at": rule.starts_at,
            "ends_at": rule.ends_at
        },
        "total": len(silenced_alerts),
        "alerts": silenced_alerts
    }

