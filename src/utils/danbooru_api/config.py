"""
@Author         : Ailitonia
@Date           : 2024/8/1 14:56:53
@FileName       : config.py
@Project        : omega-miya
@Description    : Danbooru 配置
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from dataclasses import dataclass

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, ValidationError

from src.resource import StaticResource, TemporaryResource


class DanbooruConfig(BaseModel):
    """Danbooru 配置"""
    danbooru_username: str | None = None
    danbooru_api_key: str | None = None

    model_config = ConfigDict(extra="ignore")

    @property
    def auth_params(self) -> dict[str, str]:
        return {'login': self.danbooru_username, 'api_key': self.danbooru_api_key}


@dataclass
class DanbooruLocalResourceConfig:
    # 默认字体文件
    default_font_file: StaticResource = StaticResource('fonts', 'fzzxhk.ttf')
    # 默认的缓存资源保存路径
    default_preview_folder: TemporaryResource = TemporaryResource('danbooru', 'preview')
    default_download_folder: TemporaryResource = TemporaryResource('danbooru', 'download')


try:
    danbooru_resource_config = DanbooruLocalResourceConfig()
    danbooru_config = get_plugin_config(DanbooruConfig)
    if danbooru_config.danbooru_username is None or danbooru_config.danbooru_api_key is None:
        logger.opt(colors=True).warning(
            f'<lc>Danbooru</lc> | <lr>未配置 API key</lr>, <ly>部分功能可能无法正常使用</ly>')
except ValidationError as e:
    import sys

    logger.opt(colors=True).critical(f'<r>Danbooru 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Danbooru 配置格式验证失败, {e}')

__all__ = [
    'danbooru_config',
    'danbooru_resource_config',
]
