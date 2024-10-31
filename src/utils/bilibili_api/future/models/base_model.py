"""
@Author         : Ailitonia
@Date           : 2024/10/31 16:57:22
@FileName       : base_model.py
@Project        : omega-miya
@Description    : bilibili API BaseModel
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
