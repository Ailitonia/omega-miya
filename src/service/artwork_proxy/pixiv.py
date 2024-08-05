"""
@Author         : Ailitonia
@Date           : 2024/8/5 16:14:50
@FileName       : pixiv.py
@Project        : omega-miya
@Description    : Pixiv 接口实现
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from src.utils.pixiv_api import PixivArtwork
from .internal import BaseArtworkProxy
from .models import ArtworkData


class PixivArtworkProxy(BaseArtworkProxy):
    """Pixiv 图库统一接口实现"""

    @classmethod
    def _get_base_origin_name(cls) -> str:
        return 'pixiv'

    @classmethod
    async def _get_resource(cls, url: str, *, timeout: int = 30) -> str | bytes | None:
        return await PixivArtwork.request_resource(url=url, timeout=timeout)

    async def _query(self) -> ArtworkData:
        artwork_data = await PixivArtwork(pid=self.i_aid).query_artwork()

        return ArtworkData.model_validate({
            'aid': artwork_data.pid,
            'origin': self._get_base_origin_name(),
            'title': artwork_data.title,
            'uid': artwork_data.uid,
            'uname': artwork_data.uname,
            'tags': artwork_data.tags,
            'description': artwork_data.description,
            'classification': 2 if artwork_data.is_ai else 0,
            'rating': 3 if artwork_data.is_r18 else -1,
            'source': artwork_data.url,
            'pages': [
                {
                    'preview_file': {
                        'url': page.thumb_mini,
                        'file_ext': self.parse_url_file_suffix(page.thumb_mini),
                        'width': None,
                        'height': None,
                    },
                    'regular_file': {
                        'url': page.regular,
                        'file_ext': self.parse_url_file_suffix(page.regular),
                        'width': None,
                        'height': None,
                    },
                    'original_file': {
                        'url': page.original,
                        'file_ext': self.parse_url_file_suffix(page.original),
                        'width': artwork_data.width,
                        'height': artwork_data.height,
                    }
                }
                for index, page in artwork_data.all_page.items()
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


__all__ = [
    'PixivArtworkProxy'
]
