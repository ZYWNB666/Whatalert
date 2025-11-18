# Redis缓存优化实施指南

## 概述

本文档说明如何使用Redis缓存来优化API响应速度，减少数据库查询压力。已为告警规则和数据源API实施了缓存，其他API可以按照相同的模式进行优化。

## 已实施的优化

### 1. 缓存服务 (`app/services/cache_service.py`)

创建了统一的缓存服务类，提供以下功能：

- **缓存键管理**：统一的键命名规范
- **缓存操作**：get、set、delete、delete_pattern
- **缓存失效**：列表缓存和详情缓存的失效策略
- **装饰器**：`@cache_list` 和 `@cache_detail`（可选使用）

#### 缓存键前缀

```python
PREFIX_ALERT_RULE = "alert_rule"
PREFIX_DATASOURCE = "datasource"
PREFIX_NOTIFICATION = "notification"
PREFIX_PROJECT = "project"
PREFIX_USER = "user"
PREFIX_SILENCE = "silence"
```

#### 缓存过期时间

```python
DEFAULT_TTL = 300  # 5分钟
LIST_TTL = 60      # 列表缓存1分钟
DETAIL_TTL = 300   # 详情缓存5分钟
```

### 2. 已优化的API

#### 告警规则API (`app/api/alert_rules.py`)

✅ **已实施**
- `GET /alert-rules/` - 列表查询（带缓存）
- `GET /alert-rules/{rule_id}` - 详情查询（带缓存）
- `POST /alert-rules/` - 创建后使列表缓存失效
- `PUT /alert-rules/{rule_id}` - 更新后使详情和列表缓存失效
- `DELETE /alert-rules/{rule_id}` - 删除后使详情和列表缓存失效

#### 数据源API (`app/api/datasources.py`)

✅ **已实施**
- `GET /datasources/` - 列表查询（带缓存）
- `GET /datasources/{datasource_id}` - 详情查询（带缓存）
- `POST /datasources/` - 创建后使列表缓存失效
- `PUT /datasources/{datasource_id}` - 更新后使详情和列表缓存失效
- `DELETE /datasources/{datasource_id}` - 删除后使详情和列表缓存失效

## 实施步骤

### 步骤1：导入缓存服务

在API文件顶部添加导入：

```python
from app.services.cache_service import CacheService
```

### 步骤2：为列表查询添加缓存

**原代码示例：**
```python
@router.get("/", response_model=List[NotificationChannelResponse])
async def list_notification_channels(
    project_id: int = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    conditions = [NotificationChannel.tenant_id == current_user.tenant_id]
    if project_id is not None:
        conditions.append(NotificationChannel.project_id == project_id)
    
    stmt = select(NotificationChannel).where(and_(*conditions))
    result = await db.execute(stmt)
    channels = result.scalars().all()
    
    return channels
```

**优化后代码：**
```python
@router.get("/", response_model=List[NotificationChannelResponse])
async def list_notification_channels(
    project_id: int = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取通知渠道列表 - 带缓存"""
    # 生成缓存键
    cache_key = CacheService._make_list_key(
        CacheService.PREFIX_NOTIFICATION,
        current_user.tenant_id,
        project_id
    )
    
    # 尝试从缓存获取
    cached_data = await CacheService.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    # 缓存未命中，查询数据库
    conditions = [NotificationChannel.tenant_id == current_user.tenant_id]
    if project_id is not None:
        conditions.append(NotificationChannel.project_id == project_id)
    
    stmt = select(NotificationChannel).where(and_(*conditions))
    result = await db.execute(stmt)
    channels = result.scalars().all()
    
    # 转换为字典列表以便缓存
    channels_data = [channel.to_dict() for channel in channels]
    
    # 存入缓存
    await CacheService.set(cache_key, channels_data, CacheService.LIST_TTL)
    
    return channels
```

### 步骤3：为详情查询添加缓存

**原代码示例：**
```python
@router.get("/{channel_id}", response_model=NotificationChannelResponse)
async def get_notification_channel(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(NotificationChannel).where(
        and_(
            NotificationChannel.id == channel_id,
            NotificationChannel.tenant_id == current_user.tenant_id
        )
    )
    result = await db.execute(stmt)
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    return channel
```

**优化后代码：**
```python
@router.get("/{channel_id}", response_model=NotificationChannelResponse)
async def get_notification_channel(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取通知渠道详情 - 带缓存"""
    # 生成缓存键
    cache_key = CacheService._make_key(
        CacheService.PREFIX_NOTIFICATION,
        "detail",
        channel_id
    )
    
    # 尝试从缓存获取
    cached_data = await CacheService.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    # 缓存未命中，查询数据库
    stmt = select(NotificationChannel).where(
        and_(
            NotificationChannel.id == channel_id,
            NotificationChannel.tenant_id == current_user.tenant_id
        )
    )
    result = await db.execute(stmt)
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # 转换为字典以便缓存
    channel_data = channel.to_dict()
    
    # 存入缓存
    await CacheService.set(cache_key, channel_data, CacheService.DETAIL_TTL)
    
    return channel
```

### 步骤4：在创建时使缓存失效

在创建操作的末尾添加：

```python
@router.post("/", response_model=NotificationChannelResponse, status_code=201)
async def create_notification_channel(
    channel_data: NotificationChannelCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # ... 创建逻辑 ...
    
    db.add(new_channel)
    await db.commit()
    await db.refresh(new_channel)
    
    # 使缓存失效
    await CacheService.invalidate_list_cache(
        CacheService.PREFIX_NOTIFICATION,
        current_user.tenant_id,
        channel_data.project_id
    )
    
    return new_channel
```

### 步骤5：在更新时使缓存失效

在更新操作的末尾添加：

```python
@router.put("/{channel_id}", response_model=NotificationChannelResponse)
async def update_notification_channel(
    channel_id: int,
    channel_data: NotificationChannelUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # ... 更新逻辑 ...
    
    await db.commit()
    await db.refresh(channel)
    
    # 使缓存失效
    await CacheService.invalidate_detail_cache(
        CacheService.PREFIX_NOTIFICATION,
        channel_id
    )
    await CacheService.invalidate_list_cache(
        CacheService.PREFIX_NOTIFICATION,
        current_user.tenant_id,
        channel.project_id
    )
    
    return channel
```

### 步骤6：在删除时使缓存失效

在删除操作中添加：

```python
@router.delete("/{channel_id}")
async def delete_notification_channel(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # ... 查询和验证 ...
    
    # 保存项目ID用于缓存失效
    channel_project_id = channel.project_id
    
    await db.delete(channel)
    await db.commit()
    
    # 使缓存失效
    await CacheService.invalidate_detail_cache(
        CacheService.PREFIX_NOTIFICATION,
        channel_id
    )
    await CacheService.invalidate_list_cache(
        CacheService.PREFIX_NOTIFICATION,
        current_user.tenant_id,
        channel_project_id
    )
    
    return {"message": "Channel deleted"}
```

## 待优化的API

### 1. 通知渠道API (`app/api/notifications.py`)

需要优化的接口：
- ✅ `GET /notifications/` - 列表查询
- ✅ `GET /notifications/{channel_id}` - 详情查询
- ✅ `POST /notifications/` - 创建
- ✅ `PUT /notifications/{channel_id}` - 更新
- ✅ `DELETE /notifications/{channel_id}` - 删除

使用前缀：`CacheService.PREFIX_NOTIFICATION`

### 2. 项目API (`app/api/projects.py`)

需要优化的接口：
- ✅ `GET /projects/` - 列表查询
- ✅ `GET /projects/{project_id}` - 详情查询
- ✅ `POST /projects/` - 创建
- ✅ `PUT /projects/{project_id}` - 更新
- ✅ `DELETE /projects/{project_id}` - 删除

使用前缀：`CacheService.PREFIX_PROJECT`

**注意**：项目列表需要考虑用户角色，缓存键应包含用户ID：
```python
cache_key = f"{CacheService.PREFIX_PROJECT}:list:tenant:{tenant_id}:user:{user_id}"
```

### 3. 用户API (`app/api/users.py`)

需要优化的接口：
- ✅ `GET /users/` - 列表查询
- ✅ `GET /users/{user_id}` - 详情查询
- ✅ `POST /users/` - 创建
- ✅ `PUT /users/{user_id}` - 更新
- ✅ `DELETE /users/{user_id}` - 删除

使用前缀：`CacheService.PREFIX_USER`

### 4. 静默规则API (`app/api/silence.py`)

需要优化的接口：
- ✅ `GET /silence/` - 列表查询
- ✅ `GET /silence/{rule_id}` - 详情查询
- ✅ `POST /silence/` - 创建
- ✅ `PUT /silence/{rule_id}` - 更新
- ✅ `DELETE /silence/{rule_id}` - 删除

使用前缀：`CacheService.PREFIX_SILENCE`

## 缓存策略说明

### 缓存键设计

1. **列表缓存键格式**：
   ```
   {prefix}:list:tenant:{tenant_id}:project:{project_id}
   {prefix}:list:tenant:{tenant_id}  # 不指定项目时
   ```

2. **详情缓存键格式**：
   ```
   {prefix}:detail:{item_id}
   ```

### 缓存失效策略

1. **创建操作**：
   - 使列表缓存失效（当前项目和租户级别）

2. **更新操作**：
   - 使详情缓存失效（当前项）
   - 使列表缓存失效（当前项目和租户级别）

3. **删除操作**：
   - 使详情缓存失效（当前项）
   - 使列表缓存失效（当前项目和租户级别）

### 缓存过期时间建议

- **列表缓存**：60秒（1分钟）
  - 原因：列表数据变化频繁，需要较短的过期时间
  
- **详情缓存**：300秒（5分钟）
  - 原因：详情数据相对稳定，可以使用较长的过期时间

- **特殊场景**：
  - 用户信息：可以设置更长的过期时间（如10分钟）
  - 项目信息：可以设置更长的过期时间（如10分钟）
  - 告警事件：不建议缓存（实时性要求高）

## 性能优化效果

### 预期提升

1. **列表查询**：
   - 缓存命中时：响应时间从 50-200ms 降低到 5-10ms
   - 数据库负载：减少 80-90%

2. **详情查询**：
   - 缓存命中时：响应时间从 20-100ms 降低到 5-10ms
   - 数据库负载：减少 80-90%

3. **并发能力**：
   - 可支持的并发请求数提升 5-10倍

### 监控指标

建议监控以下指标：

1. **缓存命中率**：
   ```python
   hit_rate = cache_hits / (cache_hits + cache_misses)
   ```
   目标：> 80%

2. **平均响应时间**：
   - 缓存命中：< 10ms
   - 缓存未命中：< 100ms

3. **数据库查询次数**：
   - 应该显著减少

## 注意事项

### 1. 数据一致性

- 缓存失效策略确保了数据的最终一致性
- 在高并发场景下，可能存在短暂的数据不一致（最多1分钟）
- 如果需要强一致性，可以考虑使用分布式锁

### 2. 内存使用

- 监控Redis内存使用情况
- 设置合理的过期时间
- 考虑使用LRU淘汰策略

### 3. 缓存穿透

- 对于不存在的数据，也应该缓存（设置较短的过期时间）
- 可以缓存空结果，避免频繁查询数据库

### 4. 缓存雪崩

- 避免大量缓存同时过期
- 可以在过期时间上添加随机值（如 ±10%）

### 5. 热点数据

- 对于访问频率特别高的数据，可以考虑：
  - 增加过期时间
  - 使用本地缓存（如LRU Cache）
  - 预热缓存

## 测试建议

### 1. 功能测试

```python
# 测试缓存命中
response1 = await client.get("/api/alert-rules/")
response2 = await client.get("/api/alert-rules/")
assert response1.json() == response2.json()

# 测试缓存失效
await client.post("/api/alert-rules/", json=new_rule_data)
response3 = await client.get("/api/alert-rules/")
assert len(response3.json()) == len(response1.json()) + 1
```

### 2. 性能测试

```bash
# 使用 Apache Bench 测试
ab -n 1000 -c 10 http://localhost:8000/api/alert-rules/

# 使用 wrk 测试
wrk -t4 -c100 -d30s http://localhost:8000/api/alert-rules/
```

### 3. 缓存监控

```python
# 在日志中记录缓存命中情况
logger.info(f"Cache hit: {cache_key}")
logger.info(f"Cache miss: {cache_key}")
```

## 下一步优化

1. **实施剩余API的缓存**：
   - 通知渠道API
   - 项目API
   - 用户API
   - 静默规则API

2. **添加缓存监控**：
   - 实现缓存命中率统计
   - 添加Prometheus指标
   - 创建Grafana仪表板

3. **优化缓存策略**：
   - 根据实际使用情况调整过期时间
   - 实现智能预热
   - 添加缓存预加载

4. **考虑二级缓存**：
   - 在应用层添加本地缓存（如LRU Cache）
   - 减少Redis网络开销

## 总结

通过实施Redis缓存，可以显著提升API响应速度，减少数据库负载。建议按照本文档的步骤，逐步为所有API添加缓存支持。

关键要点：
- ✅ 统一的缓存服务
- ✅ 合理的缓存键设计
- ✅ 完善的缓存失效策略
- ✅ 适当的过期时间设置
- ✅ 持续的性能监控