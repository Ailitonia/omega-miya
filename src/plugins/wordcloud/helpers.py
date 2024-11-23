"""
@Author         : Ailitonia
@Date           : 2024/11/17 18:25
@FileName       : helpers
@Project        : omega-miya
@Description    : 词云图片绘制模块
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import re
from collections.abc import Sequence
from datetime import datetime
from io import BytesIO
from typing import TYPE_CHECKING, Optional

import jieba
import jieba.analyse
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
from emoji import replace_emoji
from nonebot.log import logger
from nonebot.utils import run_sync
from wordcloud import WordCloud

from src.service.artwork_collection import get_artwork_collection, get_artwork_collection_type
from .config import wordcloud_plugin_config, wordcloud_plugin_resource_config

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from src.database.internal.history import History
    from src.resource import TemporaryResource


def prepare_message(messages: Sequence[str]) -> str:
    """预处理消息文本"""
    # 过滤命令消息
    command_start = tuple(i for i in wordcloud_plugin_config.command_start if i)
    message = ' '.join(m for m in messages if not m.startswith(command_start))

    # 过滤网址, ref: https://stackoverflow.com/a/17773849
    pattern = re.compile(
        r'(https?://(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.\S{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]'
        r'+[a-zA-Z0-9]\.\S{2,}|https?://(?:www\.|(?!www))[a-zA-Z0-9]+\.\S{2,}|www\.[a-zA-Z0-9]+\.\S{2,})'
    )
    message = pattern.sub('', message)

    # 去除零宽空白符
    message = re.sub(r'\u200b', '', message)
    # 去除 emoji
    message = replace_emoji(message)

    return message


def _analyse_tf_idf(message_text: str) -> dict[str, float]:
    """基于 TF-IDF 算法的关键词抽取方法统计词频"""
    return {str(word): freq for word, freq in jieba.analyse.extract_tags(message_text, topK=0, withWeight=True)}


def _analyse_textrank(message_text: str) -> dict[str, float]:
    """基于 TextRank 算法的关键词抽取方法统计词频"""
    return {str(word): freq for word, freq in jieba.analyse.textrank(message_text, topK=0, withWeight=True)}


def analyse_message(message_text: str) -> dict[str, float]:
    """使用 jieba 分词, 并进行关键词抽取和词频统计"""
    # 设置停用词表和加载用户词典
    jieba.analyse.set_stop_words(wordcloud_plugin_resource_config.default_stop_words_file.resolve_path)
    if wordcloud_plugin_resource_config.user_dict_file.is_file:
        jieba.load_userdict(wordcloud_plugin_resource_config.user_dict_file.resolve_path)

    # 分词和统计词频
    match wordcloud_plugin_config.wordcloud_plugin_message_analyse_mode:
        case 'TextRank':
            return _analyse_textrank(message_text)
        case 'TF-IDF' | _:
            return _analyse_tf_idf(message_text)


async def _get_random_background_artwork() -> 'TemporaryResource':
    """从数据库获取作品作为背景图"""
    random_artworks = await get_artwork_collection_type().query_any_origin_by_condition(
        keywords=None, origin=wordcloud_plugin_config.wordcloud_plugin_artwork_background_origin,
        num=3, allow_classification_range=(2, 3), allow_rating_range=(0, 0), ratio=1
    )

    for artwork in random_artworks:
        try:
            return await get_artwork_collection(artwork=artwork).artwork_proxy.get_page_file()
        except Exception as e:
            logger.warning(f'getting artwork(origin={artwork.origin}, aid={artwork.aid}) page file failed, {e}')
            continue

    raise RuntimeError('all attempts to fetch artwork resources have failed')


def _draw_wordcloud_mask(width: int, height: int) -> 'NDArray':
    """生成词云蒙版"""
    mask_size = (width, height)
    background: Image.Image = Image.new(mode='RGBA', size=mask_size, color=(255, 255, 255, 0))
    mask_draw = ImageDraw.Draw(background)
    mask_draw.chord(xy=((0, 0), mask_size), start=0, end=90, fill=(0, 0, 0, 255))
    mask_draw.polygon(
        xy=(
            (0, 0),
            (mask_size[0], 0),
            (mask_size[0], mask_size[1] // 2),
            (mask_size[0] // 2, mask_size[1]),
            (0, mask_size[1]),
        ),
        fill=(0, 0, 0, 255)
    )
    with BytesIO() as buffer:
        background.save(buffer, format='PNG')
        mask_np = np.array(Image.open(buffer))
    return mask_np


def _generate_message_history_wordcloud(messages: Sequence['History'], **wordcloud_options) -> 'Image.Image':
    """根据查询到的消息历史记录绘制词云"""
    # 统计历史消息词频
    prepared_message = prepare_message(messages=[m.message_text for m in messages])
    word_frequency = analyse_message(message_text=prepared_message)

    # 生成词云
    wordcloud = WordCloud(**wordcloud_options)
    wordcloud_image: Image.Image = wordcloud.generate_from_frequencies(word_frequency).to_image()

    return wordcloud_image


@run_sync
def _draw_message_history_wordcloud(
        messages: Sequence['History'],
        background_file: Optional['TemporaryResource'] = None,
        profile_image_file: Optional['TemporaryResource'] = None,
        desc_text: str | None = None,
) -> bytes:
    """根据查询到的消息历史记录绘制词云"""
    if background_file is not None:
        background = Image.open(background_file.resolve_path).convert('RGBA')
        background = Image.blend(background, Image.new('RGBA', background.size, (255, 255, 255, 255)), 0.75)
        background = background.filter(ImageFilter.GaussianBlur(radius=2))
        width, height = background.size
    else:
        background = Image.new('RGBA', wordcloud_plugin_config.default_image_size, (255, 255, 255, 255))
        width, height = wordcloud_plugin_config.default_image_size

    # 放置背景图片
    mask = _draw_wordcloud_mask(width=width, height=height)
    image_main = Image.new(mode='RGBA', size=(width, height), color=(255, 255, 255, 255))
    image_main.paste(background, mask=Image.fromarray(mask))

    # 生成词云图片
    wordcloud_options = wordcloud_plugin_config.wordcloud_default_options
    wordcloud_options.update({
        'font_path': wordcloud_plugin_resource_config.default_font_file.resolve_path,
        'mask': mask,
        'width': width,
        'height': height,
    })
    wordcloud_image = _generate_message_history_wordcloud(messages=messages, **wordcloud_options)

    # 放置词云图片
    image_main.paste(
        im=wordcloud_image,
        mask=ImageOps.colorize(
            image=wordcloud_image.convert('L'),
            black=(255, 255, 255),
            white=(0, 0, 0),
            blackpoint=225
        ).convert('L')
    )

    # 处理和放置头像
    if profile_image_file is not None:
        profile_image = Image.open(profile_image_file.resolve_path).convert('RGBA')
        profile_image = profile_image.resize(size=(height // 10, height // 10))
        profile_mask = Image.new(mode='L', size=profile_image.size, color=0)
        ImageDraw.Draw(profile_mask).ellipse(xy=((0, 0), profile_image.size), fill=255)
        image_main.paste(
            im=profile_image,
            box=(width - int(height / 10 * 1.2), height // 10 * 8),
            mask=profile_mask,
        )

    # 放置文本内容
    if desc_text is not None:
        font = ImageFont.truetype(wordcloud_plugin_resource_config.default_font_file.resolve_path, size=height // 54)
        ImageDraw.Draw(image_main).multiline_text(
            xy=(width - int(height / 10 * 0.2), int(height / 10 * 9.2)),
            text=desc_text,
            font=font,
            anchor='ra',
            align='right',
            fill=(96, 96, 96)
        )

    with BytesIO() as bf:
        image_main.save(bf, 'PNG')
        content = bf.getvalue()
    return content


async def draw_message_history_wordcloud(
        messages: Sequence['History'],
        profile_image_file: Optional['TemporaryResource'] = None,
        desc_text: str | None = None,
) -> 'TemporaryResource':
    """根据查询到的消息历史记录绘制词云"""
    background = None
    if wordcloud_plugin_config.wordcloud_plugin_enable_collected_artwork_background:
        background = await _get_random_background_artwork()

    wordcloud_image_content = await _draw_message_history_wordcloud(
        messages=messages,
        background_file=background,
        profile_image_file=profile_image_file,
        desc_text=desc_text,
    )
    output_file_name = f'wordcloud_{hash(wordcloud_image_content)}_{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}.png'
    output_file = wordcloud_plugin_resource_config.default_output_dir(output_file_name)

    async with output_file.async_open('wb') as af:
        await af.write(wordcloud_image_content)
    return output_file


__all__ = [
    'draw_message_history_wordcloud',
]
