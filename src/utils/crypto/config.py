"""
@Author         : Ailitonia
@Date           : 2022/04/26 19:18
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : Encrypt Utils Config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import platform
import uuid
from hashlib import sha256
from typing import Annotated

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError


def generate_aes_key_by_hardware() -> SecretStr:
    processor = platform.processor()
    machine = platform.machine()
    system = platform.system()
    node = str(uuid.getnode())

    return SecretStr(sha256(f'{system}+{machine}+{processor}+{node}'.encode()).hexdigest())


class EncryptConfig(BaseModel):
    """Encrypt Utils 配置"""
    # 若不手动配置 AES key 则会使用系统及硬件信息生成, 更换平台或硬件可能导致 key 失效
    omega_aes_key: Annotated[SecretStr, Field(default_factory=generate_aes_key_by_hardware)]

    model_config = ConfigDict(extra='ignore')


try:
    encrypt_config = get_plugin_config(EncryptConfig)
except (ValidationError, ValueError) as e:
    import sys
    logger.opt(colors=True).critical(f'<lc>EncryptUtils</lc> | <lr>全局 AES Key 配置异常</lr>, 错误信息:\n{e}')
    sys.exit(f'EncryptUtils 配置格式验证失败, {e}')


__all__ = [
    'encrypt_config',
]
