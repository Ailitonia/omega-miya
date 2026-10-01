"""
@Author         : Ailitonia
@Date           : 2026/10/1 17:31
@FileName       : x_tweet
@Project        : omega-miya
@Description    : X(Twitter) 推特发布图片图库统一接口实现
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from src.utils.twitter_x_api import TwitterGuest
from src.utils.twitter_x_api.misc import orig_image_url
from ..internal import BaseArtworkProxy
from ..models import ArtworkProxyData, ArtistUserData, ArtworkPoolData


class TweetPicArtworkProxy(BaseArtworkProxy):
    """推特发布图片图库统一接口实现"""

    @classmethod
    def _get_base_origin_name(cls) -> str:
        return 'x_twitter_tweet_pic'

    @classmethod
    async def _get_resource_as_bytes(cls, url: str, *, timeout: int = 30) -> bytes:
        return await TwitterGuest.get_resource_as_bytes(url=url, timeout=timeout)

    @classmethod
    async def _random(cls, *, limit: int = 20) -> list[str | int]:
        # 源站无此功能, 不予实现
        raise NotImplementedError

    @classmethod
    async def _search(cls, keyword: str, *, page: int | None = None, **kwargs) -> list[str | int]:
        # 源站无此功能, 不予实现
        raise NotImplementedError

    async def _query(self) -> ArtworkProxyData:
        tweet_data = await TwitterGuest.get_tweet_by_id(tweet_id=self.s_aid)
        photo_media = [
            media for media in tweet_data.media
            if media.type == 'photo' and media.media_url is not None
        ]
        if not photo_media:
            raise ValueError(f'tweet {self.s_aid} has no photo media')

        """X(Twitter) 动态图片默认分类分级
        (classification, rating)
                (0, -1)
        默认图片分类分级未知, 虽然大概不会有 r18 图片, 但 nsfw 的涩图还是有的, 导入数据库的本地图片另作处理
        """

        return ArtworkProxyData.model_validate({
            'origin': self._get_base_origin_name(),
            'aid': tweet_data.id,
            'uid': tweet_data.user.id if tweet_data.user is not None else -1,
            'title': tweet_data.text,
            'uname': f'{tweet_data.user.name}@{tweet_data.user.screen_name}' if tweet_data.user is not None else '',
            'classification': 0,
            'rating': -1,
            'width': photo_media[0].width or -1,
            'height': photo_media[0].height or -1,
            'tags': [],
            'description': tweet_data.full_text,
            'source': f'https://x.com/x/status/{tweet_data.id}',
            'pages': [
                {
                    'page_index': index,
                    'preview_file': {
                        'url': media.media_url,
                        'file_ext': self.parse_url_file_suffix(media.media_url),  # type: ignore
                        'width': media.width,
                        'height': media.height,
                    },
                    'regular_file': {
                        'url': media.media_url,
                        'file_ext': self.parse_url_file_suffix(media.media_url),  # type: ignore
                        'width': media.width,
                        'height': media.height,
                    },
                    'original_file': {
                        'url': orig_image_url(media.media_url),  # type: ignore
                        'file_ext': self.parse_url_file_suffix(media.media_url),  # type: ignore
                        'width': media.width,
                        'height': media.height,
                    }
                }
                for index, media in enumerate(photo_media)
            ],
            'published_at': tweet_data.created_at_datetime,
        })

    async def get_std_desc(self, *, split_len: int = 128) -> str:
        artwork_data = await self.query()
        return artwork_data.description[:split_len]

    async def get_std_preview_desc(self, *, split_len: int = 12) -> str:
        artwork_data = await self.query()
        return artwork_data.title[:split_len]

    @classmethod
    async def _query_pool(cls, pool_id: str | int) -> ArtworkPoolData:
        # 源站无此功能, 不予实现
        raise NotImplementedError

    @classmethod
    async def _discovery(cls, *, limit: int = 20) -> list[str | int]:
        # 源站无此功能, 不予实现
        raise NotImplementedError

    @classmethod
    async def _recommend(cls, base_aid: str | int | None = None, *, limit: int = 20) -> list[str | int]:
        # 源站无此功能, 不予实现
        raise NotImplementedError

    @classmethod
    async def _daily_ranking(cls, page: int) -> list[str | int]:
        # 源站无此功能, 不予实现
        raise NotImplementedError

    @classmethod
    async def _weekly_ranking(cls, page: int) -> list[str | int]:
        # 源站无此功能, 不予实现
        raise NotImplementedError

    @classmethod
    async def _monthly_ranking(cls, page: int) -> list[str | int]:
        # 源站无此功能, 不予实现
        raise NotImplementedError

    @classmethod
    async def _query_user(cls, uid: str | int) -> ArtistUserData:
        # 源站无此功能, 不予实现
        raise NotImplementedError

    @classmethod
    async def _query_user_bookmark_artworks(cls, uid: str | int, page: int) -> list[str | int]:
        # 源站无此功能, 不予实现
        raise NotImplementedError

    @classmethod
    async def _query_follow_latest(cls, page: int, *, filter_tag: str | None = None) -> list[str | int]:
        # 源站无此功能, 不予实现
        raise NotImplementedError


__all__ = [
    'TweetPicArtworkProxy',
]
