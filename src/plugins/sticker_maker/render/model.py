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
from collections.abc import Sequence
from datetime import datetime
from io import BytesIO
from typing import TYPE_CHECKING, Literal, Optional

import imageio.v3 as iio
from PIL import Image
from nonebot.utils import run_sync

from .consts import STICKER_OUTPUT_PATH

if TYPE_CHECKING:
    from src.resource import StaticResource, TemporaryResource


class BaseStickerRender(abc.ABC):
    """表情包生成器基类"""

    def __init__(
            self,
            text: str | None = None,
            external_image: Optional['TemporaryResource'] = None,
    ) -> None:
        """使用待生成的素材实例化生成器

        :param text: 生成表情包所使用的文字内容
        :param external_image: 生成表情包所使用的图片 (非内置模板图片, 而是需要由用户提供的图片)
        """
        if self.need_text() and text is None:
            raise ValueError('text arg can not be None')
        self.__text = text

        if self.need_external_image() and external_image is None:
            raise ValueError('external_image arg can not be None')
        self.__external_image = external_image

    @classmethod
    @abc.abstractmethod
    def need_text(cls) -> bool:
        """是否需要输入生成表情包的文字内容, 若返回为 True, 则 self.text 不能为 None"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def need_external_image(cls) -> bool:
        """是否需要用户提供图片来作为表情包生成的内容, 若返回为 True, 则 self.external_image 不能为 None"""
        raise NotImplementedError

    @classmethod
    def get_sticker_name(cls) -> str:
        """获取表情包模板名称"""
        return cls.__name__.lower().removesuffix('render')

    @classmethod
    @abc.abstractmethod
    def get_output_width(cls) -> int:
        """获取输出图片宽度"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_output_format(cls) -> Literal['JPEG', 'PNG', 'GIF']:
        """获取输出图片格式"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_default_fonts(cls) -> list['StaticResource']:
        """获取获取制作表情包所需要的字体集"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_static_images(cls) -> list['StaticResource']:
        """获取获取制作表情包所需要的模板图片集"""
        raise NotImplementedError

    def get_external_image(self) -> Optional['TemporaryResource']:
        """获取获取制作表情包所需要的, 由用户提供的图片 (默认用户仅能通过命令提供一张图片)"""
        return self.__external_image

    def get_text(self) -> str | None:
        """生成表情包所使用的文字"""
        return self.__text

    def set_text(self, text: str) -> None:
        """手动更新生成表情包所使用的文字"""
        self.__text = text

    @staticmethod
    def _resize_to_width(image: 'Image.Image', width: int) -> 'Image.Image':
        """等比缩放 PIL.Image.Image 为指定宽度"""
        image_resize_height = width * image.height // image.width
        make_image = image.resize((width, image_resize_height))
        return make_image

    @staticmethod
    def _output_pil_image(image: 'Image.Image', output_format: str = 'JPEG') -> bytes:
        """提取 PIL.Image.Image 为 bytes"""
        match output_format.upper():
            case 'PNG':
                if image.mode != 'RGBA':
                    image = image.convert(mode='RGBA')
            case 'JPEG' | _:
                output_format = 'JPEG'
                if image.mode != 'RGB':
                    image = image.convert(mode='RGB')

        with BytesIO() as bf:
            image.save(bf, output_format)
            content = bf.getvalue()
        return content

    @classmethod
    @abc.abstractmethod
    def _core_render(
            cls,
            text: str | None,
            static_images: Sequence['Image.Image'],
            external_image: Optional['Image.Image'],
            *,
            fonts: Sequence['StaticResource'],
            output_width: int,
            output_format: str,
    ) -> 'Image.Image':
        """模板处理核心流程, 负责使用提供的各项素材生成表情包, 返回为表情包图片的内容 (默认用户仅能通过命令提供一张图片)"""
        raise NotImplementedError

    @classmethod
    def _main_render(
            cls,
            text: str | None,
            static_images: Sequence['Image.Image'],
            external_image: Optional['Image.Image'],
            *,
            fonts: Sequence['StaticResource'],
            output_width: int,
            output_format: str,
    ) -> list['Image.Image']:
        """针对用户提供的图片进行处理, 自动识别用户提供图片是否为动态图片, 返回为表情包图片的内容"""

        def iter_gif_frame(_image: Image.Image):
            index = 0
            while True:
                try:
                    _image.seek(frame=index)
                    yield _image
                    index += 1
                except EOFError:
                    return

        if external_image is not None and external_image.format == 'GIF':
            output_images = [
                cls._core_render(
                    text=text, static_images=static_images, external_image=x,
                    fonts=fonts, output_width=output_width, output_format=output_format
                ) for x in iter_gif_frame(_image=external_image)
            ]
        else:
            output_images = [
                cls._core_render(
                    text=text, static_images=static_images, external_image=external_image,
                    fonts=fonts, output_width=output_width, output_format=output_format,
                )
            ]

        return output_images

    def _make(self) -> 'TemporaryResource':
        """默认的表情包处理流程"""
        external_image_file = self.get_external_image()
        external_image = Image.open(external_image_file.path) if external_image_file is not None else None

        output_images = self._main_render(
            text=self.get_text(),
            static_images=[Image.open(x.path) for x in self.get_static_images()],
            external_image=external_image,
            fonts=self.get_default_fonts(),
            output_width=self.get_output_width(),
            output_format=self.get_output_format(),
        )

        save_gif = True if (external_image is not None and external_image.format == 'GIF') else False
        save_gif = True if self.get_output_format() == 'GIF' else save_gif
        file_format = self.get_output_format().lower() if not save_gif else 'gif'

        file_name = (
            f'sticker_{self.get_sticker_name()}_{hash(self)}_{datetime.now().strftime("%Y%m%d%H%M%S")}.{file_format}'
        )
        save_file = STICKER_OUTPUT_PATH(file_name)

        if save_gif:
            with save_file.open('wb') as f:
                iio.imwrite(
                    uri=f,
                    image=[iio.imread(self._output_pil_image(frame)) for frame in output_images],
                    extension='.gif',
                    duration=60,
                    quantizer=2,
                    loop=0,
                )
        else:
            with save_file.open('wb') as f:
                output_images[0].save(f, format=self.get_output_format())

        return save_file

    @run_sync
    def _async_make(self) -> 'TemporaryResource':
        """异步执行默认的表情包处理流程"""
        return self._make()

    async def make(self) -> 'TemporaryResource':
        """表情包制作入口函数, 默认使用 self._async_make 方法制作表情包并输出, 但可被重载并自定义其他制作流程"""
        return await self._async_make()


__all__ = [
    'BaseStickerRender',
]
