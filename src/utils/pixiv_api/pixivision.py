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

from src.service import OmegaRequests
from .api_base import PixivApiBase
from .helper import PixivParser
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

    async def query_article(self) -> PixivisionArticle:
        """获取并解析 Pixivision 文章页面内容"""
        url = f'{self._articles_url}/{self.aid}'
        article_data = await self.request_resource(url=url)

        return await PixivParser.parse_pixivision_article_page(
            content=article_data,
            root_url=self._root_url
        )


__all__ = [
    'Pixivision'
]
