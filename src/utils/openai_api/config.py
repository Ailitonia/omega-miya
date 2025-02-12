"""
@Author         : Ailitonia
@Date           : 2025/2/13 11:20:41
@FileName       : config.py
@Project        : omega-miya
@Description    : openai Service Config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.compat import AnyHttpUrlStr as AnyHttpUrl


class Service(BaseModel):
    """Service"""
    name: str
    api_key: str
    base_url: AnyHttpUrl
    available_models: list[str]

    model_config = ConfigDict(extra='ignore', coerce_numbers_to_str=True)


class OpenaiServiceConfig(BaseModel):
    """LLM Service 配置"""
    openai_service_config: list[Service] = Field(default_factory=list)

    model_config = ConfigDict(extra='ignore')

    @property
    def service_map(self) -> dict[str, Service]:
        return {x.name: x for x in self.openai_service_config}


try:
    openai_service_config = get_plugin_config(OpenaiServiceConfig)
except ValidationError as e:
    import sys

    logger.opt(colors=True).critical(f'<r>openai Service 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'openai Service 配置格式验证失败, {e}')

__all__ = [
    'openai_service_config',
]
