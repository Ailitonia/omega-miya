"""
@Author         : Ailitonia
@Date           : 2021/09/01 1:20
@FileName       : utils.py
@Project        : nonebot2_miya 
@Description    : 塔罗牌图片生成相关模块
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import os
import asyncio
from datetime import datetime
from nonebot import get_driver
from PIL import Image, ImageDraw, ImageFont
from omega_miya.database import Result
from omega_miya.utils.omega_plugin_utils import TextUtils
from .tarot_resources import BaseTarotResources


global_config = get_driver().config
TMP_PATH = global_config.tmp_path_
RESOURCES_PATH = global_config.resources_path_
TAROT_CARD_PATH = os.path.abspath(os.path.join(TMP_PATH, 'tarot_card'))


async def generate_tarot_card(
        id_: int,
        resources: BaseTarotResources,
        direction: int = 1,
        *,
        need_desc: bool = True,
        need_positive: bool = True,
        need_negative: bool = True,
        width: int = 1024) -> Result.TextResult:
    """
    绘制塔罗卡片
    :param id_: 牌id
    :param resources: 卡片资源
    :param direction: 方向, 1: 正, -1: 逆
    :param need_desc: 是否绘制描述
    :param need_positive: 是否绘制正位描述
    :param need_negative: 是否绘制逆位描述
    :param width: 绘制图片宽度
    :return:
    """
    # 获取这张卡牌
    tarot_card = resources.pack.get_card_by_id(id_=id_)

    def __handle():
        # 获取卡片图片
        draw_tarot_img: Image.Image = Image.open(resources.resources.get_file_by_id(id_=id_))
        # 正逆
        if direction < 0:
            draw_tarot_img = draw_tarot_img.rotate(180)

        # 调整头图宽度
        tarot_img_height = int(width * draw_tarot_img.height / draw_tarot_img.width)
        draw_tarot_img = draw_tarot_img.resize((width, tarot_img_height))

        # 字体
        font_path = os.path.abspath(os.path.join(RESOURCES_PATH, 'fonts', 'fzzxhk.ttf'))
        title_font = ImageFont.truetype(font_path, width // 10)
        m_title_font = ImageFont.truetype(font_path, width // 20)
        text_font = ImageFont.truetype(font_path, width // 25)

        # 标题
        title_width, title_height = title_font.getsize(tarot_card.name)
        m_title_width, m_title_height = m_title_font.getsize(tarot_card.name)

        # 描述
        desc_text = TextUtils(text=tarot_card.desc).split_multiline(width=(width - int(width * 0.125)), font=text_font)
        desc_text_width, desc_text_height = text_font.getsize_multiline(desc_text)

        # 正位描述
        positive_text = TextUtils(
            text=tarot_card.positive).split_multiline(width=(width - int(width * 0.125)), font=text_font)
        positive_text_width, positive_text_height = text_font.getsize_multiline(positive_text)

        # 逆位描述
        negative_text = TextUtils(
            text=tarot_card.negative).split_multiline(width=(width - int(width * 0.125)), font=text_font)
        negative_text_width, negative_text_height = text_font.getsize_multiline(negative_text)

        # 计算高度
        background_height = title_height + m_title_height + tarot_img_height + int(0.09375 * width)
        if need_desc:
            background_height += desc_text_height + int(0.125 * width)
        if need_positive:
            background_height += m_title_height + positive_text_height + int(0.125 * width)
        if need_negative:
            background_height += m_title_height + negative_text_height + int(0.125 * width)

        # 生成背景
        background = Image.new(
            mode="RGB",
            size=(width, background_height),
            color=(255, 255, 255))

        # 开始往背景上绘制各个元素
        # 以下排列从上到下绘制 请勿变换顺序 否则导致位置错乱
        this_height = int(0.0625 * width)
        ImageDraw.Draw(background).text(xy=(width // 2, this_height),
                                        text=tarot_card.name, font=title_font, align='center', anchor='mt',
                                        fill=(0, 0, 0))  # 中文名称

        this_height += title_height
        ImageDraw.Draw(background).text(xy=(width // 2, this_height),
                                        text=tarot_card.orig_name, font=m_title_font, align='center', anchor='ma',
                                        fill=(0, 0, 0))  # 英文名称

        this_height += m_title_height + int(0.03125 * width)
        background.paste(draw_tarot_img, box=(0, this_height))  # 卡面

        this_height += tarot_img_height
        if need_desc:
            this_height += int(0.0625 * width)
            ImageDraw.Draw(background).multiline_text(xy=(width // 2, this_height),
                                                      text=desc_text, font=text_font, align='center', anchor='ma',
                                                      fill=(0, 0, 0))  # 描述
            this_height += desc_text_height

        if need_positive:
            this_height += int(0.0625 * width)
            ImageDraw.Draw(background).text(xy=(width // 2, this_height),
                                            text='【正位】', font=m_title_font, align='center', anchor='ma',
                                            fill=(0, 0, 0))  # 正位

            this_height += m_title_height + int(0.03125 * width)
            ImageDraw.Draw(background).multiline_text(xy=(width // 2, this_height),
                                                      text=positive_text, font=text_font, align='center', anchor='ma',
                                                      fill=(0, 0, 0))  # 正位描述
            this_height += positive_text_height

        if need_negative:
            this_height += int(0.0625 * width)
            ImageDraw.Draw(background).text(xy=(width // 2, this_height),
                                            text='【逆位】', font=m_title_font, align='center', anchor='ma',
                                            fill=(0, 0, 0))  # 逆位

            this_height += m_title_height + int(0.03125 * width)
            ImageDraw.Draw(background).multiline_text(xy=(width // 2, this_height),
                                                      text=negative_text, font=text_font, align='center', anchor='ma',
                                                      fill=(0, 0, 0))  # 逆位描述

        if not os.path.exists(TAROT_CARD_PATH):
            os.makedirs(TAROT_CARD_PATH)

        save_path = os.path.abspath(os.path.join(
            TAROT_CARD_PATH, f"tarot_card_{tarot_card.index}_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.jpg"))
        background.save(save_path, 'JPEG')
        return save_path

    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, __handle)
        return Result.TextResult(error=False, info='Success', result=result)
    except Exception as e:
        return Result.TextResult(error=True, info=repr(e), result='')


__all__ = [
    'generate_tarot_card'
]
