"""
@Author         : Ailitonia
@Date           : 2022/04/11 20:46
@FileName       : base_model.py
@Project        : nonebot2_miya 
@Description    : Bilibili Base Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pydantic import BaseModel


class BaseBilibiliModel(BaseModel):
    class Config:
        extra = 'ignore'
        allow_mutation = False


__all = [
    'BaseBilibiliModel'
]
