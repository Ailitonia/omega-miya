"""
@Author         : Ailitonia
@Date           : 2024/8/8 14:52:20
@FileName       : image_ops.py
@Project        : omega-miya
@Description    : 图片处理插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import abc
from typing import TYPE_CHECKING, Literal

from nonebot.utils import run_sync

from src.utils.image_utils import ImageUtils
from .models import ArtworkProxyAddonsMixin

if TYPE_CHECKING:
    from src.resource import TemporaryResource
    from ..typing import ArtworkPageParamType


class ImageOpsMixin(ArtworkProxyAddonsMixin, abc.ABC):
    """作品图片处理工具插件"""

    @staticmethod
    @run_sync
    def _handle_blur(image: "TemporaryResource", source_mark: str) -> ImageUtils:
        """模糊处理图片"""
        _image = ImageUtils.init_from_file(file=image)
        _image.gaussian_blur()
        _image.mark(text=source_mark)
        return _image

    @staticmethod
    @run_sync
    def _handle_mark(image: "TemporaryResource", source_mark: str) -> ImageUtils:
        """标记水印"""
        _image = ImageUtils.init_from_file(file=image)
        _image.mark(text=source_mark)
        return _image

    @staticmethod
    @run_sync
    def _handle_noise(image: "TemporaryResource", source_mark: str) -> ImageUtils:
        """噪点处理图片"""
        _image = ImageUtils.init_from_file(file=image)
        _image.gaussian_noise(sigma=16)
        _image.mark(text=source_mark)
        return _image

    async def _process_artwork_page(
            self,
            page_index: int = 0,
            *,
            page_type: "ArtworkPageParamType" = 'regular',
            process_mode: Literal['mark', 'blur', 'noise'] = 'mark',
    ) -> "TemporaryResource":
        artwork_data = await self.query()
        source_mark = f'{artwork_data.origin.title()} | {artwork_data.aid}'

        page_file = await self.get_page_file(page_index=page_index, page_type=page_type)
        match process_mode:
            case 'noise':
                image = await self._handle_noise(image=page_file, source_mark=source_mark)
                output_file_name = f'{page_file.path.stem}_noise_sigma16_marked.jpg'
            case 'blur':
                image = await self._handle_blur(image=page_file, source_mark=source_mark)
                output_file_name = f'{page_file.path.stem}_blur_marked.jpg'
            case 'mark' | _:
                image = await self._handle_mark(image=page_file, source_mark=source_mark)
                output_file_name = f'{page_file.path.stem}_marked.jpg'

        output_file = self._get_path_config().processed_path(output_file_name)
        return await image.save(file=output_file)

    async def get_custom_proceed_page_file(
            self,
            page_index: int = 0,
            *,
            page_type: "ArtworkPageParamType" = 'regular',
            process_mode: Literal['mark', 'blur', 'noise'] = 'mark',
    ) -> "TemporaryResource":
        return await self._process_artwork_page(page_index=page_index, page_type=page_type, process_mode=process_mode)

    async def get_proceed_page_file(
            self,
            page_index: int = 0,
            *,
            page_type: "ArtworkPageParamType" = 'regular',
            allow_rating: int = 1,
    ) -> "TemporaryResource":
        max_allow_rating = max(0, allow_rating)
        artwork_data = await self.query()

        if artwork_data.rating.value == 0:
            process = self._process_artwork_page(page_index=page_index, page_type=page_type, process_mode='mark')
        elif artwork_data.rating.value <= max_allow_rating:
            process = self._process_artwork_page(page_index=page_index, page_type=page_type, process_mode='noise')
        else:
            process = self._process_artwork_page(page_index=page_index, page_type=page_type, process_mode='blur')

        return await process


__all__ = [
    'ImageOpsMixin'
]
