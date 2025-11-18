"""通知服务

负责多渠道告警通知的发送，支持飞书、钉钉、企业微信、邮件和 Webhook。
"""
import time
import json
import re
import httpx
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.alert import AlertEvent, AlertRule
from app.models.notification import NotificationChannel, NotificationRecord
from app.models.settings import SystemSettings
from app.db.database import DatabaseSessionManager


class NotificationService:
    """通知服务
    
    提供多渠道告警通知发送功能，支持：
    - 飞书（高级卡片和文本消息）
    - 钉钉（支持签名认证）
    - 企业微信
    - 邮件（HTML 模板）
    - 自定义 Webhook
    
    Attributes:
        db_manager: 数据库会话管理器
    """
    
    def __init__(self):
        """初始化通知服务"""
        self.db_manager = DatabaseSessionManager()
    
    @staticmethod
    def render_template(template: str, alert: AlertEvent) -> str:
        """渲染模板变量
        
        支持的变量格式：
        - {{ $labels.xxx }} 或 {{$labels.xxx}}
        - {{ $value }} 或 {{$value}}
        - {{ .labels.xxx }} 或 {{.labels.xxx}}
        - {{ .value }} 或 {{.value}}
        """
        if not template:
            return template
        
        result = template
        
        # 渲染 $value 或 .value
        value_patterns = [
            r'\{\{\s*\$value\s*\}\}',
            r'\{\{\s*\.value\s*\}\}'
        ]
        for pattern in value_patterns:
            result = re.sub(pattern, str(alert.value), result)
        
        # 渲染 $labels.xxx 或 .labels.xxx
        label_patterns = [
            r'\{\{\s*\$labels\.(\w+)\s*\}\}',
            r'\{\{\s*\.labels\.(\w+)\s*\}\}'
        ]
        for pattern in label_patterns:
            def replace_label(match):
                label_key = match.group(1)
                return str(alert.labels.get(label_key, f'<未定义:{label_key}>'))
            result = re.sub(pattern, replace_label, result)
        
        return result
    
    @staticmethod
    def render_annotations(alert: AlertEvent) -> Dict[str, str]:
        """渲染告警注释中的所有模板变量"""
        if not alert.annotations:
            return {}
        
        rendered = {}
        for key, value in alert.annotations.items():
            if isinstance(value, str):
                rendered[key] = NotificationService.render_template(value, alert)
            else:
                rendered[key] = value
        
        return rendered
    
    async def send_notification(self, alert: AlertEvent, rule: AlertRule, is_recovery: bool = False):
        """发送单个告警通知（向后兼容）"""
        await self.send_batch_notification([alert], rule, is_recovery)
    
    async def send_batch_notification(
        self, 
        alerts: List[AlertEvent], 
        rule: AlertRule, 
        is_recovery: bool = False
    ):
        """发送批量告警通知（支持告警合并）"""
        if not alerts:
            return
        
        # 使用第一个告警来获取通知渠道（所有告警应该在同一个分组中）
        first_alert = alerts[0]
        
        # 根据规则路由配置获取通知渠道
        channels = await self.get_notification_channels(first_alert, rule)
        
        if not channels:
            logger.warning(f"无可用通知渠道: rule={rule.name}")
            return
        
        # 发送到所有渠道
        for channel in channels:
            await self.send_batch_to_channel(channel, alerts, rule, is_recovery)
    
    async def get_notification_channels(
        self, 
        alert: AlertEvent, 
        rule: AlertRule
    ) -> List[NotificationChannel]:
        """获取通知渠道（支持路由）
        
        Args:
            alert: 告警事件
            rule: 告警规则
            
        Returns:
            符合条件的通知渠道列表
        """
        # 使用独立的数据库会话
        async with self.db_manager.session(auto_commit=False) as db:
            # 从规则路由配置中获取渠道ID列表
            channel_ids = rule.route_config.get('notification_channels', [])
            
            if not channel_ids:
                # 如果没有配置，使用默认渠道
                stmt = select(NotificationChannel).where(
                    NotificationChannel.tenant_id == alert.tenant_id,
                    NotificationChannel.is_enabled == True,
                    NotificationChannel.is_default == True
                )
            else:
                stmt = select(NotificationChannel).where(
                    NotificationChannel.id.in_(channel_ids),
                    NotificationChannel.tenant_id == alert.tenant_id,
                    NotificationChannel.is_enabled == True
                )
            
            result = await db.execute(stmt)
            channels = result.scalars().all()
            
            # 过滤标签
            filtered_channels = []
            for channel in channels:
                if self.should_send_to_channel(alert, channel):
                    filtered_channels.append(channel)
            
            return filtered_channels
    
    @staticmethod
    def should_send_to_channel(alert: AlertEvent, channel: NotificationChannel) -> bool:
        """判断是否应该发送到该渠道（基于标签过滤）"""
        filter_config = channel.filter_config
        
        # 检查包含标签
        include_labels = filter_config.get('include_labels', {})
        if include_labels:
            for label_key, label_values in include_labels.items():
                alert_value = alert.labels.get(label_key)
                if alert_value not in label_values:
                    return False
        
        # 检查排除标签
        exclude_labels = filter_config.get('exclude_labels', {})
        if exclude_labels:
            for label_key, label_values in exclude_labels.items():
                alert_value = alert.labels.get(label_key)
                if alert_value in label_values:
                    return False
        
        return True
    
    async def send_to_channel(
        self, 
        channel: NotificationChannel, 
        alert: AlertEvent, 
        is_recovery: bool
    ):
        """发送单个告警到指定渠道（向后兼容）"""
        await self.send_batch_to_channel(channel, [alert], None, is_recovery)
    
    async def send_batch_to_channel(
        self, 
        channel: NotificationChannel, 
        alerts: List[AlertEvent],
        rule: Optional[AlertRule],
        is_recovery: bool
    ):
        """发送批量告警到指定渠道"""
        if not alerts:
            return
        
        try:
            # 根据渠道类型选择发送方法
            if channel.type == 'feishu':
                await self.send_feishu_batch(channel, alerts, is_recovery)
            elif channel.type == 'dingtalk':
                await self.send_dingtalk_batch(channel, alerts, is_recovery)
            elif channel.type == 'wechat':
                await self.send_wechat_batch(channel, alerts, is_recovery)
            elif channel.type == 'email':
                await self.send_email_batch(channel, alerts, is_recovery)
            elif channel.type == 'webhook':
                await self.send_webhook_batch(channel, alerts, is_recovery)
            else:
                logger.warning(f"不支持的通知类型: {channel.type}")
                return
            
            # 记录通知（为每个告警记录）
            for alert in alerts:
                await self.record_notification(channel, alert, 'success', None)
            
        except Exception as e:
            logger.error(f"发送通知失败: channel={channel.name}, error={str(e)}")
            # 记录失败
            for alert in alerts:
                await self.record_notification(channel, alert, 'failed', str(e))
    
    async def send_feishu(self, channel: NotificationChannel, alert: AlertEvent, is_recovery: bool):
        """发送飞书通知"""
        webhook_url = channel.config.get('webhook_url')
        card_type = channel.config.get('card_type', 'advanced')  # simple 或 advanced
        
        if card_type == 'advanced':
            # 高级消息卡片
            card = self.build_feishu_advanced_card(alert, is_recovery)
        else:
            # 简单文本消息
            content = self.build_alert_text(alert, is_recovery)
            card = {
                "msg_type": "text",
                "content": {"text": content}
            }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=card, timeout=10)
            response.raise_for_status()
    
    @staticmethod
    def build_feishu_advanced_card(alert: AlertEvent, is_recovery: bool) -> dict:
        """构建飞书高级消息卡片"""
        status_color = "red" if not is_recovery else "green"
        status_text = "告警触发" if not is_recovery else "告警恢复"
        
        # 渲染注释
        rendered_annotations = NotificationService.render_annotations(alert)
        
        # 构建标签列表
        labels_text = "\n".join([f"**{k}**: {v}" for k, v in alert.labels.items()])
        
        # 基础信息
        basic_info = f"**告警名称**: {alert.rule_name}\n**告警等级**: {alert.severity}\n**当前值**: {alert.value}"
        
        # 添加注释信息
        if rendered_annotations:
            summary = rendered_annotations.get('summary', '')
            description = rendered_annotations.get('description', '')
            if summary:
                basic_info += f"\n\n**摘要**: {summary}"
            if description:
                basic_info += f"\n**描述**: {description}"
        
        card = {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True
                },
                "header": {
                    "title": {
                        "content": f"🔔 {status_text}",
                        "tag": "plain_text"
                    },
                    "template": status_color
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "content": basic_info,
                            "tag": "lark_md"
                        }
                    },
                    {
                        "tag": "hr"
                    },
                    {
                        "tag": "div",
                        "text": {
                            "content": f"**标签**:\n{labels_text}",
                            "tag": "lark_md"
                        }
                    }
                ]
            }
        }
        
        return card
    
    async def send_dingtalk(self, channel: NotificationChannel, alert: AlertEvent, is_recovery: bool):
        """发送钉钉通知"""
        import hashlib
        import hmac
        import base64
        import urllib.parse
        
        webhook_url = channel.config.get('webhook_url')
        secret = channel.config.get('secret', '')
        
        # 如果有secret，需要签名
        if secret:
            timestamp = str(round(time.time() * 1000))
            secret_enc = secret.encode('utf-8')
            string_to_sign = f'{timestamp}\n{secret}'
            string_to_sign_enc = string_to_sign.encode('utf-8')
            hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
            sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
            webhook_url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"
        
        # 构建消息
        content = self.build_alert_text(alert, is_recovery)
        message = {
            "msgtype": "text",
            "text": {
                "content": content
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=message, timeout=10)
            response.raise_for_status()
    
    async def send_wechat(self, channel: NotificationChannel, alert: AlertEvent, is_recovery: bool):
        """发送企业微信通知"""
        webhook_url = channel.config.get('webhook_url')
        
        content = self.build_alert_text(alert, is_recovery)
        message = {
            "msgtype": "text",
            "text": {
                "content": content
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=message, timeout=10)
            response.raise_for_status()
    
    async def send_email(self, channel: NotificationChannel, alert: AlertEvent, is_recovery: bool):
        """发送邮件通知"""
        # 使用独立的数据库会话
        async with self.db_manager.session(auto_commit=False) as db:
            # 从数据库获取 SMTP 配置
            stmt = select(SystemSettings).where(SystemSettings.key == 'smtp_config')
            result = await db.execute(stmt)
            smtp_settings = result.scalar_one_or_none()
            
            if not smtp_settings:
                raise Exception("SMTP 未配置，请在系统设置中配置邮件服务器")
            
            smtp_config = smtp_settings.value
        
        to_addresses = channel.config.get('to', [])
        cc_addresses = channel.config.get('cc', [])
        subject_prefix = channel.config.get('subject_prefix', '[Alert]')
        
        # 构建邮件
        status = "恢复" if is_recovery else "触发"
        subject = f"{subject_prefix} {alert.severity.upper()} - {alert.rule_name} ({status})"
        
        # 构建HTML内容
        html_content = self.build_email_html(alert, is_recovery)
        
        message = MIMEMultipart('alternative')
        message['Subject'] = subject
        message['From'] = smtp_config.get('from_addr', 'alert@example.com')
        message['To'] = ', '.join(to_addresses)
        if cc_addresses:
            message['Cc'] = ', '.join(cc_addresses)
        
        html_part = MIMEText(html_content, 'html')
        message.attach(html_part)
        
        # 发送邮件
        await aiosmtplib.send(
            message,
            hostname=smtp_config.get('host'),
            port=smtp_config.get('port'),
            username=smtp_config.get('username'),
            password=smtp_config.get('password'),
            use_tls=smtp_config.get('use_tls', True)
        )
    
    async def send_webhook(self, channel: NotificationChannel, alert: AlertEvent, is_recovery: bool):
        """发送自定义Webhook通知"""
        webhook_url = channel.config.get('url')
        method = channel.config.get('method', 'POST').upper()
        headers = channel.config.get('headers', {})
        body_template = channel.config.get('body_template', 'default')
        
        if not webhook_url:
            raise Exception("Webhook URL 未配置")
        
        # 渲染注释中的模板变量
        rendered_annotations = self.render_annotations(alert)
        
        # 构建请求体
        if body_template == 'default':
            # 默认格式：标准 JSON
            payload = {
                "status": "resolved" if is_recovery else "firing",
                "alert": {
                    "fingerprint": alert.fingerprint,
                    "rule_name": alert.rule_name,
                    "rule_id": alert.rule_id,
                    "severity": alert.severity,
                    "status": alert.status,
                    "value": alert.value,
                    "started_at": alert.started_at,
                    "labels": alert.labels,
                    "annotations": rendered_annotations,
                    "expr": alert.expr
                },
                "is_recovery": is_recovery
            }
        else:
            # 自定义模板（JSON字符串）
            try:
                import jinja2
                template = jinja2.Template(body_template)
                payload_str = template.render(
                    alert=alert,
                    is_recovery=is_recovery,
                    status="resolved" if is_recovery else "firing"
                )
                payload = json.loads(payload_str)
            except Exception as e:
                logger.warning(f"自定义模板解析失败，使用默认格式: {str(e)}")
                payload = {
                    "status": "resolved" if is_recovery else "firing",
                    "alert": {
                        "fingerprint": alert.fingerprint,
                        "rule_name": alert.rule_name,
                        "severity": alert.severity,
                        "value": alert.value,
                        "labels": alert.labels
                    }
                }
        
        # 设置默认 Content-Type
        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'
        
        # 发送请求
        async with httpx.AsyncClient() as client:
            if method == 'POST':
                response = await client.post(webhook_url, json=payload, headers=headers, timeout=10)
            elif method == 'PUT':
                response = await client.put(webhook_url, json=payload, headers=headers, timeout=10)
            else:
                raise Exception(f"不支持的HTTP方法: {method}")
            
            response.raise_for_status()
            logger.info(f"Webhook发送成功: {webhook_url}, status={response.status_code}")
    
    @staticmethod
    def build_alert_text(alert: AlertEvent, is_recovery: bool) -> str:
        """构建告警文本"""
        status = "【恢复】" if is_recovery else "【告警】"
        labels_text = "\n".join([f"{k}: {v}" for k, v in alert.labels.items()])
        
        # 渲染注释
        rendered_annotations = NotificationService.render_annotations(alert)
        annotations_text = ""
        if rendered_annotations:
            summary = rendered_annotations.get('summary', '')
            description = rendered_annotations.get('description', '')
            if summary:
                annotations_text += f"\n摘要: {summary}"
            if description:
                annotations_text += f"\n描述: {description}"
        
        text = f"""{status}
告警名称: {alert.rule_name}
告警等级: {alert.severity}
当前值: {alert.value}
触发时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(alert.started_at))}{annotations_text}

标签:
{labels_text}
"""
        return text
    
    @staticmethod
    def build_email_html(alert: AlertEvent, is_recovery: bool) -> str:
        """构建邮件HTML内容"""
        status = "告警恢复" if is_recovery else "告警触发"
        status_color = "#28a745" if is_recovery else "#dc3545"
        
        # 渲染注释
        rendered_annotations = NotificationService.render_annotations(alert)
        
        labels_html = "".join([f"<tr><td><strong>{k}</strong></td><td>{v}</td></tr>" for k, v in alert.labels.items()])
        
        # 构建注释部分
        annotations_html = ""
        if rendered_annotations:
            summary = rendered_annotations.get('summary', '')
            description = rendered_annotations.get('description', '')
            if summary or description:
                annotations_html = "<h3>告警信息</h3><table>"
                if summary:
                    annotations_html += f"<tr><td><strong>摘要</strong></td><td>{summary}</td></tr>"
                if description:
                    annotations_html += f"<tr><td><strong>描述</strong></td><td>{description}</td></tr>"
                annotations_html += "</table>"
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: {status_color}; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{status}</h1>
            </div>
            <div class="content">
                <h2>{alert.rule_name}</h2>
                <table>
                    <tr><td><strong>告警等级</strong></td><td>{alert.severity}</td></tr>
                    <tr><td><strong>当前值</strong></td><td>{alert.value}</td></tr>
                    <tr><td><strong>触发时间</strong></td><td>{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(alert.started_at))}</td></tr>
                </table>
                {annotations_html}
                <h3>标签</h3>
                <table>
                    {labels_html}
                </table>
            </div>
        </body>
        </html>
        """
        return html
    
    async def record_notification(
        self, 
        channel: NotificationChannel, 
        alert: AlertEvent, 
        status: str, 
        error_message: Optional[str]
    ):
        """记录通知"""
        # 构建可序列化的告警内容（去除 datetime 对象）
        content = {
            "fingerprint": alert.fingerprint,
            "rule_id": alert.rule_id,
            "rule_name": alert.rule_name,
            "status": alert.status,
            "severity": alert.severity,
            "value": alert.value,
            "started_at": alert.started_at,
            "last_eval_at": alert.last_eval_at,
            "last_sent_at": alert.last_sent_at,
            "labels": alert.labels,
            "annotations": alert.annotations,
            "expr": alert.expr
        }
        
        record = NotificationRecord(
            channel_id=channel.id,
            channel_name=channel.name,
            channel_type=channel.type,
            alert_fingerprint=alert.fingerprint,
            alert_name=alert.rule_name,
            severity=alert.severity,
            status=status,
            error_message=error_message,
            content=content,
            sent_at=int(time.time()),
            tenant_id=alert.tenant_id
        )
        
        # 使用独立的数据库会话保存记录
        async with self.db_manager.session() as db:
            db.add(record)
            await db.commit()
    
    # ===== 批量告警发送方法 =====
    
    async def send_feishu_batch(self, channel: NotificationChannel, alerts: List[AlertEvent], is_recovery: bool):
        """批量发送飞书通知"""
        webhook_url = channel.config.get('webhook_url')
        card_type = channel.config.get('card_type', 'advanced')
        
        if len(alerts) == 1:
            # 单个告警，使用原有模板
            await self.send_feishu(channel, alerts[0], is_recovery)
            return
        
        # 多个告警，使用合并模板
        if card_type == 'advanced':
            card = self.build_feishu_batch_card(alerts, is_recovery)
        else:
            content = self.build_batch_alert_text(alerts, is_recovery)
            card = {
                "msg_type": "text",
                "content": {"text": content}
            }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=card, timeout=10)
            response.raise_for_status()
    
    @staticmethod
    def build_feishu_batch_card(alerts: List[AlertEvent], is_recovery: bool) -> dict:
        """构建飞书批量告警消息卡片"""
        status_color = "red" if not is_recovery else "green"
        status_text = "告警触发" if not is_recovery else "告警恢复"
        alert_count = len(alerts)
        
        # 获取规则名称（所有告警应该是同一规则）
        rule_name = alerts[0].rule_name
        
        # 构建告警列表
        alert_items = []
        for i, alert in enumerate(alerts[:10], 1):  # 最多显示10条
            labels_text = ", ".join([f"{k}={v}" for k, v in alert.labels.items()])
            alert_items.append(
                {
                    "tag": "div",
                    "text": {
                        "content": f"**告警 {i}** [{alert.severity}]\n"
                                   f"值: {alert.value}\n"
                                   f"标签: {labels_text}",
                        "tag": "lark_md"
                    }
                }
            )
            # 添加分隔线
            if i < min(len(alerts), 10):
                alert_items.append({"tag": "hr"})
        
        # 如果告警数量超过10条，添加提示
        if alert_count > 10:
            alert_items.append({
                "tag": "div",
                "text": {
                    "content": f"**还有 {alert_count - 10} 条告警未显示...**",
                    "tag": "lark_md"
                }
            })
        
        card = {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True
                },
                "header": {
                    "title": {
                        "content": f"🔔 {status_text} (共 {alert_count} 条)",
                        "tag": "plain_text"
                    },
                    "template": status_color
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "content": f"**告警规则**: {rule_name}",
                            "tag": "lark_md"
                        }
                    },
                    {
                        "tag": "hr"
                    }
                ] + alert_items
            }
        }
        
        return card
    
    async def send_dingtalk_batch(self, channel: NotificationChannel, alerts: List[AlertEvent], is_recovery: bool):
        """批量发送钉钉通知"""
        if len(alerts) == 1:
            await self.send_dingtalk(channel, alerts[0], is_recovery)
            return
        
        import hashlib
        import hmac
        import base64
        import urllib.parse
        
        webhook_url = channel.config.get('webhook_url')
        secret = channel.config.get('secret', '')
        
        # 如果有secret，需要签名
        if secret:
            timestamp = str(round(time.time() * 1000))
            secret_enc = secret.encode('utf-8')
            string_to_sign = f'{timestamp}\n{secret}'
            string_to_sign_enc = string_to_sign.encode('utf-8')
            hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
            sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
            webhook_url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"
        
        # 构建消息
        content = self.build_batch_alert_text(alerts, is_recovery)
        message = {
            "msgtype": "text",
            "text": {
                "content": content
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=message, timeout=10)
            response.raise_for_status()
    
    async def send_wechat_batch(self, channel: NotificationChannel, alerts: List[AlertEvent], is_recovery: bool):
        """批量发送企业微信通知"""
        if len(alerts) == 1:
            await self.send_wechat(channel, alerts[0], is_recovery)
            return
        
        webhook_url = channel.config.get('webhook_url')
        
        content = self.build_batch_alert_text(alerts, is_recovery)
        message = {
            "msgtype": "text",
            "text": {
                "content": content
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=message, timeout=10)
            response.raise_for_status()
    
    async def send_email_batch(self, channel: NotificationChannel, alerts: List[AlertEvent], is_recovery: bool):
        """批量发送邮件通知"""
        if len(alerts) == 1:
            await self.send_email(channel, alerts[0], is_recovery)
            return
        
        # 使用独立的数据库会话
        async with self.db_manager.session(auto_commit=False) as db:
            # 从数据库获取 SMTP 配置
            stmt = select(SystemSettings).where(SystemSettings.key == 'smtp_config')
            result = await db.execute(stmt)
            smtp_settings = result.scalar_one_or_none()
            
            if not smtp_settings:
                raise Exception("SMTP 未配置，请在系统设置中配置邮件服务器")
            
            smtp_config = smtp_settings.value
        
        to_addresses = channel.config.get('to', [])
        cc_addresses = channel.config.get('cc', [])
        subject_prefix = channel.config.get('subject_prefix', '[Alert]')
        
        # 构建邮件
        rule_name = alerts[0].rule_name
        alert_count = len(alerts)
        status = "恢复" if is_recovery else "触发"
        subject = f"{subject_prefix} {rule_name} - {alert_count} 条告警 ({status})"
        
        # 构建HTML内容
        html_content = self.build_email_batch_html(alerts, is_recovery)
        
        message = MIMEMultipart('alternative')
        message['Subject'] = subject
        message['From'] = smtp_config.get('from_addr', 'alert@example.com')
        message['To'] = ', '.join(to_addresses)
        if cc_addresses:
            message['Cc'] = ', '.join(cc_addresses)
        
        html_part = MIMEText(html_content, 'html')
        message.attach(html_part)
        
        # 发送邮件
        await aiosmtplib.send(
            message,
            hostname=smtp_config.get('host'),
            port=smtp_config.get('port'),
            username=smtp_config.get('username'),
            password=smtp_config.get('password'),
            use_tls=smtp_config.get('use_tls', True)
        )
    
    async def send_webhook_batch(self, channel: NotificationChannel, alerts: List[AlertEvent], is_recovery: bool):
        """批量发送自定义Webhook通知"""
        webhook_url = channel.config.get('url')
        method = channel.config.get('method', 'POST').upper()
        headers = channel.config.get('headers', {})
        body_template = channel.config.get('body_template', 'default')
        
        if not webhook_url:
            raise Exception("Webhook URL 未配置")
        
        # 构建请求体
        if body_template == 'default':
            # 默认格式：类似 Alertmanager 的格式
            payload = {
                "status": "resolved" if is_recovery else "firing",
                "groupLabels": alerts[0].labels if alerts else {},
                "commonLabels": self._get_common_labels(alerts),
                "alerts": [
                    {
                        "fingerprint": alert.fingerprint,
                        "status": alert.status,
                        "labels": alert.labels,
                        "annotations": self.render_annotations(alert),  # 渲染模板变量
                        "startsAt": alert.started_at,
                        "value": alert.value
                    }
                    for alert in alerts
                ]
            }
        else:
            # 自定义模板
            try:
                import jinja2
                template = jinja2.Template(body_template)
                payload_str = template.render(
                    alerts=alerts,
                    is_recovery=is_recovery,
                    status="resolved" if is_recovery else "firing",
                    alert_count=len(alerts)
                )
                payload = json.loads(payload_str)
            except Exception as e:
                logger.warning(f"自定义模板解析失败，使用默认格式: {str(e)}")
                payload = {
                    "status": "resolved" if is_recovery else "firing",
                    "alerts": [{"fingerprint": a.fingerprint, "labels": a.labels} for a in alerts]
                }
        
        # 设置默认 Content-Type
        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'
        
        # 发送请求
        async with httpx.AsyncClient() as client:
            if method == 'POST':
                response = await client.post(webhook_url, json=payload, headers=headers, timeout=10)
            elif method == 'PUT':
                response = await client.put(webhook_url, json=payload, headers=headers, timeout=10)
            else:
                raise Exception(f"不支持的HTTP方法: {method}")
            
            response.raise_for_status()
            logger.info(f"批量Webhook发送成功: {webhook_url}, 告警数={len(alerts)}")
    
    @staticmethod
    def _get_common_labels(alerts: List[AlertEvent]) -> Dict[str, str]:
        """获取所有告警的公共标签"""
        if not alerts:
            return {}
        
        # 从第一个告警开始
        common = dict(alerts[0].labels)
        
        # 找出所有告警共有的标签
        for alert in alerts[1:]:
            common = {k: v for k, v in common.items() if alert.labels.get(k) == v}
        
        return common
    
    @staticmethod
    def build_batch_alert_text(alerts: List[AlertEvent], is_recovery: bool) -> str:
        """构建批量告警文本"""
        status = "【恢复】" if is_recovery else "【告警】"
        rule_name = alerts[0].rule_name
        alert_count = len(alerts)
        
        text = f"""{status} {rule_name}
共 {alert_count} 条告警

"""
        # 添加每个告警的详情
        for i, alert in enumerate(alerts[:20], 1):  # 最多显示20条
            labels_text = ", ".join([f"{k}={v}" for k, v in alert.labels.items()])
            text += f"""
告警 {i}:
  等级: {alert.severity}
  值: {alert.value}
  时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(alert.started_at))}
  标签: {labels_text}
"""
        
        if alert_count > 20:
            text += f"\n还有 {alert_count - 20} 条告警未显示..."
        
        return text
    
    @staticmethod
    def build_email_batch_html(alerts: List[AlertEvent], is_recovery: bool) -> str:
        """构建批量告警邮件HTML内容"""
        status = "告警恢复" if is_recovery else "告警触发"
        status_color = "#28a745" if is_recovery else "#dc3545"
        rule_name = alerts[0].rule_name
        alert_count = len(alerts)
        
        # 构建告警列表HTML
        alerts_html = ""
        for i, alert in enumerate(alerts[:50], 1):  # 最多显示50条
            labels_html = "".join([f"<tr><td><strong>{k}</strong></td><td>{v}</td></tr>" for k, v in alert.labels.items()])
            
            alerts_html += f"""
            <div style="margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 5px;">
                <h3 style="margin-top: 0;">告警 {i} - {alert.severity.upper()}</h3>
                <table style="width: 100%;">
                    <tr><td><strong>当前值</strong></td><td>{alert.value}</td></tr>
                    <tr><td><strong>触发时间</strong></td><td>{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(alert.started_at))}</td></tr>
                </table>
                <h4>标签</h4>
                <table style="width: 100%;">
                    {labels_html}
                </table>
            </div>
            """
        
        if alert_count > 50:
            alerts_html += f"<p><strong>还有 {alert_count - 50} 条告警未显示...</strong></p>"
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: {status_color}; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{status}</h1>
                <h2>{rule_name} (共 {alert_count} 条)</h2>
            </div>
            <div class="content">
                {alerts_html}
            </div>
        </body>
        </html>
        """
        return html

