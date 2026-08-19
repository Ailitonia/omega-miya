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


def _generate_random_api_key() -> SecretStr:
    logger.opt(colors=True).warning('<lc>Omega API</lc> | 未指定 API key, 将生成并使用随机密钥配置')
    return SecretStr(token_hex())


class OmegaAPIConfig(BaseModel):
    """Omega API 配置"""

    omega_api_master_key: Annotated[SecretStr, Field(default_factory=_generate_random_api_key)]
    """主密钥"""
    omega_api_timestamp_expire_seconds: Annotated[int, Field(default=30, gt=0)]
    """请求时间戳允许的最大偏差秒数"""
    omega_api_used_signatures_max_size: Annotated[int, Field(default=4096, gt=0)]
    """已使用签名缓存触发清理的容量阈值"""
    omega_api_request_body_max_size: Annotated[int, Field(default=1024 * 1024, gt=0)]
    """请求体最大允许大小(字节)"""

    model_config = ConfigDict(extra='ignore')


try:
    api_config = get_plugin_config(OmegaAPIConfig)
    logger.opt(colors=True).success('<lc>Omega API</lc> | API Key 已配置')
except (ValidationError, ValueError) as e:
    import sys

    logger.opt(colors=True).critical(f'<lc>Omega API</lc> | <lr>配置异常</lr>, 错误信息:\n{e}')
    sys.exit(f'Omega API 配置格式验证失败, {e}')

__all__ = [
    'api_config',
]
