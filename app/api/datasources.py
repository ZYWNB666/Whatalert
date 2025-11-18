"""数据源 API"""
from typing import List
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.db.database import get_db
from app.models.datasource import DataSource
from app.models.user import User
from app.api.auth import get_current_user
from app.services.cache_service import CacheService
from app.schemas.datasource import DataSourceCreate, DataSourceUpdate, DataSourceResponse

router = APIRouter()


@router.post("/", response_model=DataSourceResponse, status_code=201)
async def create_datasource(
    datasource_data: DataSourceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建数据源"""
    # 检查名称是否已存在(同一项目内)
    stmt = select(DataSource).where(
        and_(
            DataSource.tenant_id == current_user.tenant_id,
            DataSource.project_id == datasource_data.project_id,
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
    
    # 使缓存失效
    await CacheService.invalidate_list_cache(
        CacheService.PREFIX_DATASOURCE,
        current_user.tenant_id,
        datasource_data.project_id
    )
    
    return new_datasource


@router.get("/", response_model=List[DataSourceResponse])
async def list_datasources(
    project_id: int = Query(None, description="项目ID,不传则显示所有项目"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取数据源列表(按项目隔离) - 带缓存"""
    # 生成缓存键
    cache_key = f"{CacheService.PREFIX_DATASOURCE}:list:tenant:{current_user.tenant_id}"
    if project_id is not None:
        cache_key += f":project:{project_id}"
    
    # 尝试从缓存获取
    cached_data = await CacheService.get(cache_key)
    if cached_data is not None:
        # 缓存命中，直接返回字典数据
        return cached_data
    
    # 缓存未命中，查询数据库
    conditions = [DataSource.tenant_id == current_user.tenant_id]
    if project_id is not None:
        conditions.append(DataSource.project_id == project_id)
    
    stmt = select(DataSource).where(and_(*conditions))
    result = await db.execute(stmt)
    datasources = result.scalars().all()
    
    # 转换为字典列表以便缓存和返回
    datasources_data = [ds.to_dict() for ds in datasources]
    
    # 存入缓存
    await CacheService.set(cache_key, datasources_data, CacheService.LIST_TTL)
    
    return datasources_data


@router.get("/{datasource_id}", response_model=DataSourceResponse)
async def get_datasource(
    datasource_id: int,
    project_id: int = Query(None, description="项目ID,不传则不校验项目"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取数据源详情 - 带缓存"""
    # 生成缓存键
    cache_key = f"{CacheService.PREFIX_DATASOURCE}:detail:{datasource_id}"
    
    # 尝试从缓存获取
    cached_data = await CacheService.get(cache_key)
    if cached_data is not None:
        # 缓存命中，直接返回字典数据
        return cached_data
    
    # 缓存未命中，查询数据库
    conditions = [
        DataSource.id == datasource_id,
        DataSource.tenant_id == current_user.tenant_id
    ]
    if project_id is not None:
        conditions.append(DataSource.project_id == project_id)
    
    stmt = select(DataSource).where(and_(*conditions))
    result = await db.execute(stmt)
    datasource = result.scalar_one_or_none()
    
    if not datasource:
        raise HTTPException(status_code=404, detail="Datasource not found")
    
    # 转换为字典以便缓存和返回
    datasource_data = datasource.to_dict()
    
    # 存入缓存
    await CacheService.set(cache_key, datasource_data, CacheService.DETAIL_TTL)
    
    return datasource_data


@router.put("/{datasource_id}", response_model=DataSourceResponse)
async def update_datasource(
    datasource_id: int,
    datasource_data: DataSourceUpdate,
    project_id: int = Query(None, description="项目ID,不传则不校验项目"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新数据源"""
    conditions = [
        DataSource.id == datasource_id,
        DataSource.tenant_id == current_user.tenant_id
    ]
    if project_id is not None:
        conditions.append(DataSource.project_id == project_id)
    
    stmt = select(DataSource).where(and_(*conditions))
    result = await db.execute(stmt)
    datasource = result.scalar_one_or_none()
    
    if not datasource:
        raise HTTPException(status_code=404, detail="Datasource not found")
    
    for key, value in datasource_data.dict(exclude_unset=True).items():
        setattr(datasource, key, value)
    
    await db.commit()
    await db.refresh(datasource)
    
    # 使缓存失效
    await CacheService.invalidate_detail_cache(CacheService.PREFIX_DATASOURCE, datasource_id)
    await CacheService.invalidate_list_cache(
        CacheService.PREFIX_DATASOURCE,
        current_user.tenant_id,
        datasource.project_id
    )
    
    return datasource


@router.delete("/{datasource_id}")
async def delete_datasource(
    datasource_id: int,
    project_id: int = Query(None, description="项目ID,不传则不校验项目"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除数据源"""
    conditions = [
        DataSource.id == datasource_id,
        DataSource.tenant_id == current_user.tenant_id
    ]
    if project_id is not None:
        conditions.append(DataSource.project_id == project_id)
    
    stmt = select(DataSource).where(and_(*conditions))
    result = await db.execute(stmt)
    datasource = result.scalar_one_or_none()
    
    if not datasource:
        raise HTTPException(status_code=404, detail="Datasource not found")
    
    # 保存项目ID用于缓存失效
    datasource_project_id = datasource.project_id
    
    await db.delete(datasource)
    await db.commit()
    
    # 使缓存失效
    await CacheService.invalidate_detail_cache(CacheService.PREFIX_DATASOURCE, datasource_id)
    await CacheService.invalidate_list_cache(
        CacheService.PREFIX_DATASOURCE,
        current_user.tenant_id,
        datasource_project_id
    )
    
    return {"message": "Datasource deleted"}


@router.post("/{datasource_id}/test")
async def test_datasource(
    datasource_id: int,
    project_id: int = Query(None, description="项目ID,不传则不校验项目"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """测试数据源连接"""
    conditions = [
        DataSource.id == datasource_id,
        DataSource.tenant_id == current_user.tenant_id
    ]
    if project_id is not None:
        conditions.append(DataSource.project_id == project_id)
    
    stmt = select(DataSource).where(and_(*conditions))
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
        
        # 统一添加 /api/v1/query 路径
        if base_url.endswith('/api/v1'):
            query_url = f"{base_url}/query"
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
