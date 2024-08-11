"""
@Author         : Ailitonia
@Date           : 2024/8/5 16:14:50
@FileName       : pixiv.py
@Project        : omega-miya
@Description    : Pixiv 图库统一接口实现
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from src.utils.pixiv_api import PixivArtwork

from ..add_ons import ImageOpsMixin
from ..internal import BaseArtworkProxy
from ..models import ArtworkData


class _PixivArtworkProxy(BaseArtworkProxy):
    """Pixiv 图库统一接口实现"""

    @classmethod
    def get_base_origin_name(cls) -> str:
        return 'pixiv'

    @classmethod
    async def _get_resource_as_bytes(cls, url: str, *, timeout: int = 30) -> bytes:
        return await PixivArtwork.get_resource_as_bytes(url=url, timeout=timeout)

    @classmethod
    async def _get_resource_as_text(cls, url: str, *, timeout: int = 10) -> str:
        return await PixivArtwork.get_resource_as_text(url=url, timeout=timeout)

    async def _query(self) -> ArtworkData:
        artwork_data = await PixivArtwork(pid=self.i_aid).query_artwork()

        """Pixiv 主站作品默认分类分级
        (classification, rating)
                    is_ai     not_ai
        is_r18     (1,  3)    (0,  3)
        not_r18    (1, -1)    (0, -1)
        """

        return ArtworkData.model_validate({
            'origin': self.get_base_origin_name(),
            'aid': artwork_data.pid,
            'title': artwork_data.title,
            'uid': artwork_data.uid,
            'uname': artwork_data.uname,
            'classification': 1 if artwork_data.is_ai else 0,
            'rating': 3 if artwork_data.is_r18 else -1,
            'width': artwork_data.width,
            'height': artwork_data.height,
            'tags': artwork_data.tags,
            'description': artwork_data.description,
            'source': artwork_data.url,
            'pages': [
                {
                    'preview_file': {
                        'url': page.small,
                        'file_ext': self.parse_url_file_suffix(page.small),  # type: ignore
                        'width': None,
                        'height': None,
                    },
                    'regular_file': {
                        'url': page.regular,
                        'file_ext': self.parse_url_file_suffix(page.regular),  # type: ignore
                        'width': None,
                        'height': None,
                    },
                    'original_file': {
                        'url': page.original,
                        'file_ext': self.parse_url_file_suffix(page.original),  # type: ignore
                        'width': artwork_data.width,
                        'height': artwork_data.height,
                    }
                }
                for _, page in artwork_data.all_page.items()
            ]
        })

    async def get_std_desc(self, *, desc_len_limit: int = 128) -> str:
        artwork_data = await self.query()

        tag_t = ' '.join(f'#{x.strip()}' for x in artwork_data.tags)

        if not artwork_data.description:
            desc_t = f'「{artwork_data.title}」/「{artwork_data.uname}」\n{tag_t}\n{artwork_data.source}'
        else:
            desc_t = (
                f'「{artwork_data.title}」/「{artwork_data.uname}」\n{tag_t}\n{artwork_data.source}\n{"-" * 16}\n'
                f'{artwork_data.description[:desc_len_limit]}'
                f'{"." * 6 if len(artwork_data.description) > desc_len_limit else ""}'
            )
        return desc_t.strip()

    async def get_std_preview_desc(self, *, text_len_limit: int = 12) -> str:
        artwork_data = await self.query()

        origin = f"{artwork_data.origin.title()}: {artwork_data.aid}"
        title = (
            f"{artwork_data.title[:text_len_limit]}..."
            if len(artwork_data.title) > text_len_limit
            else artwork_data.title
        )

        author = f"Author: {artwork_data.uname}"
        author = f"{author[:text_len_limit]}..." if len(author) > text_len_limit else author

        return f'{origin}\n{title}\n{author}'


class PixivArtworkProxy(_PixivArtworkProxy, ImageOpsMixin):
    """Pixiv 图库统一接口实现"""


__all__ = [
    'PixivArtworkProxy',
]
