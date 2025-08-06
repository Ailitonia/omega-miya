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
from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal

from nonebot.utils import run_sync

from src.utils import semaphore_gather
from src.utils.image_utils import ImageEffectProcessor, ImageLoader
from src.utils.image_utils.template import PreviewImageModel, PreviewImageThumbs, generate_thumbs_preview_image
from .typing import ArtworkProxyAddonsMixin
from ..models import ArtworkPool

if TYPE_CHECKING:
    from src.resource import TemporaryResource

    from ..models import ArtworkData
    from ..typing import ArtworkPageParamType


class ImageOpsMixin(ArtworkProxyAddonsMixin, abc.ABC):
    """作品图片处理工具插件"""

    @staticmethod
    @run_sync
    def _handle_blur(image: 'TemporaryResource', origin_mark: str) -> ImageEffectProcessor:
        """模糊处理图片"""
        _image = ImageEffectProcessor(ImageLoader.init_from_file(file=image))
        _image.gaussian_blur()
        _image.mark(text=origin_mark)
        _image.convert(mode='RGB')
        return _image

    @staticmethod
    @run_sync
    def _handle_mark(image: 'TemporaryResource', origin_mark: str) -> ImageEffectProcessor:
        """标记水印"""
        _image = ImageEffectProcessor(ImageLoader.init_from_file(file=image))
        _image.mark(text=origin_mark)
        _image.convert(mode='RGB')
        return _image

    @staticmethod
    @run_sync
    def _handle_noise(image: 'TemporaryResource', origin_mark: str) -> ImageEffectProcessor:
        """噪点处理图片"""
        _image = ImageEffectProcessor(ImageLoader.init_from_file(file=image))
        _image.gaussian_noise(sigma=16)
        _image.mark(text=origin_mark)
        _image.convert(mode='RGB')
        return _image

    """图片标记工具"""

    async def _process_artwork_page(
            self,
            page_index: int = 0,
            *,
            page_type: 'ArtworkPageParamType' = 'regular',
            process_mode: Literal['mark', 'blur', 'noise'] = 'mark',
    ) -> 'TemporaryResource':
        """处理作品图片"""
        artwork_data = await self.query()
        origin_mark = f'{artwork_data.origin.title()} | {artwork_data.aid}'

        page_file = await self.get_page_file(page_index=page_index, page_type=page_type)
        match process_mode:
            case 'noise':
                image = await self._handle_noise(image=page_file, origin_mark=origin_mark)
                output_file_name = f'{page_file.stem}_noise_sigma16_marked.jpg'
            case 'blur':
                image = await self._handle_blur(image=page_file, origin_mark=origin_mark)
                output_file_name = f'{page_file.stem}_blur_marked.jpg'
            case 'mark' | _:
                image = await self._handle_mark(image=page_file, origin_mark=origin_mark)
                output_file_name = f'{page_file.stem}_marked.jpg'

        output_file = self.path_config.processed_path(output_file_name)
        return await image.save(file=output_file)

    async def get_custom_proceed_page_file(
            self,
            page_index: int = 0,
            *,
            page_type: 'ArtworkPageParamType' = 'regular',
            process_mode: Literal['mark', 'blur', 'noise'] = 'mark',
    ) -> 'TemporaryResource':
        """使用自定义方法处理作品图片"""
        return await self._process_artwork_page(page_index=page_index, page_type=page_type, process_mode=process_mode)

    async def get_proceed_page_file(
            self,
            page_index: int = 0,
            *,
            page_type: 'ArtworkPageParamType' = 'regular',
            no_blur_rating: int = 1,
    ) -> 'TemporaryResource':
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
            page_type: 'ArtworkPageParamType' = 'preview',
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
            image_data: Sequence[tuple[str, str]],
            limit: int = 100,
    ) -> PreviewImageModel:
        """获取生成预览图所需要的所有任意图片的数据

        :param image_data: list of image data: (image_url, desc_text)
        :param limit: 限制生成时缩略图数量的最大值
        :return: PreviewImageModel
        """
        tasks = [
            cls._get_any_image_preview_thumb_data(url=url, desc_text=desc_text)
            for url, desc_text in image_data[:limit]
        ]
        requests_data = await semaphore_gather(tasks=tasks, semaphore_num=8, filter_exception=True)
        previews = list(requests_data)
        return PreviewImageModel(preview_name=preview_name, previews=previews)

    @classmethod
    async def _get_artworks_preview_data(
            cls,
            preview_name: str,
            artworks: Sequence['ImageOpsMixin'],
            *,
            page_type: 'ArtworkPageParamType' = 'preview',
            no_blur_rating: int = 1,
            limit: int = 100,
    ) -> PreviewImageModel:
        """获取生成预览图所需要的所有作品的数据"""
        tasks = [
            artwork._get_preview_thumb_data(page_type=page_type, no_blur_rating=no_blur_rating)
            for artwork in artworks[:limit]
        ]
        requests_data = await semaphore_gather(tasks=tasks, semaphore_num=8, filter_exception=True)
        previews = list(requests_data)
        return PreviewImageModel(preview_name=preview_name, previews=previews)

    @classmethod
    async def generate_any_images_preview(
            cls,
            preview_name: str,
            image_data: Sequence[tuple[str, str]],
            *,
            preview_size: tuple[int, int] = (256, 256),  # 默认预览图缩略图大小
            hold_ratio: bool = True,
            edge_scale: float = 1 / 32,
            num_of_line: int = 6,
            limit: int = 100,
    ) -> 'TemporaryResource':
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
        preview = await cls._get_any_images_preview_data(preview_name=preview_name, image_data=image_data, limit=limit)
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
            artworks: Sequence['ImageOpsMixin'],
            *,
            page_type: 'ArtworkPageParamType' = 'preview',
            no_blur_rating: int = 1,
            preview_size: tuple[int, int] = (256, 256),  # 默认预览图缩略图大小
            edge_scale: float = 1 / 32,
            num_of_line: int = 6,
            limit: int = 100,
    ) -> 'TemporaryResource':
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
            preview_name=preview_name, artworks=artworks,
            page_type=page_type, no_blur_rating=no_blur_rating, limit=limit
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


class ImageOpsPlusPoolMixin(ImageOpsMixin, abc.ABC):
    """作品图片处理工具插件(附加图集处理功能)"""

    @classmethod
    def _get_pool_meta_file(cls, pool_id: str) -> 'TemporaryResource':
        return cls._generate_path_config().meta_path(f'pool_{pool_id}.json')

    @classmethod
    async def _dumps_pool_meta(cls, pool_data: ArtworkPool) -> None:
        """内部方法, 缓存图集元数据"""
        async with cls._get_pool_meta_file(pool_id=pool_data.pool_id).async_open('w', encoding='utf8') as af:
            await af.write(pool_data.model_dump_json())

    @classmethod
    @abc.abstractmethod
    async def _query_pool(cls, pool_id: str) -> ArtworkPool:
        """获取图集信息"""
        raise NotImplementedError

    @classmethod
    async def _fast_query_pool(cls, pool_id: str, *, use_cache: bool = True) -> ArtworkPool:
        """获取图集信息, 优先从本地缓存加载"""
        if use_cache and cls._get_pool_meta_file(pool_id=pool_id).is_file:
            async with cls._get_pool_meta_file(pool_id=pool_id).async_open('r', encoding='utf8') as af:
                pool_data = ArtworkPool.model_validate_json(await af.read())
        else:
            pool_data = await cls._query_pool(pool_id=pool_id)
            await cls._dumps_pool_meta(pool_data=pool_data)

        return pool_data

    @classmethod
    async def query_pool(cls, pool_id: str, *, use_cache: bool = True) -> ArtworkPool:
        """获取图集信息"""
        return await cls._fast_query_pool(pool_id=pool_id, use_cache=use_cache)

    @classmethod
    async def query_pool_all_artworks(cls, pool_id: str) -> list['ArtworkData']:
        """获取图集中所有作品信息"""
        pool_data = await cls.query_pool(pool_id=pool_id)

        tasks = [cls(aid).query() for aid in pool_data.artwork_ids]
        all_artwork_data = await semaphore_gather(tasks=tasks, semaphore_num=4, return_exceptions=False)

        return list(all_artwork_data)

    @classmethod
    async def query_pool_all_artwork_pages(cls, pool_id: str) -> list['TemporaryResource']:
        """获取图集中所有作品图片"""
        pool_data = await cls.query_pool(pool_id=pool_id)

        tasks = [cls(aid).get_all_pages_file() for aid in pool_data.artwork_ids]
        all_artwork_pages = await semaphore_gather(tasks=tasks, semaphore_num=4, return_exceptions=False)

        return [file for artwork_pages in all_artwork_pages for file in artwork_pages]

    @classmethod
    async def generate_pool_preview(cls, pool_id: str) -> 'TemporaryResource':
        """生成图集的预览图"""
        pool_data = await cls.query_pool(pool_id=pool_id)

        return await cls.generate_artworks_preview(
            preview_name=f'{cls.get_base_origin_name().title()} Pool #{pool_id}: {pool_data.name}',
            artworks=[cls(aid) for aid in pool_data.artwork_ids]
        )


__all__ = [
    'ImageOpsMixin',
    'ImageOpsPlusPoolMixin',
]
