"""
@Author         : Ailitonia
@Date           : 2022/12/04 17:40
@FileName       : artwork_collection.py
@Project        : nonebot2_miya
@Description    : ArtworkCollection DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import Callable, Sequence
from datetime import datetime
from enum import IntEnum, unique
from typing import Annotated, Literal

from pydantic import Field
from sqlalchemy import ColumnElement, and_, delete, desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayer, BaseDataOutModel
from ..schema import ArtworkCollectionOrm, ArtworkReviewRecordsOrm, ArtworkTagOrm, ArtworkWithTagsOrm


@unique
class ArtworkClassification(IntEnum):
    """图库作品分类"""
    IGNORED = -2  # 忽略
    UNKNOWN = -1  # 未知
    UNCATEGORIZED = 0  # 未分类
    AI_GENERATED = 1  # AI 生成 (确认为 AI 生成作品)
    EXTERNAL_CONFIRMED = 2  # 外部来源确认 (来源于资源站点或 API 的数据)
    HUMAN_CONFIRMED = 3  # 人工审核确认


@unique
class ArtworkRating(IntEnum):
    """图库作品分级"""
    UNKNOWN = -1
    GENERAL = 0
    SENSITIVE = 1
    QUESTIONABLE = 2
    EXPLICIT = 3


@unique
class ArtworkOrientation(IntEnum):
    """图库作品方向/宽高比"""
    PORTRAIT = -1  # 竖图（高 > 宽）
    SQUARE = 0  # 方图（高 = 宽）
    LANDSCAPE = 1  # 横图（宽 > 高）


class ArtworkTag(BaseDataOutModel):
    """图库作品标签数据"""
    id: int
    tag_name: str
    tag_alt_name: str | None
    created_at: datetime | None
    updated_at: datetime | None


class _BaseArtwork(BaseDataOutModel):
    """图库作品数据 (只包括基本数据供关联表使用, 避免递归加载)"""
    id: int
    origin: str
    aid: str
    uid: str
    title: str
    uname: str
    classification: ArtworkClassification
    rating: ArtworkRating
    width: int
    height: int
    orientation: ArtworkOrientation
    url: str


class Artwork(_BaseArtwork):
    """图库作品数据"""
    source: str | None
    cover_page: str | None
    raw_tags: str | None
    description: str | None
    published_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None

    # 级联数据
    tags_name_artwork_had: Annotated[list[ArtworkTag], Field(default_factory=list)]


class ArtworkReviewRecord(BaseDataOutModel):
    """图库作品评审记录数据"""
    id: int
    artwork_index_id: int
    review_timestamp: int
    review_classification: ArtworkClassification
    review_rating: ArtworkRating
    review_from: str
    review_info: str
    created_at: datetime | None
    updated_at: datetime | None

    # 级联数据
    review_record_parent_artwork: _BaseArtwork


class ArtworkClassificationStatistic(BaseDataOutModel):
    """图库作品分类统计信息查询结果"""
    unused: Annotated[int, Field(default=0, description='其他所有的分类值')]
    uncategorized: Annotated[int, Field(default=0, description='0: 未分类')]
    ai_generated: Annotated[int, Field(default=0, description='1: AI 生成')]
    external_confirmed: Annotated[int, Field(default=0, description='2: 外部来源确认')]
    human_confirmed: Annotated[int, Field(default=0, description='3: 人工审核确认')]

    @property
    def total(self) -> int:
        return self.unused + self.uncategorized + self.ai_generated + self.external_confirmed + self.human_confirmed


class ArtworkRatingStatistic(BaseDataOutModel):
    """图库作品分级统计信息查询结果"""
    unknown: Annotated[int, Field(default=0, description='-1: Unknown')]
    general: Annotated[int, Field(default=0, description='0: General')]
    sensitive: Annotated[int, Field(default=0, description='1: Sensitive')]
    questionable: Annotated[int, Field(default=0, description='2: Questionable')]
    explicit: Annotated[int, Field(default=0, description='3: Explicit')]

    @property
    def total(self) -> int:
        return self.unknown + self.general + self.sensitive + self.questionable + self.explicit


class ArtworkCollectionDAL(BaseDataAccessLayer[ArtworkCollectionOrm, Artwork]):
    """图库作品和标签等相关记录"""

    async def _count_artwork_all(self) -> int:
        """查询 ArtworkCollection 全表行数"""
        stmt = select(func.count()).select_from(ArtworkCollectionOrm)
        return (await self.db_session.execute(stmt)).scalar_one()

    async def _count_artwork_review_record_all(self) -> int:
        """查询 ArtworkReviewRecords 全表行数"""
        stmt = select(func.count()).select_from(ArtworkReviewRecordsOrm)
        return (await self.db_session.execute(stmt)).scalar_one()

    async def _count_artwork_tag_all(self) -> int:
        """查询 ArtworkTag 全表行数"""
        stmt = select(func.count()).select_from(ArtworkTagOrm)
        return (await self.db_session.execute(stmt)).scalar_one()

    async def _count_artwork_with_tags_all(self) -> int:
        """查询 ArtworkWithTags 全表行数"""
        stmt = select(func.count()).select_from(ArtworkWithTagsOrm)
        return (await self.db_session.execute(stmt)).scalar_one()

    async def _clear_all(self) -> None:
        """内部方法, 清空全表 (含标签关联表/评审记录表/标签表), 敏感操作, 方法内不执行 commit, 可由外层事务 rollback

        按子表到父表的顺序删除, 不依赖数据库外键级联
        """
        await self.db_session.execute(delete(ArtworkWithTagsOrm))
        await self.db_session.execute(delete(ArtworkReviewRecordsOrm))
        await self.db_session.execute(delete(ArtworkCollectionOrm))
        await self.db_session.execute(delete(ArtworkTagOrm))
        self.db_session.expunge_all()

    @staticmethod
    def _calc_orientation(width: int, height: int) -> ArtworkOrientation:
        """计算图片宽高方位, 1=横图 0=方图 -1=竖图"""
        if width > height:
            return ArtworkOrientation.LANDSCAPE
        if width < height:
            return ArtworkOrientation.PORTRAIT
        return ArtworkOrientation.SQUARE

    @classmethod
    def _build_keyword_conditions(
            cls,
            keywords: Sequence[str] | None,
            *,
            acc_mode: bool = False,
    ) -> list[ColumnElement[bool]]:
        """构造关键词搜索条件, 每个关键词匹配标题/用户名/作品已关联的标签

        单个关键词内为 OR 语义 (命中标题/用户名/标签任一字段即视为匹配), 多个关键词之间为 AND 语义
        tag 条件使用 EXISTS 相关子查询, 仅匹配作品自身已关联的标签, 避免引入未关联的 tag 表导致笛卡尔积
        """
        conditions: list[ColumnElement[bool]] = []
        if not keywords:
            return conditions

        for keyword in keywords:
            if acc_mode:
                # 精确匹配标题, 用户, tag
                conditions.append(or_(
                    ArtworkCollectionOrm.title == keyword,
                    ArtworkCollectionOrm.uname == keyword,
                    ArtworkCollectionOrm.tags_name_artwork_had.any(ArtworkTagOrm.tag_name == keyword),
                ))
            else:
                # 模糊匹配标题, 用户, tag
                escaped_keyword = cls._escape_like(keyword)
                conditions.append(or_(
                    ArtworkCollectionOrm.title.ilike(f'%{escaped_keyword}%', escape='\\'),
                    ArtworkCollectionOrm.uname.ilike(f'%{escaped_keyword}%', escape='\\'),
                    ArtworkCollectionOrm.tags_name_artwork_had.any(
                        ArtworkTagOrm.tag_name.ilike(f'%{escaped_keyword}%', escape='\\')
                    ),
                ))
        return conditions

    @staticmethod
    def _parse_raw_tags(
            raw_tags: str | None,
            tag_handler: Callable[[str], list[tuple[str, str | None]]] | None = None,
    ) -> list[tuple[str, str | None]]:
        """解析原始标签串, 过滤空标签并按 tag_name 去重, 避免插入空标签行或关联表主键冲突

        默认解析按逗号切分并 lower, 使用 tag_handler 时保留其原始大小写, 同名标签仅保留首个别名
        """
        if raw_tags is None:
            return []
        if tag_handler is not None:
            parsed = tag_handler(raw_tags)
        else:
            parsed = [(tag.strip().lower(), None) for tag in raw_tags.split(',')]

        dedup: dict[str, str | None] = {}
        for tag_name, tag_alt_name in parsed:
            tag_name = tag_name.strip()
            if tag_name:
                dedup.setdefault(tag_name, tag_alt_name)
        return list(dedup.items())

    async def _select_unique(
            self,
            origin: str,
            aid: str,
            *,
            populate_existing: bool = False,
            with_for_update: bool = False,
            nowait_for_update: bool = False,
    ) -> ArtworkCollectionOrm:
        """内部方法, 查询作品行, 不存在直接抛出异常

        建议使用 with_for_update 锁定读, 以读到最新已提交数据并避免并发写入
        """
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
        :param keywords: 关键词列表, 多个关键词之间为 AND 语义 (任一关键词命中标题/用户名/标签名即视为匹配)
        :param page: 分页
        :param size: 每页数量
        :param classification_min: 分类标签最小值
        :param classification_max: 分类标签最大值
        :param rating_min: 分级标签最小值
        :param rating_max: 分级标签最大值
        :param acc_mode: 是否启用精确搜索模式 (精确匹配标题/用户名/标签名)
        :param ratio: 图片长宽, 1: 横图, 0: 方图, -1: 竖图
        :param order_mode: 排序模式 (aid/aid_desc 为数值感知排序),
            random 模式下每次查询独立随机, 与分页组合时不同页可能重复或遗漏
        """
        if classification_min > classification_max:
            raise ValueError('classification_min must be less than classification_max')

        if rating_min > rating_max:
            raise ValueError('rating_min must be less than rating_max')

        if page < 1:
            raise ValueError('page must be a positive integer')

        if size < 1:
            raise ValueError('size must be a positive integer')

        # 根据 acc_mode 构造关键词查询语句 (无关键词时不添加额外过滤条件)
        conditions = self._build_keyword_conditions(keywords, acc_mode=acc_mode)

        stmt = select(ArtworkCollectionOrm)

        if origin is None:
            # 匹配所有来源
            pass
        elif isinstance(origin, str):
            # 匹配单一来源
            stmt = stmt.where(ArtworkCollectionOrm.origin == origin)
        else:
            # 匹配多个来源
            stmt = stmt.where(ArtworkCollectionOrm.origin.in_(origin))

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

        # 添加搜索条件并加载级联, 多个关键词之间为 AND 语义
        for keyword_condition in conditions:
            stmt = stmt.where(keyword_condition)
        stmt = stmt.options(selectinload(ArtworkCollectionOrm.tags_name_artwork_had))

        # 根据 order_mode 构造排序语句
        # aid 为字符串列, 按 (长度, 字典序) 做数值感知排序, 避免纯数字 ID 字典序下出现 '10' < '2' 的错乱
        match order_mode:
            case 'aid':
                stmt = stmt.order_by(func.length(ArtworkCollectionOrm.aid), ArtworkCollectionOrm.aid)
            case 'aid_desc':
                stmt = stmt.order_by(desc(func.length(ArtworkCollectionOrm.aid)), desc(ArtworkCollectionOrm.aid))
            case 'latest':
                stmt = stmt.order_by(desc(ArtworkCollectionOrm.published_at))
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

        # 构造关键词模糊搜索条件 (无关键词时不添加额外过滤条件)
        conditions = self._build_keyword_conditions(keywords)

        stmt = select(ArtworkCollectionOrm.classification, func.count(ArtworkCollectionOrm.aid))

        if origin is None:
            # 匹配所有来源
            pass
        elif isinstance(origin, str):
            # 匹配单一来源
            stmt = stmt.where(ArtworkCollectionOrm.origin == origin)
        else:
            # 匹配多个来源
            stmt = stmt.where(ArtworkCollectionOrm.origin.in_(origin))

        # 添加搜索条件, 多个关键词之间为 AND 语义
        for keyword_condition in conditions:
            stmt = stmt.where(keyword_condition)
        stmt = stmt.group_by(ArtworkCollectionOrm.classification)

        session_result = await self.db_session.execute(stmt)

        result = {}
        for classification, count_num in session_result.all():
            match classification:
                case ArtworkClassification.UNCATEGORIZED:
                    result['uncategorized'] = count_num
                case ArtworkClassification.AI_GENERATED:
                    result['ai_generated'] = count_num
                case ArtworkClassification.EXTERNAL_CONFIRMED:
                    result['external_confirmed'] = count_num
                case ArtworkClassification.HUMAN_CONFIRMED:
                    result['human_confirmed'] = count_num
                case _:
                    # IGNORED(-2)/UNKNOWN(-1) 等多个枚举值均落入此分支, 需累加而非覆盖
                    result['unused'] = result.get('unused', 0) + count_num

        return ArtworkClassificationStatistic.model_validate(result)

    async def query_rating_statistic(
            self,
            origin: str | Sequence[str] | None,
            keywords: Sequence[str] | None = None,
    ) -> ArtworkRatingStatistic:
        """按分级统计收录作品数"""

        # 构造关键词模糊搜索条件 (无关键词时不添加额外过滤条件)
        conditions = self._build_keyword_conditions(keywords)

        stmt = select(ArtworkCollectionOrm.rating, func.count(ArtworkCollectionOrm.aid))

        if origin is None:
            # 匹配所有来源
            pass
        elif isinstance(origin, str):
            # 匹配单一来源
            stmt = stmt.where(ArtworkCollectionOrm.origin == origin)
        else:
            # 匹配多个来源
            stmt = stmt.where(ArtworkCollectionOrm.origin.in_(origin))

        # 添加搜索条件, 多个关键词之间为 AND 语义
        for keyword_condition in conditions:
            stmt = stmt.where(keyword_condition)
        stmt = stmt.group_by(ArtworkCollectionOrm.rating)

        session_result = await self.db_session.execute(stmt)

        result = {}
        for rating, count_num in session_result.all():
            match rating:
                case ArtworkRating.GENERAL:
                    result['general'] = count_num
                case ArtworkRating.SENSITIVE:
                    result['sensitive'] = count_num
                case ArtworkRating.QUESTIONABLE:
                    result['questionable'] = count_num
                case ArtworkRating.EXPLICIT:
                    result['explicit'] = count_num
                case _:
                    # 存在 UNKNOWN(-1) 及枚举外取值的可能, 需累加而非覆盖
                    result['unknown'] = result.get('unknown', 0) + count_num

        return ArtworkRatingStatistic.model_validate(result)

    async def query_user_all_artworks(
            self,
            origin: str | Sequence[str] | None,
            uid: str | None = None,
            uname: str | None = None,
    ) -> list[Artwork]:
        """通过 uid 或用户名精准查找用户所有作品 (uid 与 uname 同时提供时为 AND 语义)"""
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
            stmt = stmt.where(ArtworkCollectionOrm.origin.in_(origin))

        if uid is not None:
            stmt = stmt.where(ArtworkCollectionOrm.uid == uid)
        if uname is not None:
            stmt = stmt.where(ArtworkCollectionOrm.uname == uname)

        # 加载级联, 按 aid 数值感知排序
        stmt = (stmt
                .options(selectinload(ArtworkCollectionOrm.tags_name_artwork_had))
                .order_by(desc(func.length(ArtworkCollectionOrm.aid)), desc(ArtworkCollectionOrm.aid)))

        return parse_obj_as(list[Artwork], (await self.db_session.execute(stmt)).scalars().all())

    async def query_user_all_aids(
            self,
            origin: str | Sequence[str] | None,
            uid: str | None = None,
            uname: str | None = None
    ) -> list[str]:
        """通过 uid 或用户名精准查找用户所有作品的 artwork_id (uid 与 uname 同时提供时为 AND 语义)"""
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
            stmt = stmt.where(ArtworkCollectionOrm.origin.in_(origin))

        if uid is not None:
            stmt = stmt.where(ArtworkCollectionOrm.uid == uid)
        if uname is not None:
            stmt = stmt.where(ArtworkCollectionOrm.uname == uname)

        # 按 aid 数值感知排序
        stmt = stmt.order_by(desc(func.length(ArtworkCollectionOrm.aid)), desc(ArtworkCollectionOrm.aid))

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
            stmt = stmt.where(ArtworkCollectionOrm.origin.in_(origin))

        if filter_classification is not None:
            stmt = stmt.where(ArtworkCollectionOrm.classification == filter_classification)
        if filter_rating is not None:
            stmt = stmt.where(ArtworkCollectionOrm.rating == filter_rating)

        # 按 aid 数值感知排序
        stmt = (stmt
                .where(ArtworkCollectionOrm.aid.in_(aids))
                .order_by(desc(func.length(ArtworkCollectionOrm.aid)), desc(ArtworkCollectionOrm.aid)))

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
        # 按 (长度, 字典序) 的数值感知顺序倒序排列, 与查询方法的 aid 排序口径一致
        return sorted(set(aids) - set(exists_aids), key=lambda x: (len(x), x), reverse=True)

    async def _add_artwork(
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
            description: str | None = None,
            published_at: datetime | None = None,
    ) -> ArtworkCollectionOrm:
        """内部方法, 向数据库插入新行, 不校验唯一性

        尽量保证插入的是新数据时才使用, 冲突直接抛出异常
        """
        new_obj = ArtworkCollectionOrm(
            origin=origin,
            aid=aid,
            uid=uid,
            title=title,
            uname=uname,
            classification=ArtworkClassification(classification),
            rating=ArtworkRating(rating),
            width=width,
            height=height,
            orientation=self._calc_orientation(width, height),
            url=url,
            source=source,
            cover_page=cover_page,
            raw_tags=raw_tags,
            description=description,
            published_at=published_at,
        )
        self.db_session.add(new_obj)
        await self.db_session.flush()
        await self.db_session.refresh(new_obj)
        return new_obj

    async def _add_artwork_tag_update_exist_nested(
            self,
            tag_name: str,
            tag_alt_name: str | None = None,
    ) -> ArtworkTagOrm:
        """内部方法, 开启嵌套事务, 向数据库插入标签新行, 存在则忽略"""
        new_obj = ArtworkTagOrm(tag_name=tag_name, tag_alt_name=tag_alt_name)
        try:
            async with self.must_begin_nested_in_transaction() as session:
                session.add(new_obj)
                await session.flush()
            await session.refresh(new_obj)
            return new_obj
        except IntegrityError as e:
            # 只有唯一约束冲突才进入"已存在则复用"分支, 其他完整性冲突(外键/非空等)原样抛出
            if not self._is_unique_conflict_error(e):
                raise
            # 把插入失败的对象移出会话, 避免意外影响
            if new_obj in self.db_session:
                self.db_session.expunge(new_obj)
            async with self.must_begin_nested_in_transaction() as session:
                # 锁定读可以读到最新已提交数据, 避免 REPEATABLE READ 一致性快照取不到并发插入的行
                stmt = (select(ArtworkTagOrm)
                        .where(ArtworkTagOrm.tag_name == tag_name)
                        .with_for_update())
                exist_obj = (await session.execute(stmt)).scalar_one()
                if tag_alt_name is not None:
                    exist_obj.tag_alt_name = tag_alt_name
                    await session.flush()
                    await session.refresh(exist_obj)
            return exist_obj

    async def _add_artwork_with_tag(
            self,
            artwork_index_id: int,
            tag_index_id: int,
    ) -> ArtworkWithTagsOrm:
        """内部方法, 向数据库插入作品-标签关联新行, 不校验唯一性

        尽量保证插入的是新数据时才使用, 冲突直接抛出异常
        """
        new_obj = ArtworkWithTagsOrm(
            artwork_index_id=artwork_index_id,
            tag_index_id=tag_index_id,
        )
        self.db_session.add(new_obj)
        await self.db_session.flush()
        await self.db_session.refresh(new_obj)
        return new_obj

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
        """向数据库新增该作品信息, 若已存在则更新 (更新时同步重建 tag 关联)

        同一事务中处理 tag 表及 tag 关联表插入, 确保并发与原子性

        Note: SQLite 后端在嵌套事务 (SAVEPOINT) 场景下, 插入分支可能因驱动 legacy 事务控制
        (会话事务不显式发送 BEGIN, SAVEPOINT 直接开启物理事务且 RELEASE 即提交) 而被提前提交,
        外层事务 rollback 无法撤销; MySQL/PostgreSQL 后端不受影响
        """

        # 处理标签, 过滤空标签并去重, 避免插入空标签行或关联表主键冲突
        tag_list: list[tuple[str, str | None]] = self._parse_raw_tags(raw_tags=raw_tags, tag_handler=tag_handler)

        # 单事务处理作品表及标签表插入
        async with self.safe_begin_transaction() as session:
            # 先处理标签插入
            tags_item: list[ArtworkTagOrm] = []
            for tag_name, tag_alt_name in tag_list:
                tags_item.append(await self._add_artwork_tag_update_exist_nested(tag_name, tag_alt_name))

            try:
                # 处理作品插入
                async with self.must_begin_nested_in_transaction():
                    artwork_item = await self._add_artwork(
                        origin=origin,
                        aid=aid,
                        uid=uid,
                        title=title,
                        uname=uname,
                        classification=ArtworkClassification(classification),
                        rating=ArtworkRating(rating),
                        width=width,
                        height=height,
                        url=url,
                        source=source,
                        cover_page=cover_page,
                        raw_tags=raw_tags,
                        description=description,
                        published_at=published_at,
                    )
            except IntegrityError as e:
                # 只有唯一约束冲突才进入"已存在则更新"分支, 其他完整性冲突(外键/非空等)原样抛出
                if not self._is_unique_conflict_error(e):
                    raise
                # 插入失败说明是已存在的条目, 锁定查询并更新信息
                artwork_item = await self._select_unique(
                    origin=origin,
                    aid=aid,
                    with_for_update=True,
                )
                artwork_item.uid = uid
                artwork_item.title = title
                artwork_item.uname = uname
                artwork_item.classification = ArtworkClassification(classification)
                artwork_item.rating = ArtworkRating(rating)
                artwork_item.width = width
                artwork_item.height = height
                artwork_item.orientation = self._calc_orientation(width, height)
                artwork_item.url = url
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

                # 重建 tag 关联: 先删除旧关联, 再插入新关联, 保证关联与 raw_tags 一致
                await session.execute(
                    delete(ArtworkWithTagsOrm)
                    .where(ArtworkWithTagsOrm.artwork_index_id == artwork_item.id)
                )
                for tag_item in tags_item:
                    await self._add_artwork_with_tag(artwork_item.id, tag_item.id)
            else:
                # 插入成功说明是新条目, 继续插入关联表
                for tag_item in tags_item:
                    await self._add_artwork_with_tag(artwork_item.id, tag_item.id)

            # 重新加载作品及其标签, 确保返回数据模型时关系属性已加载
            artwork_item = await self._select_unique(
                origin=origin,
                aid=aid,
                populate_existing=True,
            )
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

        Note: SQLite 后端在嵌套事务 (SAVEPOINT) 场景下, 插入分支可能因驱动 legacy 事务控制
        (会话事务不显式发送 BEGIN, SAVEPOINT 直接开启物理事务且 RELEASE 即提交) 而被提前提交,
        外层事务 rollback 无法撤销; MySQL/PostgreSQL 后端不受影响
        """

        # 处理标签, 过滤空标签并去重, 避免插入空标签行或关联表主键冲突
        tag_list: list[tuple[str, str | None]] = self._parse_raw_tags(raw_tags=raw_tags, tag_handler=tag_handler)

        # 单事务处理作品表及标签表插入
        async with self.safe_begin_transaction():
            # 先处理标签插入
            tags_item: list[ArtworkTagOrm] = []
            for tag_name, tag_alt_name in tag_list:
                tags_item.append(await self._add_artwork_tag_update_exist_nested(tag_name, tag_alt_name))

            try:
                # 处理作品插入
                async with self.must_begin_nested_in_transaction():
                    artwork_item = await self._add_artwork(
                        origin=origin,
                        aid=aid,
                        uid=uid,
                        title=title,
                        uname=uname,
                        classification=ArtworkClassification(classification),
                        rating=ArtworkRating(rating),
                        width=width,
                        height=height,
                        url=url,
                        source=source,
                        cover_page=cover_page,
                        raw_tags=raw_tags,
                        description=description,
                        published_at=published_at,
                    )
            except IntegrityError as e:
                # 只有唯一约束冲突才忽略, 其他完整性冲突(外键/非空等)原样抛出
                if not self._is_unique_conflict_error(e):
                    raise
                # 插入失败说明是已存在的条目, 忽略本次提交的作品信息
            else:
                # 插入成功说明是新条目, 继续插入关联表
                for tag_item in tags_item:
                    await self._add_artwork_with_tag(artwork_item.id, tag_item.id)

            # 获取已有条目信息 (重新加载, 确保返回数据模型时关系属性已加载)
            # 锁定读以读到最新已提交数据: 插入冲突说明目标行由并发事务提交, 本事务若已建立
            # REPEATABLE READ 一致性快照, 普通一致性读可能读不到该行而误报 NoResultFound
            artwork_item = await self._select_unique(
                origin=origin,
                aid=aid,
                populate_existing=True,
                with_for_update=True,
            )
        await self.db_session.refresh(artwork_item)
        return Artwork.model_validate(artwork_item)

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
        """向数据库插入新行, 不校验唯一性, 方法内不执行 commit

        作品信息经 _select_unique 预加载了标签关系, 返回模型的父作品校验依赖同一会话 identity map 中的该实例
        如果作品不存在直接抛出异常
        """
        artwork_item = await self._select_unique(origin, aid, populate_existing=True)
        new_obj = ArtworkReviewRecordsOrm(
            artwork_index_id=artwork_item.id,
            review_timestamp=review_timestamp,
            review_classification=ArtworkClassification(review_classification),
            review_rating=ArtworkRating(review_rating),
            review_from=review_from,
            review_info=review_info,
        )
        self.db_session.add(new_obj)
        await self.db_session.flush()
        await self.db_session.refresh(new_obj)
        return ArtworkReviewRecord.model_validate(new_obj)

    async def query_artwork_review_records(
            self,
            origin: str,
            aid: str,
            *,
            start_timestamp: int | None = None,
            populate_existing: bool = False,
    ) -> list[ArtworkReviewRecord]:
        """查询作品的评审记录, 如果作品不存在直接抛出异常"""
        artwork_item = await self._select_unique(origin, aid, populate_existing=True)
        stmt = select(ArtworkReviewRecordsOrm).where(ArtworkReviewRecordsOrm.artwork_index_id == artwork_item.id)

        if start_timestamp is not None and start_timestamp > 0:
            stmt = stmt.where(ArtworkReviewRecordsOrm.review_timestamp >= start_timestamp)

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        return parse_obj_as(list[ArtworkReviewRecord], (await self.db_session.execute(stmt)).scalars().all())

    async def delete(self, origin: str, aid: str) -> None:
        """删除指定作品, 删除不存在的数据时静默成功, 方法内不执行 commit

        关联的标签关联表/评审记录表数据由数据库外键级联删除
        """
        stmt = (delete(ArtworkCollectionOrm)
                .where(ArtworkCollectionOrm.origin == origin)
                .where(ArtworkCollectionOrm.aid == aid))
        await self.db_session.execute(stmt)


__all__ = [
    'Artwork',
    'ArtworkCollectionDAL',
    'ArtworkClassification',
    'ArtworkClassificationStatistic',
    'ArtworkOrientation',
    'ArtworkRating',
    'ArtworkRatingStatistic',
    'ArtworkReviewRecord',
    'ArtworkTag',
]
