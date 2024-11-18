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
from src.service.artwork_collection import ALLOW_ARTWORK_ORIGIN


class WordcloudPluginConfig(BaseModel):
    """Wordcloud 插件配置"""
    # 从全局配置读取命令头配置
    command_start: set[str]

    # 排除机器人自身的消息
    wordcloud_plugin_exclude_bot_self_message: bool = True

    # 生成词云图片的尺寸
    wordcloud_plugin_generate_default_width: int = 1600
    wordcloud_plugin_generate_default_height: int = 1200

    # 生成图片的背景颜色
    wordcloud_plugin_background_color: str = 'white'
    # 是否额外使用内置图库中的作品作为背景图片
    wordcloud_plugin_enable_collected_artwork_background: bool = False
    # 背景图图库来源, 可配置: pixiv, danbooru, gelbooru, konachan, yandere, local, 当配置为 `None` 时, 代表从所有的来源随机获取
    wordcloud_plugin_artwork_background_origin: ALLOW_ARTWORK_ORIGIN | None = 'pixiv'

    # 生成词云频率的颜色映射图
    wordcloud_plugin_colormap: str = 'plasma'

    model_config = ConfigDict(extra='ignore')

    @property
    def default_image_size(self) -> tuple[int, int]:
        return self.wordcloud_plugin_generate_default_width, self.wordcloud_plugin_generate_default_height

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
    # 默认输出路径
    default_output_dir = TemporaryResource('wordcloud', 'output')
    # 头像缓存路径
    profile_image_tmp_dir = TemporaryResource('wordcloud', 'profile_image')
    # 用户自定义词典位置
    user_dict_file = TemporaryResource('wordcloud', 'user_dict', 'user_dict.txt')


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
