"""
@Author         : Ailitonia
@Date           : 2025/8/19 20:26:52
@FileName       : user_space.py
@Project        : omega-miya
@Description    : 用户空间相关
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import abc
from typing import TYPE_CHECKING, Literal, Self

from .typing import ArtworkProxyAddonsMixin
from ..models import ArtistUserData

if TYPE_CHECKING:
    from src.resource import TemporaryResource


class UserSpaceMixin(ArtworkProxyAddonsMixin, abc.ABC):
    """用户空间相关功能插件"""

    @classmethod
    @abc.abstractmethod
    async def _discovery(cls, *, limit: int = 20) -> list[str | int]:
        """内部方法, 获取首页/发现页/瀑布流作品"""
        raise NotImplementedError

    @classmethod
    async def discovery(cls, *, limit: int = 20) -> list[Self]:
        """获取推荐作品, 如未提供基准 Artwork ID, 则使用类似首页推荐机制进行获取"""
        return [cls(artwork_id=aid) for aid in await cls._discovery(limit=limit)]

    @classmethod
    @abc.abstractmethod
    async def _recommend(cls, base_aid: str | int | None = None, *, limit: int = 20) -> list[str | int]:
        """内部方法, 获取推荐作品, 如未提供基准 Artwork ID, 则使用类似首页推荐机制进行获取"""
        raise NotImplementedError

    @classmethod
    async def recommend(cls, base_aid: str | int | None = None, *, limit: int = 20) -> list[Self]:
        """获取推荐作品, 如未提供基准 Artwork ID, 则使用类似首页推荐机制进行获取"""
        return [cls(artwork_id=aid) for aid in await cls._recommend(base_aid=base_aid, limit=limit)]

    @classmethod
    @abc.abstractmethod
    async def _daily_ranking(cls, page: int) -> list[str | int]:
        """内部方法, 获取每日榜单作品"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    async def _weekly_ranking(cls, page: int) -> list[str | int]:
        """内部方法, 获取每周榜单作品"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    async def _monthly_ranking(cls, page: int) -> list[str | int]:
        """内部方法, 获取每月榜单作品"""
        raise NotImplementedError

    @classmethod
    async def ranking(cls, mode: Literal['daily', 'weekly', 'monthly'], page: int) -> list[Self]:
        """获取榜单作品"""
        page = 1 if page < 1 else page
        match mode:
            case 'daily':
                artwork_ids = await cls._daily_ranking(page=page)
            case 'weekly':
                artwork_ids = await cls._weekly_ranking(page=page)
            case 'monthly' | _:
                artwork_ids = await cls._monthly_ranking(page=page)
        return [cls(artwork_id=aid) for aid in artwork_ids]

    @classmethod
    def _get_user_meta_file(cls, uid: str | int) -> 'TemporaryResource':
        return cls._generate_path_config().meta_path(f'user_{uid}.json')

    @classmethod
    async def _dumps_user_meta(cls, user_data: ArtistUserData) -> None:
        """内部方法, 缓存图集元数据"""
        async with cls._get_user_meta_file(uid=user_data.uid).async_open('w', encoding='utf8') as af:
            await af.write(user_data.model_dump_json())

    @classmethod
    @abc.abstractmethod
    async def _query_user(cls, uid: str | int) -> ArtistUserData:
        """内部方法, 获取用户信息"""
        raise NotImplementedError

    @classmethod
    async def _fast_query_user(cls, uid: str | int, *, use_cache: bool = True) -> ArtistUserData:
        """内部方法, 获取用户信息, 优先从本地缓存加载"""
        if use_cache and cls._get_user_meta_file(uid=uid).is_file:
            async with cls._get_user_meta_file(uid=uid).async_open('r', encoding='utf8') as af:
                user_data = ArtistUserData.model_validate_json(await af.read())
        else:
            user_data = await cls._query_user(uid=uid)
            await cls._dumps_user_meta(user_data=user_data)

        return user_data

    @classmethod
    async def query_user(cls, uid: str | int, *, use_cache: bool = True) -> ArtistUserData:
        """获取用户信息"""
        return await cls._fast_query_user(uid=uid, use_cache=use_cache)

    @classmethod
    async def _query_user_artworks(cls, uid: str | int) -> list[str | int]:
        """内部方法, 获取用户作品列表"""
        return (await cls.query_user(uid=uid, use_cache=False)).artwork_ids

    @classmethod
    async def query_user_artworks(cls, uid: str | int) -> list[Self]:
        """获取用户作品列表"""
        return [cls(artwork_id=aid) for aid in await cls._query_user_artworks(uid=uid)]

    @classmethod
    @abc.abstractmethod
    async def _query_user_bookmark_artworks(cls, uid: str | int, page: int) -> list[str | int]:
        """内部方法, 获取用户收藏作品"""
        raise NotImplementedError

    @classmethod
    async def query_user_bookmark_artworks(cls, uid: str | int, page: int) -> list[Self]:
        """获取用户收藏作品"""
        page = 1 if page < 1 else page
        return [cls(artwork_id=aid) for aid in await cls._query_user_bookmark_artworks(uid=uid, page=page)]

    @abc.abstractmethod
    async def _follow_latest(self, page: int) -> list[str | int]:
        """内部方法, 获取已关注的最新作品, 若无关注功能, 则为站点更新最新作品"""
        raise NotImplementedError

    async def follow_latest(self, page: int) -> list[Self]:
        """获取推荐作品, 如未提供基准 Artwork ID, 则使用类似首页推荐机制进行获取"""
        return [self.__class__(artwork_id=aid) for aid in await self._follow_latest(page=page)]


__all__ = [
    'UserSpaceMixin',
]
