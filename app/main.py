"""应用入口"""
import asyncio
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.core.config import settings
from app.core.exceptions import AlertSystemException
from app.db.database import engine
from app.db.redis_client import RedisClient
from app.models.base import Base
from app.api import auth, alert_rules, datasources, notifications, silence, users, audit
from app.api import settings as settings_api
from app.api import projects
from app.services.evaluator import AlertEvaluationScheduler
from app.services.alert_manager import AlertManager
from app.db.database import AsyncSessionLocal


# 配置日志级别
logger.remove()  # 移除默认处理器
logger.add(
    sys.stderr,
    level=settings.LOG_LEVEL,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)
logger.info(f"日志级别已设置为: {settings.LOG_LEVEL}")


# 全局调度器和告警管理器
scheduler = None
alert_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global scheduler, alert_manager
    
    # 启动时
    logger.info("应用启动中...")
    
    # 初始化 Redis 连接
    try:
        await RedisClient.initialize()
        logger.info("✅ Redis 连接已初始化")
    except Exception as e:
        logger.warning(f"⚠️  Redis 连接失败，将使用内存分组器: {str(e)}")
    
    # 创建数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 创建后台任务专用的数据库会话
    # db_session = AsyncSessionLocal()  # 不再创建单一会话
    
    # 启动告警评估调度器（不传入会话，让调度器自己管理）
    scheduler = AlertEvaluationScheduler()
    
    # 创建全局告警管理器并启动分组工作器（自动检测使用 Redis 或内存分组器）
    # 不再传入会话，让 AlertManager 自己管理会话
    alert_manager = AlertManager()
    
    # 配置告警分组参数
    alert_manager.configure_grouper(
        group_wait=10,       # 分组等待时间 10 秒
        group_interval=30,   # 分组间隔 30 秒
        repeat_interval=3600 # 重复发送间隔 1 小时
    )
    
    # 在后台任务中启动调度器和分组工作器
    asyncio.create_task(scheduler.start())
    asyncio.create_task(alert_manager.start_grouping_worker())
    
    logger.info("应用启动完成")
    
    yield
    
    # 关闭时
    logger.info("应用关闭中...")
    if scheduler:
        await scheduler.stop()
    if alert_manager:
        await alert_manager.stop_grouping_worker()
    # await db_session.close()  # 不再需要关闭单一会话
    await engine.dispose()
    
    # 关闭 Redis 连接
    await RedisClient.close()
    
    logger.info("应用已关闭")


# 创建应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 审计日志中间件
from app.middleware.audit import AuditMiddleware
app.add_middleware(AuditMiddleware)


# 全局异常处理器
@app.exception_handler(AlertSystemException)
async def alert_system_exception_handler(
    request: Request,
    exc: AlertSystemException
) -> JSONResponse:
    """处理自定义异常
    
    Args:
        request: 请求对象
        exc: 异常对象
        
    Returns:
        JSONResponse: 标准化的错误响应
    """
    logger.error(
        f"AlertSystemException: {exc.code} - {exc.message}",
        extra={
            "code": exc.code,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method
        }
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """处理未捕获的异常
    
    Args:
        request: 请求对象
        exc: 异常对象
        
    Returns:
        JSONResponse: 通用错误响应
    """
    logger.exception(
        f"Unhandled exception: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method
        }
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred",
                "details": {}
            }
        }
    )

# 注册路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(alert_rules.router, prefix="/api/v1/alert-rules", tags=["告警规则"])
app.include_router(datasources.router, prefix="/api/v1/datasources", tags=["数据源"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["通知渠道"])
app.include_router(silence.router, prefix="/api/v1/silence", tags=["静默规则"])
app.include_router(users.router, prefix="/api/v1/users", tags=["用户管理"])
app.include_router(audit.router, prefix="/api/v1/audit", tags=["审计日志"])
app.include_router(settings_api.router, prefix="/api/v1/settings", tags=["系统设置"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["项目管理"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )

