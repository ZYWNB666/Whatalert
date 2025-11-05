"""数据源 API"""
from typing import List
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.db.database import get_db
from app.models.datasource import DataSource
from app.models.user import User
from app.api.auth import get_current_user
from app.schemas.datasource import DataSourceCreate, DataSourceUpdate, DataSourceResponse

router = APIRouter()


@router.post("/", response_model=DataSourceResponse, status_code=201)
async def create_datasource(
    datasource_data: DataSourceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建数据源"""
    # 检查名称是否已存在
    stmt = select(DataSource).where(
        and_(
            DataSource.tenant_id == current_user.tenant_id,
            DataSource.name == datasource_data.name
        )
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="数据源名称已存在")
    
    new_datasource = DataSource(
        **datasource_data.dict(),
        tenant_id=current_user.tenant_id
    )
    
    db.add(new_datasource)
    await db.commit()
    await db.refresh(new_datasource)
    
    return new_datasource


@router.get("/", response_model=List[DataSourceResponse])
async def list_datasources(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取数据源列表"""
    stmt = select(DataSource).where(DataSource.tenant_id == current_user.tenant_id)
    result = await db.execute(stmt)
    datasources = result.scalars().all()
    
    return datasources


@router.get("/{datasource_id}", response_model=DataSourceResponse)
async def get_datasource(
    datasource_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取数据源详情"""
    stmt = select(DataSource).where(
        and_(
            DataSource.id == datasource_id,
            DataSource.tenant_id == current_user.tenant_id
        )
    )
    result = await db.execute(stmt)
    datasource = result.scalar_one_or_none()
    
    if not datasource:
        raise HTTPException(status_code=404, detail="Datasource not found")
    
    return datasource


@router.put("/{datasource_id}", response_model=DataSourceResponse)
async def update_datasource(
    datasource_id: int,
    datasource_data: DataSourceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新数据源"""
    stmt = select(DataSource).where(
        and_(
            DataSource.id == datasource_id,
            DataSource.tenant_id == current_user.tenant_id
        )
    )
    result = await db.execute(stmt)
    datasource = result.scalar_one_or_none()
    
    if not datasource:
        raise HTTPException(status_code=404, detail="Datasource not found")
    
    for key, value in datasource_data.dict(exclude_unset=True).items():
        setattr(datasource, key, value)
    
    await db.commit()
    await db.refresh(datasource)
    
    return datasource


@router.delete("/{datasource_id}")
async def delete_datasource(
    datasource_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除数据源"""
    stmt = select(DataSource).where(
        and_(
            DataSource.id == datasource_id,
            DataSource.tenant_id == current_user.tenant_id
        )
    )
    result = await db.execute(stmt)
    datasource = result.scalar_one_or_none()
    
    if not datasource:
        raise HTTPException(status_code=404, detail="Datasource not found")
    
    await db.delete(datasource)
    await db.commit()
    
    return {"message": "Datasource deleted"}


@router.post("/{datasource_id}/test")
async def test_datasource(
    datasource_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """测试数据源连接"""
    stmt = select(DataSource).where(
        and_(
            DataSource.id == datasource_id,
            DataSource.tenant_id == current_user.tenant_id
        )
    )
    result = await db.execute(stmt)
    datasource = result.scalar_one_or_none()
    
    if not datasource:
        raise HTTPException(status_code=404, detail="Datasource not found")
    
    try:        
        headers = {}
        if datasource.auth_config:
            auth_type = datasource.auth_config.get('type')
            if auth_type == 'token':
                token = datasource.auth_config.get('token', '')
                # 如果 token 不包含 Bearer，自动添加
                if token and not token.startswith('Bearer '):
                    headers['Authorization'] = f'Bearer {token}'
                else:
                    headers['Authorization'] = token
            elif auth_type == 'basic':
                username = datasource.auth_config.get('username', '')
                password = datasource.auth_config.get('password', '')
        
        # 构建查询 URL
        base_url = datasource.url.rstrip('/')
        
        # 自动添加 /api/v1/query 路径
        # 对于 Prometheus: http://prometheus:9090 -> http://prometheus:9090/api/v1/query
        # 对于 VictoriaMetrics 多租户: http://vm:8428/select/0/prometheus -> http://vm:8428/select/0/prometheus/api/v1/query
        if base_url.endswith('/api/v1'):
            query_url = f"{base_url}/query"
        elif '/api/v1/' in base_url:
            # 已经包含完整路径
            query_url = base_url
        else:
            query_url = f"{base_url}/api/v1/query"
        
        # 发送测试查询
        verify_ssl = datasource.http_config.get('verify_ssl', True)
        timeout = datasource.http_config.get('timeout', 30)
        
        async with httpx.AsyncClient(verify=verify_ssl, timeout=timeout) as client:
            if datasource.auth_config.get('type') == 'basic':
                auth = (
                    datasource.auth_config.get('username', ''),
                    datasource.auth_config.get('password', '')
                )
                response = await client.get(
                    query_url,
                    params={"query": "up"},
                    headers=headers,
                    auth=auth
                )
            else:
                response = await client.get(
                    query_url,
                    params={"query": "up"},
                    headers=headers
                )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"连接失败: HTTP {response.status_code} - {response.text}"
            )
        
        result = response.json()
        
        # 检查响应格式
        if result.get('status') == 'success':
            data = result.get('data', {})
            metrics_count = len(data.get('result', []))
            return {
                "status": "success",
                "message": "连接成功",
                "metrics_count": metrics_count
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"查询失败: {result.get('error', '未知错误')}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"连接失败: {str(e)}")
