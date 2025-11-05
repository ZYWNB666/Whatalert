"""基于 Redis 的分布式告警分组器"""
import json
import time
from typing import List, Dict, Optional
from loguru import logger
import redis.asyncio as redis
from app.models.alert import AlertEvent, AlertRule


class RedisAlertGrouper:
    """Redis 分布式告警分组器"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.group_wait = 10  # 分组等待时间（秒）
        self.group_interval = 30  # 分组间隔时间（秒）
        self.repeat_interval = 3600  # 重复发送间隔（秒）
        
        # Redis 键前缀
        self.firing_prefix = "alert:group:firing"
        self.recovery_prefix = "alert:group:recovery"
    
    def _get_group_key(self, group_key: str, is_recovery: bool = False) -> str:
        """生成分组 Redis 键"""
        prefix = self.recovery_prefix if is_recovery else self.firing_prefix
        return f"{prefix}:{group_key}"
    
    def _generate_group_key(self, alert: AlertEvent, rule: AlertRule) -> tuple:
        """
        生成分组键
        
        返回: (group_key, group_labels)
        """
        group_by = rule.route_config.get('group_by', [])
        
        group_parts = [f"rule:{rule.name}"]
        group_labels = {"alertname": rule.name}
        
        for label_key in group_by:
            label_value = alert.labels.get(label_key, "")
            if label_value:
                group_parts.append(f"{label_key}:{label_value}")
                group_labels[label_key] = label_value
        
        group_key = "|".join(group_parts)
        return group_key, group_labels
    
    async def add_alert(self, alert: AlertEvent, rule: AlertRule) -> str:
        """
        添加告警到分组
        
        返回: group_key
        """
        group_key, group_labels = self._generate_group_key(alert, rule)
        redis_key = self._get_group_key(group_key, is_recovery=False)
        
        # 获取现有分组数据
        group_data = await self.redis.get(redis_key)
        current_time = time.time()
        
        if group_data:
            group = json.loads(group_data)
        else:
            # 创建新分组
            group = {
                "group_key": group_key,
                "group_labels": group_labels,
                "rule_id": rule.id,
                "rule_name": rule.name,
                "alerts": [],
                "created_at": current_time,
                "last_updated_at": current_time,
                "sent": False
            }
            logger.info(f"创建新的告警分组: {group_key}")
        
        # 添加告警（避免重复）
        alert_fingerprints = {a["fingerprint"] for a in group["alerts"]}
        if alert.fingerprint not in alert_fingerprints:
            group["alerts"].append({
                "fingerprint": alert.fingerprint,
                "rule_name": alert.rule_name,
                "severity": alert.severity,
                "value": alert.value,
                "labels": alert.labels,
                "annotations": alert.annotations,
                "started_at": alert.started_at,
                "expr": alert.expr,
                "tenant_id": alert.tenant_id
            })
            group["last_updated_at"] = current_time
            
            # 保存到 Redis（设置过期时间为 2 小时）
            await self.redis.setex(redis_key, 7200, json.dumps(group))
            logger.debug(f"告警添加到分组: {group_key}, 当前告警数: {len(group['alerts'])}")
        
        return group_key
    
    async def add_recovery_alert(self, alert: AlertEvent, rule: AlertRule) -> str:
        """
        添加恢复告警到分组
        
        返回: group_key
        """
        group_key, group_labels = self._generate_group_key(alert, rule)
        recovery_key = f"recovery:{group_key}"
        redis_key = self._get_group_key(recovery_key, is_recovery=True)
        
        # 获取现有分组数据
        group_data = await self.redis.get(redis_key)
        current_time = time.time()
        
        if group_data:
            group = json.loads(group_data)
        else:
            # 创建新恢复分组
            group = {
                "group_key": recovery_key,
                "group_labels": group_labels,
                "rule_id": rule.id,
                "rule_name": rule.name,
                "alerts": [],
                "created_at": current_time,
                "last_updated_at": current_time,
                "sent": False
            }
            logger.info(f"创建新的恢复告警分组: {recovery_key}")
        
        # 添加恢复告警
        alert_fingerprints = {a["fingerprint"] for a in group["alerts"]}
        if alert.fingerprint not in alert_fingerprints:
            group["alerts"].append({
                "fingerprint": alert.fingerprint,
                "rule_name": alert.rule_name,
                "severity": alert.severity,
                "value": alert.value,
                "labels": alert.labels,
                "annotations": alert.annotations,
                "started_at": alert.started_at,
                "expr": alert.expr,
                "tenant_id": alert.tenant_id
            })
            group["last_updated_at"] = current_time
            
            await self.redis.setex(redis_key, 7200, json.dumps(group))
            logger.debug(f"恢复告警添加到分组: {recovery_key}, 当前告警数: {len(group['alerts'])}")
        
        return recovery_key
    
    async def get_ready_groups(self) -> List[tuple]:
        """
        获取准备好发送的分组
        
        返回: List[tuple(group_data, is_recovery)]
        """
        ready_groups = []
        current_time = time.time()
        
        # 检查 firing 分组
        async for key in self.redis.scan_iter(match=f"{self.firing_prefix}:*", count=100):
            group_data = await self.redis.get(key)
            if group_data:
                group = json.loads(group_data)
                if self._is_group_ready(group, current_time):
                    ready_groups.append((group, False))
                    logger.info(f"✅ firing 分组等待时间已到: {group['group_key']}, 告警数: {len(group['alerts'])}")
        
        # 检查 recovery 分组
        async for key in self.redis.scan_iter(match=f"{self.recovery_prefix}:*", count=100):
            group_data = await self.redis.get(key)
            if group_data:
                group = json.loads(group_data)
                if self._is_group_ready(group, current_time):
                    ready_groups.append((group, True))
                    logger.info(f"✅ recovery 分组等待时间已到: {group['group_key']}, 告警数: {len(group['alerts'])}")
        
        return ready_groups
    
    def _is_group_ready(self, group: dict, current_time: float) -> bool:
        """检查分组是否准备好发送"""
        if not group.get("alerts"):
            return False
        
        if group.get("sent"):
            # 检查是否需要重复发送
            if (current_time - group["last_updated_at"]) >= self.repeat_interval:
                return True
            return False
        
        # 检查等待时间
        wait_time = current_time - group["created_at"]
        return wait_time >= self.group_wait
    
    async def mark_group_sent(self, group_key: str, is_recovery: bool = False):
        """标记分组为已发送"""
        redis_key = self._get_group_key(group_key, is_recovery)
        group_data = await self.redis.get(redis_key)
        
        if group_data:
            group = json.loads(group_data)
            group["sent"] = True
            await self.redis.setex(redis_key, 7200, json.dumps(group))
    
    async def clear_sent_group(self, group_key: str, is_recovery: bool = False):
        """清除已发送的分组"""
        redis_key = self._get_group_key(group_key, is_recovery)
        await self.redis.delete(redis_key)
        logger.debug(f"清除已发送分组: {group_key}")
    
    async def remove_alert_from_groups(self, fingerprint: str):
        """从所有分组中移除指定的告警"""
        # 扫描所有 firing 分组
        async for key in self.redis.scan_iter(match=f"{self.firing_prefix}:*", count=100):
            group_data = await self.redis.get(key)
            if group_data:
                group = json.loads(group_data)
                original_count = len(group["alerts"])
                group["alerts"] = [a for a in group["alerts"] if a["fingerprint"] != fingerprint]
                
                if len(group["alerts"]) < original_count:
                    if group["alerts"]:
                        await self.redis.setex(key, 7200, json.dumps(group))
                    else:
                        await self.redis.delete(key)
    
    async def get_group_stats(self) -> Dict[str, int]:
        """获取分组统计信息"""
        firing_count = 0
        recovery_count = 0
        total_alerts = 0
        sent_count = 0
        pending_count = 0
        
        # 统计 firing 分组
        async for key in self.redis.scan_iter(match=f"{self.firing_prefix}:*", count=100):
            firing_count += 1
            group_data = await self.redis.get(key)
            if group_data:
                group = json.loads(group_data)
                total_alerts += len(group["alerts"])
                if group.get("sent"):
                    sent_count += 1
                else:
                    pending_count += 1
        
        # 统计 recovery 分组
        async for key in self.redis.scan_iter(match=f"{self.recovery_prefix}:*", count=100):
            recovery_count += 1
            group_data = await self.redis.get(key)
            if group_data:
                group = json.loads(group_data)
                total_alerts += len(group["alerts"])
                if group.get("sent"):
                    sent_count += 1
                else:
                    pending_count += 1
        
        return {
            "total_groups": firing_count + recovery_count,
            "firing_groups": firing_count,
            "recovery_groups": recovery_count,
            "total_alerts": total_alerts,
            "sent_groups": sent_count,
            "pending_groups": pending_count
        }
    
    def configure(
        self, 
        group_wait: int = 10, 
        group_interval: int = 30, 
        repeat_interval: int = 3600
    ):
        """配置分组参数"""
        self.group_wait = group_wait
        self.group_interval = group_interval
        self.repeat_interval = repeat_interval
        logger.info(
            f"Redis告警分组器配置: group_wait={group_wait}s, "
            f"group_interval={group_interval}s, repeat_interval={repeat_interval}s"
        )

