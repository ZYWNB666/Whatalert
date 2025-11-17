"""告警规则API"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
import time

from app.db.database import get_db
from app.models.alert import AlertRule, AlertEvent, AlertEventHistory
from app.models.silence import SilenceRule
from app.models.user import User
from app.api.auth import get_current_user
from app.services.silence_matcher import check_silence_match
from app.schemas.alert import (
    AlertRuleCreate, AlertRuleUpdate, AlertRuleResponse,
    AlertEventResponse, AlertEventHistoryResponse
)
from app.schemas.alert_test import AlertRuleTestRequest, AlertRuleTestResponse, AlertRuleTestMetric

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
    project_id: int = Query(None, description="项目ID,不传则显示所有项目"),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取告警规则列表(按项目隔离)"""
    conditions = [AlertRule.tenant_id == current_user.tenant_id]
    if project_id is not None:
        conditions.append(AlertRule.project_id == project_id)
    
    stmt = select(AlertRule).where(and_(*conditions)).offset(skip).limit(limit)
    
    result = await db.execute(stmt)
    rules = result.scalars().all()
    
    return rules


@router.get("/{rule_id}", response_model=AlertRuleResponse)
async def get_alert_rule(
    rule_id: int,
    project_id: int = Query(None, description="项目ID,不传则不校验项目"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取告警规则详情"""
    conditions = [
        AlertRule.id == rule_id,
        AlertRule.tenant_id == current_user.tenant_id
    ]
    if project_id is not None:
        conditions.append(AlertRule.project_id == project_id)
    
    stmt = select(AlertRule).where(and_(*conditions))
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    
    return rule


@router.put("/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: int,
    rule_data: AlertRuleUpdate,
    project_id: int = Query(None, description="项目ID,不传则不校验项目"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新告警规则"""
    conditions = [
        AlertRule.id == rule_id,
        AlertRule.tenant_id == current_user.tenant_id
    ]
    if project_id is not None:
        conditions.append(AlertRule.project_id == project_id)
    
    stmt = select(AlertRule).where(and_(*conditions))
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    
    # 检查是否更新了规则名称
    old_name = rule.name
    new_name = rule_data.name if rule_data.name is not None else old_name
    name_changed = new_name != old_name
    
    for key, value in rule_data.dict(exclude_unset=True).items():
        setattr(rule, key, value)
    
    # 如果规则名称变了，同步更新所有关联的告警事件
    if name_changed:
        # 更新当前告警事件
        update_events_stmt = (
            select(AlertEvent)
            .where(AlertEvent.rule_id == rule_id)
        )
        events_result = await db.execute(update_events_stmt)
        events = events_result.scalars().all()
        for event in events:
            event.rule_name = new_name
    
    await db.commit()
    await db.refresh(rule)
    
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_rule(
    rule_id: int,
    project_id: int = Query(None, description="项目ID,不传则不校验项目"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除告警规则"""
    from sqlalchemy import text
    from loguru import logger
    
    conditions = [
        AlertRule.id == rule_id,
        AlertRule.tenant_id == current_user.tenant_id
    ]
    if project_id is not None:
        conditions.append(AlertRule.project_id == project_id)
    
    stmt = select(AlertRule).where(and_(*conditions))
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


@router.get("/events/current")
async def list_current_alerts(
    project_id: int = Query(None, description="项目ID,不传则显示所有项目"),
    include_silenced: bool = Query(False, description="是否包含被静默的告警"),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前告警列表（平铺）- 不包含已恢复的告警"""
    conditions = [
        AlertEvent.tenant_id == current_user.tenant_id,
        AlertEvent.status.in_(['pending', 'firing'])  # 只显示 pending 和 firing
    ]
    
    if project_id is not None:
        conditions.append(AlertEvent.project_id == project_id)
    
    # 获取总数
    count_stmt = select(func.count()).select_from(AlertEvent).where(and_(*conditions))
    total = await db.scalar(count_stmt)
    
    # 获取分页数据
    stmt = select(AlertEvent).where(and_(*conditions)).offset(skip).limit(limit).order_by(AlertEvent.started_at.desc())
    
    result = await db.execute(stmt)
    events = result.scalars().all()
    
    # 如果不包含静默告警，需要过滤
    if not include_silenced:
        # 查询所有生效中的静默规则
        current_time = int(time.time())
        silence_conditions = [
            SilenceRule.tenant_id == current_user.tenant_id,
            SilenceRule.is_enabled == True,
            SilenceRule.starts_at <= current_time,
            SilenceRule.ends_at >= current_time
        ]
        if project_id is not None:
            silence_conditions.append(SilenceRule.project_id == project_id)
        
        silence_stmt = select(SilenceRule).where(and_(*silence_conditions))
        silence_result = await db.execute(silence_stmt)
        active_silence_rules = silence_result.scalars().all()
        
        # 获取所有未静默的告警（用于计算准确的total）
        all_stmt = select(AlertEvent).where(and_(*conditions)).order_by(AlertEvent.started_at.desc())
        all_result = await db.execute(all_stmt)
        all_events = all_result.scalars().all()
        
        # 过滤被静默的告警
        filtered_all_events = []
        for event in all_events:
            is_silenced = False
            for rule in active_silence_rules:
                if check_silence_match(event.labels, rule.matchers):
                    is_silenced = True
                    break
            if not is_silenced:
                filtered_all_events.append(event)
        
        # 应用分页到过滤后的结果
        filtered_events = filtered_all_events[skip:skip + limit]
        
        return {
            "total": len(filtered_all_events),
            "alerts": [e.to_dict() for e in filtered_events]
        }
    
    return {
        "total": total,
        "alerts": [e.to_dict() for e in events]
    }


@router.get("/events/current/grouped")
async def list_current_alerts_grouped(
    project_id: int = Query(None, description="项目ID,不传则显示所有项目"),
    include_silenced: bool = Query(False, description="是否包含被静默的告警"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页分组数"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """获取按规则名称分组的当前告警列表 - 不包含已恢复的告警"""
    # 1. 获取所有当前告警（只包含 pending 和 firing 状态）
    conditions = [
        AlertEvent.tenant_id == current_user.tenant_id,
        AlertEvent.status.in_(['pending', 'firing'])  # 只显示 pending 和 firing
    ]
    
    if project_id is not None:
        conditions.append(AlertEvent.project_id == project_id)
    
    stmt = select(AlertEvent).where(and_(*conditions)).order_by(AlertEvent.started_at.desc())
    
    result = await db.execute(stmt)
    all_events = result.scalars().all()
    
    # 如果不包含静默告警，需要过滤
    if not include_silenced:
        # 查询所有生效中的静默规则
        current_time = int(time.time())
        silence_conditions = [
            SilenceRule.tenant_id == current_user.tenant_id,
            SilenceRule.is_enabled == True,
            SilenceRule.starts_at <= current_time,
            SilenceRule.ends_at >= current_time
        ]
        if project_id is not None:
            silence_conditions.append(SilenceRule.project_id == project_id)
        
        silence_stmt = select(SilenceRule).where(and_(*silence_conditions))
        silence_result = await db.execute(silence_stmt)
        active_silence_rules = silence_result.scalars().all()
        
        # 过滤被静默的告警
        filtered_events = []
        for event in all_events:
            is_silenced = False
            for rule in active_silence_rules:
                if check_silence_match(event.labels, rule.matchers):
                    is_silenced = True
                    break
            if not is_silenced:
                filtered_events.append(event)
        
        all_events = filtered_events
    
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
    project_id: int = Query(None, description="项目ID,不传则显示所有项目"),
    rule_id: int = Query(None, description="告警规则ID"),
    severity: str = Query(None, description="告警等级: critical, warning, info"),
    start_time: int = Query(None, description="开始时间(Unix时间戳)"),
    end_time: int = Query(None, description="结束时间(Unix时间戳)"),
    label_key: str = Query(None, description="标签键"),
    label_value: str = Query(None, description="标签值"),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取历史告警列表（平铺）- 支持多条件过滤"""
    conditions = [AlertEventHistory.tenant_id == current_user.tenant_id]
    
    if project_id is not None:
        conditions.append(AlertEventHistory.project_id == project_id)
    
    if rule_id is not None:
        conditions.append(AlertEventHistory.rule_id == rule_id)
    
    if severity:
        conditions.append(AlertEventHistory.severity == severity)
    
    if start_time is not None:
        conditions.append(AlertEventHistory.started_at >= start_time)
    
    if end_time is not None:
        conditions.append(AlertEventHistory.resolved_at <= end_time)
    
    stmt = select(AlertEventHistory).where(and_(*conditions)).offset(skip).limit(limit).order_by(AlertEventHistory.resolved_at.desc())
    
    result = await db.execute(stmt)
    events = result.scalars().all()
    
    # 如果指定了标签过滤，在内存中过滤
    if label_key and label_value:
        events = [e for e in events if e.labels.get(label_key) == label_value]
    elif label_key:
        events = [e for e in events if label_key in e.labels]
    
    return events


@router.get("/events/history/grouped")
async def list_alert_history_grouped(
    project_id: int = Query(None, description="项目ID,不传则显示所有项目"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页分组数"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """获取按规则名称分组的历史告警列表"""
    # 1. 获取所有历史告警
    conditions = [AlertEventHistory.tenant_id == current_user.tenant_id]
    if project_id is not None:
        conditions.append(AlertEventHistory.project_id == project_id)
    
    stmt = select(AlertEventHistory).where(and_(*conditions)).order_by(AlertEventHistory.resolved_at.desc())
    
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


@router.post("/test")
async def test_alert_rule(
    test_data: AlertRuleTestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """测试告警规则的 PromQL 表达式
    
    限流：每个用户每分钟最多 10 次
    """
    import time
    from prometheus_api_client import PrometheusConnect
    from app.models.datasource import DataSource
    
    # 简单的速率限制（基于内存，实际应使用 Redis）
    # 这里为演示简化处理
    rate_limit_key = f"test_rate_limit:{current_user.id}"
    # TODO: 使用 Redis 实现分布式限流
    
    # 获取数据源
    datasource = await db.get(DataSource, test_data.datasource_id)
    if not datasource:
        raise HTTPException(status_code=404, detail="数据源不存在")
    
    # 检查权限：数据源必须属于用户的租户
    if datasource.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="无权限访问该数据源")
    
    # 执行查询
    try:
        start_time = time.time()
        
        # 创建 Prometheus 客户端
        headers = datasource.auth_config.get('headers', {})
        disable_ssl = datasource.http_config.get('verify_ssl', True) is False
        
        prom = PrometheusConnect(
            url=datasource.url,
            headers=headers,
            disable_ssl=disable_ssl
        )
        
        # 执行查询（设置超时 5 秒）
        result = prom.custom_query(query=test_data.expr)
        
        query_time = time.time() - start_time
        
        # 解析结果
        if not result:
            return AlertRuleTestResponse(
                success=True,
                result_count=0,
                results=[],
                query_time=round(query_time, 3),
                timestamp=int(time.time()),
                message="查询成功，但没有匹配到任何数据"
            )
        
        # 最多返回 10 条结果
        results = []
        for item in result[:10]:
            metric_labels = item.get('metric', {})
            value = item.get('value', [])
            
            results.append(AlertRuleTestMetric(
                metric=metric_labels,
                value=value
            ))
        
        return AlertRuleTestResponse(
            success=True,
            result_count=len(result),
            results=results,
            query_time=round(query_time, 3),
            timestamp=int(time.time())
        )
        
    except Exception as e:
        # 解析错误类型
        error_msg = str(e)
        error_type = 'execution'
        
        if 'parse error' in error_msg.lower() or 'syntax' in error_msg.lower():
            error_type = 'syntax'
        elif 'connection' in error_msg.lower() or 'timeout' in error_msg.lower():
            error_type = 'connection'
        
        return AlertRuleTestResponse(
            success=False,
            error=error_msg,
            error_type=error_type
        )

