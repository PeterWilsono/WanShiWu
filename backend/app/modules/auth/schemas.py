"""认证接口的请求与响应模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, description="登录名，3~50 个非空白字符")
    password: str = Field(min_length=8, max_length=128, description="密码，8~128 个字符")

    @field_validator("username", mode="before")
    @classmethod
    def strip_username(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if any(char.isspace() for char in value):
            raise ValueError("用户名不能包含空白字符")
        return value


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50, description="登录名")
    password: str = Field(min_length=1, max_length=128, description="密码")

    @field_validator("username", mode="before")
    @classmethod
    def strip_username(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class UserResponse(BaseModel):
    """公开用户信息：刻意不包含 password_hash。"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="用户 ID")
    username: str = Field(description="登录名")
    timezone: str = Field(description="用户时区")
    settings_json: dict = Field(description="个人设置")
    created_at: datetime = Field(description="创建时间，ISO 8601 格式")


class TokenResponse(BaseModel):
    access_token: str = Field(description="JWT 访问令牌")
    token_type: str = Field(default="bearer", description="认证方案，固定为 bearer")
