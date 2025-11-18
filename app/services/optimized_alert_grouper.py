"""优化的基于 Redis 的分布式告警分组器 - 使用 Pipeline 和异步处理"""
import json
import time
import asyncio
from typing import List, Dict, Optional, Set
from loguru import logger
import redis.asyncio as redis
from app.models.alert import AlertEvent, AlertRule


class OptimizedAlertGrouper:
    """优化的 Redis 分布式告警分组器
    
    性能优化特性：
    1. Redis Pipeline 批量操作 - 减少网络往返
    2. 异步批处理队列 - 非阻塞处理
    3. 并发控制 - 使用信号量限制并发
    4. 批量读写 - 减少 Redis 操作次数
    5. 内存缓存 - 减少重复读取
    """
    
    def __init__(self, redis_client: redis.Redis, max_concurrent: int = 100):
        self.redis = redis_client
        self.group_wait = 10  # 分组等待时间（秒）
        self.group_interval = 30  # 分组间隔时间（秒）
        self.repeat_interval = 3600  # 重复发送间隔（秒）
        
        # Redis 键前缀
        self.firing_prefix = "alert:group:firing"
        self.recovery_prefix = "alert:group:recovery"
        
        # 性能优化配置
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.batch_size = 50  # 批处理大小
        self.batch_queue: List[tuple] = []  # 批处理队列
        self.batch_lock = asyncio.Lock()
        
        # 内存缓存（减少 Redis 读取）
        self.group_cache: Dict[str, dict] = {}
        self.cache_ttl = 5  # 缓存 TTL（秒）
        self.cache_timestamps: Dict[str, float] = {}
        
        logger.info(f"✨ 优化告警分组器初始化: max_concurrent={max_concurrent}, batch_size={self.batch_size}")
    
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
    
    def _is_cache_valid(self, redis_key: str) -> bool:
        """检查缓存是否有效"""
        if redis_key not in self.cache_timestamps:
            return False
        return (time.time() - self.cache_timestamps[redis_key]) < self.cache_ttl
    
    async def _get_group_from_cache_or_redis(self, redis_key: str) -> Optional[dict]:
        """从缓存或 Redis 获取分组数据"""
        # 检查内存缓存
        if self._is_cache_valid(redis_key):
            return self.group_cache.get(redis_key)
        
        # 从 Redis 读取
        group_data = await self.redis.get(redis_key)
        if group_data:
            group = json.loads(group_data)
            # 更新缓存
            self.group_cache[redis_key] = group
            self.cache_timestamps[redis_key] = time.time()
            return group
        
        return None
    
    def _invalidate_cache(self, redis_key: str):
        """使缓存失效"""
        self.group_cache.pop(redis_key, None)
        self.cache_timestamps.pop(redis_key, None)
    
    async def add_alert(self, alert: AlertEvent, rule: AlertRule) -> str:
        """
        添加告警到分组（优化版本）
        
        返回: group_key
        """
        async with self.semaphore:  # 并发控制
            group_key, group_labels = self._generate_group_key(alert, rule)
            redis_key = self._get_group_key(group_key, is_recovery=False)
            
            # 从缓存或 Redis 获取现有分组数据
            group = await self._get_group_from_cache_or_redis(redis_key)
            current_time = time.time()
            
            if not group:
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
                logger.debug(f"创建新的告警分组: {group_key}")
            
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
                
                # 使用 Pipeline 批量写入
                async with self.redis.pipeline(transaction=True) as pipe:
                    pipe.setex(redis_key, 7200, json.dumps(group))
                    await pipe.execute()
                
                # 更新缓存
                self.group_cache[redis_key] = group
                self.cache_timestamps[redis_key] = current_time
                
                logger.debug(f"告警添加到分组: {group_key}, 当前告警数: {len(group['alerts'])}")
            
            return group_key
    
    async def add_alerts_batch(self, alerts_with_rules: List[tuple]) -> List[str]:
        """
        批量添加告警到分组（高性能版本）
        
        参数:
            alerts_with_rules: List[(alert, rule)]
        
        返回: List[group_key]
        """
        if not alerts_with_rules:
            return []
        
        logger.info(f"🚀 批量添加 {len(alerts_with_rules)} 个告警到分组器")
        start_time = time.time()
        
        # 按分组键分组告警
        groups_map: Dict[str, dict] = {}
        redis_keys_to_fetch: Set[str] = set()
        
        for alert, rule in alerts_with_rules:
            group_key, group_labels = self._generate_group_key(alert, rule)
            redis_key = self._get_group_key(group_key, is_recovery=False)
            
            if redis_key not in groups_map:
                groups_map[redis_key] = {
                    "group_key": group_key,
                    "group_labels": group_labels,
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "alerts": [],
                    "redis_key": redis_key
                }
                redis_keys_to_fetch.add(redis_key)
        
        # 批量从 Redis 读取现有分组（使用 Pipeline）
        if redis_keys_to_fetch:
            async with self.redis.pipeline(transaction=False) as pipe:
                for redis_key in redis_keys_to_fetch:
                    # 先检查缓存
                    if not self._is_cache_valid(redis_key):
                        pipe.get(redis_key)
                
                results = await pipe.execute()
                
                # 处理结果
                result_idx = 0
                for redis_key in redis_keys_to_fetch:
                    if self._is_cache_valid(redis_key):
                        # 使用缓存数据
                        cached_group = self.group_cache.get(redis_key)
                        if cached_group:
                            groups_map[redis_key].update(cached_group)
                    elif result_idx < len(results) and results[result_idx]:
                        # 使用 Redis 数据
                        existing_group = json.loads(results[result_idx])
                        groups_map[redis_key].update(existing_group)
                        # 更新缓存
                        self.group_cache[redis_key] = existing_group
                        self.cache_timestamps[redis_key] = time.time()
                        result_idx += 1
        
        # 添加告警到对应分组
        current_time = time.time()
        for alert, rule in alerts_with_rules:
            group_key, _ = self._generate_group_key(alert, rule)
            redis_key = self._get_group_key(group_key, is_recovery=False)
            group = groups_map[redis_key]
            
            # 初始化时间戳（如果是新分组）
            if "created_at" not in group:
                group["created_at"] = current_time
                group["last_updated_at"] = current_time
                group["sent"] = False
            
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
        
        # 批量写入 Redis（使用 Pipeline）
        async with self.redis.pipeline(transaction=True) as pipe:
            for redis_key, group in groups_map.items():
                # 移除临时字段
                group_to_save = {k: v for k, v in group.items() if k != "redis_key"}
                pipe.setex(redis_key, 7200, json.dumps(group_to_save))
                
                # 更新缓存
                self.group_cache[redis_key] = group_to_save
                self.cache_timestamps[redis_key] = current_time
            
            await pipe.execute()
        
        elapsed = time.time() - start_time
        logger.info(f"✅ 批量添加完成: {len(alerts_with_rules)} 个告警, {len(groups_map)} 个分组, 耗时 {elapsed:.3f}s")
        
        return list(groups_map.keys())
    
    async def add_recovery_alert(self, alert: AlertEvent, rule: AlertRule) -> str:
        """
        添加恢复告警到分组（优化版本）
        
        返回: group_key
        """
        async with self.semaphore:  # 并发控制
            group_key, group_labels = self._generate_group_key(alert, rule)
            recovery_key = f"recovery:{group_key}"
            redis_key = self._get_group_key(recovery_key, is_recovery=True)
            
            # 从缓存或 Redis 获取现有分组数据
            group = await self._get_group_from_cache_or_redis(redis_key)
            current_time = time.time()
            
            if not group:
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
                logger.debug(f"创建新的恢复告警分组: {recovery_key}")
            
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
                
                # 使用 Pipeline 写入
                async with self.redis.pipeline(transaction=True) as pipe:
                    pipe.setex(redis_key, 7200, json.dumps(group))
                    await pipe.execute()
                
                # 更新缓存
                self.group_cache[redis_key] = group
                self.cache_timestamps[redis_key] = current_time
                
                logger.debug(f"恢复告警添加到分组: {recovery_key}, 当前告警数: {len(group['alerts'])}")
            
            return recovery_key
    
    async def get_ready_groups(self) -> List[tuple]:
        """
        获取准备好发送的分组（优化版本）
        
        返回: List[tuple(group_data, is_recovery)]
        """
        ready_groups = []
        current_time = time.time()
        
        # 使用 Pipeline 批量读取
        firing_keys = []
        recovery_keys = []
        
        # 收集所有键
        async for key in self.redis.scan_iter(match=f"{self.firing_prefix}:*", count=100):
            firing_keys.append(key)
        
        async for key in self.redis.scan_iter(match=f"{self.recovery_prefix}:*", count=100):
            recovery_keys.append(key)
        
        # 批量读取 firing 分组
        if firing_keys:
            async with self.redis.pipeline(transaction=False) as pipe:
                for key in firing_keys:
                    pipe.get(key)
                results = await pipe.execute()
                
                for group_data in results:
                    if group_data:
                        group = json.loads(group_data)
                        if self._is_group_ready(group, current_time):
                            ready_groups.append((group, False))
                            logger.debug(f"✅ firing 分组准备就绪: {group['group_key']}, 告警数: {len(group['alerts'])}")
        
        # 批量读取 recovery 分组
        if recovery_keys:
            async with self.redis.pipeline(transaction=False) as pipe:
                for key in recovery_keys:
                    pipe.get(key)
                results = await pipe.execute()
                
                for group_data in results:
                    if group_data:
                        group = json.loads(group_data)
                        if self._is_group_ready(group, current_time):
                            ready_groups.append((group, True))
                            logger.debug(f"✅ recovery 分组准备就绪: {group['group_key']}, 告警数: {len(group['alerts'])}")
        
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
        """标记分组为已发送（优化版本）"""
        redis_key = self._get_group_key(group_key, is_recovery)
        
        # 从缓存或 Redis 获取
        group = await self._get_group_from_cache_or_redis(redis_key)
        
        if group:
            group["sent"] = True
            
            # 使用 Pipeline 写入
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.setex(redis_key, 7200, json.dumps(group))
                await pipe.execute()
            
            # 更新缓存
            self.group_cache[redis_key] = group
            self.cache_timestamps[redis_key] = time.time()
    
    async def clear_sent_group(self, group_key: str, is_recovery: bool = False):
        """清除已发送的分组"""
        redis_key = self._get_group_key(group_key, is_recovery)
        
        # 使用 Pipeline 删除
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.delete(redis_key)
            await pipe.execute()
        
        # 清除缓存
        self._invalidate_cache(redis_key)
        logger.debug(f"清除已发送分组: {group_key}")
    
    async def remove_alert_from_groups(self, fingerprint: str):
        """从所有分组中移除指定的告警（优化版本）"""
        # 收集所有需要更新的键
        keys_to_update = []
        
        async for key in self.redis.scan_iter(match=f"{self.firing_prefix}:*", count=100):
            keys_to_update.append(key)
        
        if not keys_to_update:
            return
        
        # 批量读取
        async with self.redis.pipeline(transaction=False) as pipe:
            for key in keys_to_update:
                pipe.get(key)
            results = await pipe.execute()
        
        # 处理并批量写入
        async with self.redis.pipeline(transaction=True) as pipe:
            for key, group_data in zip(keys_to_update, results):
                if group_data:
                    group = json.loads(group_data)
                    original_count = len(group["alerts"])
                    group["alerts"] = [a for a in group["alerts"] if a["fingerprint"] != fingerprint]
                    
                    if len(group["alerts"]) < original_count:
                        if group["alerts"]:
                            pipe.setex(key, 7200, json.dumps(group))
                            # 更新缓存
                            self.group_cache[key] = group
                            self.cache_timestamps[key] = time.time()
                        else:
                            pipe.delete(key)
                            # 清除缓存
                            self._invalidate_cache(key)
            
            await pipe.execute()
    
    async def get_group_stats(self) -> Dict[str, int]:
        """获取分组统计信息（优化版本）"""
        firing_keys = []
        recovery_keys = []
        
        # 收集所有键
        async for key in self.redis.scan_iter(match=f"{self.firing_prefix}:*", count=100):
            firing_keys.append(key)
        
        async for key in self.redis.scan_iter(match=f"{self.recovery_prefix}:*", count=100):
            recovery_keys.append(key)
        
        total_alerts = 0
        sent_count = 0
        pending_count = 0
        
        # 批量读取 firing 分组
        if firing_keys:
            async with self.redis.pipeline(transaction=False) as pipe:
                for key in firing_keys:
                    pipe.get(key)
                results = await pipe.execute()
                
                for group_data in results:
                    if group_data:
                        group = json.loads(group_data)
                        total_alerts += len(group["alerts"])
                        if group.get("sent"):
                            sent_count += 1
                        else:
                            pending_count += 1
        
        # 批量读取 recovery 分组
        if recovery_keys:
            async with self.redis.pipeline(transaction=False) as pipe:
                for key in recovery_keys:
                    pipe.get(key)
                results = await pipe.execute()
                
                for group_data in results:
                    if group_data:
                        group = json.loads(group_data)
                        total_alerts += len(group["alerts"])
                        if group.get("sent"):
                            sent_count += 1
                        else:
                            pending_count += 1
        
        return {
            "total_groups": len(firing_keys) + len(recovery_keys),
            "firing_groups": len(firing_keys),
            "recovery_groups": len(recovery_keys),
            "total_alerts": total_alerts,
            "sent_groups": sent_count,
            "pending_groups": pending_count,
            "cache_size": len(self.group_cache)
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
            f"优化告警分组器配置: group_wait={group_wait}s, "
            f"group_interval={group_interval}s, repeat_interval={repeat_interval}s"
        )
    
    async def clear_cache(self):
        """清除内存缓存"""
        self.group_cache.clear()
        self.cache_timestamps.clear()
        logger.info("内存缓存已清除")