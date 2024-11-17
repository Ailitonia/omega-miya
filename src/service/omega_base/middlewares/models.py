"""
@Author         : Ailitonia
@Date           : 2024/8/20 15:06:42
@FileName       : models.py
@Project        : omega-miya
@Description    : Omega 中间件数据模型
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Any

from pydantic import BaseModel, ConfigDict


class BaseMiddlewareModel(BaseModel):
    """Omega 中间件数据模型基类"""

    model_config = ConfigDict(extra='ignore', frozen=True, coerce_numbers_to_str=True)


class EntityInitParams(BaseMiddlewareModel):
    """构造 OmegaEntity 的参数"""
    bot_id: str
    entity_type: str
    entity_id: str
    parent_id: str
    entity_name: str | None = None
    entity_info: str | None = None

    @property
    def kwargs(self) -> dict[str, Any]:
        return self.model_dump()


class EntityTargetSendParams(BaseMiddlewareModel):
    """EntityTarget 发送消息参数"""
    api: str
    message_param_name: str
    params: dict[str, Any]


class EntityTargetRevokeParams(BaseMiddlewareModel):
    """EntityTarget 撤回消息参数"""
    api: str
    params: dict[str, Any]


__all__ = [
    'EntityInitParams',
    'EntityTargetSendParams',
    'EntityTargetRevokeParams',
]
