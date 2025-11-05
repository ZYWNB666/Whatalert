"""租户模型"""
from sqlalchemy import Column, String, Boolean, Integer, JSON
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Tenant(BaseModel):
    """租户模型"""
    __tablename__ = "tenant"

    name = Column(String(100), unique=True, nullable=False, index=True, comment="租户名称")
    code = Column(String(50), unique=True, nullable=False, index=True, comment="租户代码")
    description = Column(String(500), comment="描述")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    
    # 配额设置
    quota_config = Column(JSON, default={}, comment="配额配置")
    # 示例: {"max_users": 100, "max_alert_rules": 1000, "max_datasources": 50}
    
    # 自定义配置
    settings = Column(JSON, default={}, comment="租户设置")
    
    # 关系
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    roles = relationship("Role", back_populates="tenant", cascade="all, delete-orphan")
    alert_rules = relationship("AlertRule", back_populates="tenant", cascade="all, delete-orphan")
    datasources = relationship("DataSource", back_populates="tenant", cascade="all, delete-orphan")
    silence_rules = relationship("SilenceRule", back_populates="tenant", cascade="all, delete-orphan")
    notification_channels = relationship("NotificationChannel", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tenant(name='{self.name}', code='{self.code}')>"

