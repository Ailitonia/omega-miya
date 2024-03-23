"""
@Author         : Ailitonia
@Date           : 2022/04/26 19:18
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : Encrypt Utils Config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, ValidationError


class EncryptConfig(BaseModel):
    """Encrypt Utils 配置"""
    aes_key: str

    model_config = ConfigDict(extra="ignore")


try:
    encrypt_config = get_plugin_config(EncryptConfig)
    if not encrypt_config.aes_key:
        raise ValueError('Incorrect AES Key length, key can not be null')
    if len(encrypt_config.aes_key) > 16:
        raise ValueError('Incorrect AES key length, key length should be less than 16')
except (ValidationError, ValueError) as e:
    import sys
    logger.opt(colors=True).critical(f'<lc>EncryptUtils</lc> | <lr>全局 AES Key 配置异常</lr>, 错误信息:\n{e}')
    sys.exit(f'EncryptUtils 配置格式验证失败, {e}')


__all__ = [
    'encrypt_config'
]
