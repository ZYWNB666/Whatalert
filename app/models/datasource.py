"""数据源模型"""
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class DataSource(BaseModel):
    """数据源模型"""
    __tablename__ = "datasource"

    name = Column(String(100), nullable=False, comment="数据源名称")
    type = Column(String(50), nullable=False, comment="数据源类型")  # prometheus, victoriametrics
    url = Column(String(500), nullable=False, comment="数据源地址")
    description = Column(String(500), comment="描述")
    is_default = Column(Boolean, default=False, comment="是否默认数据源")
    is_enabled = Column(Boolean, default=True, nullable=False, comment="是否启用")
    
    # 认证配置
    auth_config = Column(JSON, default={}, comment="认证配置")
    # 示例: {"type": "basic", "username": "xxx", "password": "xxx"}
    #       {"type": "token", "token": "Bearer xxx"}
    
    # HTTP 配置
    http_config = Column(JSON, default={}, comment="HTTP配置")
    # 示例: {"timeout": 30, "verify_ssl": true, "headers": {}}
    
    # 额外标签（会附加到所有查询结果）
    extra_labels = Column(JSON, default={}, comment="额外标签")
    
    # 多租户和项目
    tenant_id = Column(Integer, ForeignKey('tenant.id', ondelete='CASCADE'), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey('project.id', ondelete='CASCADE'), nullable=True, index=True, comment="项目ID")
    
    # 关系
    tenant = relationship("Tenant", back_populates="datasources")
    project = relationship("Project", back_populates="datasources")
    alert_rules = relationship("AlertRule", back_populates="datasource")

    def __repr__(self):
        return f"<DataSource(name='{self.name}', type='{self.type}')>"

