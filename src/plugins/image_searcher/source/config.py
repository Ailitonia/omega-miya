"""
@Author         : Ailitonia
@Date           : 2022/05/08 16:15
@FileName       : config.py
@Project        : nonebot2_miya
@Description    : Image Searcher Config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Literal

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.compat import AnyHttpUrlStr as AnyHttpUrl


class ImageSearcherConfig(BaseModel):
    """ImageSearcher 配置"""
    # 启用的识图引擎
    image_searcher_enable_searchers: list[str] = Field(default=['iqdb', 'ascii2d'])
    # 特定识图引擎配置
    # ascii2d
    image_searcher_ascii2d_alternative_url: AnyHttpUrl | None = Field(default=None)
    # AnimeTrace
    image_searcher_anime_trace_enable_multi: bool = Field(default=True)
    image_searcher_anime_trace_enable_ai_detect: bool = Field(default=True)
    image_searcher_anime_trace_default_model: Literal[
        'anime_model_lovelive',  # 高级动画识别模型①
        'pre_stable',  # 高级动画识别模型②
        'anime',  # 普通动画识别模型
        'full_game_model_kira',  # 高级Gal识别模型
    ] = Field(default='anime_model_lovelive')
    # Saucenao
    image_searcher_saucenao_api_key: str | None = Field(default=None)

    model_config = ConfigDict(extra='ignore')


try:
    image_searcher_config = get_plugin_config(ImageSearcherConfig)
    if (
            'saucenao' in image_searcher_config.image_searcher_enable_searchers
            and not image_searcher_config.image_searcher_saucenao_api_key
    ):
        logger.opt(colors=True).warning(
            '<lc>ImageSearcher</lc> | <lr>未配置 Saucenao API KEY</lr>, <ly>部分识图功能可能无法正常使用</ly>'
        )
except ValidationError as e:
    import sys

    logger.opt(colors=True).critical(f'<r>ImageSearcher 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'ImageSearcher 配置格式验证失败, {e}')

__all__ = [
    'image_searcher_config'
]
