"""收藏后台任务依赖，测试可替换为无网络处理器。"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends

from app.modules.inbox.ai_service import process_bookmark


def get_bookmark_processor() -> Callable[[int, int], None]:
    return process_bookmark


BookmarkProcessor = Annotated[Callable[[int, int], None], Depends(get_bookmark_processor)]
