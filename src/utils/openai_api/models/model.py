"""
@Author         : Ailitonia
@Date           : 2025/2/12 16:47:56
@FileName       : model.py
@Project        : omega-miya
@Description    : openai model model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from .base import BaseOpenAIModel


class Model(BaseOpenAIModel):
    id: str
    object: str
    owned_by: str
    created: int | None = None


class ModelList(BaseOpenAIModel):
    object: str
    data: list[Model]


__all__ = [
    'Model',
    'ModelList',
]
