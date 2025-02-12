"""
@Author         : Ailitonia
@Date           : 2025/2/11 20:52:52
@FileName       : base.py
@Project        : omega-miya
@Description    : openai BaseModel
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pydantic import BaseModel, ConfigDict


class BaseOpenAIModel(BaseModel):
    """openai 数据基类"""

    model_config = ConfigDict(extra='ignore', coerce_numbers_to_str=True, frozen=False)


__all__ = [
    'BaseOpenAIModel',
]
