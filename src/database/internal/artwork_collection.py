"""
@Author         : Ailitonia
@Date           : 2022/12/04 17:40
@FileName       : artwork_collection.py
@Project        : nonebot2_miya 
@Description    : ArtworkCollection DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Literal

from sqlalchemy import and_, delete, desc, func, or_, select, update

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayerModel, BaseDataQueryResultModel
from ..schema import ArtworkCollectionOrm


class ArtworkCollection(BaseDataQueryResultModel):
    """图库作品 Model"""
    origin: str
    aid: str
    title: str
    uid: str
    uname: str
    classification: int
    rating: int
    width: int
    height: int
    tags: str
    description: str | None = None
    source: str
    cover_page: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ArtworkClassificationStatistic(BaseDataQueryResultModel):
    """分类统计信息查询结果"""
    unused: int = 0
    unclassified: int = 0
    ai_generated: int = 0
    automatic: int = 0
    confirmed: int = 0

    @property
    def total(self) -> int:
        return self.unused + self.unclassified + self.ai_generated + self.automatic + self.confirmed


class ArtworkRatingStatistic(BaseDataQueryResultModel):
    """分级统计信息查询结果"""
    unknown: int = 0
    general: int = 0
    sensitive: int = 0
    questionable: int = 0
    explicit: int = 0

    @property
    def total(self) -> int:
        return self.unknown + self.general + self.sensitive + self.questionable + self.explicit


class ArtworkCollectionDAL(BaseDataAccessLayerModel[ArtworkCollectionOrm, ArtworkCollection]):
    """图库作品 数据库操作对象"""

    async def query_unique(self, origin: str, aid: str) -> ArtworkCollection:
        stmt = (select(ArtworkCollectionOrm)
                .where(ArtworkCollectionOrm.origin == origin)
                .where(ArtworkCollectionOrm.aid == aid))
        session_result = await self.db_session.execute(stmt)
        return ArtworkCollection.model_validate(session_result.scalar_one())

    async def query_by_condition(
            self,
            origin: str | Sequence[str] | None,
            keywords: Sequence[str] | None,
            num: int = 3,
            *,
            classification_min: int = 2,
            classification_max: int = 3,
            rating_min: int = 0,
            rating_max: int = 0,
            acc_mode: bool = False,
            ratio: int | None = None,
            order_mode: Literal['random', 'latest', 'aid', 'aid_desc'] = 'random',
    ) -> list[ArtworkCollection]:
        """按条件搜索图库收录作品

        :param origin: 作品来源
        :param keywords: 关键词列表
        :param num: 数量
        :param classification_min: 分类标签最小值
        :param classification_max: 分类标签最大值
        :param rating_min: 分级标签最小值
        :param rating_max: 分级标签最大值
        :param acc_mode: 是否启用精确搜索模式
        :param ratio: 图片长宽, 1: 横图, -1: 纵图, 0: 正方形图
        :param order_mode: 排序模式
        """
        if classification_min > classification_max:
            raise ValueError('param: classification_min must be less than classification_max')

        if rating_min > rating_max:
            raise ValueError('param: rating_min must be less than rating_max')

        stmt = select(ArtworkCollectionOrm)

        if origin is None:
            # 匹配所有来源
            pass
        elif isinstance(origin, str):
            # 匹配单一来源
            stmt = stmt.where(ArtworkCollectionOrm.origin == origin)
        else:
            # 匹配任意来源
            stmt = stmt.where(or_(*(ArtworkCollectionOrm.origin == x for x in origin)))

        # classification 条件
        stmt = stmt.where(and_(ArtworkCollectionOrm.classification >= classification_min,
                               ArtworkCollectionOrm.classification <= classification_max))
        # rating 条件
        stmt = stmt.where(and_(ArtworkCollectionOrm.rating >= rating_min,
                               ArtworkCollectionOrm.rating <= rating_max))

        # 根据 acc_mode 构造关键词查询语句
        if (keywords is None) or (not keywords):
            # 无关键词则随机
            pass
        elif acc_mode:
            # 精确搜索标题, 用户, tag
            for keyword in keywords:
                stmt = stmt.where(or_(
                    func.find_in_set(keyword, ArtworkCollectionOrm.title),
                    func.find_in_set(keyword, ArtworkCollectionOrm.uname),
                    func.find_in_set(keyword, ArtworkCollectionOrm.tags)
                ))
        else:
            # 模糊搜索标题, 用户, tag
            for keyword in keywords:
                stmt = stmt.where(or_(
                    ArtworkCollectionOrm.title.ilike(f'%{keyword}%'),
                    ArtworkCollectionOrm.uname.ilike(f'%{keyword}%'),
                    ArtworkCollectionOrm.tags.ilike(f'%{keyword}%')
                ))

        # 根据 ratio 构造图片长宽类型查询语句
        if ratio is None:
            pass
        elif ratio < 0:
            stmt = stmt.where(ArtworkCollectionOrm.width <= ArtworkCollectionOrm.height)
        elif ratio > 0:
            stmt = stmt.where(ArtworkCollectionOrm.width >= ArtworkCollectionOrm.height)
        else:
            stmt = stmt.where(ArtworkCollectionOrm.width == ArtworkCollectionOrm.height)

        # 根据 order_mode 构造排序语句
        match order_mode:
            case 'aid':
                stmt = stmt.order_by(ArtworkCollectionOrm.aid)
            case 'aid_desc':
                stmt = stmt.order_by(desc(ArtworkCollectionOrm.aid))
            case 'latest':
                stmt = stmt.order_by(desc(ArtworkCollectionOrm.created_at))
            case 'random' | _:
                stmt = stmt.order_by(func.random())

        # 结果数量限制
        if num is None:
            pass
        else:
            stmt = stmt.limit(num)

        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[ArtworkCollection], session_result.scalars().all())

    async def query_classification_statistic(
            self,
            origin: str | None = None,
            keywords: Sequence[str] | None = None
    ) -> ArtworkClassificationStatistic:
        """按分类统计收录作品数"""
        stmt = select(ArtworkCollectionOrm.classification, func.count(ArtworkCollectionOrm.aid))

        if origin is not None:
            stmt = stmt.where(ArtworkCollectionOrm.origin == origin)

        if keywords:
            for keyword in keywords:
                stmt = stmt.where(or_(
                    ArtworkCollectionOrm.tags.ilike(f'%{keyword}%'),
                    ArtworkCollectionOrm.uname.ilike(f'%{keyword}%'),
                    ArtworkCollectionOrm.title.ilike(f'%{keyword}%')
                ))

        stmt = stmt.group_by(ArtworkCollectionOrm.classification)
        session_result = await self.db_session.execute(stmt)

        result = {}
        for k, v in session_result.all():
            match k:
                case 0:
                    result.update({'unclassified': v})
                case 1:
                    result.update({'ai_generated': v})
                case 2:
                    result.update({'automatic': v})
                case 3:
                    result.update({'confirmed': v})
                case _:
                    result.update({'unused': v})

        return ArtworkClassificationStatistic.model_validate(result)

    async def query_rating_statistic(
            self,
            origin: str | None = None,
            keywords: Sequence[str] | None = None
    ) -> ArtworkRatingStatistic:
        """按分级统计收录作品数"""
        stmt = select(ArtworkCollectionOrm.rating, func.count(ArtworkCollectionOrm.aid))

        if origin is not None:
            stmt = stmt.where(ArtworkCollectionOrm.origin == origin)

        if keywords:
            for keyword in keywords:
                stmt = stmt.where(or_(
                    ArtworkCollectionOrm.tags.ilike(f'%{keyword}%'),
                    ArtworkCollectionOrm.uname.ilike(f'%{keyword}%'),
                    ArtworkCollectionOrm.title.ilike(f'%{keyword}%')
                ))

        stmt = stmt.group_by(ArtworkCollectionOrm.rating)
        session_result = await self.db_session.execute(stmt)

        result = {}
        for k, v in session_result.all():
            match k:
                case 0:
                    result.update({'general': v})
                case 1:
                    result.update({'sensitive': v})
                case 2:
                    result.update({'questionable': v})
                case 3:
                    result.update({'explicit': v})
                case _:
                    result.update({'unknown': v})

        return ArtworkRatingStatistic.model_validate(result)

    async def query_user_all(
            self,
            origin: str | None = None,
            uid: str | None = None,
            uname: str | None = None
    ) -> list[ArtworkCollection]:
        """通过 uid 或用户名精准查找用户所有作品"""
        if uid is None and uname is None:
            raise ValueError('need at least one of the uid and uname parameters')

        stmt = select(ArtworkCollectionOrm)
        if origin is not None:
            stmt = stmt.where(ArtworkCollectionOrm.origin == origin)
        if uid:
            stmt = stmt.where(ArtworkCollectionOrm.uid == uid)
        if uname:
            stmt = stmt.where(ArtworkCollectionOrm.uname == uname)
        stmt = stmt.order_by(desc(ArtworkCollectionOrm.aid))

        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[ArtworkCollection], session_result.scalars().all())

    async def query_user_all_aids(
            self,
            origin: str | None = None,
            uid: str | None = None,
            uname: str | None = None
    ) -> list[str]:
        """通过 uid 或用户名精准查找用户所有作品的 artwork_id"""
        if uid is None and uname is None:
            raise ValueError('need at least one of the uid and uname parameters')

        stmt = select(ArtworkCollectionOrm.aid)
        if origin is not None:
            stmt = stmt.where(ArtworkCollectionOrm.origin == origin)
        if uid:
            stmt = stmt.where(ArtworkCollectionOrm.uid == uid)
        if uname:
            stmt = stmt.where(ArtworkCollectionOrm.uname == uname)
        stmt = stmt.order_by(desc(ArtworkCollectionOrm.aid))

        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[str], session_result.scalars().all())

    async def query_exists_aids(
            self,
            origin: str | None,
            aids: Sequence[str],
            *,
            filter_classification: int | None = None,
            filter_rating: int | None = None,
    ) -> list[str]:
        """根据提供的 aids 列表查询数据库中已存在的列表中的 aid

        :param origin: 指定作品源
        :param aids: 待匹配的作品 artwork_id 清单
        :param filter_classification: 筛选指定的作品分类, 只有该分类的作品都会被视为存在
        :param filter_rating: 筛选指定的作品分级, 只有该分级的作品都会被视为存在
        :return: 数据库中已存在的, 匹配提供的作品清单的 artwork_id 列表
        """
        stmt = select(ArtworkCollectionOrm.aid)
        if origin is not None:
            stmt = stmt.where(ArtworkCollectionOrm.origin == origin)
        if filter_classification is not None:
            stmt = stmt.where(ArtworkCollectionOrm.classification == filter_classification)
        if filter_rating is not None:
            stmt = stmt.where(ArtworkCollectionOrm.rating == filter_rating)
        stmt = stmt.where(ArtworkCollectionOrm.aid.in_(aids)).order_by(desc(ArtworkCollectionOrm.aid))

        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[str], session_result.scalars().all())

    async def query_not_exists_aids(
            self,
            origin: str | None,
            aids: Sequence[str],
            *,
            exclude_classification: int | None = None,
            exclude_rating: int | None = None,
    ) -> list[str]:
        """根据提供的 aids 列表查询数据库中不存在的列表中的 aid

        :param origin: 指定作品源
        :param aids: 待匹配的作品 artwork_id 清单
        :param exclude_classification: 排除指定的作品分类, 所有非该分类的作品都会被视为不存在
        :param exclude_rating: 排除指定的作品分级, 所有非该分级的作品都会被视为不存在
        :return: 数据库中不存在的, 匹配提供的作品清单的 artwork_id 列表
        """
        exists_aids = await self.query_exists_aids(
            origin=origin, aids=aids, filter_classification=exclude_classification, filter_rating=exclude_rating
        )
        return sorted(list(set(aids) - set(exists_aids)), reverse=True)

    async def query_all(self) -> list[ArtworkCollection]:
        raise NotImplementedError

    async def add(
            self,
            origin: str,
            aid: str,
            title: str,
            uid: str,
            uname: str,
            classification: int,
            rating: int,
            width: int,
            height: int,
            tags: str,
            source: str,
            cover_page: str,
            description: str | None = None,
    ) -> None:
        new_obj = ArtworkCollectionOrm(origin=origin, aid=aid, title=title, uid=uid, uname=uname,
                                       classification=classification, rating=rating,
                                       width=width, height=height,
                                       tags=tags[:4096], source=source, cover_page=cover_page,
                                       description=description if description is None else description[:4096],
                                       created_at=datetime.now())
        await self._add(new_obj)

    async def upsert(
            self,
            origin: str,
            aid: str,
            title: str,
            uid: str,
            uname: str,
            classification: int,
            rating: int,
            width: int,
            height: int,
            tags: str,
            source: str,
            cover_page: str,
            description: str | None = None,
    ) -> None:
        new_obj = ArtworkCollectionOrm(origin=origin, aid=aid, title=title, uid=uid, uname=uname,
                                       classification=classification, rating=rating,
                                       width=width, height=height,
                                       tags=tags[:4096], source=source, cover_page=cover_page,
                                       description=description if description is None else description[:4096],
                                       updated_at=datetime.now())
        await self._merge(new_obj)

    async def update(
            self,
            origin: str,
            aid: str,
            *,
            title: str | None = None,
            uid: str | None = None,
            uname: str | None = None,
            classification: int | None = None,
            rating: int | None = None,
            width: int | None = None,
            height: int | None = None,
            tags: str | None = None,
            source: str | None = None,
            cover_page: str | None = None,
            description: str | None = None,
    ) -> None:
        stmt = (update(ArtworkCollectionOrm)
                .where(ArtworkCollectionOrm.origin == origin)
                .where(ArtworkCollectionOrm.aid == aid))
        if title is not None:
            stmt = stmt.values(title=title)
        if uid is not None:
            stmt = stmt.values(uid=uid)
        if uname is not None:
            stmt = stmt.values(uname=uname)
        if classification is not None:
            stmt = stmt.values(classification=classification)
        if rating is not None:
            stmt = stmt.values(rating=rating)
        if width is not None:
            stmt = stmt.values(width=width)
        if height is not None:
            stmt = stmt.values(height=height)
        if tags is not None:
            stmt = stmt.values(tags=tags[:4096])
        if source is not None:
            stmt = stmt.values(source=source)
        if cover_page is not None:
            stmt = stmt.values(cover_page=cover_page)
        if description is not None:
            stmt = stmt.values(description=description[:4096])
        stmt = stmt.values(updated_at=datetime.now())
        stmt.execution_options(synchronize_session='fetch')
        await self.db_session.execute(stmt)

    async def delete(self, origin: str, aid: str) -> None:
        stmt = (delete(ArtworkCollectionOrm)
                .where(ArtworkCollectionOrm.origin == origin)
                .where(ArtworkCollectionOrm.aid == aid))
        stmt.execution_options(synchronize_session='fetch')
        await self.db_session.execute(stmt)


__all__ = [
    'ArtworkCollection',
    'ArtworkCollectionDAL',
    'ArtworkClassificationStatistic',
    'ArtworkRatingStatistic',
]
