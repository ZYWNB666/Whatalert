"""告警分组器 - 实现类似 Alertmanager 的告警合并功能"""
import asyncio
import time
from typing import Dict, List, Set, Optional
from collections import defaultdict
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.alert import AlertEvent, AlertRule


class AlertGroup:
    """告警分组"""
    
    def __init__(self, group_key: str, group_labels: Dict[str, str]):
        self.group_key = group_key
        self.group_labels = group_labels
        self.alerts: List[AlertEvent] = []
        self.rule: Optional[AlertRule] = None
        self.created_at = time.time()
        self.last_updated_at = time.time()
        self.sent = False
    
    def add_alert(self, alert: AlertEvent):
        """添加告警到组"""
        self.alerts.append(alert)
        self.last_updated_at = time.time()
    
    def get_alerts(self) -> List[AlertEvent]:
        """获取组内所有告警"""
        return self.alerts
    
    def mark_sent(self):
        """标记为已发送"""
        self.sent = True


class AlertGrouper:
    """告警分组器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.groups: Dict[str, AlertGroup] = {}  # firing 告警分组
        self.recovery_groups: Dict[str, AlertGroup] = {}  # resolved 告警分组
        self.group_wait = 10  # 分组等待时间（秒）
        self.group_interval = 30  # 分组间隔时间（秒）
        self.repeat_interval = 3600  # 重复发送间隔（秒）
        self._lock = asyncio.Lock()
    
    def _generate_group_key(
        self, 
        alert: AlertEvent, 
        rule: AlertRule
    ) -> tuple:
        """
        生成分组键
        
        分组规则：
        1. 相同规则名称
        2. group_by 指定的 labels 相同
        
        返回: (group_key, group_labels)
        """
        # 获取分组配置
        group_by = rule.route_config.get('group_by', [])
        
        # 默认按规则名称分组
        group_parts = [f"rule:{rule.name}"]
        group_labels = {"alertname": rule.name}
        
        # 添加指定的 labels 到分组键
        for label_key in group_by:
            label_value = alert.labels.get(label_key, "")
            if label_value:
                group_parts.append(f"{label_key}:{label_value}")
                group_labels[label_key] = label_value
        
        # 生成分组键
        group_key = "|".join(group_parts)
        
        return group_key, group_labels
    
    async def add_alert(self, alert: AlertEvent, rule: AlertRule) -> str:
        """
        添加告警到分组
        
        返回: group_key
        """
        async with self._lock:
            group_key, group_labels = self._generate_group_key(alert, rule)
            
            # 检查是否已存在该分组
            if group_key not in self.groups:
                # 创建新分组
                group = AlertGroup(group_key, group_labels)
                group.rule = rule
                self.groups[group_key] = group
                logger.info(f"创建新的告警分组: {group_key}")
            else:
                group = self.groups[group_key]
            
            # 添加告警到分组
            group.add_alert(alert)
            logger.debug(f"告警添加到分组: {group_key}, 当前告警数: {len(group.alerts)}")
            
            return group_key
    
    async def add_recovery_alert(self, alert: AlertEvent, rule: AlertRule) -> str:
        """
        添加恢复告警到分组
        
        返回: group_key
        """
        async with self._lock:
            group_key, group_labels = self._generate_group_key(alert, rule)
            # 恢复告警使用单独的 key
            recovery_key = f"recovery:{group_key}"
            
            # 检查是否已存在该恢复分组
            if recovery_key not in self.recovery_groups:
                # 创建新恢复分组
                group = AlertGroup(recovery_key, group_labels)
                group.rule = rule
                self.recovery_groups[recovery_key] = group
                logger.info(f"创建新的恢复告警分组: {recovery_key}")
            else:
                group = self.recovery_groups[recovery_key]
            
            # 添加恢复告警到分组
            group.add_alert(alert)
            logger.debug(f"恢复告警添加到分组: {recovery_key}, 当前告警数: {len(group.alerts)}")
            
            return recovery_key
    
    async def get_ready_groups(self) -> List[tuple]:
        """
        获取准备好发送的分组
        
        返回: List[tuple(group, is_recovery)]
        """
        async with self._lock:
            ready_groups = []
            current_time = time.time()
            
            logger.debug(f"🔍 检查分组: firing={len(self.groups)}, recovery={len(self.recovery_groups)}")
            
            # 检查 firing 告警分组
            for group_key, group in list(self.groups.items()):
                wait_time = current_time - group.created_at
                logger.debug(f"🔍 检查firing分组 {group_key}: wait_time={wait_time:.1f}s, group_wait={self.group_wait}s, sent={group.sent}")
                if self._is_group_ready(group, current_time):
                    ready_groups.append((group, False))
                    logger.info(f"✅ firing 分组等待时间已到: {group_key}, 告警数: {len(group.alerts)}")
            
            # 检查 recovery 告警分组
            for group_key, group in list(self.recovery_groups.items()):
                wait_time = current_time - group.created_at
                logger.debug(f"🔍 检查recovery分组 {group_key}: wait_time={wait_time:.1f}s, group_wait={self.group_wait}s, sent={group.sent}")
                if self._is_group_ready(group, current_time):
                    ready_groups.append((group, True))
                    logger.info(f"✅ recovery 分组等待时间已到: {group_key}, 告警数: {len(group.alerts)}")
            
            return ready_groups
    
    def _is_group_ready(self, group: AlertGroup, current_time: float) -> bool:
        """检查分组是否准备好发送"""
        # 跳过空分组
        if not group.alerts:
            return False
        
        # 检查是否已发送
        if group.sent:
            # 检查是否需要重复发送
            if (current_time - group.last_updated_at) >= self.repeat_interval:
                logger.debug(f"分组达到重复发送间隔: {group.group_key}")
                return True
            return False
        
        # 检查等待时间
        wait_time = current_time - group.created_at
        return wait_time >= self.group_wait
    
    async def clear_sent_group(self, group_key: str, is_recovery: bool = False):
        """清除已发送的分组"""
        async with self._lock:
            groups_dict = self.recovery_groups if is_recovery else self.groups
            if group_key in groups_dict:
                del groups_dict[group_key]
                logger.debug(f"清除已发送分组: {group_key}")
    
    async def remove_alert_from_groups(self, fingerprint: str):
        """从所有分组中移除指定的告警（用于告警恢复）"""
        async with self._lock:
            for group in self.groups.values():
                group.alerts = [a for a in group.alerts if a.fingerprint != fingerprint]
    
    def get_group_stats(self) -> Dict[str, int]:
        """获取分组统计信息"""
        return {
            "total_groups": len(self.groups) + len(self.recovery_groups),
            "firing_groups": len(self.groups),
            "recovery_groups": len(self.recovery_groups),
            "total_alerts": sum(len(g.alerts) for g in self.groups.values()) + sum(len(g.alerts) for g in self.recovery_groups.values()),
            "sent_groups": sum(1 for g in self.groups.values() if g.sent) + sum(1 for g in self.recovery_groups.values() if g.sent),
            "pending_groups": sum(1 for g in self.groups.values() if not g.sent) + sum(1 for g in self.recovery_groups.values() if not g.sent)
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
            f"告警分组器配置: group_wait={group_wait}s, "
            f"group_interval={group_interval}s, repeat_interval={repeat_interval}s"
        )

