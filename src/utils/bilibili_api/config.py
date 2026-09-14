"""
@Author         : Ailitonia
@Date           : 2024/10/28 14:38:44
@FileName       : config.py
@Project        : omega-miya
@Description    : bilibili API 配置
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, ValidationError

from src.resource import TemporaryResource


class BilibiliAPIConfig(BaseModel):
    """bilibili API 配置"""

    model_config = ConfigDict(extra='ignore')

    @property
    def temporary_folder(self) -> 'TemporaryResource':
        """获取缓存目录路径"""
        return TemporaryResource('bilibili_api')

    @property
    def download_folder(self) -> 'TemporaryResource':
        """缓存下载文件目录"""
        return self.temporary_folder('download')

    def get_temporary_file_path(self, *path: str) -> 'TemporaryResource':
        """获取缓存资源文件路径"""
        return self.temporary_folder(*path)


try:
    bilibili_api_config = get_plugin_config(BilibiliAPIConfig)
except ValidationError as e:
    import sys

    logger.opt(colors=True).critical(f'<r>bilibili api 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'bilibili api 配置格式验证失败, {e}')


__all__ = [
    'bilibili_api_config',
]
