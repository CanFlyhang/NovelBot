from functools import lru_cache
from typing import List

from pydantic import v1 as pydantic_v1


class Settings(pydantic_v1.BaseSettings):
    """
    全局配置对象，负责从环境变量加载系统运行参数。
    """

    app_name: str = pydantic_v1.Field("NovelBot 自动小说创作系统")
    mysql_dsn: str = pydantic_v1.Field(
        "mysql+pymysql://root:password@localhost:3306/novelbot?charset=utf8mb4",
        description="SQLAlchemy 使用的 MySQL 连接串",
    )
    deepseek_api_key: str = pydantic_v1.Field("", description="DeepSeek API 密钥")
    deepseek_base_url: str = pydantic_v1.Field(
        "https://api.deepseek.com",
        description="DeepSeek API 基础地址",
    )
    deepseek_model: str = pydantic_v1.Field(
        "deepseek-chat",
        description="用于小说生成的 DeepSeek 模型名称",
    )

    daily_target_novels: int = pydantic_v1.Field(
        2,
        description="系统每天目标创作的小说数量",
    )
    default_chapters_per_novel: int = pydantic_v1.Field(
        10,
        description="默认每本小说的章节数量",
    )

    max_concurrent_api_requests: int = pydantic_v1.Field(
        3,
        description="DeepSeek API 最大并发请求数",
    )
    max_requests_per_minute: int = pydantic_v1.Field(
        30,
        description="DeepSeek API 每分钟最大请求数",
    )
    api_request_timeout: int = pydantic_v1.Field(
        60,
        description="DeepSeek API 请求超时时间（秒）",
    )
    api_max_retries: int = pydantic_v1.Field(
        3,
        description="DeepSeek API 调用失败时的最大重试次数",
    )

    scheduler_enabled: bool = pydantic_v1.Field(
        True,
        description="是否自动启用每日调度器",
    )
    scheduler_tick_seconds: int = pydantic_v1.Field(
        60,
        description="调度器轮询间隔秒数",
    )

    preferred_genres: List[str] = pydantic_v1.Field(
        default_factory=lambda: ["玄幻", "科幻", "都市", "悬疑"],
        description="系统偏好的默认小说类型",
    )
    generation_language: str = pydantic_v1.Field(
        "zh",
        description="生成内容的语言标记",
    )

    class Config:
        env_prefix = "NOVELBOT_"
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """
    获取全局配置实例，使用 LRU 缓存确保单例模式。
    """

    return Settings()


settings: Settings = get_settings()
