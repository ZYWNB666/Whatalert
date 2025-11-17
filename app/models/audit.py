"""审计日志模型"""
import time
from sqlalchemy import Column, String, Integer, ForeignKey, JSON, BigInteger, Text
from app.models.base import Base


class AuditLog(Base):
    """审计日志"""
    __tablename__ = "audit_log"
    
    # 主键
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 操作信息
    action = Column(String(50), nullable=False, comment="操作类型")  # create, update, delete, login, etc.
    resource_type = Column(String(50), nullable=False, comment="资源类型")  # user, alert_rule, datasource, etc.
    resource_id = Column(Integer, comment="资源ID")
    resource_name = Column(String(200), comment="资源名称")
    
    # 操作者信息
    user_id = Column(Integer, index=True, comment="用户ID")
    username = Column(String(50), comment="用户名")
    
    # 请求信息
    ip_address = Column(String(50), comment="IP地址")
    user_agent = Column(String(500), comment="User Agent")
    request_method = Column(String(10), comment="请求方法")
    request_path = Column(String(500), comment="请求路径")
    
    # 变更内容
    changes = Column(JSON, comment="变更内容")
    # 示例: {"old": {...}, "new": {...}}
    
    # 结果
    status = Column(String(20), default="success", comment="状态")  # success, failed
    error_message = Column(Text, comment="错误信息")
    
    # 时间戳
    timestamp = Column(BigInteger, nullable=False, comment="时间戳")
    
    # 多租户
    tenant_id = Column(Integer, ForeignKey('tenant.id', ondelete='CASCADE'), index=True)
    
    # 只有创建时间，没有更新时间（审计日志不应该被修改）
    created_at = Column(Integer, default=lambda: int(time.time()), nullable=False, comment="创建时间戳")

    def __repr__(self):
        return f"<AuditLog(action='{self.action}', resource='{self.resource_type}')>"

