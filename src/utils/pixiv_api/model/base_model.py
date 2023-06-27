"""
@Author         : Ailitonia
@Date           : 2022/04/06 2:10
@FileName       : base_model.py
@Project        : nonebot2_miya 
@Description    : Pixiv Base Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pydantic import BaseModel


class BasePixivModel(BaseModel):
    class Config:
        extra = 'ignore'
        allow_mutation = False


__all = [
    'BasePixivModel'
]
