"""基础模型"""
import time
from typing import Any
from sqlalchemy import Column, Integer
from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    """基础模型类"""
    pass


class BaseModel(Base):
    """带有通用字段的基础模型"""
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(Integer, default=lambda: int(time.time()), nullable=False, comment="创建时间戳")
    updated_at = Column(Integer, default=lambda: int(time.time()), onupdate=lambda: int(time.time()), nullable=False, comment="更新时间戳")

    @declared_attr
    def __tablename__(cls) -> str:
        """自动生成表名"""
        return cls.__name__.lower()

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

