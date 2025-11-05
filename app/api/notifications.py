"""通知渠道 API"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.database import get_db
from app.models.notification import NotificationChannel
from app.models.user import User
from app.api.auth import get_current_user
from app.schemas.notification import (
    NotificationChannelCreate, 
    NotificationChannelUpdate, 
    NotificationChannelResponse
)

router = APIRouter()


@router.post("/", response_model=NotificationChannelResponse, status_code=201)
async def create_notification_channel(
    channel_data: NotificationChannelCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建通知渠道"""
    new_channel = NotificationChannel(
        **channel_data.dict(),
        tenant_id=current_user.tenant_id
    )
    
    db.add(new_channel)
    await db.commit()
    await db.refresh(new_channel)
    
    return new_channel


@router.get("/", response_model=List[NotificationChannelResponse])
async def list_notification_channels(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取通知渠道列表"""
    stmt = select(NotificationChannel).where(
        NotificationChannel.tenant_id == current_user.tenant_id
    )
    result = await db.execute(stmt)
    channels = result.scalars().all()
    
    return channels


@router.get("/{channel_id}", response_model=NotificationChannelResponse)
async def get_notification_channel(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取通知渠道详情"""
    stmt = select(NotificationChannel).where(
        and_(
            NotificationChannel.id == channel_id,
            NotificationChannel.tenant_id == current_user.tenant_id
        )
    )
    result = await db.execute(stmt)
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Notification channel not found")
    
    return channel


@router.put("/{channel_id}", response_model=NotificationChannelResponse)
async def update_notification_channel(
    channel_id: int,
    channel_data: NotificationChannelUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新通知渠道"""
    stmt = select(NotificationChannel).where(
        and_(
            NotificationChannel.id == channel_id,
            NotificationChannel.tenant_id == current_user.tenant_id
        )
    )
    result = await db.execute(stmt)
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Notification channel not found")
    
    for key, value in channel_data.dict(exclude_unset=True).items():
        setattr(channel, key, value)
    
    await db.commit()
    await db.refresh(channel)
    
    return channel


@router.delete("/{channel_id}")
async def delete_notification_channel(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除通知渠道"""
    stmt = select(NotificationChannel).where(
        and_(
            NotificationChannel.id == channel_id,
            NotificationChannel.tenant_id == current_user.tenant_id
        )
    )
    result = await db.execute(stmt)
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Notification channel not found")
    
    await db.delete(channel)
    await db.commit()
    
    return {"message": "Notification channel deleted"}


@router.post("/{channel_id}/test")
async def test_notification_channel(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """测试通知渠道"""
    stmt = select(NotificationChannel).where(
        and_(
            NotificationChannel.id == channel_id,
            NotificationChannel.tenant_id == current_user.tenant_id
        )
    )
    result = await db.execute(stmt)
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Notification channel not found")
    
    try:
        import httpx
        
        test_message = {
            "msg_type": "text",
            "content": {
                "text": "这是一条来自监控告警系统的测试消息"
            }
        }
        
        if channel.type == 'feishu':
            webhook_url = channel.config.get('webhook_url')
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=test_message, timeout=10)
                response.raise_for_status()
        elif channel.type == 'dingtalk':
            webhook_url = channel.config.get('webhook_url')
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=test_message, timeout=10)
                response.raise_for_status()
        elif channel.type == 'wechat':
            webhook_url = channel.config.get('webhook_url')
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=test_message, timeout=10)
                response.raise_for_status()
        elif channel.type == 'email':
            # Email 测试需要 SMTP 配置
            return {"status": "success", "message": "邮件通知需要配置 SMTP 服务器"}
        else:
            raise HTTPException(status_code=400, detail="不支持的通知类型")
        
        return {"status": "success", "message": "测试消息发送成功"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"测试失败: {str(e)}")
