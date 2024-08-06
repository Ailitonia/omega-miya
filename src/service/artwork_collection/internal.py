"""
@Author         : Ailitonia
@Date           : 2024/8/6 16:10:38
@FileName       : internal.py
@Project        : omega-miya
@Description    : 基于 Artwork Proxy 实现数据库与图站接口整合
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import abc
from typing import TYPE_CHECKING, Literal, Optional

from sqlalchemy.exc import NoResultFound

from src.database import begin_db_session
from src.database.internal.artwork_collection import (
    ArtworkCollection,
    ArtworkCollectionDAL,
    ArtworkClassificationStatistic,
    ArtworkRatingStatistic,
)

if TYPE_CHECKING:
    from src.service.artwork_proxy.internal import BaseArtworkProxy
    from src.service.artwork_proxy.models import ArtworkData


class BaseArtworkCollection(abc.ABC):
    """作品合集基类, 封装后用于插件调用的数据库实体操作对象"""

    def __init__(self, artwork_proxy: "BaseArtworkProxy"):
        self.__ap = artwork_proxy

    @property
    def aid(self) -> str:
        return self.__ap.s_aid

    @property
    def origin_name(self) -> str:
        """对外暴露该作品对应图库的来源名称, 用于数据库收录"""
        return self._get_base_origin_name()

    @property
    @abc.abstractmethod
    def origin_desc(self) -> str:
        """作品名及作品原始来源介绍"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def _get_base_origin_name(cls) -> str:
        """内部方法, 返回该图库的来源名称, 作为数据库收录分类字段名"""
        raise NotImplementedError

    @classmethod
    async def query_by_condition(
            cls,
            keywords: Optional[str | list[str]],
            num: int = 3,
            *,
            allow_classification_range: Optional[tuple[int, int]] = None,
            allow_rating_range: Optional[tuple[int, int]] = None,
            acc_mode: bool = False,
            ratio: Optional[int] = None,
            order_mode: Literal['random', 'aid', 'aid_desc', 'create_time', 'create_time_desc'] = 'random'
    ) -> list["ArtworkCollection"]:
        """根据要求查询作品"""
        if isinstance(keywords, str):
            keywords = [keywords]

        if allow_classification_range is None:
            allow_classification_range = (2, 3)

        if allow_rating_range is None:
            allow_rating_range = (0, 1)

        async with begin_db_session() as session:
            result = await ArtworkCollectionDAL(session=session).query_by_condition(
                origin=cls._get_base_origin_name(),
                keywords=keywords, num=num,
                classification_min=min(allow_classification_range), classification_max=max(allow_classification_range),
                rating_min=min(allow_rating_range), rating_max=max(allow_rating_range),
                acc_mode=acc_mode, ratio=ratio, order_mode=order_mode
            )
        return result

    @classmethod
    async def random(
            cls,
            num: Optional[int],
            allow_classification_range: Optional[tuple[int, int]] = None,
            allow_rating_range: Optional[tuple[int, int]] = None,
            ratio: Optional[int] = None
    ) -> list["ArtworkCollection"]:
        """获取随机作品"""
        return await cls.query_by_condition(
            keywords=None, num=num, ratio=ratio,
            allow_classification_range=allow_classification_range, allow_rating_range=allow_rating_range
        )

    @classmethod
    async def query_classification_statistic(
            cls,
            *,
            keywords: Optional[str | list[str]] = None,
    ) -> ArtworkClassificationStatistic:
        """按分类统计收录作品数"""
        if isinstance(keywords, str):
            keywords = [keywords]

        async with begin_db_session() as session:
            result = await ArtworkCollectionDAL(session=session).query_classification_statistic(
                origin=cls._get_base_origin_name(), keywords=keywords
            )
        return result

    @classmethod
    async def query_rating_statistic(
            cls,
            *,
            keywords: Optional[str | list[str]] = None,
    ) -> ArtworkRatingStatistic:
        """按分级统计收录作品数"""
        if isinstance(keywords, str):
            keywords = [keywords]

        async with begin_db_session() as session:
            result = await ArtworkCollectionDAL(session=session).query_rating_statistic(
                origin=cls._get_base_origin_name(), keywords=keywords
            )
        return result

    @classmethod
    async def query_user_all(cls, uid: Optional[str] = None, uname: Optional[str] = None) -> list[ArtworkCollection]:
        """通过 uid 或用户名精准查找用户所有作品"""
        async with begin_db_session() as session:
            result = await ArtworkCollectionDAL(session=session).query_user_all(
                origin=cls._get_base_origin_name(), uid=uid, uname=uname
            )
        return result

    @classmethod
    async def query_user_all_aids(cls, uid: Optional[str] = None, uname: Optional[str] = None) -> list[str]:
        """通过 uid 或用户名精准查找用户所有作品的 artwork_id"""
        async with begin_db_session() as session:
            result = await ArtworkCollectionDAL(session=session).query_user_all_aids(
                origin=cls._get_base_origin_name(), uid=uid, uname=uname
            )
        return result

    async def query_artwork_from_database(self) -> ArtworkCollection:
        """查询数据库获取作品信息"""
        async with begin_db_session() as session:
            result = await ArtworkCollectionDAL(session=session).query_unique(
                origin=self.origin_name, aid=self.__ap.s_aid
            )
        return result

    async def query_artwork_from_proxy(self) -> "ArtworkData":
        """通过接口查询图站获取作品元数据"""
        return await self.__ap.query()

    async def add_artwork_into_database_ignore_exists(self) -> None:
        """查询图站获取作品元数据, 向数据库新增该作品信息, 若已存在忽略"""
        async with begin_db_session() as session:
            artwork_dal = ArtworkCollectionDAL(session=session)
            try:
                await artwork_dal.query_unique(origin=self.origin_name, aid=self.__ap.s_aid)
            except NoResultFound:
                artwork_data = await self.__ap.query()
                await artwork_dal.add(
                    origin=self.origin_name, aid=self.__ap.s_aid,
                    title=artwork_data.title, uid=artwork_data.uid, uname=artwork_data.uname,
                    classification=artwork_data.classification.value, rating=artwork_data.rating.value,
                    width=artwork_data.width, height=artwork_data.height,
                    tags=','.join(tag for tag in artwork_data.tags),
                    source=artwork_data.source, cover_page=artwork_data.cover_page_url,
                    description=artwork_data.description
                )

    async def add_and_upgrade_artwork_into_database(self, force_update_mark: bool = False) -> None:
        """查询图站获取作品元数据, 向数据库新增该作品信息, 若已存在则更新

        :param force_update_mark: 更新时是否强制更新数据库中存在的 classification 及 rating 标签, 若否则仅大于已有值时更新
        """
        artwork_data = await self.__ap.query()

        async with begin_db_session() as session:
            artwork_dal = ArtworkCollectionDAL(session=session)
            try:
                artwork = await artwork_dal.query_unique(origin=self.origin_name, aid=self.__ap.s_aid)

                if force_update_mark:
                    classification = artwork_data.classification.value
                    rating = artwork_data.rating.value
                else:
                    classification = max(artwork.classification, artwork_data.classification.value)
                    rating = max(artwork.rating, artwork_data.rating.value)

                await artwork_dal.update(
                    id_=artwork.id,
                    title=artwork_data.title, uid=artwork_data.uid, uname=artwork_data.uname,
                    classification=classification, rating=rating,
                    width=artwork_data.width, height=artwork_data.height,
                    tags=','.join(tag for tag in artwork_data.tags),
                    source=artwork_data.source, cover_page=artwork_data.cover_page_url,
                    description=artwork_data.description
                )
            except NoResultFound:
                await artwork_dal.add(
                    origin=self.origin_name, aid=self.__ap.s_aid,
                    title=artwork_data.title, uid=artwork_data.uid, uname=artwork_data.uname,
                    classification=artwork_data.classification.value, rating=artwork_data.rating.value,
                    width=artwork_data.width, height=artwork_data.height,
                    tags=','.join(tag for tag in artwork_data.tags),
                    source=artwork_data.source, cover_page=artwork_data.cover_page_url,
                    description=artwork_data.description
                )

    async def delete_artwork_from_database(self) -> None:
        """从数据库删除该作品信息"""
        async with begin_db_session() as session:
            artwork_dal = ArtworkCollectionDAL(session=session)
            artwork = await artwork_dal.query_unique(origin=self.origin_name, aid=self.__ap.s_aid)
            await artwork_dal.delete(id_=artwork.id)


__all__ = [
    'BaseArtworkCollection',
]
