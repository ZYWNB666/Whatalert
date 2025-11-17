"""通知渠道模型"""
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, JSON, BigInteger, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class NotificationChannel(BaseModel):
    """通知渠道模型"""
    __tablename__ = "notification_channel"

    name = Column(String(100), nullable=False, comment="渠道名称")
    type = Column(String(50), nullable=False, comment="渠道类型")  # feishu, dingtalk, wechat, email
    description = Column(Text, comment="描述")
    
    # 渠道配置
    config = Column(JSON, nullable=False, comment="渠道配置")
    # 飞书示例: {"webhook_url": "https://...", "secret": "xxx", "card_type": "advanced"}
    # 钉钉示例: {"webhook_url": "https://...", "secret": "xxx"}
    # 企业微信示例: {"webhook_url": "https://..."}
    # 邮件示例: {"to": ["user1@example.com", "user2@example.com"], "cc": [], "subject_prefix": "[Alert]"}
    # Webhook示例: {"url": "https://...", "method": "POST", "headers": {"Authorization": "Bearer xxx"}, "body_template": "default"}
    
    # 标签过滤
    filter_config = Column(JSON, default={}, comment="过滤配置")
    # 示例: {
    #   "include_labels": {"severity": ["critical", "warning"]},  # 只包含这些标签
    #   "exclude_labels": {"team": ["test"]}                      # 排除这些标签
    # }
    
    # 状态
    is_enabled = Column(Boolean, default=True, nullable=False, comment="是否启用")
    is_default = Column(Boolean, default=False, comment="是否默认渠道")
    
    # 多租户和项目
    tenant_id = Column(Integer, ForeignKey('tenant.id', ondelete='CASCADE'), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey('project.id', ondelete='CASCADE'), nullable=True, index=True, comment="项目ID")
    
    # 关系
    tenant = relationship("Tenant", back_populates="notification_channels")
    project = relationship("Project", back_populates="notification_channels")
    records = relationship("NotificationRecord", back_populates="channel", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<NotificationChannel(name='{self.name}', type='{self.type}')>"


class NotificationRecord(BaseModel):
    """通知记录"""
    __tablename__ = "notification_record"

    channel_id = Column(Integer, ForeignKey('notification_channel.id', ondelete='SET NULL'), index=True)
    channel_name = Column(String(100), comment="渠道名称")
    channel_type = Column(String(50), comment="渠道类型")
    
    # 告警信息
    alert_fingerprint = Column(String(100), index=True, comment="告警指纹")
    alert_name = Column(String(200), comment="告警名称")
    severity = Column(String(20), comment="告警等级")
    
    # 发送状态
    status = Column(String(20), default="pending", comment="状态")  # pending, success, failed
    error_message = Column(Text, comment="错误信息")
    
    # 发送内容
    content = Column(JSON, comment="发送内容")
    
    # 发送时间
    sent_at = Column(BigInteger, comment="发送时间戳")
    
    # 多租户
    tenant_id = Column(Integer, ForeignKey('tenant.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # 关系
    channel = relationship("NotificationChannel", back_populates="records")

    def __repr__(self):
        return f"<NotificationRecord(alert='{self.alert_name}', status='{self.status}')>"

