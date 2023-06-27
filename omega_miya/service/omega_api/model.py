"""
@Author         : Ailitonia
@Date           : 2022/11/29 19:49
@FileName       : model.py
@Project        : nonebot2_miya 
@Description    : api model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Optional
from pydantic import BaseModel


class BaseApiModel(BaseModel):
    """api 基类"""
    class Config:
        extra = 'ignore'
        allow_mutation = False


class BaseApiReturn(BaseApiModel):
    """api 返回值基类"""
    error: bool
    body: BaseApiModel
    message: str
    exception: Optional[str]


__all = [
    'BaseApiModel',
    'BaseApiReturn'
]
