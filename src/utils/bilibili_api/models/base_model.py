"""
@Author         : Ailitonia
@Date           : 2024/10/31 16:57:22
@FileName       : base_model.py
@Project        : omega-miya
@Description    : bilibili API BaseModel
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pydantic import BaseModel, ConfigDict, Field


class BaseBilibiliModel(BaseModel):
    """bilibili 数据基类"""

    model_config = ConfigDict(extra='ignore', frozen=True, coerce_numbers_to_str=True)


class BaseBilibiliResponse(BaseBilibiliModel):
    """bilibili 通用 API 调用响应结果基类"""
    code: int
    message: str
    ttl: int = Field(default=1)

    @property
    def error(self) -> bool:
        return self.code != 0


__all = [
    'BaseBilibiliModel',
    'BaseBilibiliResponse',
]
