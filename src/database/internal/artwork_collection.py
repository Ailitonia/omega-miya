"""
@Author         : Ailitonia
@Date           : 2022/12/04 17:40
@FileName       : artwork_collection.py
@Project        : nonebot2_miya 
@Description    : ArtworkCollection DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime
from typing import Literal, Optional, Sequence

from pydantic import BaseModel, ConfigDict
from sqlalchemy import update, delete, desc, or_, and_
from sqlalchemy.future import select
from sqlalchemy.sql.expression import func

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayerModel
from ..schema import ArtworkCollectionOrm


class ArtworkCollection(BaseModel):
    """图库作品 Model"""
    id: int
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
    description: Optional[str] = None
    source: str
    cover_page: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(extra='ignore', from_attributes=True, frozen=True)


class ArtworkClassificationStatistic(BaseModel):
    """分类统计信息查询结果"""
    unknown: int = 0
    unclassified: int = 0
    ai_generated: int = 0
    automatic: int = 0
    confirmed: int = 0

    model_config = ConfigDict(extra='ignore', frozen=True)

    @property
    def total(self) -> int:
        return self.unknown + self.unclassified + self.ai_generated + self.automatic + self.confirmed


class ArtworkRatingStatistic(BaseModel):
    """分级统计信息查询结果"""
    unknown: int = 0
    general: int = 0
    sensitive: int = 0
    questionable: int = 0
    explicit: int = 0

    model_config = ConfigDict(extra='ignore', frozen=True)

    @property
    def total(self) -> int:
        return self.unknown + self.general + self.sensitive + self.questionable + self.explicit


class ArtworkCollectionDAL(BaseDataAccessLayerModel):
    """图库作品 数据库操作对象"""

    async def query_unique(self, origin: str, aid: str) -> ArtworkCollection:
        stmt = (select(ArtworkCollectionOrm).
                where(ArtworkCollectionOrm.origin == origin).
                where(ArtworkCollectionOrm.aid == aid))
        session_result = await self.db_session.execute(stmt)
        return ArtworkCollection.model_validate(session_result.scalar_one())

    async def query_by_condition(
            self,
            origin: Optional[str | Sequence[str]],
            keywords: Optional[Sequence[str]],
            num: int = 3,
            *,
            classification_min: int = 2,
            classification_max: int = 3,
            rating_min: int = 0,
            rating_max: int = 0,
            acc_mode: bool = False,
            ratio: Optional[int] = None,
            order_mode: Literal['random', 'aid', 'aid_desc', 'create_time', 'create_time_desc'] = 'random'
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
            case 'random':
                stmt = stmt.order_by(func.random())
            case 'aid':
                stmt = stmt.order_by(ArtworkCollectionOrm.aid)
            case 'aid_desc':
                stmt = stmt.order_by(desc(ArtworkCollectionOrm.aid))
            case 'create_time':
                stmt = stmt.order_by(ArtworkCollectionOrm.created_at)
            case 'create_time_desc':
                stmt = stmt.order_by(desc(ArtworkCollectionOrm.created_at))

        # 结果数量限制
        if num is None:
            pass
        else:
            stmt = stmt.limit(num)

        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[ArtworkCollection], session_result.scalars().all())

    async def query_classification_statistic(
            self,
            origin: Optional[str] = None,
            keywords: Optional[Sequence[str]] = None
    ) -> ArtworkClassificationStatistic:
        """按分类统计收录作品数"""
        stmt = select(ArtworkCollectionOrm.classification, func.count(ArtworkCollectionOrm.id))

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
                    result.update({'unknown': v})

        return ArtworkClassificationStatistic.model_validate(result)

    async def query_rating_statistic(
            self,
            origin: Optional[str] = None,
            keywords: Optional[Sequence[str]] = None
    ) -> ArtworkRatingStatistic:
        """按分级统计收录作品数"""
        stmt = select(ArtworkCollectionOrm.rating, func.count(ArtworkCollectionOrm.id))

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
            origin: Optional[str] = None,
            uid: Optional[str] = None,
            uname: Optional[str] = None
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
            origin: Optional[str] = None,
            uid: Optional[str] = None,
            uname: Optional[str] = None
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

    async def query_exists_aids(self, origin: Optional[str], aids: Sequence[str]) -> list[str]:
        """根据提供的 aids 列表查询数据库中已存在的列表中的 aid"""
        stmt = select(ArtworkCollectionOrm.aid)
        if origin is not None:
            stmt = stmt.where(ArtworkCollectionOrm.origin == origin)
        stmt = stmt.where(ArtworkCollectionOrm.aid.in_(aids)).order_by(desc(ArtworkCollectionOrm.aid))

        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[str], session_result.scalars().all())

    async def query_not_exists_aids(self, origin: Optional[str], aids: Sequence[str]) -> list[str]:
        """根据提供的 aids 列表查询数据库中不存在的列表中的 aid"""
        exists_aids = await self.query_exists_aids(origin=origin, aids=aids)
        return sorted(list(set(aids) - set(exists_aids)), reverse=True)

    async def query_all(self) -> list[ArtworkCollection]:
        raise NotImplementedError('method not supported')

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
            description: Optional[str] = None,
    ) -> None:
        new_obj = ArtworkCollectionOrm(
            origin=origin, aid=aid, title=title, uid=uid, uname=uname,
            classification=classification, rating=rating, width=width, height=height,
            tags=tags[:2048], source=source, cover_page=cover_page,
            description=description if description is None else description[:2048],
            created_at=datetime.now()
        )
        self.db_session.add(new_obj)
        await self.db_session.flush()

    async def update(
            self,
            id_: int,
            *,
            origin: Optional[str] = None,
            aid: Optional[str] = None,
            title: Optional[str] = None,
            uid: Optional[str] = None,
            uname: Optional[str] = None,
            classification: Optional[int] = None,
            rating: Optional[int] = None,
            width: Optional[int] = None,
            height: Optional[int] = None,
            tags: Optional[str] = None,
            source: Optional[str] = None,
            cover_page: Optional[str] = None,
            description: Optional[str] = None,
    ) -> None:
        stmt = update(ArtworkCollectionOrm).where(ArtworkCollectionOrm.id == id_)
        if origin is not None:
            stmt = stmt.values(origin=origin)
        if aid is not None:
            stmt = stmt.values(aid=aid)
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
            stmt = stmt.values(tags=tags[:2048])
        if source is not None:
            stmt = stmt.values(source=source)
        if cover_page is not None:
            stmt = stmt.values(cover_page=cover_page)
        if description is not None:
            stmt = stmt.values(description=description[:2048])
        stmt = stmt.values(updated_at=datetime.now())
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)

    async def delete(self, id_: int) -> None:
        stmt = delete(ArtworkCollectionOrm).where(ArtworkCollectionOrm.id == id_)
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)


__all__ = [
    'ArtworkCollection',
    'ArtworkCollectionDAL',
    'ArtworkClassificationStatistic',
    'ArtworkRatingStatistic',
]
