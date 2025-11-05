"""配置管理"""
import yaml
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置 - 只包含基础设施配置"""
    
    # 应用配置
    APP_NAME: str = "Alert System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # 数据库配置（MySQL）
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 3306
    DATABASE_USERNAME: str = "alert_user"
    DATABASE_PASSWORD: str = "alert_password"
    DATABASE_NAME: str = "alert_system"
    
    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    
    # JWT 配置
    JWT_SECRET_KEY: str = "change-this-secret-key-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    
    @property
    def database_url(self) -> str:
        """获取数据库连接字符串（MySQL）"""
        from urllib.parse import quote_plus
        # URL 编码用户名和密码，避免特殊字符问题
        username = quote_plus(self.DATABASE_USERNAME)
        password = quote_plus(self.DATABASE_PASSWORD)
        return f"mysql+aiomysql://{username}:{password}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}?charset=utf8mb4"
    
    @property
    def redis_url(self) -> str:
        """获取 Redis 连接字符串"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


def load_config_from_yaml(config_file: str = "config/config.yaml") -> Settings:
    """从 YAML 文件加载配置"""
    config_path = Path(config_file)
    if not config_path.exists():
        return Settings()
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)
    
    # 只读取数据库和 Redis 配置
    settings_dict = {}
    
    if 'database' in config_data:
        db = config_data['database']
        settings_dict['DATABASE_HOST'] = db.get('host', 'localhost')
        settings_dict['DATABASE_PORT'] = db.get('port', 3306)
        settings_dict['DATABASE_USERNAME'] = db.get('username', 'alert_user')
        settings_dict['DATABASE_PASSWORD'] = db.get('password', 'alert_password')
        settings_dict['DATABASE_NAME'] = db.get('database', 'alert_system')
    
    if 'redis' in config_data:
        redis = config_data['redis']
        settings_dict['REDIS_HOST'] = redis.get('host', 'localhost')
        settings_dict['REDIS_PORT'] = redis.get('port', 6379)
        settings_dict['REDIS_PASSWORD'] = redis.get('password', '')
        settings_dict['REDIS_DB'] = redis.get('db', 0)
    
    if 'logging' in config_data:
        logging = config_data['logging']
        settings_dict['LOG_LEVEL'] = logging.get('level', 'INFO').upper()
    
    return Settings(**settings_dict)


# 全局配置实例
settings = load_config_from_yaml()

