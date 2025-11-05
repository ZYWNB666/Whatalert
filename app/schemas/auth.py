"""认证相关 Schema"""
from pydantic import BaseModel


class Token(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Token 数据"""
    username: str | None = None


class UserLogin(BaseModel):
    """用户登录"""
    username: str
    password: str

