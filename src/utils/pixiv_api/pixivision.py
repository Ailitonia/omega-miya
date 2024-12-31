"""
@Author         : Ailitonia
@Date           : 2022/04/05 22:03
@FileName       : pixivision.py
@Project        : nonebot2_miya
@Description    : Pixivision Api
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import TYPE_CHECKING

from .api_base import BasePixivAPI
from .helper import PixivParser
from .model import PixivisionArticle, PixivisionIllustrationList

if TYPE_CHECKING:
    from src.resource import TemporaryResource


class Pixivision(BasePixivAPI):
    """Pixivision 接口集成"""

    def __init__(self, aid: int):
        self.aid = aid
        self.url = f'{self._get_articles_url()}/{aid}'

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(aid={self.aid})'

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'https://www.pixivision.net'

    @classmethod
    def _get_illustration_url(cls) -> str:
        return f'{cls._get_root_url()}/zh/c/illustration'

    @classmethod
    def _get_articles_url(cls) -> str:
        return f'{cls._get_root_url()}/zh/a'

    @classmethod
    def _get_tag_url(cls) -> str:
        return f'{cls._get_root_url()}/zh/t'

    @classmethod
    async def download_resource(
            cls,
            url: str,
            save_folder: 'TemporaryResource',
            custom_file_name: str | None = None,
            *,
            subdir: str | None = None,
            ignore_exist_file: bool = False
    ) -> 'TemporaryResource':
        """下载任意资源到本地, 保持原始文件名, 直接覆盖同名文件"""
        return await cls._download_resource(
            save_folder=save_folder,
            url=url,
            subdir=subdir,
            ignore_exist_file=ignore_exist_file,
            custom_file_name=custom_file_name,
        )

    @classmethod
    async def query_illustration_list(cls, page: int = 1) -> PixivisionIllustrationList:
        """获取并解析 Pixivision Illustration 导览页面内容"""
        params = {'p': page, 'lang': 'zh'}
        illustration_data = await cls.get_resource_as_text(url=cls._get_illustration_url(), params=params)

        return await PixivParser.parse_pixivision_show_page(
            content=illustration_data,
            root_url=cls._get_root_url()
        )

    async def query_article(self) -> PixivisionArticle:
        """获取并解析 Pixivision 文章页面内容"""
        url = f'{self._get_articles_url()}/{self.aid}'
        article_data = await self.get_resource_as_text(url=url)

        return await PixivParser.parse_pixivision_article_page(
            content=article_data,
            root_url=self._get_root_url()
        )


__all__ = [
    'Pixivision'
]
