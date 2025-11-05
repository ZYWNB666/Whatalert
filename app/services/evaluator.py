"""告警规则评估引擎"""
import time
import hashlib
import asyncio
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.alert import AlertRule, AlertEvent
from app.models.datasource import DataSource
from app.services.alert_manager import AlertManager


class RuleEvaluator:
    """规则评估器"""
    
    def __init__(self, db: AsyncSession, alert_manager: AlertManager):
        self.db = db
        self.alert_manager = alert_manager
    
    async def query_datasource(self, datasource: DataSource, query: str) -> List[Dict[str, Any]]:
        """查询数据源"""
        try:
            # 构建请求头
            headers = {}
            auth = None
            
            if datasource.auth_config:
                auth_type = datasource.auth_config.get('type')
                if auth_type == 'token':
                    token = datasource.auth_config.get('token', '')
                    if token and not token.startswith('Bearer '):
                        headers['Authorization'] = f'Bearer {token}'
                    else:
                        headers['Authorization'] = token
                elif auth_type == 'basic':
                    auth = (
                        datasource.auth_config.get('username', ''),
                        datasource.auth_config.get('password', '')
                    )
            
            # 构建查询 URL
            base_url = datasource.url.rstrip('/')
            if base_url.endswith('/api/v1'):
                query_url = f"{base_url}/query"
            elif '/api/v1/' in base_url:
                query_url = base_url
            else:
                query_url = f"{base_url}/api/v1/query"
            
            # 发送查询
            verify_ssl = datasource.http_config.get('verify_ssl', True)
            timeout = datasource.http_config.get('timeout', 30)
            
            async with httpx.AsyncClient(verify=verify_ssl, timeout=timeout) as client:
                response = await client.get(
                    query_url,
                    params={"query": query},
                    headers=headers,
                    auth=auth
                )
            
            if response.status_code != 200:
                logger.error(f"数据源查询失败: status={response.status_code}, text={response.text}")
                return []
            
            result = response.json()
            
            if result.get('status') == 'success':
                return result.get('data', {}).get('result', [])
            else:
                logger.error(f"查询失败: {result.get('error', '未知错误')}")
                return []
                
        except Exception as e:
            logger.error(f"查询异常: {str(e)}")
            return []
    
    async def evaluate_rule(self, rule: AlertRule) -> List[Dict[str, Any]]:
        """评估单个规则"""
        try:
            # 获取数据源
            stmt = select(DataSource).where(
                DataSource.id == rule.datasource_id,
                DataSource.is_enabled == True
            )
            result = await self.db.execute(stmt)
            datasource = result.scalar_one_or_none()
            
            if not datasource:
                logger.warning(f"数据源不可用: rule_id={rule.id}")
                return []
            
            # 查询数据
            query_result = await self.query_datasource(datasource, rule.expr)
            
            if not query_result:
                logger.debug(f"查询无结果: rule_id={rule.id}, expr={rule.expr}")
                return []
            
            # 处理查询结果
            alerts = []
            current_time = int(time.time())
            
            for metric in query_result:
                # 提取标签和值
                labels = metric.get('metric', {})
                value = float(metric.get('value', [0, '0'])[1])
                
                # 合并规则标签和数据源标签
                all_labels = {
                    **datasource.extra_labels,
                    **labels,
                    **rule.labels,
                }
                
                # 生成指纹
                fingerprint = self.generate_fingerprint(rule.id, all_labels)
                
                # 创建告警事件
                alert_data = {
                    'fingerprint': fingerprint,
                    'rule_id': rule.id,
                    'rule_name': rule.name,
                    'severity': rule.severity,
                    'value': value,
                    'labels': all_labels,
                    'annotations': self.render_annotations(rule.annotations, all_labels, value),
                    'expr': rule.expr,
                    'tenant_id': rule.tenant_id,
                    'status': 'pending',  # 初始状态
                    'started_at': current_time,
                    'last_eval_at': current_time,
                }
                
                alerts.append(alert_data)
            
            return alerts
            
        except Exception as e:
            logger.error(f"规则评估失败: rule_id={rule.id}, error={str(e)}")
            return []
    
    @staticmethod
    def generate_fingerprint(rule_id: int, labels: Dict[str, Any]) -> str:
        """生成告警指纹"""
        # 按键排序标签，确保一致性
        sorted_labels = sorted(labels.items())
        label_str = ','.join([f"{k}={v}" for k, v in sorted_labels])
        fingerprint_str = f"{rule_id}:{label_str}"
        return hashlib.md5(fingerprint_str.encode()).hexdigest()
    
    @staticmethod
    def render_annotations(annotations: Dict[str, str], labels: Dict[str, Any], value: float) -> Dict[str, str]:
        """渲染注释（支持模板变量）"""
        rendered = {}
        template_vars = {**labels, 'value': value}
        
        for key, template in annotations.items():
            try:
                # 简单的模板渲染，支持 {{ variable }} 语法
                result = template
                for var_name, var_value in template_vars.items():
                    result = result.replace(f"{{{{{var_name}}}}}", str(var_value))
                rendered[key] = result
            except Exception as e:
                logger.warning(f"注释渲染失败: key={key}, error={str(e)}")
                rendered[key] = template
        
        return rendered
    
    async def process_alert_events(self, rule: AlertRule, alert_data_list: List[Dict[str, Any]]):
        """处理告警事件（状态管理）"""
        current_time = int(time.time())
        
        # 获取当前该规则的所有告警（包括所有状态）
        stmt = select(AlertEvent).where(AlertEvent.rule_id == rule.id)
        result = await self.db.execute(stmt)
        all_alerts = {alert.fingerprint: alert for alert in result.scalars().all()}
        
        # 当前触发的告警指纹
        current_fingerprints = {alert['fingerprint'] for alert in alert_data_list}
        
        # 处理新告警和更新
        for alert_data in alert_data_list:
            fingerprint = alert_data['fingerprint']
            
            if fingerprint in all_alerts:
                # 更新已有告警
                existing_alert = all_alerts[fingerprint]
                existing_alert.last_eval_at = current_time
                existing_alert.value = alert_data['value']
                
                # 如果告警之前已经 resolved，重新激活
                if existing_alert.status == 'resolved':
                    existing_alert.status = 'pending'
                    existing_alert.started_at = current_time
                
                # 检查是否应该从 pending 转为 firing
                if existing_alert.status == 'pending':
                    duration = current_time - existing_alert.started_at
                    if duration >= rule.for_duration:
                        existing_alert.status = 'firing'
                        # 发送告警通知
                        await self.alert_manager.send_alert(existing_alert, rule)
                
            else:
                # 创建新告警
                new_alert = AlertEvent(**alert_data)
                self.db.add(new_alert)
        
        # 处理已恢复的告警（只处理之前是 pending 或 firing 的）
        active_alerts = {fp: alert for fp, alert in all_alerts.items() 
                        if alert.status in ['pending', 'firing']}
        resolved_fingerprints = set(active_alerts.keys()) - current_fingerprints
        
        for fingerprint in resolved_fingerprints:
            alert = active_alerts[fingerprint]
            alert.status = 'resolved'
            alert.last_eval_at = current_time
            
            # 发送恢复通知
            await self.alert_manager.send_recovery(alert, rule)
            
            # 移动到历史记录
            await self.alert_manager.archive_alert(alert)
        
        await self.db.commit()


class AlertEvaluationScheduler:
    """告警评估调度器"""
    
    def __init__(self):
        self.running = False
    
    async def start(self):
        """启动调度器"""
        self.running = True
        logger.info("告警评估调度器已启动")
        
        while self.running:
            try:
                await self.evaluate_all_rules()
            except Exception as e:
                logger.error(f"评估周期出错: {str(e)}")
            
            # 等待下一个评估周期
            await asyncio.sleep(15)  # 默认15秒
    
    async def stop(self):
        """停止调度器"""
        self.running = False
        logger.info("告警评估调度器已停止")
    
    async def evaluate_all_rules(self):
        """评估所有启用的规则"""
        from app.db.database import AsyncSessionLocal
        
        # 查询所有启用的规则
        async with AsyncSessionLocal() as db:
            stmt = select(AlertRule).where(AlertRule.is_enabled == True)
            result = await db.execute(stmt)
            rules = result.scalars().all()
        
        logger.info(f"开始评估 {len(rules)} 条规则")
        
        # 并发评估规则 - 每个规则使用独立的数据库会话
        tasks = []
        for rule in rules:
            task = self.evaluate_single_rule(rule)
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def evaluate_single_rule(self, rule: AlertRule):
        """评估单条规则（使用独立的数据库会话）"""
        from app.db.database import AsyncSessionLocal
        import app.main as main_module
        
        try:
            # 每个规则使用独立的数据库会话，避免并发冲突
            async with AsyncSessionLocal() as db:
                # 使用全局的 alert_manager（重要！确保告警添加到同一个分组器）
                if main_module.alert_manager:
                    alert_manager = main_module.alert_manager
                else:
                    # 如果全局 alert_manager 未初始化，创建临时的
                    alert_manager = AlertManager(db)
                    logger.warning("全局 alert_manager 未初始化，使用临时实例")
                
                evaluator = RuleEvaluator(db, alert_manager)
                
                # 评估规则
                alert_data_list = await evaluator.evaluate_rule(rule)
                
                # 处理告警事件
                await evaluator.process_alert_events(rule, alert_data_list)
            
        except Exception as e:
            logger.error(f"规则评估失败: rule_id={rule.id}, error={str(e)}")

