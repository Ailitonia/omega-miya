"""
@Author         : Ailitonia
@Date           : 2022/05/07 21:02
@FileName       : render.py
@Project        : nonebot2_miya 
@Description    : Sticker Renders
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import date
from typing import TYPE_CHECKING, Any, Optional, Sequence, Literal

import numpy
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

from src.utils import OmegaRequests
from src.utils.image_utils import ImageUtils
from src.utils.tencent_cloud_api import TencentTMT
from .consts import STATIC_RESOURCE, FONT_RESOURCE, TMP_PATH
from .model import BaseStickerRender

if TYPE_CHECKING:
    from src.resource import StaticResource, TemporaryResource


class TraitorRender(BaseStickerRender):
    """有内鬼表情包模板"""

    @classmethod
    def need_text(cls) -> bool:
        return True

    @classmethod
    def need_external_image(cls) -> bool:
        return False

    @classmethod
    def get_output_width(cls) -> int:
        return 800

    @classmethod
    def get_output_format(cls) -> Literal['JPEG', 'PNG', 'GIF']:
        return 'PNG'

    @classmethod
    def get_default_fonts(cls) -> list["StaticResource"]:
        return [FONT_RESOURCE('pixel.ttf')]

    @classmethod
    def get_static_images(cls) -> list["StaticResource"]:
        return [STATIC_RESOURCE('traitor', 'default_bg.png')]

    @classmethod
    def _core_render(
            cls,
            text: Optional[str],
            static_images: Sequence["Image.Image"],
            external_image: Optional["Image.Image"],
            *,
            fonts: Sequence["StaticResource"],
            output_width: int,
            output_format: str,
    ) -> "Image.Image":
        image = cls._resize_to_width(image=static_images[0], width=output_width)
        text = '有内鬼, 中止交易' if text is None else text[:100]

        # 初始化背景图层
        background = Image.new(mode='RGB', size=image.size, color=(255, 255, 255))

        # 处理文字层 字数部分
        text_num_img = Image.new(mode='RGBA', size=image.size, color=(0, 0, 0, 0))
        font_num_size = int(image.width / 16.6)
        font_num = ImageFont.truetype(fonts[0].resolve_path, font_num_size)
        ImageDraw.Draw(text_num_img).text(xy=(0, 0), text=f'{len(text)}/100', font=font_num, fill=(255, 255, 255))

        # 处理文字层 主体部分
        text_main_img = Image.new(mode='RGBA', size=image.size, color=(0, 0, 0, 0))
        font_main_size = int(image.width / 15.6)
        font_main = ImageFont.truetype(fonts[0].resolve_path, font_main_size)
        # 按长度切分文本
        test_main_fin = ImageUtils.split_multiline_text(text=text, width=int(image.width * 0.53), font=font_main)
        ImageDraw.Draw(text_main_img).multiline_text(xy=(0, 0), text=test_main_fin, font=font_main, spacing=12,
                                                     fill=(0, 0, 0))

        # 处理文字部分旋转
        text_num_img = text_num_img.rotate(angle=-9, expand=True, resample=Image.Resampling.BICUBIC, center=(0, 0))
        text_main_img = text_main_img.rotate(angle=-9.25, expand=True, resample=Image.Resampling.BICUBIC, center=(0, 0))

        # 向模板图片中置入文字图层
        background.paste(im=image, box=(0, 0))
        background.paste(im=text_num_img, box=(int(image.width / 1.84), int(image.width / 5.715)), mask=text_num_img)
        background.paste(im=text_main_img, box=(int(image.width / 6.4), int(image.width / 5.16)), mask=text_main_img)

        return background


class JichouRender(BaseStickerRender):
    """记仇表情包模板"""

    @classmethod
    def need_text(cls) -> bool:
        return True

    @classmethod
    def need_external_image(cls) -> bool:
        return False

    @classmethod
    def get_output_width(cls) -> int:
        return 512

    @classmethod
    def get_output_format(cls) -> Literal['JPEG', 'PNG', 'GIF']:
        return 'JPEG'

    @classmethod
    def get_default_fonts(cls) -> list["StaticResource"]:
        return [FONT_RESOURCE('SourceHanSansSC-Regular.otf')]

    @classmethod
    def get_static_images(cls) -> list["StaticResource"]:
        return [STATIC_RESOURCE('jichou', 'default_bg.png')]

    @classmethod
    def _core_render(
            cls,
            text: Optional[str],
            static_images: Sequence["Image.Image"],
            external_image: Optional["Image.Image"],
            *,
            fonts: Sequence["StaticResource"],
            output_width: int,
            output_format: str,
    ) -> "Image.Image":
        image = cls._resize_to_width(image=static_images[0], width=output_width)

        # 处理文本主体
        text = f'今天是{date.today().strftime("%Y年%m月%d日")}\n{text}，这个仇我先记下了'

        font_main_size = int(image.width / 12)
        font = ImageFont.truetype(fonts[0].resolve_path, font_main_size)
        # 按长度切分文本
        text_main_fin = ImageUtils.split_multiline_text(text=text, width=(image.width * 7 // 8), font=font)
        _, text_h = ImageUtils.get_text_size(text=text_main_fin, font=font)

        # 处理图片
        background_h = int(image.height * 1.08) + text_h
        background = Image.new(mode='RGB', size=(image.width, background_h), color=(255, 255, 255))

        # 处理粘贴位置 顶头
        background.paste(image, (0, 0))

        draw = ImageDraw.Draw(background)
        # 计算居中文字位置
        text_coordinate = ((image.width // 2), int(image.height))
        draw.multiline_text(text_coordinate, text_main_fin, anchor='ma', font=font, fill=(0, 0, 0))

        return background


class PhLogoRender(BaseStickerRender):
    """phlogo 表情包模板"""

    @classmethod
    def need_text(cls) -> bool:
        return True

    @classmethod
    def need_external_image(cls) -> bool:
        return False

    @classmethod
    def get_output_width(cls) -> int:
        return 0

    @classmethod
    def get_output_format(cls) -> Literal['JPEG', 'PNG', 'GIF']:
        return 'PNG'

    @classmethod
    def get_default_fonts(cls) -> list["StaticResource"]:
        return [FONT_RESOURCE('SourceHanSansSC-Heavy.otf')]

    @classmethod
    def get_static_images(cls) -> list["StaticResource"]:
        return []

    @classmethod
    def _core_render(
            cls,
            text: Optional[str],
            static_images: Sequence["Image.Image"],
            external_image: Optional["Image.Image"],
            *,
            fonts: Sequence["StaticResource"],
            output_width: int,
            output_format: str,
    ) -> "Image.Image":
        # 处理文本主体
        text = 'Git Hub' if text is None else text
        test_sentences = text.strip().split(maxsplit=1)
        match len(test_sentences):
            case 2:
                white_text = test_sentences[0]
                yellow_text = test_sentences[1]
            case _:
                white_text = text[:len(text) // 2]
                yellow_text = text[len(text) // 2:]

        font = ImageFont.truetype(fonts[0].resolve_path, 320)

        # 分别确定两边文字的大小
        w_text_width, text_height = ImageUtils.get_text_size(white_text, font)
        y_text_width, _ = ImageUtils.get_text_size(yellow_text, font)

        # 生成图片定长 两部分文字之间间隔及两侧留空为固定值三个空格大小
        split_width, _ = ImageUtils.get_text_size(' ', font)
        image_width = w_text_width + y_text_width + int(split_width * 5.5)
        image_height = int(text_height * 2.25)

        # 计算黄色圆角矩形所在位置
        y_r_rectangle_x0 = w_text_width + int(split_width * 2.5)
        y_r_rectangle_y0 = int(text_height * 0.425)
        y_r_rectangle_x1 = image_width - int(split_width * 2)
        y_r_rectangle_y1 = int(text_height * 2)

        # 生成背景层
        background = Image.new(mode='RGB', size=(image_width, image_height), color=(0, 0, 0))
        background_draw = ImageDraw.Draw(background)
        # 生成圆角矩形
        background_draw.rounded_rectangle(
            xy=((y_r_rectangle_x0, y_r_rectangle_y0), (y_r_rectangle_x1, y_r_rectangle_y1)),
            radius=(image_height // 20),
            fill=(254, 154, 0)
        )

        # 绘制白色文字部分
        background_draw.text(
            xy=(split_width * 2, image_height // 2),  # 左对齐前间距 上下居中
            text=white_text,
            anchor='lm',
            font=font,
            fill=(255, 255, 255)
        )
        # 绘制黄框黑字部分
        background_draw.text(
            xy=(w_text_width + int(split_width * 3), image_height // 2),  # 左对齐白字加间距 上下居中
            text=yellow_text,
            anchor='lm',
            font=font,
            fill=(0, 0, 0)
        )

        return background


class LuxunSayRender(BaseStickerRender):
    """鲁迅说表情包模板"""

    @classmethod
    def need_text(cls) -> bool:
        return True

    @classmethod
    def need_external_image(cls) -> bool:
        return False

    @classmethod
    def get_output_width(cls) -> int:
        return 512

    @classmethod
    def get_output_format(cls) -> Literal['JPEG', 'PNG', 'GIF']:
        return 'JPEG'

    @classmethod
    def get_default_fonts(cls) -> list["StaticResource"]:
        return [FONT_RESOURCE('SourceHanSansSC-Regular.otf')]

    @classmethod
    def get_static_images(cls) -> list["StaticResource"]:
        return [STATIC_RESOURCE('luxunsay', 'default_bg.png')]

    @classmethod
    def _core_render(
            cls,
            text: Optional[str],
            static_images: Sequence["Image.Image"],
            external_image: Optional["Image.Image"],
            *,
            fonts: Sequence["StaticResource"],
            output_width: int,
            output_format: str,
    ) -> "Image.Image":
        image = cls._resize_to_width(image=static_images[0], width=output_width)

        # 处理文本主体
        text = '我没说过' if text is None else text
        font_size = image.width // 15
        text_stroke_width = int(font_size / 15)
        font = ImageFont.truetype(fonts[0].resolve_path, font_size)
        text_width_limit = int(image.width * 0.8125)

        sign_text = '—— 鲁迅'

        # 分割文本
        text_ = ImageUtils.split_multiline_text(
            text=text, width=text_width_limit, font=font, stroke_width=text_stroke_width
        )

        # 文本大小
        _, main_text_height = ImageUtils.get_text_size(text_, font, stroke_width=text_stroke_width)
        _, sign_text_height = ImageUtils.get_text_size(sign_text, font, stroke_width=text_stroke_width)

        # 创建背景图层
        # 定位主体文字到图片下侧往上 1/4 处, 落款与主体文字间隔半行, 底部间隔一行, 超出部分为所有文字高度减去图片 1/4 高度
        bg_height_inc_ = int(main_text_height + sign_text_height * 2.5 - image.height * 0.25)
        bg_height_inc = bg_height_inc_ if bg_height_inc_ > 0 else 0
        background = Image.new(
            mode='RGB',
            size=(image.width, image.height + bg_height_inc),
            color=(32, 32, 32))

        # 先把鲁迅图贴上去
        background.paste(image, box=(0, 0))

        # 再贴主体文本
        ImageDraw.Draw(background).multiline_text(
            xy=(image.width // 2, int(image.height * 0.75)),
            text=text_, font=font, align='left', anchor='ma',
            fill=(255, 255, 255),
            stroke_width=text_stroke_width,
            stroke_fill=(0, 0, 0))

        ImageDraw.Draw(background).text(
            xy=(int(image.width * 0.85), int(main_text_height + sign_text_height / 2 + image.height * 0.75)),
            text=sign_text, font=font, align='right', anchor='ra',
            fill=(255, 255, 255),
            stroke_width=text_stroke_width,
            stroke_fill=(0, 0, 0))

        return background


class LuxunWriteRender(LuxunSayRender):
    """鲁迅写表情包模板"""

    @classmethod
    def get_static_images(cls) -> list["StaticResource"]:
        return [STATIC_RESOURCE('luxunwrite', 'default_bg.png')]


class JiangzhuangRender(BaseStickerRender):
    """奖状表情包模板"""

    @classmethod
    def need_text(cls) -> bool:
        return True

    @classmethod
    def need_external_image(cls) -> bool:
        return False

    @classmethod
    def get_output_width(cls) -> int:
        return 1024

    @classmethod
    def get_output_format(cls) -> Literal['JPEG', 'PNG', 'GIF']:
        return 'JPEG'

    @classmethod
    def get_default_fonts(cls) -> list["StaticResource"]:
        return [FONT_RESOURCE('HanYiWeiBeiJian.ttf')]

    @classmethod
    def get_static_images(cls) -> list["StaticResource"]:
        return [STATIC_RESOURCE('jiangzhuang', 'default_bg.png')]

    @classmethod
    def _core_render(
            cls,
            text: Optional[str],
            static_images: Sequence["Image.Image"],
            external_image: Optional["Image.Image"],
            *,
            fonts: Sequence["StaticResource"],
            output_width: int,
            output_format: str,
    ) -> "Image.Image":
        image = cls._resize_to_width(image=static_images[0], width=output_width)

        # 处理文本主体
        text = ' ' if text is None else text
        font_size = image.width // 22
        font = ImageFont.truetype(fonts[0].resolve_path, font_size)
        text_width_limit = int(image.width * 0.65)

        # 分割文本
        text_ = ImageUtils.split_multiline_text(text=text, width=text_width_limit, font=font)

        # 粘贴主体文本
        ImageDraw.Draw(image).multiline_text(
            xy=(image.width // 2, int(image.height * 5 / 9)),
            text=text_, font=font, align='left', anchor='mm',
            spacing=16,
            fill=(0, 0, 0))

        return image


class XibaoHorizontalRender(BaseStickerRender):
    """喜报横版情包模板"""

    @classmethod
    def need_text(cls) -> bool:
        return True

    @classmethod
    def need_external_image(cls) -> bool:
        return False

    @classmethod
    def get_output_width(cls) -> int:
        return 1024

    @classmethod
    def get_output_format(cls) -> Literal['JPEG', 'PNG', 'GIF']:
        return 'JPEG'

    @classmethod
    def get_default_fonts(cls) -> list["StaticResource"]:
        return [FONT_RESOURCE('HanYiWeiBeiJian.ttf')]

    @classmethod
    def get_static_images(cls) -> list["StaticResource"]:
        return [STATIC_RESOURCE('xibaoh', 'default_bg.png')]

    @classmethod
    def _core_render(
            cls,
            text: Optional[str],
            static_images: Sequence["Image.Image"],
            external_image: Optional["Image.Image"],
            *,
            fonts: Sequence["StaticResource"],
            output_width: int,
            output_format: str,
    ) -> "Image.Image":
        image = cls._resize_to_width(image=static_images[0], width=output_width)

        # 处理文本主体
        text = ' ' if text is None else text
        font_size = image.width // 15
        font = ImageFont.truetype(fonts[0].resolve_path, font_size)
        text_stroke_width = int(font_size / 15)
        text_width_limit = int(image.width * 0.75)

        # 分割文本
        text_ = ImageUtils.split_multiline_text(
            text=text, width=text_width_limit, font=font, stroke_width=text_stroke_width
        )

        # 粘贴主体文本
        ImageDraw.Draw(image).multiline_text(
            xy=(image.width // 2, int(image.height / 2)),
            text=text_, font=font, align='left', anchor='mm',
            spacing=16,
            stroke_width=text_stroke_width,
            stroke_fill=(255, 255, 153),
            fill=(238, 0, 0))

        return image


class XibaoVerticalRender(BaseStickerRender):
    """喜报竖版情包模板"""

    @classmethod
    def need_text(cls) -> bool:
        return True

    @classmethod
    def need_external_image(cls) -> bool:
        return False

    @classmethod
    def get_output_width(cls) -> int:
        return 1024

    @classmethod
    def get_output_format(cls) -> Literal['JPEG', 'PNG', 'GIF']:
        return 'JPEG'

    @classmethod
    def get_default_fonts(cls) -> list["StaticResource"]:
        return [FONT_RESOURCE('SourceHanSerif-Bold.ttc')]

    @classmethod
    def get_static_images(cls) -> list["StaticResource"]:
        return [STATIC_RESOURCE('xibaos', 'default_bg.png')]

    @classmethod
    def _core_render(
            cls,
            text: Optional[str],
            static_images: Sequence["Image.Image"],
            external_image: Optional["Image.Image"],
            *,
            fonts: Sequence["StaticResource"],
            output_width: int,
            output_format: str,
    ) -> "Image.Image":
        image = cls._resize_to_width(image=static_images[0], width=output_width)

        # 处理文本主体
        text = ' ' if text is None else text
        font_size = image.width // 15
        font = ImageFont.truetype(fonts[0].resolve_path, font_size)
        text_stroke_width = int(font_size / 50)
        text_width_limit = int(image.width * 0.75)

        # 分割文本
        text_ = ImageUtils.split_multiline_text(
            text=text, width=text_width_limit, font=font, stroke_width=text_stroke_width
        )

        # 粘贴主体文本
        ImageDraw.Draw(image).multiline_text(
            xy=(image.width // 2, int(image.height * 10 / 17)),
            text=text_, font=font, align='center', anchor='mm',
            spacing=16,
            stroke_width=text_stroke_width,
            stroke_fill=(153, 0, 0),
            fill=(255, 255, 153))

        return image


class DefaultRender(BaseStickerRender):
    """默认加字表情包模板"""

    @classmethod
    def need_text(cls) -> bool:
        return True

    @classmethod
    def need_external_image(cls) -> bool:
        return True

    @classmethod
    def get_output_width(cls) -> int:
        return 512

    @classmethod
    def get_output_format(cls) -> Literal['JPEG', 'PNG', 'GIF']:
        return 'JPEG'

    @classmethod
    def get_default_fonts(cls) -> list["StaticResource"]:
        return [FONT_RESOURCE('msyhbd.ttc')]

    @classmethod
    def get_static_images(cls) -> list["StaticResource"]:
        return []

    @classmethod
    def _core_render(
            cls,
            text: Optional[str],
            static_images: Sequence["Image.Image"],
            external_image: Optional["Image.Image"],
            *,
            fonts: Sequence["StaticResource"],
            output_width: int,
            output_format: str,
    ) -> "Image.Image":
        if external_image is None:
            raise ValueError('external_image can not be None')
        if external_image.format != 'RGB':
            external_image = external_image.convert('RGB')

        text = ' ' if text is None else text
        font_size = external_image.width // 8
        text_stroke_width = int(font_size / 20)
        font = ImageFont.truetype(fonts[0].resolve_path, font_size)

        text_w, text_h = ImageUtils.get_text_size(text, font=font, stroke_width=text_stroke_width)
        # 自适应处理文字大小
        while text_w >= int(external_image.width * 0.95):
            font_size -= 1
            font = ImageFont.truetype(fonts[0].resolve_path, font_size)
            text_w, text_h = ImageUtils.get_text_size(text, font=font, stroke_width=text_stroke_width)
        # 计算居中文字位置
        text_coordinate = (external_image.width // 2, 9 * (external_image.height - text_h) // 10)
        ImageDraw.Draw(external_image).multiline_text(
            xy=text_coordinate, text=text,
            font=font, fill=(255, 255, 255), align='center', anchor='ma',
            stroke_width=text_stroke_width, stroke_fill=(0, 0, 0)
        )

        return external_image


class LittleAngelRender(BaseStickerRender):
    """小天使表情包模板"""

    @classmethod
    def need_text(cls) -> bool:
        return True

    @classmethod
    def need_external_image(cls) -> bool:
        return True

    @classmethod
    def get_output_width(cls) -> int:
        return 512

    @classmethod
    def get_output_format(cls) -> Literal['JPEG', 'PNG', 'GIF']:
        return 'JPEG'

    @classmethod
    def get_default_fonts(cls) -> list["StaticResource"]:
        return [FONT_RESOURCE('msyhbd.ttc')]

    @classmethod
    def get_static_images(cls) -> list["StaticResource"]:
        return []

    @classmethod
    def _core_render(
            cls,
            text: Optional[str],
            static_images: Sequence["Image.Image"],
            external_image: Optional["Image.Image"],
            *,
            fonts: Sequence["StaticResource"],
            output_width: int,
            output_format: str,
    ) -> "Image.Image":
        if external_image is None:
            raise ValueError('external_image can not be None')
        if external_image.format != 'RGB':
            external_image = external_image.convert('RGB')

        # 处理文本内容
        text = ' ' if text is None else text
        font_size_up = int(external_image.width / 7)
        font_up = ImageFont.truetype(fonts[0].resolve_path, font_size_up)
        text_up = f'请问你们看到{text}了吗?'
        text_up_w, text_up_h = ImageUtils.get_text_size(text_up, font_up)
        # 自适应处理文字大小
        while text_up_w >= int(external_image.width * 1.14):
            font_size_up -= 1
            font_up = ImageFont.truetype(fonts[0].resolve_path, font_size_up)
            text_up_w, text_up_h = ImageUtils.get_text_size(text_up, font_up)

        # 处理图片
        background = Image.new(
            mode='RGB',
            size=(
                int(external_image.width * 1.2),
                int(external_image.width * 0.368 + text_up_h + external_image.height)
            ),
            color=(255, 255, 255)
        )

        # 粘贴头部文字
        ImageDraw.Draw(background).text(
            xy=(background.width // 2, int(external_image.width * 0.0512)),
            text=text_up, anchor='ma', font=font_up, fill=(0, 0, 0))

        # 处理图片粘贴位置
        image_coordinate = (
            ((background.width - external_image.width) // 2),
            int(external_image.width * 0.096 + text_up_h)
        )
        background.paste(external_image, image_coordinate)

        # 粘贴底部文字
        font_down_1 = ImageFont.truetype(fonts[0].resolve_path, int(background.width / 12.75))
        text_down_1 = r'非常可爱! 简直就是小天使'
        ImageDraw.Draw(background).text(
            xy=(background.width // 2, int(external_image.width * 0.135 + external_image.height + text_up_h)),
            text=text_down_1, anchor='ma', font=font_down_1, fill=(0, 0, 0)
        )

        font_down_2 = ImageFont.truetype(fonts[0].resolve_path, int(background.width / 23.54))
        text_down_2 = r'她没失踪也没怎么样  我只是觉得你们都该看一下'
        ImageDraw.Draw(background).text(
            xy=(background.width // 2, int(external_image.width * 0.255 + external_image.height + text_up_h)),
            text=text_down_2, anchor='ma', font=font_down_2, fill=(0, 0, 0)
        )

        return background


class WhiteBackgroundRender(BaseStickerRender):
    """白底加字表情包模板"""

    @classmethod
    def need_text(cls) -> bool:
        return True

    @classmethod
    def need_external_image(cls) -> bool:
        return True

    @classmethod
    def get_output_width(cls) -> int:
        return 512

    @classmethod
    def get_output_format(cls) -> Literal['JPEG', 'PNG', 'GIF']:
        return 'JPEG'

    @classmethod
    def get_default_fonts(cls) -> list["StaticResource"]:
        return [FONT_RESOURCE('msyhbd.ttc')]

    @classmethod
    def get_static_images(cls) -> list["StaticResource"]:
        return []

    @classmethod
    def _core_render(
            cls,
            text: Optional[str],
            static_images: Sequence["Image.Image"],
            external_image: Optional["Image.Image"],
            *,
            fonts: Sequence["StaticResource"],
            output_width: int,
            output_format: str,
    ) -> "Image.Image":
        if external_image is None:
            raise ValueError('external_image can not be None')
        if external_image.format != 'RGB':
            external_image = external_image.convert('RGB')

        text = ' ' if text is None else text
        font_size = external_image.width // 10
        font = ImageFont.truetype(fonts[0].resolve_path, font_size)
        text_w, text_h = ImageUtils.get_text_size(text, font=font)
        # 自适应处理文字大小
        while text_w >= int(external_image.width * 8 / 9):
            font_size -= 1
            font = ImageFont.truetype(fonts[0].resolve_path, font_size)
            text_w, text_h = ImageUtils.get_text_size(text, font=font)

        # 处理图片
        background = Image.new(
            mode='RGB',
            size=(external_image.width, int(external_image.height + external_image.width * 0.06 + text_h)),
            color=(255, 255, 255)
        )

        # 处理粘贴位置 顶头
        background.paste(external_image, (0, 0))

        # 计算居中文字位置
        ImageDraw.Draw(background).multiline_text(
            xy=(background.width // 2, int(external_image.height + external_image.width * 0.015)),
            text=text, align='center', anchor='ma', font=font, fill=(0, 0, 0)
        )

        return background


class BlackBackgroundRender(BaseStickerRender):
    """黑边加底字表情包模板"""

    @classmethod
    def need_text(cls) -> bool:
        return True

    @classmethod
    def need_external_image(cls) -> bool:
        return True

    @classmethod
    def get_output_width(cls) -> int:
        return 512

    @classmethod
    def get_output_format(cls) -> Literal['JPEG', 'PNG', 'GIF']:
        return 'JPEG'

    @classmethod
    def get_default_fonts(cls) -> list["StaticResource"]:
        return [FONT_RESOURCE('msyhbd.ttc')]

    @classmethod
    def get_static_images(cls) -> list["StaticResource"]:
        return []

    @classmethod
    def _core_render(
            cls,
            text: Optional[str],
            static_images: Sequence["Image.Image"],
            external_image: Optional["Image.Image"],
            *,
            fonts: Sequence["StaticResource"],
            output_width: int,
            output_format: str,
    ) -> "Image.Image":
        if external_image is None:
            raise ValueError('external_image can not be None')
        if external_image.format != 'RGB':
            external_image = external_image.convert('RGB')

        text = ' ' if text is None else text
        font_size = external_image.width // 8
        font = ImageFont.truetype(fonts[0].resolve_path, font_size)
        text_w, text_h = ImageUtils.get_text_size(text, font=font)
        # 自适应处理文字大小
        while text_w >= int(external_image.width * 1.1):
            font_size -= 1
            font = ImageFont.truetype(fonts[0].resolve_path, font_size)
            text_w, text_h = ImageUtils.get_text_size(text, font=font)

        # 处理图片
        background = Image.new(
            mode='RGB',
            color=(0, 0, 0),
            size=(int(external_image.width * 1.3), int(external_image.height + external_image.width * 0.3 + text_h))
        )
        background.paste(external_image, (int(external_image.width * 0.15), int(external_image.width * 0.15)))

        # 计算居中文字位置
        ImageDraw.Draw(background).multiline_text(
            xy=(background.width // 2, int(external_image.height + external_image.width * 0.2)),
            text=text, align='center', anchor='ma', font=font, fill=(255, 255, 255)
        )

        return background


class DeColorizeRender(BaseStickerRender):
    """去色表情包模板"""

    @classmethod
    def need_text(cls) -> bool:
        return True

    @classmethod
    def need_external_image(cls) -> bool:
        return True

    @classmethod
    def get_output_width(cls) -> int:
        return 512

    @classmethod
    def get_output_format(cls) -> Literal['JPEG', 'PNG', 'GIF']:
        return 'JPEG'

    @classmethod
    def get_default_fonts(cls) -> list["StaticResource"]:
        return []

    @classmethod
    def get_static_images(cls) -> list["StaticResource"]:
        return []

    @classmethod
    def _core_render(
            cls,
            text: Optional[str],
            static_images: Sequence["Image.Image"],
            external_image: Optional["Image.Image"],
            *,
            fonts: Sequence["StaticResource"],
            output_width: int,
            output_format: str,
    ) -> "Image.Image":
        if external_image is None:
            raise ValueError('external_image can not be None')
        if external_image.format != 'RGB':
            external_image = external_image.convert('RGB')

        enhancer = ImageEnhance.Color(external_image)
        made_image = enhancer.enhance(0)

        return made_image


class GunjoRender(BaseStickerRender):
    """群青表情包模板"""

    @classmethod
    def need_text(cls) -> bool:
        return False

    @classmethod
    def need_external_image(cls) -> bool:
        return True

    @classmethod
    def get_output_width(cls) -> int:
        return 512

    @classmethod
    def get_output_format(cls) -> Literal['JPEG', 'PNG', 'GIF']:
        return 'JPEG'

    @classmethod
    def get_default_fonts(cls) -> list["StaticResource"]:
        return [FONT_RESOURCE('SourceHanSansSC-Bold.otf')]

    @classmethod
    def get_static_images(cls) -> list["StaticResource"]:
        return []

    @classmethod
    def _core_render(
            cls,
            text: Optional[str],
            static_images: Sequence["Image.Image"],
            external_image: Optional["Image.Image"],
            *,
            fonts: Sequence["StaticResource"],
            output_width: int,
            output_format: str,
    ) -> "Image.Image":
        if external_image is None:
            raise ValueError('external_image can not be None')
        if external_image.format != 'RGBA':
            external_image = external_image.convert('RGBA')

        # 图片去色
        made_image = ImageEnhance.Color(external_image).enhance(0)

        # 图片转化为透明度蒙版到底色背景上
        mask = made_image.convert('L')
        background_color = (28, 48, 180)
        background = Image.new(mode='RGBA', size=made_image.size, color=background_color)
        background.paste(im=made_image, mask=mask)

        # 写字
        upper_font_size = int(made_image.width / 6)
        upper_font = ImageFont.truetype(fonts[0].resolve_path, upper_font_size)
        upper_text_coordinate = (int(made_image.width * 12 / 13), int(made_image.height / 11))

        _, upper_text_height = ImageUtils.get_text_size('群\n青', upper_font, stroke_width=upper_font_size // 20)
        ImageDraw.Draw(background).multiline_text(
            xy=upper_text_coordinate, text='群\n青', anchor='ra', align='center', font=upper_font,
            fill=(255, 255, 255), stroke_width=upper_font_size // 20, stroke_fill=background_color
        )

        lower_font_size = int(made_image.width / 12)
        lower_font = ImageFont.truetype(fonts[0].resolve_path, lower_font_size)
        lower_text_coordinate = (int(made_image.width * 12 / 13), upper_text_coordinate[1] + upper_text_height * 1.1)
        ImageDraw.Draw(background).text(
            xy=lower_text_coordinate, text='YOASOBI', anchor='ra', align='center', font=lower_font,
            fill=(255, 255, 255), stroke_width=lower_font_size // 10, stroke_fill=background_color
        )

        return background.convert('RGB')


class MarriageRender(BaseStickerRender):
    """结婚登记表情包模板"""

    @classmethod
    def need_text(cls) -> bool:
        return False

    @classmethod
    def need_external_image(cls) -> bool:
        return True

    @classmethod
    def get_output_width(cls) -> int:
        return 512

    @classmethod
    def get_output_format(cls) -> Literal['JPEG', 'PNG', 'GIF']:
        return 'PNG'

    @classmethod
    def get_default_fonts(cls) -> list["StaticResource"]:
        return []

    @classmethod
    def get_static_images(cls) -> list["StaticResource"]:
        return [STATIC_RESOURCE('marriage', 'default_bg.png')]

    @classmethod
    def _core_render(
            cls,
            text: Optional[str],
            static_images: Sequence["Image.Image"],
            external_image: Optional["Image.Image"],
            *,
            fonts: Sequence["StaticResource"],
            output_width: int,
            output_format: str,
    ) -> "Image.Image":
        if external_image is None:
            raise ValueError('external_image can not be None')
        if external_image.format != 'RGBA':
            external_image = external_image.convert('RGBA')

        image = cls._resize_to_width(image=external_image, width=output_width)
        upper_image = cls._resize_to_width(image=static_images[0], width=output_width)

        background = Image.new(mode='RGBA', size=image.size, color=(255, 255, 255, 255))
        background.paste(im=image, box=(0, 0), mask=image)
        background.paste(im=upper_image, box=(0, 0), mask=upper_image)

        return background


class GrassJaRender(BaseStickerRender):
    """生草日语表情包模板"""

    @classmethod
    def need_text(cls) -> bool:
        return True

    @classmethod
    def need_external_image(cls) -> bool:
        return True

    @classmethod
    def get_output_width(cls) -> int:
        return 512

    @classmethod
    def get_output_format(cls) -> Literal['JPEG', 'PNG', 'GIF']:
        return 'JPEG'

    @classmethod
    def get_default_fonts(cls) -> list["StaticResource"]:
        return [FONT_RESOURCE('fzzxhk.ttf')]

    @classmethod
    def get_static_images(cls) -> list["StaticResource"]:
        return []

    @classmethod
    def _core_render(
            cls,
            text: Optional[str],
            static_images: Sequence["Image.Image"],
            external_image: Optional["Image.Image"],
            *,
            fonts: Sequence["StaticResource"],
            output_width: int,
            output_format: str,
    ) -> "Image.Image":
        if external_image is None:
            raise ValueError('external_image can not be None')
        if external_image.format != 'RGB':
            external_image = external_image.convert('RGB')

        enhancer = ImageEnhance.Color(external_image)
        image = enhancer.enhance(0)

        # 分割文本
        text = ' ' if text is None else text
        font_zh = ImageFont.truetype(fonts[0].resolve_path, int(image.width / 13))
        font_jp = ImageFont.truetype(fonts[0].resolve_path, int(image.width / 24))

        text_zh, text_jp = text.split(maxsplit=1)
        text_zh = ImageUtils.split_multiline_text(text=text_zh, width=int(image.width * 0.9), font=font_zh)
        text_jp = ImageUtils.split_multiline_text(text=text_jp, width=int(image.width * 0.9), font=font_jp)

        _, text_zh_h = ImageUtils.get_text_size(text_zh, font=font_zh)
        _, text_jp_h = ImageUtils.get_text_size(text_jp, font=font_jp)

        # 处理图片
        background = Image.new(
            mode='RGB',
            color=(0, 0, 0),
            size=(image.width, int(image.height + image.width * 0.08 + text_zh_h + text_jp_h))
        )

        # 处理粘贴位置
        background.paste(image, (0, 0))

        # 粘贴文字
        ImageDraw.Draw(background).multiline_text(
            xy=(background.width // 2, int(image.height + image.width * 0.025)),
            text=text_zh, align='center', anchor='ma', font=font_zh, fill=(255, 255, 255)
        )
        ImageDraw.Draw(background).multiline_text(
            xy=(background.width // 2, int(image.height + image.width * 0.05 + text_zh_h)),
            text=text_jp, align='center', anchor='ma', font=font_jp, fill=(255, 255, 255)
        )

        return background

    async def _translate_preprocessor(self) -> None:
        text_origin = self.get_text()
        text_origin = ' ' if text_origin is None else text_origin.replace('\n', ' ')

        text_trans_result = await TencentTMT().text_translate(source_text=text_origin, target='ja')
        if text_trans_result.error:
            text_ja = '翻訳に失敗しました！'
        else:
            text_ja = text_trans_result.Response.TargetText  # type: ignore
        text_ja = text_ja.replace('\n', ' ')
        self.set_text(f'{text_origin.strip()}\n{text_ja.strip()}')

    async def make(self) -> "TemporaryResource":
        await self._translate_preprocessor()
        return await self._async_make()


class PetPetRender(BaseStickerRender):
    """petpet 表情包模板"""

    @classmethod
    def need_text(cls) -> bool:
        return False

    @classmethod
    def need_external_image(cls) -> bool:
        return True

    @classmethod
    def get_output_width(cls) -> int:
        return 512

    @classmethod
    def get_output_format(cls) -> Literal['JPEG', 'PNG', 'GIF']:
        return 'GIF'

    @classmethod
    def get_default_fonts(cls) -> list["StaticResource"]:
        return []

    @classmethod
    def get_static_images(cls) -> list["StaticResource"]:
        return [STATIC_RESOURCE('petpet', f'template_p{i}.png') for i in range(5)]

    @classmethod
    def _core_render(
            cls,
            text: Optional[str],
            static_images: Sequence["Image.Image"],
            external_image: Optional["Image.Image"],
            *,
            fonts: Sequence["StaticResource"],
            output_width: int,
            output_format: str,
    ) -> "Image.Image":
        raise NotImplementedError

    @classmethod
    def _main_render(
            cls,
            text: Optional[str],
            static_images: Sequence["Image.Image"],
            external_image: Optional["Image.Image"],
            *,
            fonts: Sequence["StaticResource"],
            output_width: int,
            output_format: str,
    ) -> list["Image.Image"]:
        resize_paste_loc: list[tuple[tuple[int, int], tuple[int, int]]] = [
            ((95, 95), (12, 15)),
            ((97, 80), (11, 30)),
            ((99, 70), (10, 40)),
            ((97, 75), (11, 35)),
            ((96, 90), (11, 20))
        ]

        if external_image is None:
            raise ValueError('external_image can not be None')
        if external_image.format != 'RGBA':
            external_image = external_image.convert('RGBA')

        frames_list = []
        for index, frame in enumerate(static_images):
            background = Image.new(mode='RGBA', size=(112, 112), color=(255, 255, 255))
            background.paste(external_image.resize(resize_paste_loc[index][0]), resize_paste_loc[index][1])
            background.paste(frame, (0, 0), mask=frame)
            frames_list.append(background)

        return frames_list


class WorshipRender(BaseStickerRender):
    """膜拜表情包模板"""

    @classmethod
    def need_text(cls) -> bool:
        return False

    @classmethod
    def need_external_image(cls) -> bool:
        return True

    @classmethod
    def get_output_width(cls) -> int:
        return 512

    @classmethod
    def get_output_format(cls) -> Literal['JPEG', 'PNG', 'GIF']:
        return 'GIF'

    @classmethod
    def get_default_fonts(cls) -> list["StaticResource"]:
        return []

    @classmethod
    def get_static_images(cls) -> list["StaticResource"]:
        return [STATIC_RESOURCE('worship', f'template_p{i}.png') for i in range(10)]

    @classmethod
    def _core_render(
            cls,
            text: Optional[str],
            static_images: Sequence["Image.Image"],
            external_image: Optional["Image.Image"],
            *,
            fonts: Sequence["StaticResource"],
            output_width: int,
            output_format: str,
    ) -> "Image.Image":
        raise NotImplementedError

    @staticmethod
    def _get_perspective_data(
            target_point: tuple[tuple[float, float], tuple[float, float], tuple[float, float], tuple[float, float]],
            source_point: tuple[tuple[float, float], tuple[float, float], tuple[float, float], tuple[float, float]]
    ) -> Any:
        """Method to determine perspective transformation coefficients

        https://stackoverflow.com/questions/14177744/how-does-perspective-transformation-work-in-pil/14178717#14178717
        """
        matrix = []
        for p1, p2 in zip(target_point, source_point):
            matrix.append([p1[0], p1[1], 1, 0, 0, 0, -p2[0] * p1[0], -p2[0] * p1[1]])
            matrix.append([0, 0, 0, p1[0], p1[1], 1, -p2[1] * p1[0], -p2[1] * p1[1]])

        target_matrix = numpy.matrix(matrix, dtype=numpy.float64)
        source_array = numpy.array(source_point).reshape(8)

        res = numpy.dot(numpy.linalg.inv(target_matrix.T * target_matrix) * target_matrix.T, source_array)
        return numpy.array(res).reshape(8)

    @classmethod
    def _main_render(
            cls,
            text: Optional[str],
            static_images: Sequence["Image.Image"],
            external_image: Optional["Image.Image"],
            *,
            fonts: Sequence["StaticResource"],
            output_width: int,
            output_format: str,
    ) -> list["Image.Image"]:
        if external_image is None:
            raise ValueError('external_image can not be None')
        if external_image.format != 'RGBA':
            external_image = external_image.convert('RGBA')

        width, height = external_image.size
        perspective_data = cls._get_perspective_data(
            target_point=((0, -30), (135, 17), (135, 145), (0, 140)),
            source_point=((0, 0), (width, 0), (width, height), (0, height))
        )
        p_image = external_image.transform(
            size=external_image.size,
            method=Image.Transform.PERSPECTIVE,
            data=perspective_data,
            fill=Image.Resampling.BICUBIC
        )

        frames_list = []
        for frame in static_images:
            background = Image.new(mode='RGBA', size=(300, 169), color=(255, 255, 255, 255))
            background.paste(im=p_image, box=(0, 0), mask=p_image)
            background.paste(im=frame, box=(0, 0), mask=frame)
            frames_list.append(background)

        return frames_list


class TwistRender(BaseStickerRender):
    """搓表情包模板"""

    @classmethod
    def need_text(cls) -> bool:
        return False

    @classmethod
    def need_external_image(cls) -> bool:
        return True

    @classmethod
    def get_output_width(cls) -> int:
        return 128

    @classmethod
    def get_output_format(cls) -> Literal['JPEG', 'PNG', 'GIF']:
        return 'GIF'

    @classmethod
    def get_default_fonts(cls) -> list["StaticResource"]:
        return []

    @classmethod
    def get_static_images(cls) -> list["StaticResource"]:
        return [STATIC_RESOURCE('twist', f'template_p{i}.png') for i in range(10)]

    @classmethod
    def _core_render(
            cls,
            text: Optional[str],
            static_images: Sequence["Image.Image"],
            external_image: Optional["Image.Image"],
            *,
            fonts: Sequence["StaticResource"],
            output_width: int,
            output_format: str,
    ) -> "Image.Image":
        raise NotImplementedError

    @classmethod
    def _main_render(
            cls,
            text: Optional[str],
            static_images: Sequence["Image.Image"],
            external_image: Optional["Image.Image"],
            *,
            fonts: Sequence["StaticResource"],
            output_width: int,
            output_format: str,
    ) -> list["Image.Image"]:
        if external_image is None:
            raise ValueError('external_image can not be None')
        if external_image.format != 'RGBA':
            external_image = external_image.convert('RGBA')

        image = ImageUtils(image=external_image).resize_with_filling(size=(128, 128)).image

        angle = 0
        paste_coordinate: list[tuple[int, int]] = [
            (35, 101), (37, 101), (37, 101), (37, 101), (37, 99), (35, 101), (37, 101), (37, 101), (37, 101), (37, 99)
        ]

        frames_list = []
        for index, frame in enumerate(static_images):
            background = Image.new(mode='RGBA', size=(256, 256), color=(255, 255, 255, 255))
            frame_image = image.rotate(
                angle=angle, center=(64, 64), expand=False, resample=Image.Resampling.BICUBIC, fillcolor=(255, 255, 255)
            )
            background.paste(im=frame_image, box=paste_coordinate[index], mask=frame_image)
            background.paste(im=frame, box=(0, 0), mask=frame)
            frames_list.append(background)
            angle += 36

        return frames_list


class WangjingzeRender(BaseStickerRender):
    """王境泽表情包模板"""

    @classmethod
    def need_text(cls) -> bool:
        return True

    @classmethod
    def need_external_image(cls) -> bool:
        return False

    @classmethod
    def get_output_width(cls) -> int:
        return 512

    @classmethod
    def get_output_format(cls) -> Literal['JPEG', 'PNG', 'GIF']:
        return 'GIF'

    @classmethod
    def get_default_fonts(cls) -> list["StaticResource"]:
        return [FONT_RESOURCE('SourceHanSansSC-Regular.otf')]

    @classmethod
    def get_static_images(cls) -> list["StaticResource"]:
        return [STATIC_RESOURCE('wangjingze', f'template_p{i}.jpg') for i in range(46)]

    @classmethod
    def _core_render(
            cls,
            text: Optional[str],
            static_images: Sequence["Image.Image"],
            external_image: Optional["Image.Image"],
            *,
            fonts: Sequence["StaticResource"],
            output_width: int,
            output_format: str,
    ) -> "Image.Image":
        raise NotImplementedError

    @classmethod
    def _main_render(
            cls,
            text: Optional[str],
            static_images: Sequence["Image.Image"],
            external_image: Optional["Image.Image"],
            *,
            fonts: Sequence["StaticResource"],
            output_width: int,
            output_format: str,
    ) -> list["Image.Image"]:
        text = '我王境泽就是饿死 死外边,从这跳下去 也不会吃你们一点东西 真香' if text is None else text

        # 分割文本
        text_list = text.split(maxsplit=3)
        if (text_len := len(text_list)) < 4:
            text_list.extend(['' for _ in range(4 - text_len)])

        font = ImageFont.truetype(fonts[0].resolve_path, 22)

        frames_list = []
        for index, frame in enumerate(static_images):
            if 0 <= index <= 8:
                ImageDraw.Draw(frame).text(
                    xy=(219, 223), text=text_list[0], font=font, anchor='ma', align='center',
                    stroke_width=2, stroke_fill=(0, 0, 0)
                )
            elif 12 <= index <= 23:
                ImageDraw.Draw(frame).text(
                    xy=(219, 223), text=text_list[1], font=font, anchor='ma', align='center',
                    stroke_width=2, stroke_fill=(0, 0, 0)
                )
            elif 25 <= index <= 34:
                ImageDraw.Draw(frame).text(
                    xy=(219, 223), text=text_list[2], font=font, anchor='ma', align='center',
                    stroke_width=2, stroke_fill=(0, 0, 0)
                )
            elif 36 <= index <= 42:
                ImageDraw.Draw(frame).text(
                    xy=(219, 223), text=text_list[3], font=font, anchor='ma', align='center',
                    stroke_width=2, stroke_fill=(0, 0, 0)
                )
            frames_list.append(frame)

        return frames_list


_ALL_Render: dict[str, type[BaseStickerRender]] = {
    '默认': DefaultRender,
    '白底': WhiteBackgroundRender,
    '黑底': BlackBackgroundRender,
    '黑白': DeColorizeRender,
    '小天使': LittleAngelRender,
    '生草日语': GrassJaRender,
    '群青': GunjoRender,
    '结婚登记': MarriageRender,
    '有内鬼': TraitorRender,
    '记仇': JichouRender,
    '鲁迅说': LuxunSayRender,
    '鲁迅写': LuxunWriteRender,
    '奖状': JiangzhuangRender,
    '喜报横版': XibaoHorizontalRender,
    '喜报竖版': XibaoVerticalRender,
    'ph': PhLogoRender,
    'petpet': PetPetRender,
    '膜拜': WorshipRender,
    '搓': TwistRender,
    '王境泽': WangjingzeRender
}


def get_render(render_name: str) -> type[BaseStickerRender]:
    """获取表情包 Render"""
    return _ALL_Render[render_name]


def get_all_render_name() -> list[str]:
    """获取所有表情包 Render 名称"""
    return [str(x) for x in _ALL_Render.keys()]


async def download_source_image(url: str) -> "TemporaryResource":
    """下载图片到本地, 保持原始文件名, 直接覆盖同名文件"""
    file_name = OmegaRequests.hash_url_file_name('sticker_source_tmp', url=url)
    return await OmegaRequests().download(url=url, file=TMP_PATH(file_name))


__all__ = [
    'get_render',
    'get_all_render_name',
    'download_source_image',
]
