"""
@Author         : Ailitonia
@Date           : 2022/11/29 19:49
@FileName       : model.py
@Project        : nonebot2_miya 
@Description    : Omega API model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pydantic import BaseModel, ConfigDict


class BaseApiModel(BaseModel):
    """Omega API 数据基类"""

    model_config = ConfigDict(extra='ignore', coerce_numbers_to_str=True, frozen=True)


class StandardApiReturn[T: BaseApiModel](BaseModel):
    """Omega API 返回值基类"""
    error: bool
    body: T | None
    message: str
    exception: str | None = None

    model_config = ConfigDict(extra='ignore', coerce_numbers_to_str=True, from_attributes=True, frozen=True)

    @property
    def success(self) -> bool:
        return not self.error


__all = [
    'BaseApiModel',
    'StandardApiReturn',
]
