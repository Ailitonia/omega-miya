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
from typing import Annotated, Callable, Literal

from pydantic import Field
from sqlalchemy import and_, delete, desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayer, BaseDataOutModel
from ..schema import ArtworkCollectionOrm, ArtworkReviewRecordsOrm, ArtworkTagOrm, ArtworkWithTagsOrm


class Artwork(BaseDataOutModel):
    """图库作品数据"""
    id: int
    origin: str
    aid: str
    uid: str
    title: str
    uname: str
    classification: int
    rating: int
    width: int
    height: int
    orientation: int
    url: str
    source: str | None
    cover_page: str | None
    raw_tags: str | None
    description: str | None
    published_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None
    tags_name_artwork_had: Annotated[list['ArtworkTag'], Field(default_factory=list)]


class ArtworkReviewRecord(BaseDataOutModel):
    """图库作品评审记录数据"""
    id: int
    artwork_index_id: int
    review_timestamp: int
    review_classification: int
    review_rating: int
    review_from: str
    review_info: str
    created_at: datetime | None
    updated_at: datetime | None
    review_record_parent_artwork: Artwork


class ArtworkTag(BaseDataOutModel):
    """图库作品标签数据"""
    id: int
    tag_name: str
    tag_alt_name: str | None
    created_at: datetime | None
    updated_at: datetime | None


class ArtworkClassificationStatistic(BaseDataOutModel):
    """图库作品分类统计信息查询结果"""
    unused: Annotated[int, Field(default=0)]
    unclassified: Annotated[int, Field(default=0)]
    ai_generated: Annotated[int, Field(default=0)]
    automatic: Annotated[int, Field(default=0)]
    confirmed: Annotated[int, Field(default=0)]

    @property
    def total(self) -> int:
        return self.unused + self.unclassified + self.ai_generated + self.automatic + self.confirmed


class ArtworkRatingStatistic(BaseDataOutModel):
    """图库作品分级统计信息查询结果"""
    unknown: Annotated[int, Field(default=0)]
    general: Annotated[int, Field(default=0)]
    sensitive: Annotated[int, Field(default=0)]
    questionable: Annotated[int, Field(default=0)]
    explicit: Annotated[int, Field(default=0)]

    @property
    def total(self) -> int:
        return self.unknown + self.general + self.sensitive + self.questionable + self.explicit


class ArtworkCollectionDAL(BaseDataAccessLayer[ArtworkCollectionOrm, Artwork]):
    """图库作品 数据库操作对象"""

    async def _count_all(self) -> int:
        """查询全表行数"""
        stmt = select(func.count()).select_from(ArtworkCollectionOrm)
        return (await self.db_session.execute(stmt)).scalar_one()

    async def _clear_all(self) -> None:
        """清空全表, 敏感操作, 方法内不执行 commit, 可由外层事务 rollback"""
        await self.db_session.execute(delete(ArtworkCollectionOrm))
        self.db_session.expunge_all()

    async def _select_unique(
            self,
            origin: str,
            aid: str,
            *,
            populate_existing: bool = False,
            with_for_update: bool = False,
            nowait_for_update: bool = False,
    ) -> ArtworkCollectionOrm:
        stmt = (select(ArtworkCollectionOrm)
                .options(selectinload(ArtworkCollectionOrm.tags_name_artwork_had))
                .where(ArtworkCollectionOrm.origin == origin)
                .where(ArtworkCollectionOrm.aid == aid))

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        if with_for_update:
            stmt = stmt.with_for_update(nowait=nowait_for_update)

        return (await self.db_session.execute(stmt)).scalar_one()

    async def query_unique(
            self,
            origin: str,
            aid: str,
            *,
            populate_existing: bool = False,
    ) -> Artwork:
        item = await self._select_unique(
            origin,
            aid,
            populate_existing=populate_existing,
        )
        return Artwork.model_validate(item)

    async def query_by_condition(
            self,
            origin: str | Sequence[str] | None,
            keywords: Sequence[str] | None,
            page: int = 1,
            size: int = 3,
            *,
            classification_min: int = 2,
            classification_max: int = 3,
            rating_min: int = 0,
            rating_max: int = 0,
            acc_mode: bool = False,
            ratio: int | None = None,
            order_mode: Literal['random', 'latest', 'aid', 'aid_desc'] = 'random',
    ) -> list[Artwork]:
        """按条件搜索图库收录作品

        :param origin: 作品来源
        :param keywords: 关键词列表
        :param page: 分页
        :param size: 每页数量
        :param classification_min: 分类标签最小值
        :param classification_max: 分类标签最大值
        :param rating_min: 分级标签最小值
        :param rating_max: 分级标签最大值
        :param acc_mode: 是否启用精确搜索模式
        :param ratio: 图片长宽, 1: 横图, 0: 方图, -1: 竖图
        :param order_mode: 排序模式
        """
        if classification_min > classification_max:
            raise ValueError('classification_min must be less than classification_max')

        if rating_min > rating_max:
            raise ValueError('rating_min must be less than rating_max')

        conditions = []
        # 根据 acc_mode 构造关键词查询语句
        if (keywords is None) or (not keywords):
            # 无关键词则随机
            pass
        elif acc_mode:
            # 精确搜索标题, 用户, tag
            for keyword in keywords:
                conditions.append(func.find_in_set(keyword, ArtworkCollectionOrm.title))
                conditions.append(func.find_in_set(keyword, ArtworkCollectionOrm.uname))
                conditions.append(func.find_in_set(keyword, ArtworkTagOrm.tag_name))
        else:
            # 模糊搜索标题, 用户, tag
            for keyword in keywords:
                conditions.append(ArtworkCollectionOrm.title.ilike(f'%{self._escape_like(keyword)}%', escape="\\"))
                conditions.append(ArtworkCollectionOrm.uname.ilike(f'%{self._escape_like(keyword)}%', escape="\\"))
                conditions.append(ArtworkTagOrm.tag_name.ilike(f'%{self._escape_like(keyword)}%', escape="\\"))

        stmt = select(ArtworkCollectionOrm)

        if origin is None:
            # 匹配所有来源
            pass
        elif isinstance(origin, str):
            # 匹配单一来源
            stmt = stmt.where(ArtworkCollectionOrm.origin == origin)
        else:
            # 匹配多个来源
            stmt = stmt.where(or_(*(ArtworkCollectionOrm.origin == x for x in origin)))

        # classification 条件
        stmt = stmt.where(and_(
            ArtworkCollectionOrm.classification >= classification_min,
            ArtworkCollectionOrm.classification <= classification_max
        ))
        # rating 条件
        stmt = stmt.where(and_(
            ArtworkCollectionOrm.rating >= rating_min,
            ArtworkCollectionOrm.rating <= rating_max
        ))

        # 根据 ratio 构造图片长宽类型查询语句
        if ratio is not None:
            stmt = stmt.where(ArtworkCollectionOrm.orientation == ratio)

        # 添加搜索条件并加载级联
        stmt = stmt.where(or_(*conditions)).options(selectinload(ArtworkCollectionOrm.tags_name_artwork_had))

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
        stmt = stmt.limit(size).offset((page - 1) * size)

        return parse_obj_as(list[Artwork], (await self.db_session.execute(stmt)).scalars().all())

    async def query_classification_statistic(
            self,
            origin: str | Sequence[str] | None,
            keywords: Sequence[str] | None = None,
    ) -> ArtworkClassificationStatistic:
        """按分类统计收录作品数"""

        conditions = []
        if (keywords is None) or (not keywords):
            pass
        else:
            # 模糊搜索标题, 用户, tag
            for keyword in keywords:
                conditions.append(ArtworkCollectionOrm.title.ilike(f'%{self._escape_like(keyword)}%', escape="\\"))
                conditions.append(ArtworkCollectionOrm.uname.ilike(f'%{self._escape_like(keyword)}%', escape="\\"))
                conditions.append(ArtworkTagOrm.tag_name.ilike(f'%{self._escape_like(keyword)}%', escape="\\"))

        stmt = select(ArtworkCollectionOrm.classification, func.count(ArtworkCollectionOrm.aid))

        if origin is None:
            # 匹配所有来源
            pass
        elif isinstance(origin, str):
            # 匹配单一来源
            stmt = stmt.where(ArtworkCollectionOrm.origin == origin)
        else:
            # 匹配多个来源
            stmt = stmt.where(or_(*(ArtworkCollectionOrm.origin == x for x in origin)))

        # 添加搜索条件并加载级联
        stmt = (stmt
                .where(or_(*conditions))
                .options(selectinload(ArtworkCollectionOrm.tags_name_artwork_had))
                .group_by(ArtworkCollectionOrm.classification))

        session_result = await self.db_session.execute(stmt)

        result = {}
        for classification, count_num in session_result.all():
            match classification:
                case 0:
                    result['unclassified'] = count_num
                case 1:
                    result['ai_generated'] = count_num
                case 2:
                    result['automatic'] = count_num
                case 3:
                    result['confirmed'] = count_num
                case _:
                    result['unused'] = count_num

        return ArtworkClassificationStatistic.model_validate(result)

    async def query_rating_statistic(
            self,
            origin: str | Sequence[str] | None,
            keywords: Sequence[str] | None = None,
    ) -> ArtworkRatingStatistic:
        """按分级统计收录作品数"""

        conditions = []
        if (keywords is None) or (not keywords):
            pass
        else:
            # 模糊搜索标题, 用户, tag
            for keyword in keywords:
                conditions.append(ArtworkCollectionOrm.title.ilike(f'%{self._escape_like(keyword)}%', escape="\\"))
                conditions.append(ArtworkCollectionOrm.uname.ilike(f'%{self._escape_like(keyword)}%', escape="\\"))
                conditions.append(ArtworkTagOrm.tag_name.ilike(f'%{self._escape_like(keyword)}%', escape="\\"))

        stmt = select(ArtworkCollectionOrm.rating, func.count(ArtworkCollectionOrm.aid))

        if origin is None:
            # 匹配所有来源
            pass
        elif isinstance(origin, str):
            # 匹配单一来源
            stmt = stmt.where(ArtworkCollectionOrm.origin == origin)
        else:
            # 匹配多个来源
            stmt = stmt.where(or_(*(ArtworkCollectionOrm.origin == x for x in origin)))

        # 添加搜索条件并加载级联
        stmt = (stmt
                .where(or_(*conditions))
                .options(selectinload(ArtworkCollectionOrm.tags_name_artwork_had))
                .group_by(ArtworkCollectionOrm.rating))

        session_result = await self.db_session.execute(stmt)

        result = {}
        for rating, count_num in session_result.all():
            match rating:
                case 0:
                    result['general'] = count_num
                case 1:
                    result['sensitive'] = count_num
                case 2:
                    result['questionable'] = count_num
                case 3:
                    result['explicit'] = count_num
                case _:
                    result['unknown'] = count_num

        return ArtworkRatingStatistic.model_validate(result)

    async def query_user_all_artworks(
            self,
            origin: str | Sequence[str] | None,
            uid: str | None = None,
            uname: str | None = None,
    ) -> list[Artwork]:
        """通过 uid 或用户名精准查找用户所有作品"""
        if uid is None and uname is None:
            raise ValueError('need at least one of the uid and uname parameters')

        stmt = select(ArtworkCollectionOrm)

        if origin is None:
            # 匹配所有来源
            pass
        elif isinstance(origin, str):
            # 匹配单一来源
            stmt = stmt.where(ArtworkCollectionOrm.origin == origin)
        else:
            # 匹配多个来源
            stmt = stmt.where(or_(*(ArtworkCollectionOrm.origin == x for x in origin)))

        if uid:
            stmt = stmt.where(ArtworkCollectionOrm.uid == uid)
        if uname:
            stmt = stmt.where(ArtworkCollectionOrm.uname == uname)

        # 添加搜索条件并加载级联
        stmt = (stmt
                .options(selectinload(ArtworkCollectionOrm.tags_name_artwork_had))
                .order_by(desc(ArtworkCollectionOrm.aid)))

        return parse_obj_as(list[Artwork], (await self.db_session.execute(stmt)).scalars().all())

    async def query_user_all_aids(
            self,
            origin: str | Sequence[str] | None,
            uid: str | None = None,
            uname: str | None = None
    ) -> list[str]:
        """通过 uid 或用户名精准查找用户所有作品的 artwork_id"""
        if uid is None and uname is None:
            raise ValueError('need at least one of the uid and uname parameters')

        stmt = select(ArtworkCollectionOrm.aid)

        if origin is None:
            # 匹配所有来源
            pass
        elif isinstance(origin, str):
            # 匹配单一来源
            stmt = stmt.where(ArtworkCollectionOrm.origin == origin)
        else:
            # 匹配多个来源
            stmt = stmt.where(or_(*(ArtworkCollectionOrm.origin == x for x in origin)))

        if uid:
            stmt = stmt.where(ArtworkCollectionOrm.uid == uid)
        if uname:
            stmt = stmt.where(ArtworkCollectionOrm.uname == uname)

        stmt = stmt.order_by(desc(ArtworkCollectionOrm.aid))

        return parse_obj_as(list[str], (await self.db_session.execute(stmt)).scalars().all())

    async def query_exists_aids(
            self,
            origin: str | Sequence[str] | None,
            aids: Sequence[str],
            *,
            filter_classification: int | None = None,
            filter_rating: int | None = None,
    ) -> list[str]:
        """根据提供的 artwork_id 列表查询数据库中已存在的列表中的 artwork_id

        :param origin: 指定作品源
        :param aids: 待匹配的作品 artwork_id 清单
        :param filter_classification: 筛选指定的作品分类, 只有该分类的作品都会被视为存在
        :param filter_rating: 筛选指定的作品分级, 只有该分级的作品都会被视为存在
        :return: 数据库中已存在的, 匹配提供的作品清单的 artwork_id 列表
        """
        stmt = select(ArtworkCollectionOrm.aid)

        if origin is None:
            # 匹配所有来源
            pass
        elif isinstance(origin, str):
            # 匹配单一来源
            stmt = stmt.where(ArtworkCollectionOrm.origin == origin)
        else:
            # 匹配多个来源
            stmt = stmt.where(or_(*(ArtworkCollectionOrm.origin == x for x in origin)))

        if filter_classification is not None:
            stmt = stmt.where(ArtworkCollectionOrm.classification == filter_classification)
        if filter_rating is not None:
            stmt = stmt.where(ArtworkCollectionOrm.rating == filter_rating)

        stmt = stmt.where(ArtworkCollectionOrm.aid.in_(aids)).order_by(desc(ArtworkCollectionOrm.aid))

        return parse_obj_as(list[str], (await self.db_session.execute(stmt)).scalars().all())

    async def query_not_exists_aids(
            self,
            origin: str | Sequence[str] | None,
            aids: Sequence[str],
            *,
            exclude_classification: int | None = None,
            exclude_rating: int | None = None,
    ) -> list[str]:
        """根据提供的 artwork_id 列表查询数据库中不存在的列表中的 artwork_id

        :param origin: 指定作品源
        :param aids: 待匹配的作品 artwork_id 清单
        :param exclude_classification: 排除指定的作品分类, 所有非该分类的作品都会被视为不存在
        :param exclude_rating: 排除指定的作品分级, 所有非该分级的作品都会被视为不存在
        :return: 数据库中不存在的, 匹配提供的作品清单的 artwork_id 列表
        """
        exists_aids = await self.query_exists_aids(
            origin=origin, aids=aids, filter_classification=exclude_classification, filter_rating=exclude_rating
        )
        return sorted(set(aids) - set(exists_aids), reverse=True)

    @staticmethod
    async def _add_artwork(
            session: AsyncSession,
            origin: str,
            aid: str,
            uid: str,
            title: str,
            uname: str,
            classification: int,
            rating: int,
            width: int,
            height: int,
            url: str,
            source: str | None = None,
            cover_page: str | None = None,
            raw_tags: str | None = None,
            description: str | None = None,
            published_at: datetime | None = None,
    ) -> ArtworkCollectionOrm:
        """内部方法, 向数据库插入新行, 不校验唯一性

        尽量保证插入的是新数据时才使用, 冲突直接抛出异常
        """
        if width > height:
            orientation = 1
        elif width < height:
            orientation = -1
        else:
            orientation = 0

        new_obj = ArtworkCollectionOrm(
            origin=origin,
            aid=aid,
            uid=uid,
            title=title,
            uname=uname,
            classification=classification,
            rating=rating,
            width=width,
            height=height,
            orientation=orientation,
            url=url,
            source=source,
            cover_page=cover_page,
            raw_tags=raw_tags,
            description=description,
            published_at=published_at,
        )
        session.add(new_obj)
        await session.flush()
        await session.refresh(new_obj)
        return new_obj

    @staticmethod
    async def _add_artwork_tag_update_exist_nested(
            session: AsyncSession,
            tag_name: str,
            tag_alt_name: str | None = None,
    ) -> ArtworkTagOrm:
        """内部方法, 开启嵌套事务, 向数据库插入新行, 存在则忽略"""
        new_obj = ArtworkTagOrm(tag_name=tag_name, tag_alt_name=tag_alt_name)
        try:
            async with session.begin_nested():
                session.add(new_obj)
                await session.flush()
            await session.refresh(new_obj)
            return new_obj
        except IntegrityError:
            # 把插入失败的对象移出会话, 避免意外影响
            if new_obj in session:
                session.expunge(new_obj)
            async with session.begin_nested():
                stmt = select(ArtworkTagOrm).where(ArtworkTagOrm.tag_name == tag_name)
                exist_obj = (await session.execute(stmt)).scalar_one()
                if tag_alt_name is not None:
                    exist_obj.tag_alt_name = tag_alt_name
                    await session.flush()
                    await session.refresh(exist_obj)
            return exist_obj

    @staticmethod
    async def _add_artwork_with_tag(
            session: AsyncSession,
            artwork_index_id: int,
            tag_index_id: int,
    ) -> ArtworkWithTagsOrm:
        new_obj = ArtworkWithTagsOrm(
            artwork_index_id=artwork_index_id,
            tag_index_id=tag_index_id,
        )
        await session.flush()
        await session.refresh(new_obj)
        return new_obj

    @staticmethod
    async def _select_artwork_unique_nested(
            session: AsyncSession,
            origin: str,
            aid: str,
            *,
            populate_existing: bool = False,
            with_for_update: bool = False,
            nowait_for_update: bool = False,
    ) -> ArtworkCollectionOrm:
        """内部方法, 在嵌套事务中使用, 查询作品行, 不存在直接抛出异常"""
        stmt = (select(ArtworkCollectionOrm)
                .options(selectinload(ArtworkCollectionOrm.tags_name_artwork_had))
                .where(ArtworkCollectionOrm.origin == origin)
                .where(ArtworkCollectionOrm.aid == aid))

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        if with_for_update:
            stmt = stmt.with_for_update(nowait=nowait_for_update)

        return (await session.execute(stmt)).scalar_one()

    async def add_artwork_update_exist(
            self,
            origin: str,
            aid: str,
            uid: str,
            title: str,
            uname: str,
            classification: int,
            rating: int,
            width: int,
            height: int,
            url: str,
            source: str | None = None,
            cover_page: str | None = None,
            raw_tags: str | None = None,
            tag_handler: Callable[[str], list[tuple[str, str | None]]] | None = None,
            description: str | None = None,
            published_at: datetime | None = None,
    ) -> Artwork:
        """向数据库新增该作品信息, 若已存在则更新

        同一事务中处理 tag 表及 tag 关联表插入, 确保并发与原子性
        """

        # 处理标签
        if raw_tags is None:
            tag_list: list[tuple[str, str | None]] = []
        elif tag_handler is not None:
            tag_list = tag_handler(raw_tags)
        else:
            tag_list = [(tag.strip().lower(), None) for tag in raw_tags.strip().split(',')]

        # 单事务处理作品表及标签表插入
        async with self.safe_begin_transaction() as session:
            # 先处理标签插入
            tags_item: list[ArtworkTagOrm] = []
            for tag_name, tag_alt_name in tag_list:
                tags_item.append(await self._add_artwork_tag_update_exist_nested(session, tag_name, tag_alt_name))

            try:
                # 处理作品插入
                async with self.must_begin_nested_in_transaction() as artwork_session:
                    artwork_item = await self._add_artwork(
                        session=artwork_session,
                        origin=origin,
                        aid=aid,
                        uid=uid,
                        title=title,
                        uname=uname,
                        classification=classification,
                        rating=rating,
                        width=width,
                        height=height,
                        url=url,
                        source=source,
                        cover_page=cover_page,
                        raw_tags=raw_tags,
                        description=description,
                        published_at=published_at,
                    )
                    # 这里插入成功说明是新条目, 继续插入关联表
                    for tag_item in tags_item:
                        await self._add_artwork_with_tag(artwork_session, artwork_item.id, tag_item.id)
            except IntegrityError:
                # 插入失败说明是已存在的条目, 更新信息
                artwork_item = await self._select_artwork_unique_nested(
                    session=session,
                    origin=origin,
                    aid=aid,
                )
                artwork_item.uid = uid
                artwork_item.title = title
                artwork_item.uname = uname
                artwork_item.classification = classification
                artwork_item.rating = rating
                artwork_item.width = width
                artwork_item.height = height
                if width > height:
                    artwork_item.orientation = 1
                elif width < height:
                    artwork_item.orientation = -1
                else:
                    artwork_item.orientation = 0
                if source is not None:
                    artwork_item.source = source
                if cover_page is not None:
                    artwork_item.cover_page = cover_page
                if raw_tags is not None:
                    artwork_item.raw_tags = raw_tags
                if description is not None:
                    artwork_item.description = description
                if published_at is not None:
                    artwork_item.published_at = published_at
                await session.flush()
        await self.db_session.refresh(artwork_item)
        return Artwork.model_validate(artwork_item)

    async def add_artwork_ignore_exist(
            self,
            origin: str,
            aid: str,
            uid: str,
            title: str,
            uname: str,
            classification: int,
            rating: int,
            width: int,
            height: int,
            url: str,
            source: str | None = None,
            cover_page: str | None = None,
            raw_tags: str | None = None,
            tag_handler: Callable[[str], list[tuple[str, str | None]]] | None = None,
            description: str | None = None,
            published_at: datetime | None = None,
    ) -> Artwork:
        """向数据库新增该作品信息, 若已存在则忽略

        同一事务中处理 tag 表及 tag 关联表插入, 确保并发与原子性
        """

        # 处理标签
        if raw_tags is None:
            tag_list: list[tuple[str, str | None]] = []
        elif tag_handler is not None:
            tag_list = tag_handler(raw_tags)
        else:
            tag_list = [(tag.strip().lower(), None) for tag in raw_tags.strip().split(',')]

        # 单事务处理作品表及标签表插入
        async with self.safe_begin_transaction() as session:
            # 先处理标签插入
            tags_item: list[ArtworkTagOrm] = []
            for tag_name, tag_alt_name in tag_list:
                tags_item.append(await self._add_artwork_tag_update_exist_nested(session, tag_name, tag_alt_name))

            try:
                # 处理作品插入
                async with self.must_begin_nested_in_transaction() as artwork_session:
                    artwork_item = await self._add_artwork(
                        session=artwork_session,
                        origin=origin,
                        aid=aid,
                        uid=uid,
                        title=title,
                        uname=uname,
                        classification=classification,
                        rating=rating,
                        width=width,
                        height=height,
                        url=url,
                        source=source,
                        cover_page=cover_page,
                        raw_tags=raw_tags,
                        description=description,
                        published_at=published_at,
                    )
                    # 这里插入成功说明是新条目, 继续插入关联表
                    for tag_item in tags_item:
                        await self._add_artwork_with_tag(artwork_session, artwork_item.id, tag_item.id)
            except IntegrityError:
                # 插入失败说明是已存在的条目, 获取已有条目信息
                artwork_item = await self._select_artwork_unique_nested(
                    session=session,
                    origin=origin,
                    aid=aid,
                )
        await self.db_session.refresh(artwork_item)
        return Artwork.model_validate(artwork_item)

    @staticmethod
    async def _add_artwork_review_record(
            session: AsyncSession,
            artwork_index_id: int,
            review_timestamp: int,
            review_classification: int,
            review_rating: int,
            review_from: str,
            review_info: str,
    ) -> ArtworkReviewRecordsOrm:
        """内部方法, 向数据库插入新行, 不校验唯一性

        尽量保证插入的是新数据时才使用, 冲突直接抛出异常
        """
        new_obj = ArtworkReviewRecordsOrm(
            artwork_index_id=artwork_index_id,
            review_timestamp=review_timestamp,
            review_classification=review_classification,
            review_rating=review_rating,
            review_from=review_from,
            review_info=review_info,
        )
        await session.flush()
        await session.refresh(new_obj)
        return new_obj

    async def add_artwork_review_record(
            self,
            origin: str,
            aid: str,
            review_timestamp: int,
            review_classification: int,
            review_rating: int,
            review_from: str,
            review_info: str,
    ) -> ArtworkReviewRecord:
        """向数据库插入新行, 不校验唯一性

        如果作品不存在直接抛出异常
        """
        artwork_item = await self._select_unique(origin, aid)
        new_obj = ArtworkReviewRecordsOrm(
            artwork_index_id=artwork_item.id,
            review_timestamp=review_timestamp,
            review_classification=review_classification,
            review_rating=review_rating,
            review_from=review_from,
            review_info=review_info,
        )
        self.db_session.add(new_obj)
        await self.db_session.flush()
        await self.db_session.refresh(new_obj)
        return ArtworkReviewRecord.model_validate(new_obj)

    async def delete(self, origin: str, aid: str) -> None:
        stmt = (delete(ArtworkCollectionOrm)
                .where(ArtworkCollectionOrm.origin == origin)
                .where(ArtworkCollectionOrm.aid == aid))
        await self.db_session.execute(stmt)


__all__ = [
    'Artwork',
    'ArtworkCollectionDAL',
    'ArtworkClassificationStatistic',
    'ArtworkRatingStatistic',
    'ArtworkReviewRecord',
    'ArtworkTag',
]
