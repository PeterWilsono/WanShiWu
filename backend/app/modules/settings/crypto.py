"""模型密钥的对称加密；密钥材料由服务端 JWT 密钥派生，不写入数据库。"""

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.core.errors import AppError, ErrorCode


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    digest = hashlib.sha256(f"wanshiwu.llm-key.v1:{settings.jwt_secret}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_api_key(api_key: str) -> str:
    return _fernet().encrypt(api_key.encode()).decode()


def decrypt_api_key(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except (InvalidToken, UnicodeDecodeError) as exc:
        raise AppError(
            ErrorCode.BUSINESS_RULE_VIOLATION,
            "已保存的模型密钥无法读取，请在设置中重新填写",
            422,
        ) from exc
