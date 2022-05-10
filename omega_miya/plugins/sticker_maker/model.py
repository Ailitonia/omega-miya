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
from datetime import datetime
from io import BytesIO
from PIL import Image

from omega_miya.local_resource import LocalResource, TmpResource
from omega_miya.utils.process_utils import run_sync


_STICKER_OUTPUT_PATH: TmpResource = TmpResource('sticker_maker', 'output')
"""生成表情包图片保存路径"""


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
            source_image: LocalResource | None = None
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
    def _handler(self) -> bytes:
        """表情包制作方法"""
        raise NotImplementedError

    def _load_source_image(self) -> Image.Image:
        """载入并初始化图片素材"""
        with self.source_image.open('rb') as f:
            image: Image.Image = Image.open(f)
            image.load()
        return image

    @staticmethod
    def _zoom_pil_image_width(image: Image.Image, width: int) -> Image.Image:
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

    async def make(self) -> TmpResource:
        """使用 _handle 方法制作表情包并输出"""
        image_content = await run_sync(self._handler)()
        file_name = f"sticker_{self._sticker_name}_" \
                    f"{datetime.now().strftime('%Y%m%d%H%M%S')}.{self._default_output_format}"
        save_file = _STICKER_OUTPUT_PATH(file_name)
        async with save_file.async_open('wb') as af:
            await af.write(image_content)
        return save_file


__all__ = [
    'StickerRender'
]
