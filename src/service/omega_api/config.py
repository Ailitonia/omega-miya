"""
@Author         : Ailitonia
@Date           : 2025/2/8 17:05:58
@FileName       : config.py
@Project        : omega-miya
@Description    : Omega API 配置
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from secrets import token_hex
from typing import Annotated

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError


def generate_api_key() -> SecretStr:
    return SecretStr(token_hex())


class OmegaApiConfig(BaseModel):
    """Omega API 配置"""
    omega_api_key: Annotated[SecretStr, Field(default_factory=generate_api_key)]

    model_config = ConfigDict(extra='ignore')


try:
    api_config = get_plugin_config(OmegaApiConfig)
    logger.opt(colors=True).success(
        f'<lc>Omega API</lc> | API Key 已配置: <ly>{api_config.omega_api_key.get_secret_value()}</ly>'
    )
except (ValidationError, ValueError) as e:
    import sys

    logger.opt(colors=True).critical(f'<lc>Omega API</lc> | <lr>配置异常</lr>, 错误信息:\n{e}')
    sys.exit(f'Omega API 配置格式验证失败, {e}')

__all__ = [
    'api_config',
]
