"""
@Author         : Ailitonia
@Date           : 2024/10/27 00:23
@FileName       : config
@Project        : omega-miya
@Description    : 词云插件配置
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Any, Literal

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, ValidationError

from src.resource import StaticResource, TemporaryResource
from src.service.artwork_collection import ALLOW_ARTWORK_ORIGIN


class WordcloudPluginConfig(BaseModel):
    """Wordcloud 插件配置"""
    # 从全局配置读取命令头配置
    command_start: set[str]

    # 分词模式
    wordcloud_plugin_message_analyse_mode: Literal['TF-IDF', 'TextRank'] = 'TF-IDF'
    # 排除机器人自身的消息
    wordcloud_plugin_exclude_bot_self_message: bool = True
    # 查询消息历史记录的数量上限
    wordcloud_plugin_query_history_limit: int = 20000

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

    # 资源文件配置
    # 内置的字体文件
    wordcloud_plugin_default_font_name: str = 'fzzxhk.ttf'
    # 默认缓存资源保存路径
    wordcloud_plugin_default_output_folder_name: Literal['wordcloud'] = 'wordcloud'

    model_config = ConfigDict(extra='ignore')

    @property
    def default_font(self) -> StaticResource:
        return StaticResource('fonts', self.wordcloud_plugin_default_font_name)

    @property
    def default_stop_words_file(self) -> StaticResource:
        """默认停用词清单"""
        return StaticResource('docs', 'wordcloud', 'stop_words', 'default_stop_words.txt')

    @property
    def user_dict_file(self) -> TemporaryResource:
        """用户自定义词典"""
        return TemporaryResource(self.wordcloud_plugin_default_output_folder_name, 'user_dict', 'user_dict.txt')

    @property
    def default_output_folder(self) -> TemporaryResource:
        """默认输出路径"""
        return TemporaryResource(self.wordcloud_plugin_default_output_folder_name, 'output')

    @property
    def profile_image_folder(self) -> TemporaryResource:
        """头像缓存路径"""
        return TemporaryResource(self.wordcloud_plugin_default_output_folder_name, 'profile_image')

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


try:
    wordcloud_plugin_config = get_plugin_config(WordcloudPluginConfig)
except ValidationError as e:
    import sys

    logger.opt(colors=True).critical(f'<r>Wordcloud 插件配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Wordcloud 插件配置格式验证失败, {e}')

__all__ = [
    'wordcloud_plugin_config',
]
