"""
@Author         : Ailitonia
@Date           : 2025/2/12 16:47:56
@FileName       : model.py
@Project        : omega-miya
@Description    : openai model model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Any

from .base import BaseOpenAIModel


class Model(BaseOpenAIModel):
    id: str
    object: str
    owned_by: str
    created: int | None = None
    context_length: int | None = None
    root: str | None = None
    parent: str | None = None
    permission: list[dict[str, Any]] | None = None
    supports_image_in: bool | None = None
    supports_reasoning: bool | None = None
    supports_video_in: bool | None = None
    supports_dynamic_tools: bool | None = None
    supports_thinking_type: str | None = None
    reasoning_efforts: dict[str, Any] | None = None
    think_efforts: dict[str, Any] | None = None


class ModelList(BaseOpenAIModel):
    object: str
    data: list[Model]


__all__ = [
    'Model',
    'ModelList',
]
