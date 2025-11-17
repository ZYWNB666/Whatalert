"""告警规则和告警事件模型"""
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, JSON, Text, BigInteger, Float
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class AlertRule(BaseModel):
    """告警规则模型"""
    __tablename__ = "alert_rule"

    name = Column(String(200), nullable=False, comment="规则名称")
    description = Column(Text, comment="描述")
    
    # PromQL 表达式
    expr = Column(Text, nullable=False, comment="PromQL表达式")
    
    # 评估配置
    eval_interval = Column(Integer, default=60, nullable=False, comment="评估间隔(秒)")
    for_duration = Column(Integer, default=60, comment="持续时间(秒)")  # 满足条件持续多久才告警
    repeat_interval = Column(Integer, default=1800, nullable=False, comment="重复发送间隔(秒)")  # 默认30分钟
    
    # 告警等级
    severity = Column(String(20), default="warning", comment="告警等级")  # critical, warning, info
    
    # 标签和注释
    labels = Column(JSON, default={}, comment="标签")
    annotations = Column(JSON, default={}, comment="注释")
    
    # 告警路由配置
    route_config = Column(JSON, default={}, comment="路由配置")
    # 示例: {
    #   "match_labels": {"team": "backend"},  # 匹配标签
    #   "notification_channels": [1, 2, 3]     # 通知渠道ID列表
    # }
    
    # 状态
    is_enabled = Column(Boolean, default=True, nullable=False, comment="是否启用")
    
    # 数据源
    datasource_id = Column(Integer, ForeignKey('datasource.id', ondelete='CASCADE'), nullable=False)
    
    # 多租户和项目
    tenant_id = Column(Integer, ForeignKey('tenant.id', ondelete='CASCADE'), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey('project.id', ondelete='CASCADE'), nullable=True, index=True, comment="项目ID")
    
    # 关系
    tenant = relationship("Tenant", back_populates="alert_rules")
    project = relationship("Project", back_populates="alert_rules")
    datasource = relationship("DataSource", back_populates="alert_rules")
    events = relationship("AlertEvent", back_populates="rule", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AlertRule(name='{self.name}', severity='{self.severity}')>"


class AlertEvent(BaseModel):
    """当前告警事件"""
    __tablename__ = "alert_event"

    # 指纹（用于标识唯一告警）
    fingerprint = Column(String(100), unique=True, nullable=False, index=True, comment="指纹")
    
    # 关联规则
    rule_id = Column(Integer, ForeignKey('alert_rule.id', ondelete='CASCADE'), nullable=False, index=True)
    rule_name = Column(String(200), nullable=False, comment="规则名称")
    
    # 状态
    status = Column(String(20), default="firing", nullable=False, comment="状态")  # pending, firing, resolved
    severity = Column(String(20), nullable=False, comment="告警等级")
    
    # 时间戳
    started_at = Column(BigInteger, nullable=False, comment="开始时间")
    last_eval_at = Column(BigInteger, nullable=False, comment="最后评估时间")
    last_sent_at = Column(BigInteger, default=0, comment="最后发送时间")
    
    # 值
    value = Column(Float, comment="触发值")
    
    # 标签和注释
    labels = Column(JSON, default={}, comment="标签")
    annotations = Column(JSON, default={}, comment="注释")
    
    # 查询语句
    expr = Column(Text, comment="查询表达式")
    
    # 多租户和项目
    tenant_id = Column(Integer, ForeignKey('tenant.id', ondelete='CASCADE'), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey('project.id', ondelete='CASCADE'), nullable=True, index=True, comment="项目ID")
    
    # 关系
    rule = relationship("AlertRule", back_populates="events")

    def __repr__(self):
        return f"<AlertEvent(fingerprint='{self.fingerprint}', status='{self.status}')>"


class AlertEventHistory(BaseModel):
    """历史告警事件"""
    __tablename__ = "alert_event_history"

    fingerprint = Column(String(100), nullable=False, index=True, comment="指纹")
    rule_id = Column(Integer, comment="规则ID")
    rule_name = Column(String(200), comment="规则名称")
    status = Column(String(20), comment="状态")
    severity = Column(String(20), comment="告警等级")
    
    started_at = Column(BigInteger, comment="开始时间")
    resolved_at = Column(BigInteger, comment="恢复时间")
    duration = Column(BigInteger, comment="持续时间(秒)")
    
    value = Column(Float, comment="触发值")
    labels = Column(JSON, default={}, comment="标签")
    annotations = Column(JSON, default={}, comment="注释")
    expr = Column(Text, comment="查询表达式")
    
    # 多租户和项目
    tenant_id = Column(Integer, ForeignKey('tenant.id', ondelete='CASCADE'), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey('project.id', ondelete='CASCADE'), nullable=True, index=True, comment="项目ID")

    def __repr__(self):
        return f"<AlertEventHistory(fingerprint='{self.fingerprint}', duration='{self.duration}')>"

