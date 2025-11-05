"""系统设置模型"""
from sqlalchemy import Column, String, Integer, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class SystemSettings(BaseModel):
    """系统设置模型"""
    __tablename__ = "system_settings"

    # 设置键值对
    key = Column(String(100), unique=True, nullable=False, index=True, comment="设置键")
    value = Column(JSON, nullable=False, comment="设置值")
    description = Column(String(500), comment="描述")
    category = Column(String(50), comment="分类")  # smtp, general, etc.
    
    # 多租户（系统级设置可以设为 0 或 null）
    tenant_id = Column(Integer, ForeignKey('tenant.id', ondelete='CASCADE'), nullable=True, index=True)

    def __repr__(self):
        return f"<SystemSettings(key='{self.key}')>"

