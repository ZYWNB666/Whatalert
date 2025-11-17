"""静默规则模型"""
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, JSON, BigInteger, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class SilenceRule(BaseModel):
    """静默规则模型"""
    __tablename__ = "silence_rule"

    name = Column(String(200), nullable=False, comment="规则名称")
    description = Column(Text, comment="描述")
    
    # 匹配器（用于匹配告警标签）
    matchers = Column(JSON, nullable=False, comment="匹配器")
    # 示例: [
    #   {"label": "alertname", "operator": "=", "value": "HighCPU"},
    #   {"label": "severity", "operator": "=~", "value": "warning|critical"}
    # ]
    # 操作符: = (等于), != (不等于), =~ (正则匹配), !~ (正则不匹配)
    
    # 时间范围
    starts_at = Column(BigInteger, nullable=False, comment="开始时间戳")
    ends_at = Column(BigInteger, nullable=False, comment="结束时间戳")
    
    # 状态
    is_enabled = Column(Boolean, default=True, nullable=False, comment="是否启用")
    
    # 创建者
    created_by = Column(String(100), comment="创建者")
    comment = Column(Text, comment="备注")
    
    # 多租户和项目
    tenant_id = Column(Integer, ForeignKey('tenant.id', ondelete='CASCADE'), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey('project.id', ondelete='CASCADE'), nullable=True, index=True, comment="项目ID")
    
    # 关系
    tenant = relationship("Tenant", back_populates="silence_rules")
    project = relationship("Project", back_populates="silence_rules")

    def __repr__(self):
        return f"<SilenceRule(name='{self.name}', enabled='{self.is_enabled}')>"

