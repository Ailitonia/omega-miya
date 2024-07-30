"""
@Author         : Ailitonia
@Date           : 2022/04/05 22:03
@FileName       : pixivision.py
@Project        : nonebot2_miya
@Description    : Pixivision Api
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Optional, Any

from src.resource import TemporaryResource
from src.service import OmegaRequests
from .api_base import PixivApiBase
from .helper import PixivParser, PixivPreviewGenerator
from .model import PixivisionArticle, PixivisionIllustrationList


class Pixivision(PixivApiBase):
    """Pixivision 接口集成"""
    _root_url: str = 'https://www.pixivision.net'
    _illustration_url: str = 'https://www.pixivision.net/zh/c/illustration'
    _articles_url: str = 'https://www.pixivision.net/zh/a'
    _tag_url: str = 'https://www.pixivision.net/zh/t'

    def __init__(self, aid: int):
        self.aid = aid
        self.url = f'{self._articles_url}/{aid}'

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(aid={self.aid})'

    @classmethod
    async def request_resource(
            cls,
            url: str,
            params: Optional[dict[str, Any]] = None,
            headers: Optional[dict[str, Any]] = None,
            timeout: int = 45
    ) -> str | bytes | None:
        """请求原始资源内容"""
        if headers is None:
            headers = OmegaRequests.get_default_headers()
            headers.update({'referer': 'https://www.pixivision.net/zh/'})

        return await super().request_resource(url=url, params=params, headers=headers, timeout=timeout)

    @classmethod
    async def query_illustration_list(cls, page: int = 1) -> PixivisionIllustrationList:
        """获取并解析 Pixivision Illustration 导览页面内容"""
        params = {'p': page, 'lang': 'zh'}
        illustration_data = await cls.request_resource(url=cls._illustration_url, params=params)

        return await PixivParser.parse_pixivision_show_page(
            content=illustration_data,
            root_url=cls._root_url
        )

    @classmethod
    async def query_illustration_list_with_preview(cls, page: int = 1) -> TemporaryResource:
        """获取并解析 Pixivision Illustration 导览页面内容并生成预览图"""
        illustration_result = await cls.query_illustration_list(page=page)
        # 获取缩略图内容
        name = f'Pixivision Illustration - Page {page}'
        preview_request = await PixivPreviewGenerator.emit_preview_model_from_pixivision_illustration_model(
            preview_name=name, model=illustration_result
        )
        preview_img_file = await PixivPreviewGenerator.generate_artworks_preview_image(
            preview=preview_request, preview_size=(480, 270), hold_ratio=True, num_of_line=4
        )
        return preview_img_file

    async def query_article(self) -> PixivisionArticle:
        """获取并解析 Pixivision 文章页面内容"""
        url = f'{self._articles_url}/{self.aid}'
        article_data = await self.request_resource(url=url)

        return await PixivParser.parse_pixivision_article_page(
            content=article_data,
            root_url=self._root_url
        )

    async def query_eyecatch_image(self) -> TemporaryResource:
        """获取 Pixivision 文章头图"""
        article_data = await self.query_article()
        image_content = await self.request_resource(url=article_data.eyecatch_image)

        file_name = f'eyecatch_{self.aid}.jpg'
        file = TemporaryResource('pixivision', 'eyecatch', file_name)
        async with file.async_open('wb') as af:
            await af.write(image_content)
        return file

    async def query_article_with_preview(self) -> TemporaryResource:
        """获取并解析 Pixivision 文章页面内容并生成预览图"""
        article_result = await self.query_article()
        # 获取缩略图内容
        name = f'Pixivision - {article_result.title_without_mark}'
        preview_request = await PixivPreviewGenerator.emit_preview_model_from_pixivision_article_model(
            preview_name=name, model=article_result
        )
        preview_img_file = await PixivPreviewGenerator.generate_artworks_preview_image(
            preview=preview_request, preview_size=(512, 512), hold_ratio=True, num_of_line=4
        )
        return preview_img_file


__all__ = [
    'Pixivision'
]
