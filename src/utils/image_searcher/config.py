"""
@Author         : Ailitonia
@Date           : 2022/05/08 16:15
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : Image Searcher Config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, ValidationError


class ImageSearcherConfig(BaseModel):
    """ImageSearcher 配置"""
    saucenao_api_key: str | None = None

    image_searcher_enable_ascii2d: bool = True
    image_searcher_enable_saucenao: bool = True
    image_searcher_enable_iqdb: bool = True
    image_searcher_enable_yandex: bool = False
    image_searcher_enable_trace_moe: bool = True

    model_config = ConfigDict(extra='ignore')


try:
    image_searcher_config = get_plugin_config(ImageSearcherConfig)
    if not image_searcher_config.saucenao_api_key:
        logger.opt(colors=True).warning(f'<lc>ImageSearcher</lc> | <lr>未配置 Saucenao API KEY</lr>, '
                                        f'<ly>部分识图功能可能无法正常使用</ly>')
except ValidationError as e:
    import sys
    logger.opt(colors=True).critical(f'<r>ImageSearcher 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'ImageSearcher 配置格式验证失败, {e}')


__all__ = [
    'image_searcher_config'
]
