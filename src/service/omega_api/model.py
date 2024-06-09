"""
@Author         : Ailitonia
@Date           : 2022/11/29 19:49
@FileName       : model.py
@Project        : nonebot2_miya 
@Description    : Omega API model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Any, Optional
from pydantic import BaseModel, ConfigDict


class BaseApiModel(BaseModel):
    """omega API 基类"""

    model_config = ConfigDict(extra='ignore', frozen=True)


class BaseApiReturn(BaseApiModel):
    """api 返回值基类"""
    error: bool
    body: Any
    message: str
    exception: Optional[str] = None

    @property
    def success(self) -> bool:
        return not self.error


__all = [
    'BaseApiModel',
    'BaseApiReturn'
]
