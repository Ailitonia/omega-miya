"""
@Author         : Ailitonia
@Date           : 2022/11/29 19:49
@FileName       : model.py
@Project        : nonebot2_miya
@Description    : Omega API model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StandardOmegaAPIReturn[T: Any](BaseModel):
    """Omega API 返回值基类"""
    error: bool
    body: T | None = Field(default=None)
    message: str = Field(default_factory=str)

    model_config = ConfigDict(extra='ignore', coerce_numbers_to_str=True, from_attributes=True, frozen=True)

    @property
    def success(self) -> bool:
        return not self.error


__all__ = [
    'StandardOmegaAPIReturn',
]
