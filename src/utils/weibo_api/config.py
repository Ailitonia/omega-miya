"""
@Author         : Ailitonia
@Date           : 2023/2/3 23:55
@FileName       : config
@Project        : nonebot2_miya
@Description    : Weibo config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, ValidationError

from src.resource import TemporaryResource


class WeiboAPIConfig(BaseModel):
    """微博 API 配置"""

    model_config = ConfigDict(extra='ignore')

    @property
    def default_tmp_folder(self) -> TemporaryResource:
        return TemporaryResource('weibo')

    @property
    def default_download_folder(self) -> TemporaryResource:
        return self.default_tmp_folder('download')


try:
    weibo_api_config = get_plugin_config(WeiboAPIConfig)
except ValidationError as e:
    import sys

    logger.opt(colors=True).critical(f'<r>微博 API 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'微博 API 配置格式验证失败, {e}')


__all__ = [
    'weibo_api_config',
]
