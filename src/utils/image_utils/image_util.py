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
from copy import deepcopy
from io import BytesIO
from typing import Literal, Optional, Self

from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont
from nonebot.utils import run_sync

from src.resource import BaseResource, TemporaryResource
from src.service import OmegaRequests
from .config import image_utils_config


class ImageUtils(object):
    def __init__(self, image: Image.Image):
        self._image: Image.Image = image

    @classmethod
    def init_from_bytes(cls, image: bytes) -> Self:
        """从 Bytes 中初始化"""
        with BytesIO(image) as bf:
            _image: Image.Image = Image.open(bf)
            _image.load()
            new_obj = cls(image=_image)
        return new_obj

    @classmethod
    def init_from_file(cls, file: BaseResource) -> Self:
        """从文件初始化"""
        with file.open('rb') as f:
            image: Image.Image = Image.open(f)
            image.load()
            new_obj = cls(image=image)
        return new_obj

    @classmethod
    async def async_init_from_url(cls, image_url: str) -> Self:
        """从 URL 初始化"""
        requests = OmegaRequests(timeout=30)
        response = await requests.get(url=image_url)
        return await cls.async_init_from_bytes(image=requests.parse_content_as_bytes(response=response))

    @classmethod
    @run_sync
    def async_init_from_bytes(cls, image: bytes) -> Self:
        return cls.init_from_bytes(image=image)

    @classmethod
    @run_sync
    def async_init_from_file(cls, file: BaseResource) -> Self:
        return cls.init_from_file(file=file)

    @classmethod
    @run_sync
    def async_init_from_text(
            cls,
            text: str,
            *,
            image_width: int = 512,
            font_name: str | None = None,
            alpha: bool = False
    ) -> Self:
        """异步从文本初始化, 文本转图片并自动裁切"""
        return cls.init_from_text(text, image_width=image_width, font_name=font_name, alpha=alpha)

    @classmethod
    def init_from_text(
            cls,
            text: str,
            *,
            image_width: int = 512,
            font_name: str | None = None,
            alpha: bool = False
    ) -> Self:
        """从文本初始化, 文本转图片并自动裁切

        :param text: 待转换文本
        :param image_width: 限制图片宽度, 像素
        :param font_name: 字体名称, 本地资源中字体文件名
        :param alpha: 输出带 alpha 通道的图片
        """
        if font_name is None:
            font_file = image_utils_config.default_font_file
        else:
            font_file = image_utils_config.default_font_folder(font_name)

        # 处理文字层 主体部分
        font_size = image_width // 25
        font = ImageFont.truetype(font_file.resolve_path, font_size)
        # 按长度切分文本
        text = cls.split_multiline_text(text=text, width=int(image_width * 0.75), font=font)
        _, text_height = cls.get_text_size(text, font=font)
        # 初始化背景图层
        image_height = text_height + int(image_width * 0.25)
        if alpha:
            background = Image.new(mode="RGBA", size=(image_width, image_height), color=(255, 255, 255, 0))
        else:
            background = Image.new(mode="RGB", size=(image_width, image_height), color=(255, 255, 255))
        # 绘制文字
        ImageDraw.Draw(background).multiline_text(
            xy=(int(image_width * 0.115), int(image_width * 0.115)),
            text=text,
            font=font,
            fill=(0, 0, 0)
        )
        new_obj = cls(image=background)
        return new_obj

    @staticmethod
    def get_text_size(
            text: str,
            font: ImageFont.FreeTypeFont,
            *,
            anchor: Optional[str] = None,
            spacing: int = 4,
            stroke_width: int = 0,
            **kwargs
    ) -> tuple[int, int]:
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
            **kwargs
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
            stroke_width: int = 0
    ) -> str:
        """按字体绘制的文本长度切分换行文本

        :param text: 待切分的文本
        :param width: 宽度限制, 像素
        :param font: 绘制使用的字体, 传入 str 为本地字体资源文件名
        :param stroke_width: 文字描边, 像素
        """
        if font is None:
            font = ImageFont.truetype(image_utils_config.default_font_file.resolve_path,
                                      image_utils_config.default_font_size)
        elif isinstance(font, str):
            font = ImageFont.truetype(image_utils_config.default_font_folder(font).resolve_path,
                                      image_utils_config.default_font_size)

        spl_num = 0
        spl_list = []
        for num in range(len(text)):
            text_width, _ = cls.get_text_size(text[spl_num:num], font=font, stroke_width=stroke_width)
            if text_width > width:
                spl_list.append(text[spl_num:num])
                spl_num = num
        else:
            spl_list.append(text[spl_num:])

        return '\n'.join(spl_list)

    @property
    def image(self) -> Image.Image:
        """获取 Image 对象副本"""
        return deepcopy(self._image)

    @property
    def base64_output(self) -> str:
        """转换为 Base64 输出"""
        b64 = base64.b64encode(self.get_bytes())
        b64 = str(b64, encoding='utf-8')
        return 'base64://' + b64

    @property
    def bytes_output(self) -> bytes:
        """转换为 bytes 输出"""
        return self.get_bytes()

    def set_image(self, image: Image.Image) -> Self:
        """手动更新 Image"""
        self._image = image
        return self

    @run_sync
    def async_get_bytes(self, *, format_: str = 'JPEG') -> bytes:
        return self.get_bytes(format_=format_)

    @run_sync
    def async_get_bytes_add_blank(self, bytes_num: int = 16, *, format_: str = 'JPEG') -> bytes:
        """返回图片并在末尾添加空白比特"""
        return self.get_bytes_add_blank(bytes_num=bytes_num, format_=format_)

    def get_bytes(self, *, format_: str = 'JPEG') -> bytes:
        """获取 Image 内容, 以 Bytes 输出"""
        with BytesIO() as _bf:
            self._image.save(_bf, format=format_)
            _content = _bf.getvalue()
        return _content

    def get_bytes_add_blank(self, bytes_num: int = 16, *, format_: str = 'JPEG') -> bytes:
        """返回图片并在末尾添加空白比特"""
        return self.get_bytes(format_=format_) + b' '*bytes_num

    async def save(
            self,
            file: str | TemporaryResource,
            *,
            format_: str = 'JPEG'
    ) -> TemporaryResource:
        """输出指定格式图片到文件"""
        if isinstance(file, TemporaryResource):
            save_file = file
        else:
            save_file = image_utils_config.tmp_output_folder(file)

        async with save_file.async_open('wb') as af:
            await af.write(self.get_bytes(format_=format_))
        return save_file

    def convert(self, mode: str) -> Self:
        self._image = self._image.convert(mode=mode)
        return self

    def mark(
            self,
            text: str,
            *,
            position: Literal['la', 'ra', 'lb', 'rb', 'c'] = 'rb',
            fill: tuple[int, int, int] = (128, 128, 128)
    ) -> Self:
        """在图片上添加标注文本"""
        image = self.image
        if image.mode == 'L':
            image = image.convert(mode='RGB')

        width, height = image.size
        edge_w = width // 32 if width // 32 <= 10 else 10
        edge_h = height // 32 if height // 32 <= 10 else 10

        font = ImageFont.truetype(image_utils_config.default_font_file.resolve_path, width // 32)
        text_kwargs = {
            'text': text,
            'font': font,
            'fill': fill,
            'stroke_width': width // 256,
            'stroke_fill': (255, 255, 255)
        }

        match position:
            case 'c':
                ImageDraw.Draw(image).text(
                    xy=(width // 2, height // 2), align='center', anchor='mm', **text_kwargs
                )
            case 'la':
                ImageDraw.Draw(image).text(
                    xy=(0, 0), align='left', anchor='la', **text_kwargs
                )
            case 'ra':
                ImageDraw.Draw(image).text(
                    xy=(width - edge_w, 0), align='right', anchor='ra', **text_kwargs
                )
            case 'lb':
                ImageDraw.Draw(image).text(
                    xy=(0, height - edge_h), align='left', anchor='lb', **text_kwargs
                )
            case 'rb' | _:
                ImageDraw.Draw(image).text(
                    xy=(width - edge_w, height - edge_h), align='right', anchor='rb', **text_kwargs
                )

        self._image = image
        return self

    def gaussian_blur(self, radius: int | None = None) -> Self:
        """高斯模糊"""
        _image = self.image
        if radius is None:
            blur_radius = _image.width // 16
        else:
            blur_radius = radius
        blur_image = _image.filter(ImageFilter.GaussianBlur(radius=blur_radius))

        self._image = blur_image
        return self

    def gaussian_noise(
            self,
            *,
            sigma: float = 8,
            enable_random: bool = True,
            mask_factor: float = 0.25) -> Self:
        """为图片添加肉眼不可见的底噪

        :param sigma: 噪声sigma, 默认值8
        :param enable_random: 为噪声sigma添加随机扰动, 默认值True
        :param mask_factor: 噪声蒙版透明度修正, 默认值0.25
        :return:
        """
        _image = self.image
        # 处理图片
        width, height = _image.size
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
        _image.paste(noise_image, (0, 0), mask=noise_mask)

        self._image = _image
        return self

    def add_edge(
            self,
            edge_scale: float = 1/32,
            edge_color: tuple[int, int, int] | tuple[int, int, int, int] = (255, 255, 255, 0)
    ) -> Self:
        """在保持原图大小的条件下, 使用透明图层为原图添加边框"""
        image = self.image
        if image.mode != 'RGBA':
            image = image.convert(mode='RGBA')

        # 计算调整比例
        width, height = image.size

        edge_scale = 0 if edge_scale < 0 else 1 if edge_scale > 1 else edge_scale
        scaled_size = int(width * (1 - edge_scale)), int(height * (1 - edge_scale))

        scale = min(scaled_size[0] / width, scaled_size[1] / height)
        image = image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)

        box = (int(width * (1 - scale) / 2)), int(height * (1 - scale) / 2)
        background = Image.new(mode="RGBA", size=(width, height), color=edge_color)
        background.paste(image, box=box, mask=image)

        self._image = background
        return self

    def resize_with_filling(
            self,
            size: tuple[int, int],
            background_color: tuple[int, int, int] | tuple[int, int, int, int] = (255, 255, 255, 0)
    ) -> Self:
        """在不损失原图长宽比的条件下, 使用透明图层将原图转换成指定大小"""
        image = self.image
        if image.mode != 'RGBA':
            image = image.convert(mode='RGBA')

        # 计算调整比例
        width, height = image.size
        rs_width, rs_height = size
        scale = min(rs_width / width, rs_height / height)

        image = image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)
        box = (int(abs(width * scale - rs_width) / 2), int(abs(height * scale - rs_height) / 2))
        background = Image.new(mode="RGBA", size=size, color=background_color)
        background.paste(image, box=box, mask=image)

        self._image = background
        return self

    def resize_fill_canvas(
            self,
            size: tuple[int, int],
            background_color: tuple[int, int, int] | tuple[int, int, int, int] = (255, 255, 255, 0)
    ) -> Self:
        """在不损失原图长宽比的条件下, 填充并平铺指定大小画布"""
        image = self.image
        if image.mode != 'RGBA':
            image = image.convert(mode='RGBA')

        # 计算调整比例
        width, height = image.size
        rs_width, rs_height = size
        scale = max(rs_width / width, rs_height / height)
        image = image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)

        box = (- int(abs(width * scale - rs_width) / 2), - int(abs(height * scale - rs_height) / 2))
        background = Image.new(mode="RGBA", size=size, color=background_color)
        background.paste(image, box=box, mask=image)

        self._image = background
        return self


__all__ = [
    'ImageUtils'
]
