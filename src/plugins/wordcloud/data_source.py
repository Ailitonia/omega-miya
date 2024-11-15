"""
@Author         : Ailitonia
@Date           : 2024/10/27 00:19
@FileName       : data_source
@Project        : omega-miya
@Description    : 词云内容生成模块
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import re
from datetime import datetime
from io import BytesIO
from typing import TYPE_CHECKING, Sequence

import jieba
import jieba.analyse
from emoji import replace_emoji
from nonebot.utils import run_sync
from wordcloud import WordCloud

from .config import wordcloud_plugin_config, wordcloud_plugin_resource_config

if TYPE_CHECKING:
    from PIL.Image import Image
    from src.database.internal.history import History
    from src.resource import TemporaryResource


def prepare_message(messages: Sequence[str]) -> str:
    """预处理消息文本"""
    # 过滤命令消息
    command_start = tuple(i for i in wordcloud_plugin_config.command_start if i)
    message = " ".join(m for m in messages if not m.startswith(command_start))

    # 过滤网址, ref: https://stackoverflow.com/a/17773849
    pattern = re.compile(
        r"(https?://(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.\S{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]"
        r"+[a-zA-Z0-9]\.\S{2,}|https?://(?:www\.|(?!www))[a-zA-Z0-9]+\.\S{2,}|www\.[a-zA-Z0-9]+\.\S{2,})"
    )
    message = pattern.sub("", message)

    # 去除零宽空白符
    message = re.sub(r"\u200b", "", message)
    # 去除 emoji
    message = replace_emoji(message)

    return message


def analyse_message(message_text: str) -> dict[str, float]:
    """使用 jieba 分词, 使用基于 TF-IDF 算法的关键词抽取方法统计词频"""
    # 设置停用词表和加载用户词典
    jieba.analyse.set_stop_words(wordcloud_plugin_resource_config.default_stop_words_file.resolve_path)
    if wordcloud_plugin_resource_config.user_dict_file.is_file:
        jieba.load_userdict(wordcloud_plugin_resource_config.user_dict_file.resolve_path)

    # 分词和统计词频
    return {str(word): freq for word, freq in jieba.analyse.extract_tags(message_text, topK=0, withWeight=True)}


@run_sync
def _draw_message_history_wordcloud(messages: Sequence["History"]) -> bytes:
    """根据查询到的消息历史记录绘制词云"""
    # 统计历史消息词频
    prepared_message = prepare_message(messages=[m.message_text for m in messages])
    word_frequency = analyse_message(message_text=prepared_message)

    wordcloud_options = wordcloud_plugin_config.wordcloud_default_options
    wordcloud_options.update({
        'font_path': wordcloud_plugin_resource_config.default_font_file.resolve_path,
    })

    wordcloud = WordCloud(**wordcloud_options)
    wordcloud_image: "Image" = wordcloud.generate_from_frequencies(word_frequency).to_image()

    with BytesIO() as bf:
        wordcloud_image.save(bf, 'PNG')
        content = bf.getvalue()
    return content


async def draw_message_history_wordcloud(messages: Sequence["History"]) -> "TemporaryResource":
    """根据查询到的消息历史记录绘制词云"""
    wordcloud_image_content = await _draw_message_history_wordcloud(messages=messages)
    output_file_name = f'wordcloud_{hash(wordcloud_image_content)}_{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}.png'
    output_file = wordcloud_plugin_resource_config.default_output_dir(output_file_name)

    async with output_file.async_open('wb') as af:
        await af.write(wordcloud_image_content)

    return output_file


__all__ = [
    'draw_message_history_wordcloud',
]
