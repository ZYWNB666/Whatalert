"""告警管理器

负责管理告警的生命周期、静默检查、通知发送和告警分组。
"""
import time
import asyncio
from typing import List, Dict, Any, Optional
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.alert import AlertEvent, AlertEventHistory, AlertRule
from app.models.silence import SilenceRule
from app.services.notifier import NotificationService
from app.services.alert_grouper import AlertGrouper
from app.db.database import DatabaseSessionManager


class AlertManager:
    """告警管理器
    
    负责管理告警的完整生命周期，包括：
    - 告警发送和静默检查
    - 告警分组和批量发送
    - 告警恢复通知
    - 告警归档
    
    Attributes:
        db_manager: 数据库会话管理器
        notifier: 通知服务
        grouper: 告警分组器（内存版本）
        _grouping_enabled: 是否启用告警分组
        _use_redis: 是否使用 Redis 分组器
    """
    
    def __init__(self, use_redis: bool = True):
        """初始化告警管理器
        
        Args:
            use_redis: 是否使用 Redis 分组器，默认 True
        """
        self.db_manager = DatabaseSessionManager()
        self.notifier = NotificationService()
        self._grouping_enabled = True  # 是否启用告警分组
        self._grouping_task = None
        self._use_redis = use_redis
        self._redis_grouper = None
        self._lock_manager = None
        self._redis_init_pending = use_redis  # 标记 Redis 初始化待处理
        
        # 初始化分组器（内存版本作为后备）
        self.grouper = AlertGrouper()
    
    
    async def _init_redis_components(self):
        """异步初始化 Redis 组件"""
        if not self._redis_init_pending:
            logger.debug("Redis 组件已初始化，跳过")
            return
        
        logger.info("开始初始化 Redis 组件...")
        
        try:
            from app.db.redis_client import RedisClient
            from app.services.redis_alert_grouper import RedisAlertGrouper
            from app.core.distributed_lock import AlertLockManager
            
            # 异步获取 Redis 客户端
            redis_client = await RedisClient.get_client()
            logger.info(f"Redis 客户端获取成功: {redis_client}")
            
            # 初始化 Redis 分组器和锁管理器
            self._redis_grouper = RedisAlertGrouper(redis_client)
            self._lock_manager = AlertLockManager(redis_client)
            
            self._redis_init_pending = False
            logger.info(f"✅ Redis 分组器和分布式锁已启用 (grouper={self._redis_grouper}, lock={self._lock_manager})")
        except Exception as e:
            logger.warning(f"⚠️  Redis 组件初始化失败，使用内存分组器: {str(e)}")
            logger.exception(e)
            self._use_redis = False
            self._redis_init_pending = False
    
    @property
    def active_grouper(self):
        """获取当前激活的分组器"""
        is_redis = self._use_redis and self._redis_grouper is not None
        grouper = self._redis_grouper if is_redis else self.grouper
        grouper_type = "Redis" if is_redis else "Memory"
        logger.debug(f"使用{grouper_type}分组器 (use_redis={self._use_redis}, redis_grouper={self._redis_grouper is not None})")
        return grouper
    
    async def send_alert(self, alert: AlertEvent, rule: AlertRule):
        """发送告警通知（支持分布式锁）"""
        try:
            # 检查是否被静默
            if await self.is_silenced(alert):
                logger.info(f"告警被静默: fingerprint={alert.fingerprint}")
                return
            
            # 使用分布式锁防止重复发送
            if self._lock_manager:
                # 检查是否正在发送
                if await self._lock_manager.is_alert_sending(alert.fingerprint):
                    logger.debug(f"告警正在发送中（分布式锁保护）: {alert.fingerprint}")
                    return
                
                # 获取锁
                lock = self._lock_manager.get_alert_lock(alert.fingerprint, timeout=60)
                if not await lock.acquire(blocking=False):
                    logger.debug(f"无法获取告警锁，跳过: {alert.fingerprint}")
                    return
                
                try:
                    await self._send_alert_internal(alert, rule)
                finally:
                    await lock.release()
            else:
                await self._send_alert_internal(alert, rule)
            
        except Exception as e:
            logger.error(f"发送告警失败: fingerprint={alert.fingerprint}, error={str(e)}")
    
    async def _send_alert_internal(self, alert: AlertEvent, rule: AlertRule):
        """内部发送告警逻辑"""
        # 检查是否启用告警分组
        enable_grouping = rule.route_config.get('enable_grouping', True)
        if self._grouping_enabled and enable_grouping:
            # 使用分组模式
            current_time = int(time.time())
            if alert.last_sent_at > 0 and (current_time - alert.last_sent_at) < self.active_grouper.group_wait + 5:
                logger.debug(f"告警已在分组中，跳过: {alert.fingerprint}")
                return
            
            # 添加到分组器
            await self.active_grouper.add_alert(alert, rule)
            logger.info(f"告警已添加到分组器: {alert.fingerprint}")
            
            # 标记为已处理（避免重复添加）
            async with self.db_manager.session() as db:
                alert.last_sent_at = current_time
        else:
            # 直接发送（不分组）
            if not self.should_send_notification(alert):
                logger.debug(f"未到通知间隔: fingerprint={alert.fingerprint}")
                return
            
            await self.notifier.send_notification(alert, rule, is_recovery=False)
            
            # 更新最后发送时间
            async with self.db_manager.session() as db:
                alert.last_sent_at = int(time.time())
    
    async def send_recovery(self, alert: AlertEvent, rule: AlertRule):
        """发送恢复通知"""
        try:
            # 从 firing 分组器中移除该告警
            await self.active_grouper.remove_alert_from_groups(alert.fingerprint)
            
            # 检查是否启用恢复告警分组
            enable_grouping = rule.route_config.get('enable_grouping', True)
            enable_recovery_grouping = rule.route_config.get('enable_recovery_grouping', True)
            
            if self._grouping_enabled and enable_grouping and enable_recovery_grouping:
                # 添加到恢复告警分组器
                await self.active_grouper.add_recovery_alert(alert, rule)
                logger.info(f"恢复告警已添加到分组器: {alert.fingerprint}")
            else:
                # 直接发送恢复通知
                await self.notifier.send_notification(alert, rule, is_recovery=True)
            
        except Exception as e:
            logger.error(f"发送恢复通知失败: fingerprint={alert.fingerprint}, error={str(e)}")
    
    async def is_silenced(self, alert: AlertEvent) -> bool:
        """检查告警是否被静默"""
        from app.services.silence_matcher import check_silence_match
        
        current_time = int(time.time())
        
        # 使用独立会话查询生效的静默规则
        async with self.db_manager.session(auto_commit=False) as db:
            # 查询生效的静默规则
            stmt = select(SilenceRule).where(
                SilenceRule.tenant_id == alert.tenant_id,
                SilenceRule.is_enabled == True,
                SilenceRule.starts_at <= current_time,
                SilenceRule.ends_at >= current_time
            )
            result = await db.execute(stmt)
            silence_rules = result.scalars().all()
        
        # 检查是否匹配静默规则（使用新的匹配逻辑）
        for rule in silence_rules:
            if check_silence_match(alert.labels, rule.matchers):
                logger.info(f"告警匹配静默规则: fingerprint={alert.fingerprint}, silence_rule={rule.name}")
                return True
        
        return False
    
    @staticmethod
    def should_send_notification(alert: AlertEvent, min_interval: int = 300) -> bool:
        """判断是否应该发送通知（基于时间间隔）"""
        if alert.last_sent_at == 0:
            return True
        
        current_time = int(time.time())
        return (current_time - alert.last_sent_at) >= min_interval
    
    async def archive_alert(self, alert: AlertEvent):
        """归档告警到历史"""
        try:
            # 重新查询告警对象(避免会话冲突)
            stmt = select(AlertEvent).where(AlertEvent.fingerprint == alert.fingerprint)
            result = await self.db.execute(stmt)
            db_alert = result.scalar_one_or_none()
            
            if not db_alert:
                logger.warning(f"告警不存在,无需归档: {alert.fingerprint}")
                return
            
            # 创建历史记录
            history = AlertEventHistory(
                fingerprint=db_alert.fingerprint,
                rule_id=db_alert.rule_id,
                rule_name=db_alert.rule_name,
                status=db_alert.status,
                severity=db_alert.severity,
                started_at=db_alert.started_at,
                resolved_at=int(time.time()),
                duration=int(time.time()) - db_alert.started_at,
                value=db_alert.value,
                labels=db_alert.labels,
                annotations=db_alert.annotations,
                expr=db_alert.expr,
                tenant_id=db_alert.tenant_id,
                project_id=db_alert.project_id
            )
            
            self.db.add(history)
            
            # 删除当前告警
            await self.db.delete(db_alert)
            await self.db.commit()
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"归档告警失败: fingerprint={alert.fingerprint}, error={str(e)}")
    
    async def start_grouping_worker(self):
        """启动告警分组工作器（后台任务）"""
        if self._grouping_task is not None:
            logger.warning("告警分组工作器已在运行")
            return
        
        # 先初始化 Redis 组件（如果需要）
        if self._redis_init_pending:
            await self._init_redis_components()
        
        self._grouping_task = asyncio.create_task(self._grouping_worker())
        logger.info("告警分组工作器已启动")
    
    async def stop_grouping_worker(self):
        """停止告警分组工作器"""
        if self._grouping_task:
            self._grouping_task.cancel()
            try:
                await self._grouping_task
            except asyncio.CancelledError:
                pass
            self._grouping_task = None
            logger.info("告警分组工作器已停止")
    
    async def _grouping_worker(self):
        """
        告警分组工作器（定期检查并发送准备好的分组）
        
        参考 Alertmanager 的逻辑：
        1. 每隔一段时间检查分组
        2. group_wait: 首次等待时间
        3. group_interval: 已发送分组的重复间隔
        4. repeat_interval: 持续告警的重复发送间隔
        """
        logger.info("🚀 告警分组工作器开始运行")
        iteration = 0
        
        while True:
            try:
                iteration += 1
                
                # 每10次迭代输出一次心跳（50秒）
                if iteration % 10 == 0:
                    logger.info(f"💓 分组工作器心跳检查 (迭代: {iteration})")
                
                # 获取分组统计
                stats = await self.get_grouping_stats()
                logger.debug(f"🔍 当前分组统计: {stats}")
                if stats.get('total_groups', 0) > 0:
                    logger.info(f"📊 分组统计: {stats}")
                
                # 获取准备好发送的分组
                ready_groups = await self.active_grouper.get_ready_groups()
                
                if ready_groups:
                    logger.info(f"🎯 检测到 {len(ready_groups)} 个准备好的分组")
                
                # 发送每个准备好的分组
                for group, is_recovery in ready_groups:
                    try:
                        await self._send_alert_group(group, is_recovery)
                    except Exception as e:
                        # 兼容对象和字典格式
                        group_key = group.get('group_key') if isinstance(group, dict) else getattr(group, 'group_key', 'unknown')
                        logger.error(f"❌ 发送告警分组失败: group={group_key}, is_recovery={is_recovery}, error={str(e)}")
                        import traceback
                        logger.error(f"详细错误: {traceback.format_exc()}")
                
                # 每隔5秒检查一次（类似 Alertmanager 的 check interval）
                await asyncio.sleep(5)
                
            except asyncio.CancelledError:
                logger.info("🛑 告警分组工作器被取消")
                break
            except Exception as e:
                logger.error(f"❌ 告警分组工作器错误: {str(e)}")
                import traceback
                logger.error(f"详细错误: {traceback.format_exc()}")
                await asyncio.sleep(5)  # 发生错误时等待后重试
    
    async def _send_alert_group(self, group, is_recovery: bool = False):
        """发送告警分组（支持对象和字典格式）
        
        Args:
            group: 告警分组对象或字典
            is_recovery: 是否为恢复告警
        """
        # 使用独立的数据库会话
        async with self.db_manager.session() as db:
            try:
                # 兼容对象和字典两种格式
                if isinstance(group, dict):
                    # Redis 分组器返回字典
                    alerts_data = group.get('alerts', [])
                    group_key = group.get('group_key')
                    rule_id = group.get('rule_id')
                    
                    if not alerts_data:
                        logger.warning(f"分组为空: {group_key}")
                        return
                    
                    # 查询规则对象
                    stmt = select(AlertRule).where(AlertRule.id == rule_id)
                    result = await db.execute(stmt)
                    rule = result.scalar_one_or_none()
                    
                    if not rule:
                        logger.warning(f"分组没有关联的规则: {group_key}")
                        return
                    
                    # 将字典数据转换为 AlertEvent 对象列表（用于发送）
                    alerts = []
                    for alert_data in alerts_data:
                        # 从数据库查询完整的 AlertEvent 对象
                        stmt = select(AlertEvent).where(AlertEvent.fingerprint == alert_data['fingerprint'])
                        result = await db.execute(stmt)
                        alert_obj = result.scalar_one_or_none()
                        if alert_obj:
                            alerts.append(alert_obj)
                    
                else:
                    # 内存分组器返回对象
                    alerts = group.get_alerts()
                    group_key = group.group_key
                    rule = group.rule
                    
                    if not alerts:
                        logger.warning(f"分组为空: {group_key}")
                        return
                    
                    if not rule:
                        logger.warning(f"分组没有关联的规则: {group_key}")
                        return
                
                status_text = "恢复" if is_recovery else "告警"
                logger.info(f"⭐ 发送{status_text}分组: {group_key}, 告警数: {len(alerts)}")
                
                # 批量发送告警
                await self.notifier.send_batch_notification(alerts, rule, is_recovery=is_recovery)
                
                # 更新所有告警的最后发送时间
                current_time = int(time.time())
                for alert in alerts:
                    try:
                        # 重新查询对象以确保在当前会话中
                        stmt = select(AlertEvent).where(AlertEvent.fingerprint == alert.fingerprint)
                        result = await db.execute(stmt)
                        db_alert = result.scalar_one_or_none()
                        if db_alert:
                            db_alert.last_sent_at = current_time
                    except Exception as e:
                        logger.warning(f"更新告警发送时间失败: {alert.fingerprint}, error={str(e)}")
                
                logger.info(f"✅ {status_text}分组发送成功: {group_key}")
                
                # 标记分组为已发送（对象格式才需要）
                if not isinstance(group, dict) and hasattr(group, 'mark_sent'):
                    group.mark_sent()
                
                # 清理已发送的分组
                await self.active_grouper.clear_sent_group(group_key, is_recovery)
                
            except Exception as e:
                group_key = group.get('group_key') if isinstance(group, dict) else getattr(group, 'group_key', 'unknown')
                logger.error(f"❌ 发送告警分组失败: {group_key}, error={str(e)}")
                import traceback
                logger.error(f"详细错误: {traceback.format_exc()}")
                # 不再重新抛出异常，避免中断分组工作器
    
    def configure_grouper(
        self, 
        group_wait: int = 10, 
        group_interval: int = 30, 
        repeat_interval: int = 3600
    ):
        """配置告警分组器参数"""
        self.grouper.configure(group_wait, group_interval, repeat_interval)
        if self._redis_grouper:
            self._redis_grouper.configure(group_wait, group_interval, repeat_interval)
    
    def enable_grouping(self, enabled: bool = True):
        """启用或禁用告警分组"""
        self._grouping_enabled = enabled
        logger.info(f"告警分组已{'启用' if enabled else '禁用'}")
    
    async def get_grouping_stats(self) -> Dict[str, int]:
        """获取告警分组统计信息"""
        try:
            if self._use_redis and self._redis_grouper:
                return await self.active_grouper.get_group_stats()
            else:
                return self.grouper.get_group_stats()
        except Exception as e:
            logger.debug(f"获取分组统计失败，使用默认值: {str(e)}")
            # 回退到内存分组器
            return self.grouper.get_group_stats()

