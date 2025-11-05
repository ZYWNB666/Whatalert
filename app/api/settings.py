"""系统设置 API"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.db.database import get_db
from app.models.settings import SystemSettings
from app.models.user import User
from app.api.auth import get_current_user

router = APIRouter()


@router.get("/smtp")
async def get_smtp_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取 SMTP 配置"""
    stmt = select(SystemSettings).where(
        and_(
            SystemSettings.key == 'smtp_config',
            or_(
                SystemSettings.tenant_id == current_user.tenant_id,
                SystemSettings.tenant_id == None
            )
        )
    )
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()
    
    if not settings:
        return {
            "host": "",
            "port": 587,
            "username": "",
            "password": "",
            "from_addr": "",
            "use_tls": True
        }
    
    return settings.value


@router.post("/smtp")
async def update_smtp_settings(
    smtp_config: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新 SMTP 配置"""
    # 只有超级管理员可以修改
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    stmt = select(SystemSettings).where(SystemSettings.key == 'smtp_config')
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()
    
    if settings:
        settings.value = smtp_config
    else:
        settings = SystemSettings(
            key='smtp_config',
            value=smtp_config,
            description='SMTP 邮件服务器配置',
            category='smtp',
            tenant_id=None  # 系统级配置
        )
        db.add(settings)
    
    await db.commit()
    
    return {"message": "SMTP 配置已更新"}


@router.post("/smtp/test")
async def test_smtp_settings(
    test_email: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """测试 SMTP 配置"""
    import aiosmtplib
    from email.mime.text import MIMEText
    
    # 获取 SMTP 配置
    stmt = select(SystemSettings).where(SystemSettings.key == 'smtp_config')
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()
    
    if not settings:
        raise HTTPException(status_code=400, detail="请先配置 SMTP")
    
    config = settings.value
    
    try:
        message = MIMEText("这是一条来自监控告警系统的测试邮件", 'plain', 'utf-8')
        message['Subject'] = '测试邮件'
        message['From'] = config.get('from_addr')
        message['To'] = test_email
        
        await aiosmtplib.send(
            message,
            hostname=config.get('host'),
            port=config.get('port'),
            username=config.get('username'),
            password=config.get('password'),
            use_tls=config.get('use_tls', True)
        )
        
        return {"status": "success", "message": f"测试邮件已发送到 {test_email}"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"发送失败: {str(e)}")

