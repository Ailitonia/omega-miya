"""
@Author         : Ailitonia
@Date           : 2026/9/27 22:49
@FileName       : config
@Project        : omega-miya
@Description    : Twitter API Config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, ValidationError

from src.resource import TemporaryResource


class TwitterAPIConfig(BaseModel):
    """推特 API 配置"""

    model_config = ConfigDict(extra='ignore')

    @property
    def default_tmp_folder(self) -> TemporaryResource:
        return TemporaryResource('twitter')

    @property
    def default_download_folder(self) -> TemporaryResource:
        return self.default_tmp_folder('download')


try:
    twitter_api_config = get_plugin_config(TwitterAPIConfig)
except ValidationError as e:
    import sys

    logger.opt(colors=True).critical(f'<r>推特 API 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'推特 API 配置格式验证失败, {e}')

__all__ = [
    'twitter_api_config',
]
