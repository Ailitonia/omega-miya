"""
@Author         : Ailitonia
@Date           : 2024/8/8 14:52:20
@FileName       : image_ops.py
@Project        : omega-miya
@Description    : 图片处理工具插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import abc
from typing import TYPE_CHECKING, Literal

from nonebot.utils import run_sync

from src.utils.image_utils import ImageUtils
from src.utils.image_utils.template import generate_thumbs_preview_image, PreviewImageThumbs, PreviewImageModel
from src.utils.process_utils import semaphore_gather
from .models import ArtworkProxyAddonsMixin

if TYPE_CHECKING:
    from src.resource import TemporaryResource
    from ..typing import ArtworkPageParamType


class ImageOpsMixin(ArtworkProxyAddonsMixin, abc.ABC):
    """作品图片处理工具插件"""

    @staticmethod
    @run_sync
    def _handle_blur(image: "TemporaryResource", origin_mark: str) -> ImageUtils:
        """模糊处理图片"""
        _image = ImageUtils.init_from_file(file=image)
        _image.gaussian_blur()
        _image.mark(text=origin_mark)
        return _image

    @staticmethod
    @run_sync
    def _handle_mark(image: "TemporaryResource", origin_mark: str) -> ImageUtils:
        """标记水印"""
        _image = ImageUtils.init_from_file(file=image)
        _image.mark(text=origin_mark)
        return _image

    @staticmethod
    @run_sync
    def _handle_noise(image: "TemporaryResource", origin_mark: str) -> ImageUtils:
        """噪点处理图片"""
        _image = ImageUtils.init_from_file(file=image)
        _image.gaussian_noise(sigma=16)
        _image.mark(text=origin_mark)
        return _image

    """图片标记工具"""

    async def _process_artwork_page(
            self,
            page_index: int = 0,
            *,
            page_type: "ArtworkPageParamType" = 'regular',
            process_mode: Literal['mark', 'blur', 'noise'] = 'mark',
    ) -> "TemporaryResource":
        """处理作品图片"""
        artwork_data = await self.query()
        origin_mark = f'{artwork_data.origin.title()} | {artwork_data.aid}'

        page_file = await self.get_page_file(page_index=page_index, page_type=page_type)
        match process_mode:
            case 'noise':
                image = await self._handle_noise(image=page_file, origin_mark=origin_mark)
                output_file_name = f'{page_file.path.stem}_noise_sigma16_marked.jpg'
            case 'blur':
                image = await self._handle_blur(image=page_file, origin_mark=origin_mark)
                output_file_name = f'{page_file.path.stem}_blur_marked.jpg'
            case 'mark' | _:
                image = await self._handle_mark(image=page_file, origin_mark=origin_mark)
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
        """使用自定义方法处理作品图片"""
        return await self._process_artwork_page(page_index=page_index, page_type=page_type, process_mode=process_mode)

    async def get_proceed_page_file(
            self,
            page_index: int = 0,
            *,
            page_type: "ArtworkPageParamType" = 'regular',
            no_blur_rating: int = 1,
    ) -> "TemporaryResource":
        """根据作品分级处理作品图片

        :param page_index: 作品图片页码
        :param page_type: 作品图片类型
        :param no_blur_rating: 最高不需要模糊处理的分级等级
        :return: TemporaryResource
        """
        max_no_blur_rating = max(0, no_blur_rating)
        artwork_data = await self.query()

        if artwork_data.rating.value == 0:
            process = self._process_artwork_page(page_index=page_index, page_type=page_type, process_mode='mark')
        elif artwork_data.rating.value <= max_no_blur_rating:
            process = self._process_artwork_page(page_index=page_index, page_type=page_type, process_mode='noise')
        else:
            process = self._process_artwork_page(page_index=page_index, page_type=page_type, process_mode='blur')

        return await process

    """预览图生成工具"""

    @classmethod
    async def _get_any_image_preview_thumb_data(cls, url: str, desc_text: str) -> PreviewImageThumbs:
        """获取生成预览图所需要的任意图片的数据"""
        return PreviewImageThumbs(desc_text=desc_text, preview_thumb=await cls._get_resource_as_bytes(url=url))

    async def _get_preview_thumb_data(
            self,
            *,
            page_type: "ArtworkPageParamType" = 'preview',
            no_blur_rating: int = 1,
    ) -> PreviewImageThumbs:
        """获取生成预览图所需要的作品数据"""
        max_no_blur_rating = max(0, no_blur_rating)
        artwork_data = await self.query()

        image_file = await self.get_page_file(page_type=page_type)
        if artwork_data.rating.value <= max_no_blur_rating:
            proceed_image = await self._handle_mark(image=image_file, origin_mark=artwork_data.aid)
        else:
            proceed_image = await self._handle_blur(image=image_file, origin_mark=artwork_data.aid)

        desc_text = await self.get_std_preview_desc()
        preview_thumb = await proceed_image.async_get_bytes()

        return PreviewImageThumbs(desc_text=desc_text, preview_thumb=preview_thumb)

    @classmethod
    async def _get_any_images_preview_data(
            cls,
            preview_name: str,
            image_data: list[tuple[str, str]]
    ) -> PreviewImageModel:
        """获取生成预览图所需要的所有任意图片的数据

        :param image_data: list of image data: (image_url, desc_text)
        :return: PreviewImageModel
        """
        tasks = [
            cls._get_any_image_preview_thumb_data(url=url, desc_text=desc_text)
            for url, desc_text in image_data
        ]
        requests_data = await semaphore_gather(tasks=tasks, semaphore_num=16, filter_exception=True)
        previews = list(requests_data)
        count = len(previews)
        return PreviewImageModel(preview_name=preview_name, count=count, previews=previews)

    @classmethod
    async def _get_artworks_preview_data(
            cls,
            preview_name: str,
            artworks: list["ImageOpsMixin"],
            *,
            page_type: "ArtworkPageParamType" = 'preview',
            no_blur_rating: int = 1,
    ) -> PreviewImageModel:
        """获取生成预览图所需要的所有作品的数据"""
        tasks = [
            artwork._get_preview_thumb_data(page_type=page_type, no_blur_rating=no_blur_rating)
            for artwork in artworks
        ]
        requests_data = await semaphore_gather(tasks=tasks, semaphore_num=16, filter_exception=True)
        previews = list(requests_data)
        count = len(previews)
        return PreviewImageModel(preview_name=preview_name, count=count, previews=previews)

    @classmethod
    async def generate_any_images_preview(
            cls,
            preview_name: str,
            image_data: list[tuple[str, str]],
            *,
            preview_size: tuple[int, int] = (256, 256),  # 默认预览图缩略图大小
            hold_ratio: bool = True,
            edge_scale: float = 1 / 32,
            num_of_line: int = 6,
            limit: int = 1000
    ) -> "TemporaryResource":
        """生成多个任意图片的预览图

        :param preview_name: 预览图标题
        :param image_data: 图片数据列表: (image_url, desc_text)
        :param preview_size: 单个小缩略图的尺寸
        :param hold_ratio: 是否保持缩略图原图比例
        :param edge_scale: 缩略图添加白边的比例, 范围 0~1
        :param num_of_line: 生成预览每一行的预览图数
        :param limit: 限制生成时缩略图数量的最大值
        :return: TemporaryResource
        """
        preview = await cls._get_any_images_preview_data(preview_name=preview_name, image_data=image_data)
        path_config = cls._generate_path_config()

        return await generate_thumbs_preview_image(
            preview=preview,
            preview_size=preview_size,
            font_path=path_config.theme_font,
            header_color=(0, 150, 250),
            hold_ratio=hold_ratio,
            edge_scale=edge_scale,
            num_of_line=num_of_line,
            limit=limit,
            output_folder=path_config.preview_path
        )

    @classmethod
    async def generate_artworks_preview(
            cls,
            preview_name: str,
            artworks: list["ImageOpsMixin"],
            *,
            page_type: "ArtworkPageParamType" = 'preview',
            no_blur_rating: int = 1,
            preview_size: tuple[int, int] = (256, 256),  # 默认预览图缩略图大小
            edge_scale: float = 1 / 32,
            num_of_line: int = 6,
            limit: int = 1000
    ) -> "TemporaryResource":
        """生成多个作品的预览图

        :param preview_name: 预览图标题
        :param artworks: 作品列表
        :param page_type: 作品图片类型
        :param no_blur_rating: 最高不需要模糊处理的分级等级
        :param preview_size: 单个小缩略图的尺寸
        :param edge_scale: 缩略图添加白边的比例, 范围 0~1
        :param num_of_line: 生成预览每一行的预览图数
        :param limit: 限制生成时缩略图数量的最大值
        :return: TemporaryResource
        """
        preview = await cls._get_artworks_preview_data(
            preview_name=preview_name, artworks=artworks, page_type=page_type, no_blur_rating=no_blur_rating
        )
        path_config = cls._generate_path_config()

        return await generate_thumbs_preview_image(
            preview=preview,
            preview_size=preview_size,
            font_path=path_config.theme_font,
            header_color=(0, 150, 250),
            hold_ratio=True,
            edge_scale=edge_scale,
            num_of_line=num_of_line,
            limit=limit,
            output_folder=path_config.preview_path
        )


__all__ = [
    'ImageOpsMixin',
]
