"""
@Author         : Ailitonia
@Date           : 2024/10/27 00:23
@FileName       : config
@Project        : omega-miya
@Description    : 词云插件配置
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from dataclasses import dataclass
from typing import Any

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, ValidationError

from src.resource import StaticResource, TemporaryResource


class WordcloudPluginConfig(BaseModel):
    """Wordcloud 插件配置"""
    # 从全局配置读取命令头配置
    command_start: set[str]

    # 生成词云图片的尺寸
    wordcloud_plugin_generate_default_width: int = 1600
    wordcloud_plugin_generate_default_height: int = 1200

    # 生成图片的背景颜色
    wordcloud_plugin_background_color: str = 'white'
    # 是否额外使用内置图库中的作品作为背景图片
    wordcloud_plugin_enable_collected_artwork_background: bool = False
    # 使用的颜色映射图
    wordcloud_plugin_colormap: str = 'viridis'

    model_config = ConfigDict(extra='ignore')

    @property
    def wordcloud_default_options(self) -> dict[str, Any]:
        return {
            'width': self.wordcloud_plugin_generate_default_width,
            'height': self.wordcloud_plugin_generate_default_height,
            'background_color': self.wordcloud_plugin_background_color,
            'colormap': self.wordcloud_plugin_colormap,
        }


@dataclass
class WordcloudPluginLocalResourceConfig:
    # 默认字体文件
    default_font_file = StaticResource('fonts', 'fzzxhk.ttf')
    # 默认停用词清单
    default_stop_words_file = StaticResource('docs', 'wordcloud', 'stop_words', 'default_stop_words.txt')
    # 用户自定义词典位置
    user_dict_file = TemporaryResource('docs', 'wordcloud', 'user_dict', 'user_dict.txt')
    # 默认输出路径
    default_output_dir = TemporaryResource('wordcloud', 'output')


try:
    wordcloud_plugin_resource_config = WordcloudPluginLocalResourceConfig()
    wordcloud_plugin_config = get_plugin_config(WordcloudPluginConfig)
except ValidationError as e:
    import sys

    logger.opt(colors=True).critical(f'<r>Wordcloud 插件配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Wordcloud 插件配置格式验证失败, {e}')

__all__ = [
    'wordcloud_plugin_config',
    'wordcloud_plugin_resource_config',
]
