"""
@Author         : Ailitonia
@Date           : 2022/05/07 20:41
@FileName       : model.py
@Project        : nonebot2_miya 
@Description    : Sticker Render Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import abc
import imageio
from datetime import datetime
from io import BytesIO
from typing import Iterable
from PIL import Image

from nonebot.utils import run_sync

from src.resource import StaticResource, TemporaryResource

from .consts import STICKER_OUTPUT_PATH


class StickerRender(abc.ABC):
    """表情包生成器"""
    _sticker_name: str = 'abc_render'

    _need_text: bool = True
    """是否需要输入生成表情包的文字内容"""
    _need_external_img: bool = False
    """是否需要外部图片来作为表情包生成的内容"""

    _default_output_width: int = 512
    """输出图片宽度"""
    _default_output_format: str = 'jpg'
    """输出图片格式"""

    def __init__(
            self,
            text: str | None = None,
            source_image: TemporaryResource | None = None
    ):
        """使用待生成的素材实例化生成器

        :param text: 表情包文字
        :param source_image: 生成素材图片, 若有必须是文件
        """
        self.text = text
        self.source_image = source_image

    @classmethod
    @property
    def need_text(cls) -> bool:
        """是否需要输入生成表情包的文字内容"""
        return cls._need_text

    @classmethod
    @property
    def need_image(cls) -> bool:
        """是否需要外部图片来作为表情包生成的内容"""
        return cls._need_external_img

    @abc.abstractmethod
    def _static_handler(self, *args, **kwargs) -> bytes:
        """静态图片表情包制作方法"""
        raise NotImplementedError

    @abc.abstractmethod
    def _gif_handler(self, *args, **kwargs) -> bytes:
        """动态图片表情包制作方法"""
        raise NotImplementedError

    @abc.abstractmethod
    def _handler(self) -> bytes:
        """表情包制作入口函数"""
        raise NotImplementedError

    def _get_source_image_info(self) -> (str, dict):
        """获取图片素材格式信息

        :return: format: str, num of frames: int, info: dict
        """
        with Image.open(self.source_image.resolve_path) as im:
            f_im = im.format
            info = im.info
        return f_im, info

    def _load_source_image(self, frame: int | None = None) -> Image.Image:
        """载入并初始化图片素材"""
        image: Image.Image = Image.open(self.source_image.resolve_path)
        if frame:
            image.seek(frame=frame)
        image.load()
        return image

    @staticmethod
    def _load_extra_source_image(source_file: StaticResource) -> Image.Image:
        """载入并初始化额外图片素材"""
        with source_file.open('rb') as f:
            image: Image.Image = Image.open(f)
            image.load()
        return image

    @staticmethod
    def _resize_to_width(image: Image.Image, width: int) -> Image.Image:
        """等比缩放 PIL.Image.Image 为指定宽度"""
        image_resize_height = width * image.height // image.width
        make_image = image.resize((width, image_resize_height))
        return make_image

    @staticmethod
    def _get_pil_image(image: Image.Image, output_format: str = 'JPEG') -> bytes:
        """提取 PIL.Image.Image 为 bytes"""
        match output_format.upper():
            case 'JPEG' | 'JPG':
                if image.mode != 'RGB':
                    image = image.convert(mode='RGB')
            case 'PNG':
                if image.mode != 'RGBA':
                    image = image.convert(mode='RGBA')

        with BytesIO() as bf:
            image.save(bf, output_format)
            content = bf.getvalue()
        return content

    @staticmethod
    def _generate_gif_from_bytes_seq(
            frames: Iterable[bytes],
            duration: float = 0.06,
            *,
            quantizer: int = 2
    ) -> bytes:
        """使用图片序列输出 GIF 图像"""
        frames_list = [imageio.v2.imread(frame) for frame in frames]

        with BytesIO() as bf:
            imageio.mimsave(bf, frames_list, 'GIF', duration=duration, quantizer=quantizer)
            content = bf.getvalue()

        return content

    async def make(self) -> TemporaryResource:
        """使用 _handle 方法制作表情包并输出"""
        image_content = await run_sync(self._handler)()
        file_name = f"sticker_{self._sticker_name}_" \
                    f"{datetime.now().strftime('%Y%m%d%H%M%S')}.{self._default_output_format}"
        save_file = STICKER_OUTPUT_PATH(file_name)
        async with save_file.async_open('wb') as af:
            await af.write(image_content)
        return save_file


__all__ = [
    'StickerRender'
]
