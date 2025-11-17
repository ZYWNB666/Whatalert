"""通知渠道 API"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
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
    # 如果未指定项目ID，使用用户当前项目
    project_id = channel_data.project_id
    if project_id is None and hasattr(current_user, 'current_project_id'):
        project_id = current_user.current_project_id
    
    channel_dict = channel_data.dict()
    channel_dict['tenant_id'] = current_user.tenant_id
    channel_dict['project_id'] = project_id
    
    new_channel = NotificationChannel(**channel_dict)
    
    db.add(new_channel)
    await db.commit()
    await db.refresh(new_channel)
    
    return new_channel


@router.get("/", response_model=List[NotificationChannelResponse])
async def list_notification_channels(
    project_id: int = Query(None, description="项目ID,不传则显示所有项目"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取通知渠道列表"""
    conditions = [NotificationChannel.tenant_id == current_user.tenant_id]
    if project_id is not None:
        conditions.append(NotificationChannel.project_id == project_id)
    
    stmt = select(NotificationChannel).where(and_(*conditions))
    result = await db.execute(stmt)
    channels = result.scalars().all()
    
    return channels


@router.get("/{channel_id}", response_model=NotificationChannelResponse)
async def get_notification_channel(
    channel_id: int,
    project_id: int = Query(None, description="项目ID,不传则不校验项目"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取通知渠道详情"""
    conditions = [
        NotificationChannel.id == channel_id,
        NotificationChannel.tenant_id == current_user.tenant_id
    ]
    if project_id is not None:
        conditions.append(NotificationChannel.project_id == project_id)
    
    stmt = select(NotificationChannel).where(and_(*conditions))
    result = await db.execute(stmt)
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Notification channel not found")
    
    return channel


@router.put("/{channel_id}", response_model=NotificationChannelResponse)
async def update_notification_channel(
    channel_id: int,
    channel_data: NotificationChannelUpdate,
    project_id: int = Query(None, description="项目ID,不传则不校验项目"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新通知渠道"""
    conditions = [
        NotificationChannel.id == channel_id,
        NotificationChannel.tenant_id == current_user.tenant_id
    ]
    if project_id is not None:
        conditions.append(NotificationChannel.project_id == project_id)
    
    stmt = select(NotificationChannel).where(and_(*conditions))
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
    project_id: int = Query(None, description="项目ID,不传则不校验项目"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除通知渠道"""
    conditions = [
        NotificationChannel.id == channel_id,
        NotificationChannel.tenant_id == current_user.tenant_id
    ]
    if project_id is not None:
        conditions.append(NotificationChannel.project_id == project_id)
    
    stmt = select(NotificationChannel).where(and_(*conditions))
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
    project_id: int = Query(None, description="项目ID,不传则不校验项目"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """测试通知渠道"""
    conditions = [
        NotificationChannel.id == channel_id,
        NotificationChannel.tenant_id == current_user.tenant_id
    ]
    if project_id is not None:
        conditions.append(NotificationChannel.project_id == project_id)
    
    stmt = select(NotificationChannel).where(and_(*conditions))
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
        elif channel.type == 'webhook':
            # 自定义 Webhook
            webhook_url = channel.config.get('url')
            method = channel.config.get('method', 'POST').upper()
            headers = channel.config.get('headers', {})
            body_template = channel.config.get('body_template', 'default')
            
            # 构建请求体
            if body_template == 'default' or not body_template:
                request_body = {
                    "alert_name": "测试告警",
                    "severity": "info",
                    "message": "这是一条来自监控告警系统的测试消息",
                    "timestamp": "2024-01-01T00:00:00Z"
                }
            else:
                # 使用自定义模板（支持字符串或对象）
                if isinstance(body_template, str):
                    try:
                        import json
                        request_body = json.loads(body_template)
                    except:
                        request_body = {"message": body_template}
                else:
                    request_body = body_template
            
            async with httpx.AsyncClient() as client:
                if method == 'GET':
                    response = await client.get(webhook_url, headers=headers, timeout=10)
                elif method == 'POST':
                    response = await client.post(webhook_url, json=request_body, headers=headers, timeout=10)
                elif method == 'PUT':
                    response = await client.put(webhook_url, json=request_body, headers=headers, timeout=10)
                else:
                    raise HTTPException(status_code=400, detail=f"不支持的 HTTP 方法: {method}")
                
                response.raise_for_status()
        elif channel.type == 'email':
            # Email 测试需要 SMTP 配置
            return {"status": "success", "message": "邮件通知需要配置 SMTP 服务器"}
        else:
            raise HTTPException(status_code=400, detail=f"不支持的通知类型: {channel.type}")
        
        return {"status": "success", "message": "测试消息发送成功"}
        
    except httpx.HTTPStatusError as e:
        # HTTP 状态码错误
        raise HTTPException(
            status_code=400, 
            detail=f"测试失败: HTTP {e.response.status_code} - {e.response.text[:200]}"
        )
    except httpx.RequestError as e:
        # 请求错误（网络问题等）
        raise HTTPException(
            status_code=400, 
            detail=f"测试失败: 网络请求错误 - {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"测试失败: {str(e)}")
