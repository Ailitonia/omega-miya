"""
@Author         : Ailitonia
@Date           : 2022/04/11 20:46
@FileName       : base_model.py
@Project        : nonebot2_miya 
@Description    : Bilibili Base Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pydantic import BaseModel, ConfigDict


class BaseBilibiliModel(BaseModel):
    """bilibili 数据基类"""

    model_config = ConfigDict(extra='ignore', frozen=True, coerce_numbers_to_str=True)


__all = [
    'BaseBilibiliModel'
]
