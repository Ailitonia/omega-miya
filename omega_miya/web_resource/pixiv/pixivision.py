from omega_miya.local_resource import TmpResource
from omega_miya.web_resource import HttpFetcher
from omega_miya.utils.process_utils import run_sync

from .config import pixiv_config
from .exception import PixivisionNetworkError
from .model import PixivisionArticle, PixivisionIllustrationList
from .helper import (parse_pixivision_show_page, parse_pixivision_article_page,
                     emit_preview_model_from_pixivision_illustration_model,
                     emit_preview_model_from_pixivision_article_model, generate_artworks_preview_image)


class Pixivision(object):
    """Pixiv 基类"""
    _root_url: str = 'https://www.pixivision.net'
    _illustration_url: str = 'https://www.pixivision.net/zh/c/illustration'
    _articles_url: str = 'https://www.pixivision.net/zh/a'
    _tag_url: str = 'https://www.pixivision.net/zh/t'

    _default_headers = HttpFetcher.get_default_headers()
    _default_headers.update({'referer': 'https://www.pixivision.net/zh/'})

    _fetcher = HttpFetcher(timeout=10, headers=_default_headers, cookies=pixiv_config.cookie_phpssid)

    def __init__(self, aid: int):
        self.aid = aid
        self.url = f'{self._articles_url}/{aid}'

    def __repr__(self):
        return f'<{self.__class__.__name__}(aid={self.aid})>'

    @classmethod
    async def query_illustration_list(cls, page: int = 1) -> PixivisionIllustrationList:
        """获取并解析 Pixivision Illustration 导览页面内容"""
        params = {'p': page, 'lang': 'zh'}
        illustration_data = await cls._fetcher.get_text(url=cls._illustration_url, params=params)
        if illustration_data.status != 200:
            raise PixivisionNetworkError(f'PixivisionNetworkError, {illustration_data.status}')
        # 解析页面
        illustration_result = await run_sync(parse_pixivision_show_page)(content=illustration_data.result,
                                                                         root_url=cls._root_url)
        return illustration_result

    @classmethod
    async def query_illustration_list_with_preview(cls, page: int = 1) -> TmpResource:
        """获取并解析 Pixivision Illustration 导览页面内容并生成预览图"""
        illustration_result = await cls.query_illustration_list(page=page)
        # 获取缩略图内容
        name = f'Pixivision Illustration - Page {page}'
        preview_request = await emit_preview_model_from_pixivision_illustration_model(
            preview_name=name, model=illustration_result)
        preview_img_file = await generate_artworks_preview_image(
            preview=preview_request, preview_size=(480, 270), hold_ratio=True, num_of_line=4)
        return preview_img_file

    async def query_article(self) -> PixivisionArticle:
        """获取并解析 Pixivision 文章页面内容"""
        url = f'{self._articles_url}/{self.aid}'
        article_data = await self._fetcher.get_text(url=url)
        if article_data.status != 200:
            raise PixivisionNetworkError(f'PixivisionNetworkError, {article_data.status}')
        # 解析页面
        article_result = await run_sync(parse_pixivision_article_page)(content=article_data.result,
                                                                       root_url=self._root_url)
        return article_result

    async def query_eyecatch_image(self) -> TmpResource:
        """获取 Pixivision 文章头图"""
        article_data = await self.query_article()
        image_content = await self._fetcher.get_bytes(url=article_data.eyecatch_image)
        if image_content.status != 200:
            raise PixivisionNetworkError(f'PixivisionNetworkError, status code {image_content.status}')

        file_name = f'eyecatch_{self.aid}.jpg'
        file = TmpResource('pixivision', 'eyecatch', file_name)
        async with file.async_open('wb') as af:
            await af.write(image_content.result)
        return file

    async def query_article_with_preview(self) -> TmpResource:
        """获取并解析 Pixivision 文章页面内容并生成预览图"""
        article_result = await self.query_article()
        # 获取缩略图内容
        name = f'Pixivision - {article_result.title_without_mark}'
        preview_request = await emit_preview_model_from_pixivision_article_model(
            preview_name=name, model=article_result)
        preview_img_file = await generate_artworks_preview_image(
            preview=preview_request, preview_size=(512, 512), hold_ratio=True, num_of_line=4)
        return preview_img_file


__all__ = [
    'Pixivision'
]
