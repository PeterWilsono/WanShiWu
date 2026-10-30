"""应用配置。

依据 PROJECT_SPEC.md 附录 A：所有配置通过环境变量 / .env 读取，
密钥不写进代码、不提交仓库（.env 已在 .gitignore 中）。
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置，字段与 backend/.env.example 一一对应。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- 应用 ----
    app_env: str = "dev"  # dev / test / prod
    log_level: str = "INFO"
    database_url: str = "sqlite:///./data/wanshiwu.db"
    default_timezone: str = "Asia/Shanghai"
    allow_register: bool = True

    # ---- 鉴权 ----
    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_expire_minutes: int = 10080  # 7 天

    # ---- 大模型（OpenAI 兼容接口）----
    llm_base_url: str = "https://api.deepseek.com"
    llm_api_key: str = "your-api-key-here"
    llm_model: str = "deepseek-chat"
    llm_timeout_seconds: int = 30
    daily_llm_call_limit: int = 200


settings = Settings()
