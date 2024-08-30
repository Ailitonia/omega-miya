"""
@Author         : Ailitonia
@Date           : 2024/8/1 14:56:53
@FileName       : config.py
@Project        : omega-miya
@Description    : Danbooru 配置
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, ValidationError


class BooruConfig(BaseModel):
    """Booru API 配置"""
    danbooru_username: str | None = None
    danbooru_api_key: str | None = None

    gelbooru_user_id: str | None = None
    gelbooru_api_key: str | None = None

    behoimi_login_name: str | None = None
    behoimi_password_hash: str | None = None

    yandere_login_name: str | None = None
    yandere_password_hash: str | None = None

    konachan_com_login_name: str | None = None
    konachan_com_password_hash: str | None = None

    konachan_net_login_name: str | None = None
    konachan_net_password_hash: str | None = None

    model_config = ConfigDict(extra='ignore', coerce_numbers_to_str=True, frozen=True)


try:
    booru_config = get_plugin_config(BooruConfig)
except ValidationError as e:
    import sys

    logger.opt(colors=True).critical(f'<r>Booru API 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Booru API 配置格式验证失败, {e}')

__all__ = [
    'booru_config',
]
