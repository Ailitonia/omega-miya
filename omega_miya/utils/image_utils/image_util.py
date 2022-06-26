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
from typing import Literal
from copy import deepcopy
from io import BytesIO
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont

from omega_miya.local_resource import LocalResource, TmpResource
from omega_miya.web_resource import HttpFetcher

from .config import image_utils_config


class ImageUtils(object):
    def __init__(self, image: Image.Image):
        self._image = image

    @classmethod
    def init_from_bytes(cls, image: bytes) -> "ImageUtils":
        with BytesIO(image) as bf:
            image: Image.Image = Image.open(bf)
            image.load()
            new_obj = cls(image=image)
        return new_obj

    @classmethod
    def init_from_file(cls, file: LocalResource) -> "ImageUtils":
        with file.open('rb') as f:
            image: Image.Image = Image.open(f)
            image.load()
            new_obj = cls(image=image)
        return new_obj

    @classmethod
    async def init_from_url(cls, image_url: str) -> "ImageUtils":
        fetcher = HttpFetcher(timeout=30)
        image_result = await fetcher.get_bytes(url=image_url)
        with BytesIO(image_result.result) as bf:
            image: Image.Image = Image.open(bf)
            image.load()
            new_obj = cls(image=image)
        return new_obj

    @property
    def image(self) -> Image.Image:
        return deepcopy(self._image)

    @property
    def base64(self) -> str:
        b64 = base64.b64encode(self.get_bytes())
        b64 = str(b64, encoding='utf-8')
        return 'base64://' + b64

    def get_bytes(self, *, format_: str = 'JPEG') -> bytes:
        with BytesIO() as _bf:
            self._image.save(_bf, format=format_)
            _content = _bf.getvalue()
        return _content

    def get_bytes_add_blank(self, bytes_num: int = 16, *, format_: str = 'JPEG') -> bytes:
        """返回图片并在末尾添加空白比特"""
        return self.get_bytes(format_=format_) + b' '*bytes_num

    async def save(self, file_name: str, *, format_: str = 'JPEG') -> TmpResource:
        """输出指定格式图片到文件"""
        save_file = image_utils_config.default_save_folder(file_name)
        async with save_file.async_open('wb') as af:
            await af.write(self.get_bytes(format_=format_))
        return save_file

    def mark(
            self,
            text: str,
            *,
            position: Literal['la', 'ra', 'lb', 'rb', 'c'] = 'rb',
            fill: tuple[int, int, int] = (128, 128, 128)
    ) -> "ImageUtils":
        """在图片上添加标注文本"""
        image = self.image
        width, height = image.size
        font = ImageFont.truetype(image_utils_config.default_font_file.resolve_path, width // 32)

        match position:
            case 'c':
                ImageDraw.Draw(image).text(
                    xy=(width // 2, height // 2), text=text, font=font, align='center', anchor='mm', fill=fill)
            case 'la':
                ImageDraw.Draw(image).text(
                    xy=(0, 0), text=text, font=font, align='left', anchor='la', fill=fill)
            case 'ra':
                ImageDraw.Draw(image).text(
                    xy=(width, 0), text=text, font=font, align='right', anchor='ra', fill=fill)
            case 'lb':
                ImageDraw.Draw(image).text(
                    xy=(0, height), text=text, font=font, align='left', anchor='lb', fill=fill)
            case 'rb' | _:
                ImageDraw.Draw(image).text(
                    xy=(width, height), text=text, font=font, align='right', anchor='rb', fill=fill)

        self._image = image
        return self

    def gaussian_blur(self, radius: int | None = None) -> "ImageUtils":
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
            mask_factor: float = 0.25) -> "ImageUtils":
        """
        为图片添加肉眼不可见的底噪
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

    def resize_with_filling(self, size: tuple[int, int]) -> "ImageUtils":
        """在不损失原图长宽比的条件下, 使用透明图层将原图转换成指定大小"""
        _image = self.image
        # 计算调整比例
        width, height = _image.size
        rs_width, rs_height = size
        scale = min(rs_width / width, rs_height / height)

        _image = _image.resize((int(width * scale), int(height * scale)))
        box = (int(abs(width * scale - rs_width) / 2), int(abs(height * scale - rs_height) / 2))
        background = Image.new(mode="RGBA", size=size, color=(255, 255, 255, 0))
        background.paste(_image, box=box)

        self._image = background
        return self


__all__ = [
    'ImageUtils'
]
