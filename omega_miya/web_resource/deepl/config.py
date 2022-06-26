"""
@Author         : Ailitonia
@Date           : 2022/05/08 1:28
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : DeepL config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_driver, logger
from pydantic import BaseModel, ValidationError


class DeepLConfig(BaseModel):
    """DeepL 配置"""
    deepl_auth_key: str | None = None

    class Config:
        extra = "ignore"


try:
    deepl_config = DeepLConfig.parse_obj(get_driver().config)
    # if not deepl_config.deepl_auth_key:
    #     logger.opt(colors=True).warning(f'<lc>DeepL</lc> | <r>未配置 DeepL Auth Key</r>, 翻译功能可能无法正常使用')
except ValidationError as e:
    import sys
    logger.opt(colors=True).critical(f'<r>DeepL 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'DeepL 配置格式验证失败, {e}')


__all__ = [
    'deepl_config'
]
