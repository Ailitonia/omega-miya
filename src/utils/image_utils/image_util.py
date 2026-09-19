"""
@Author         : Ailitonia
@Date           : 2022/04/17 0:03
@FileName       : image_util.py
@Project        : nonebot2_miya
@Description    : Image Tools
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import base64
import random
from io import BytesIO
from typing import TYPE_CHECKING, Literal, Self

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from fontTools.ttLib import TTFont
from nonebot.log import logger
from nonebot.utils import run_sync

from .config import image_utils_config

if TYPE_CHECKING:
    from src.resource import BaseResource, TemporaryResource


class ImageLoader:
    """图片加载工具"""

    @staticmethod
    def _check_image_pixels(image: 'Image.Image') -> None:
        """校验图片像素尺寸, 防止解压炸弹

        Image.open 为惰性加载, 尺寸信息可直接从文件头读取, 在 load() 前校验可避免解码超大图片
        """
        max_pixels = image_utils_config.max_image_pixels
        if image.width * image.height > max_pixels:
            raise ValueError(f'image size {image.width}x{image.height} exceeds max pixels limit {max_pixels}')

    @classmethod
    def init_from_bytes(cls, image: bytes) -> 'Image.Image':
        """从 Bytes 中初始化, 像素尺寸超出限制时抛出 ValueError"""
        with BytesIO(image) as bf:
            _image = Image.open(bf)
            cls._check_image_pixels(_image)
            _image.load()
        return _image

    @classmethod
    def init_from_file(cls, file: 'BaseResource') -> 'Image.Image':
        """从文件初始化, 像素尺寸超出限制时抛出 ValueError"""
        with file.open('rb') as f:
            image = Image.open(f)
            cls._check_image_pixels(image)
            image.load()
        return image

    @staticmethod
    def init_from_text(
            text: str,
            *,
            image_width: int = 512,
            font_name: str | None = None,
            alpha: bool = False,
    ) -> 'Image.Image':
        """从文本初始化, 文本转图片并自动裁切

        :param text: 待转换文本
        :param image_width: 限制图片宽度, 像素
        :param font_name: 字体名称, 本地资源中字体文件名
        :param alpha: 输出带 alpha 通道的图片
        """
        if font_name is None:
            font_file = image_utils_config.default_font
        else:
            font_file = image_utils_config.get_custom_name_font(font_name)

        # 处理文字层 主体部分
        font_size = image_width // 25
        font = ImageFont.truetype(font_file.resolve_path, font_size)
        # 按长度切分文本
        text = ImageTextProcessor.split_multiline_text(text=text, width=int(image_width * 0.75), font=font)
        _, text_height = ImageTextProcessor.get_text_size(text, font=font)
        # 初始化背景图层
        image_height = int(text_height + image_width * 0.25)
        if alpha:
            background = Image.new(mode='RGBA', size=(image_width, image_height), color=(255, 255, 255, 0))
        else:
            background = Image.new(mode='RGB', size=(image_width, image_height), color=(255, 255, 255))
        # 绘制文字
        ImageDraw.Draw(background).multiline_text(
            xy=(int(image_width * 0.115), int(image_width * 0.115)),
            text=text,
            font=font,
            fill=(0, 0, 0)
        )
        return background

    @classmethod
    @run_sync
    def async_init_from_bytes(cls, image: bytes) -> 'Image.Image':
        return cls.init_from_bytes(image=image)

    @classmethod
    @run_sync
    def async_init_from_file(cls, file: 'BaseResource') -> 'Image.Image':
        return cls.init_from_file(file=file)

    @classmethod
    @run_sync
    def async_init_from_text(
            cls,
            text: str,
            *,
            image_width: int = 512,
            font_name: str | None = None,
            alpha: bool = False,
    ) -> 'Image.Image':
        """异步从文本初始化, 文本转图片并自动裁切"""
        return cls.init_from_text(text, image_width=image_width, font_name=font_name, alpha=alpha)


class ImageTextProcessor:
    """图片文字处理工具

    python-pillow/Pillow Issue #4808 Backup font for missing characters when drawing text
    https://github.com/python-pillow/Pillow/issues/4808#issuecomment-2067558946
    Provided a pure Python implementation solution: https://github.com/TrueMyst/PillowFontFallback
    """

    type FontMap = dict[str, TTFont]

    @staticmethod
    def load_fonts(*font_names: str) -> FontMap:
        """从本地字体资源加载指定名称的字体文件, 返回以文件路径为键的字体对象字典"""
        fonts = {}
        for name in font_names:
            font_path = image_utils_config.get_custom_name_font(name).resolve_path
            font = TTFont(font_path, fontNumber=0)
            fonts[font_path] = font
        return fonts

    @staticmethod
    def has_glyph(font: TTFont, glyph: str) -> bool:
        """检查指定字体是否包含给定字符的字形"""
        for table in font['cmap'].tables:  # type: ignore
            if table.cmap.get(ord(glyph)):
                return True
        return False

    @classmethod
    def merge_chunks(cls, text: str, fonts: FontMap) -> list[list[str]]:
        """将连续的使用同一字体的字符合并为一个簇, 优化绘制时的字体查找

        字符在所有字体中均无字形时, 回退使用第一个字体绘制并记录警告日志
        """
        if not fonts:
            raise ValueError('merge_chunks requires at least one font')

        chunks: list[list[str]] = []
        fallback_font_path = next(iter(fonts))

        for char in text:
            for font_path, font in fonts.items():
                if cls.has_glyph(font, char):
                    chunks.append([char, font_path])
                    break
            else:
                logger.warning(f'ImageTextProcessor missing glyph in all fonts, drawing with fallback font: {char!r}')
                chunks.append([char, fallback_font_path])

        cluster = chunks[:1]

        for char, font_path in chunks[1:]:
            if cluster[-1][1] == font_path:
                cluster[-1][0] += char
            else:
                cluster.append([char, font_path])
        return cluster

    @classmethod
    def _draw_text_v3(
            cls,
            draw: ImageDraw.ImageDraw,
            xy: tuple[int | float, int | float],
            text: str,
            color: tuple[int, int, int],
            fonts: FontMap,
            size: int,
            anchor: str | None = None,
            align: Literal['left', 'center', 'right'] = 'left',
    ) -> tuple[float, float]:
        """在图像指定坐标绘制文本, 使用指定的字号, 颜色和字体集

        相比旧版对 anchor 有更好的支持. (但并不完美)
        Provided by @bradenhilton in: https://github.com/TrueMyst/PillowFontFallback/issues/1

        :return: 文本框尺寸: (float, float)
        """

        sentence = cls.merge_chunks(text, fonts)

        chunk_data = []
        for text_chunk, font_path in sentence:
            font = ImageFont.truetype(font_path, size)
            chunk_data.append({
                'text': text_chunk,
                'font': font,
                'bbox': font.getbbox(text_chunk, anchor=anchor)
            })

        if not chunk_data:
            return 0.0, 0.0

        x_offset = chunk_data[0]['bbox'][0]
        min_top = min(chunk['bbox'][1] for chunk in chunk_data)
        max_bottom = max(chunk['bbox'][3] for chunk in chunk_data)

        for chunk in chunk_data:
            draw.text(
                xy=(xy[0] + x_offset, xy[1]),
                text=chunk['text'],
                fill=color,
                font=chunk['font'],
                anchor=None,
                align=align,
                embedded_color=True,
            )
            x_offset += chunk['bbox'][2] - chunk['bbox'][0]

        return x_offset, max_bottom - min_top

    @classmethod
    def _draw_multiline_text_v3(
            cls,
            draw: 'ImageDraw.ImageDraw',
            xy: tuple[int | float, int | float],
            text: str,
            color: tuple[int, int, int],
            fonts: FontMap,
            size: int,
            spacing: int = 4,
            anchor: str | None = None,
            align: Literal['left', 'center', 'right'] = 'left',
    ) -> tuple[float, float]:
        """在图像上绘制多行文本, 处理换行符并调整行间距

        相比旧版对 anchor 有更好的支持. (但并不完美)
        Provided by @bradenhilton in: https://github.com/TrueMyst/PillowFontFallback/issues/1

        :return: 文本框尺寸: (float, float)
        """
        width = 0.0
        height = 0.0
        y_offset = 0.0
        lines = text.split('\n')

        for line in lines:
            if not line:
                continue

            mod_cord = (xy[0], xy[1] + y_offset)
            box = cls._draw_text_v3(
                draw,
                xy=mod_cord,
                text=line,
                color=color,
                fonts=fonts,
                size=size,
                anchor=anchor,
                align=align,
            )
            width = max(width, box[0])
            height = max(height, box[1] + y_offset)
            y_offset += box[1] + spacing

        return width, height

    @classmethod
    def draw_multiline_text(
            cls,
            draw: 'ImageDraw.ImageDraw',
            xy: tuple[int | float, int | float],
            text: str,
            size: int,
            *,
            fonts: FontMap | None = None,
            color: tuple[int, int, int] = (0, 0, 0),
            spacing: int = 4,
    ) -> tuple[float, float]:
        """在图像上绘制多行文本, 处理换行符并调整行间距

        为保证兼容性, 不允许使用 anchor 参数, align 参数仅允许为 'left'.

        :return: 文本框尺寸: (float, float)
        """
        if fonts is None:
            fonts = cls.load_fonts(
                image_utils_config.default_font.name,
                image_utils_config.emoji_font.name,
                image_utils_config.get_custom_name_font('msyh.ttc').name,
            )
        return cls._draw_multiline_text_v3(
            draw,
            xy=xy,
            text=text,
            size=size,
            spacing=spacing,
            color=color,
            anchor=None,
            align='left',
            fonts=fonts,
        )

    @staticmethod
    def get_text_size(
            text: str,
            font: ImageFont.FreeTypeFont,
            *,
            anchor: str | None = None,
            spacing: int = 4,
            stroke_width: int = 0,
            **kwargs,
    ) -> tuple[float, float]:
        """获取文本宽度和长度(根据图像框)"""
        left, top, right, bottom = ImageDraw.Draw(Image.new(mode='L', size=(0, 0), color=0)).textbbox(
            xy=(0, 0), text=text, font=font, anchor=anchor, spacing=spacing, stroke_width=stroke_width, **kwargs
        )
        return right - left, bottom - top

    @staticmethod
    def get_font_size(
            text: str,
            font: ImageFont.FreeTypeFont,
            *,
            mode='',
            stroke_width=0,
            anchor=None,
            **kwargs,
    ) -> tuple[float, float]:
        """获取文本宽度和长度(根据字体)"""
        left, top, right, bottom = font.getbbox(
            mode=mode, text=text, stroke_width=stroke_width, anchor=anchor, **kwargs
        )
        return right - left, bottom - top

    @classmethod
    def split_multiline_text(
            cls,
            text: str,
            width: int,
            *,
            font: ImageFont.FreeTypeFont | str | None = None,
            stroke_width: int = 0,
    ) -> str:
        """按字体绘制的文本长度切分换行文本

        逐字符增量测量文本宽度, 在行宽将超出限制处的前一个字符断行,
        单个字符本身超宽时单独成行, 保证切分结果中每一行均不超过宽度限制

        :param text: 待切分的文本
        :param width: 宽度限制, 像素
        :param font: 绘制使用的字体, 传入 str 为本地字体资源文件名
        :param stroke_width: 文字描边, 像素
        """
        if font is None:
            font = ImageFont.truetype(
                image_utils_config.default_font.resolve_path, image_utils_config.default_font_size
            )
        elif isinstance(font, str):
            font = ImageFont.truetype(
                image_utils_config.get_custom_name_font(font).resolve_path, image_utils_config.default_font_size
            )

        spl_list = []
        line = ''
        line_width = 0.0

        for char in text:
            char_width = font.getlength(char) + 2 * stroke_width
            if line and line_width + char_width > width:
                spl_list.append(line)
                line = char
                line_width = char_width
            else:
                line += char
                line_width += char_width

        spl_list.append(line)
        return '\n'.join(spl_list)


class ImageEffectProcessor:
    """图片处理工具集"""

    def __init__(self, image: Image.Image):
        self.image: Image.Image = image

    def convert(self, mode: str) -> Self:
        self.image = self.image.convert(mode=mode)
        return self

    def _auto_convert_mode_for_save(self, *, format_: str) -> None:
        """目标编码格式不支持当前色彩模式时, 自动转换色彩模式

        JPEG 等不带透明通道的格式无法编码 RGBA/P/LA 等模式, 直接编码会抛出 OSError
        """
        if format_.upper() in {'JPEG', 'JPG'} and self.image.mode not in {'L', 'RGB', 'CMYK'}:
            self.image = self.image.convert(mode='RGB')

    async def save(
            self,
            file: 'TemporaryResource | str',
            *,
            format_: str = 'JPEG',
    ) -> 'TemporaryResource':
        """输出指定格式图片到文件"""
        if isinstance(file, str):
            save_file = image_utils_config.default_output_folder(file)
        else:
            save_file = file

        async with save_file.async_open('wb') as af:
            await af.write(await self.async_get_bytes(format_=format_))
        return save_file

    @run_sync
    def async_get_base64(self, *, format_: str = 'JPEG', use_data_uri_scheme: bool = False) -> str:
        """获取 Image 内容, 以 Base64 输出"""
        return self.get_base64(format_=format_, use_data_uri_scheme=use_data_uri_scheme)

    @run_sync
    def async_get_bytes(self, *, format_: str = 'JPEG') -> bytes:
        """获取 Image 内容, 以 Bytes 输出"""
        return self.get_bytes(format_=format_)

    def get_base64(self, *, format_: str = 'JPEG', use_data_uri_scheme: bool = False) -> str:
        """获取 Image 内容, 以 Base64 输出"""
        if use_data_uri_scheme:
            prefix = f'data:image/{format_.lower()};base64,'
        else:
            prefix = 'base64://'
        return f'{prefix}{base64.b64encode(self.get_bytes(format_=format_)).decode()}'

    def get_bytes(self, *, format_: str = 'JPEG') -> bytes:
        """获取 Image 内容, 以 Bytes 输出, 目标编码格式不支持当前色彩模式时自动转换色彩模式"""
        self._auto_convert_mode_for_save(format_=format_)
        with BytesIO() as _bf:
            self.image.save(_bf, format=format_)
            content = _bf.getvalue()
        return content

    def mark(
            self,
            text: str,
            *,
            position: Literal['la', 'ra', 'lb', 'rb', 'c'] = 'rb',
            fill: tuple[int, int, int] = (128, 128, 128),
    ) -> Self:
        """在图片上添加标注文本"""
        if self.image.mode == 'L':
            self.convert(mode='RGB')

        width, height = self.image.size
        edge_w = width // 32 if width // 32 <= 10 else 10
        edge_h = height // 32 if height // 32 <= 10 else 10

        font_size = max(1, width // 32)
        font = ImageFont.truetype(image_utils_config.default_font.resolve_path, font_size)
        text_kwargs = {
            'text': text,
            'font': font,
            'fill': fill,
            'stroke_width': width // 256,
            'stroke_fill': (255, 255, 255)
        }

        match position:
            case 'c':
                ImageDraw.Draw(self.image).text(
                    xy=(width // 2, height // 2), align='center', anchor='mm', **text_kwargs
                )
            case 'la':
                ImageDraw.Draw(self.image).text(
                    xy=(0, 0), align='left', anchor='la', **text_kwargs
                )
            case 'ra':
                ImageDraw.Draw(self.image).text(
                    xy=(width - edge_w, 0), align='right', anchor='ra', **text_kwargs
                )
            case 'lb':
                ImageDraw.Draw(self.image).text(
                    xy=(0, height - edge_h), align='left', anchor='lb', **text_kwargs
                )
            case 'rb':
                ImageDraw.Draw(self.image).text(
                    xy=(width - edge_w, height - edge_h), align='right', anchor='rb', **text_kwargs
                )
            case _:
                raise ValueError(f'invalid mark position, expected la/ra/lb/rb/c but got {position!r}')

        return self

    def gaussian_blur(self, radius: int | None = None) -> Self:
        """高斯模糊"""
        if radius is None:
            blur_radius = self.image.width // 16
        else:
            blur_radius = radius
        self.image = self.image.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        return self

    def gaussian_noise(
            self,
            *,
            sigma: float = 8,
            enable_random: bool = True,
            mask_factor: float = 0.25,
    ) -> Self:
        """为图片添加肉眼不可见的底噪

        :param sigma: 噪声sigma, 默认值8
        :param enable_random: 为噪声sigma添加随机扰动, 默认值True
        :param mask_factor: 噪声蒙版透明度修正, 默认值0.25
        """
        # 处理图片
        width, height = self.image.size
        # 为sigma添加随机扰动
        if enable_random:
            _sigma = sigma * (1 + 0.1 * random.random())
        else:
            _sigma = sigma
        # 生成高斯噪声底图
        noise_image = Image.effect_noise(size=(width, height), sigma=_sigma)
        # 生成底噪蒙版
        noise_mask = ImageEnhance.Brightness(noise_image.convert('L')).enhance(factor=mask_factor)
        # 叠加噪声图层
        self.image.paste(noise_image, (0, 0), mask=noise_mask)

        return self

    def add_edge(
            self,
            edge_scale: float = 1 / 32,
            edge_color: tuple[int, int, int] | tuple[int, int, int, int] = (255, 255, 255, 0),
    ) -> Self:
        """在保持原图大小的条件下, 使用透明图层为原图添加边框"""
        if self.image.mode != 'RGBA':
            self.convert(mode='RGBA')

        # 计算调整比例
        width, height = self.image.size

        edge_scale = 0 if edge_scale < 0 else 1 if edge_scale > 1 else edge_scale
        scaled_size = max(1, int(width * (1 - edge_scale))), max(1, int(height * (1 - edge_scale)))

        scale = min(scaled_size[0] / width, scaled_size[1] / height)
        image = self.image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)

        box = (int(width * (1 - scale) / 2), int(height * (1 - scale) / 2))
        background = Image.new(mode='RGBA', size=(width, height), color=edge_color)
        background.paste(image, box=box, mask=image)

        self.image = background
        return self

    def resize_with_filling(
            self,
            size: tuple[int, int],
            background_color: tuple[int, int, int] | tuple[int, int, int, int] = (255, 255, 255, 0),
    ) -> Self:
        """在不损失原图长宽比的条件下, 使用透明图层将原图转换成指定大小"""
        if self.image.mode != 'RGBA':
            self.convert(mode='RGBA')

        # 计算调整比例
        width, height = self.image.size
        rs_width, rs_height = size
        scale = min(rs_width / width, rs_height / height)

        image = self.image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)
        box = (int(abs(width * scale - rs_width) / 2), int(abs(height * scale - rs_height) / 2))
        background = Image.new(mode='RGBA', size=size, color=background_color)
        background.paste(image, box=box, mask=image)

        self.image = background
        return self

    def resize_fill_canvas(
            self,
            size: tuple[int, int],
            background_color: tuple[int, int, int] | tuple[int, int, int, int] = (255, 255, 255, 0),
    ) -> Self:
        """在不损失原图长宽比的条件下, 按比例放大裁切并平铺填充指定大小画布"""
        if self.image.mode != 'RGBA':
            self.convert(mode='RGBA')

        # 计算调整比例
        width, height = self.image.size
        rs_width, rs_height = size
        scale = max(rs_width / width, rs_height / height)
        image = self.image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)

        box = (- int(abs(width * scale - rs_width) / 2), - int(abs(height * scale - rs_height) / 2))
        background = Image.new(mode='RGBA', size=size, color=background_color)
        background.paste(image, box=box, mask=image)

        self.image = background
        return self


__all__ = [
    'ImageEffectProcessor',
    'ImageLoader',
    'ImageTextProcessor',
]
