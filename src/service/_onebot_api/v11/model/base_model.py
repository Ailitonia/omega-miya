"""
@Author         : Ailitonia
@Date           : 2022/04/13 22:08
@FileName       : base_model.py
@Project        : nonebot2_miya 
@Description    : Onebot Base Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pydantic import BaseModel


class BaseOnebotModel(BaseModel):
    class Config:
        extra = 'ignore'
        allow_mutation = False


__all = [
    'BaseGoCqhttpModel'
]
