"""
@Author         : Ailitonia
@Date           : 2022/03/27 13:38
@FileName       : pixiv_artwork.py
@Project        : nonebot2_miya 
@Description    : PixivArtwork Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal, List, Optional
from datetime import datetime
from sqlalchemy import update, delete, desc, or_
from sqlalchemy.sql.expression import func
from sqlalchemy.future import select
from omega_miya.result import BaseResult, BoolResult, IntListResult
from .base_model import (BaseDatabaseModel, BaseDatabase, Select, Update, Delete,
                         DatabaseModelResult, DatabaseModelListResult)
from ..model import PixivArtworkOrm


class PixivArtworkUniqueModel(BaseDatabaseModel):
    """数据库对象唯一性模型"""
    pid: int


class PixivArtworkRequireModel(PixivArtworkUniqueModel):
    """数据库对象变更请求必须数据模型"""
    uid: int
    title: str
    uname: str
    tags: str
    url: str
    classified: int
    nsfw_tag: int
    width: int
    height: int


class PixivArtworkModel(PixivArtworkRequireModel):
    """数据库对象完整模型"""
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class PixivArtworkModelResult(DatabaseModelResult):
    """数据库查询结果基类"""
    result: Optional["PixivArtworkModel"]


class PixivArtworkModelListResult(DatabaseModelListResult):
    """PixivArtwork 查询结果类"""
    result: List["PixivArtworkModel"]


class PixivArtworkCountResult(BaseResult):
    """统计信息查询结果类"""
    total: int = -1
    moe: int = -1
    setu: int = -1
    r18: int = -1


class PixivArtwork(BaseDatabase):
    orm_model = PixivArtworkOrm
    unique_model = PixivArtworkUniqueModel
    require_model = PixivArtworkRequireModel
    data_model = PixivArtworkModel
    self_model: PixivArtworkUniqueModel

    def __init__(self, pid: int):
        self.self_model = PixivArtworkUniqueModel(pid=pid)

    @classmethod
    def _make_all_select(cls) -> Select:
        stmt = select(cls.orm_model).with_for_update(read=True).order_by(desc(cls.orm_model.pid))
        return stmt

    def _make_unique_self_select(self) -> Select:
        stmt = select(self.orm_model).\
            where(self.orm_model.pid == self.self_model.pid).\
            order_by(desc(self.orm_model.pid))
        return stmt

    def _make_unique_self_update(self, new_model: PixivArtworkRequireModel) -> Update:
        stmt = update(self.orm_model).\
            where(self.orm_model.pid == self.self_model.pid).\
            values(**new_model.dict()).\
            values(updated_at=datetime.now()).\
            execution_options(synchronize_session="fetch")
        return stmt

    def _make_unique_self_delete(self) -> Delete:
        stmt = delete(self.orm_model).\
            where(self.orm_model.pid == self.self_model.pid).\
            execution_options(synchronize_session="fetch")
        return stmt

    async def update_unique_self(
            self,
            uid: int,
            title: str,
            uname: str,
            tags: str,
            url: str,
            classified: int = 0,
            nsfw_tag: int = -1,
            width: int = 0,
            height: int = 0) -> BoolResult:
        return await self._update_unique_self(new_model=self.require_model(
            pid=self.self_model.pid,
            uid=uid,
            title=title,
            uname=uname,
            tags=tags,
            url=url,
            classified=classified,
            nsfw_tag=nsfw_tag,
            width=width,
            height=height
        ))

    async def add_upgrade_unique_self(
            self,
            uid: int,
            title: str,
            uname: str,
            tags: str,
            url: str,
            classified: int = 0,
            nsfw_tag: int = -1,
            width: int = 0,
            height: int = 0) -> BoolResult:
        return await self._add_upgrade_unique_self(new_model=self.require_model(
            pid=self.self_model.pid,
            uid=uid,
            title=title,
            uname=uname,
            tags=tags,
            url=url,
            classified=classified,
            nsfw_tag=nsfw_tag,
            width=width,
            height=height
        ))

    async def add_only(
            self,
            uid: int,
            title: str,
            uname: str,
            tags: str,
            url: str,
            classified: int = 0,
            nsfw_tag: int = -1,
            width: int = 0,
            height: int = 0) -> BoolResult:
        return await self._add_only_without_upgrade_unique_self(new_model=self.require_model(
            pid=self.self_model.pid,
            uid=uid,
            title=title,
            uname=uname,
            tags=tags,
            url=url,
            classified=classified,
            nsfw_tag=nsfw_tag,
            width=width,
            height=height
        ))

    async def query(self) -> PixivArtworkModelResult:
        return PixivArtworkModelResult.parse_obj(await self.query_unique_self())

    @classmethod
    async def query_by_condition(
            cls,
            keywords: Optional[List[str]],
            num: Optional[int] = 3,
            nsfw_tag: int = 0,
            *,
            classified: int = 1,
            acc_mode: bool = False,
            ratio: Optional[int] = None,
            order_mode: Literal['random', 'pid', 'pid_desc', 'create_time', 'create_time_desc'] = 'random'
    ) -> PixivArtworkModelListResult:
        """按条件搜索 Pixiv 作品

        :param keywords: 关键词列表
        :param num: 数量
        :param nsfw_tag: nsfw 标签值, 0=sfw, 1=nsfw, 2=r18, -1=(sfw+nsfw), -2=(sfw+nsfw+r18), -3=(nsfw+r18)
        :param classified: 已标记标签项, 0=未标记, 1=已标记, 其他=all
        :param acc_mode: 是否启用精确搜索模式
        :param ratio: 图片长宽, 1: 横图, -1: 纵图, 0: 正方形图
        :param order_mode: 排序模式, random: 随机, pid: 按 pid 顺序, pid_desc: 按 pid 逆序,
            create_time: 按收录时间顺序, create_time_desc: 按收录时间逆序
        """

        stmt = select(cls.orm_model).with_for_update(read=True)

        # 处理 nsfw 条件
        match nsfw_tag:
            case -1:
                stmt = stmt.where(or_(cls.orm_model.nsfw_tag == 0, cls.orm_model.nsfw_tag == 1))
            case -2:
                stmt = stmt.where(or_(cls.orm_model.nsfw_tag == 0,
                                      cls.orm_model.nsfw_tag == 1,
                                      cls.orm_model.nsfw_tag == 2))
            case -3:
                stmt = stmt.where(or_(cls.orm_model.nsfw_tag == 1, cls.orm_model.nsfw_tag == 2))
            case _:
                stmt = stmt.where(cls.orm_model.nsfw_tag == nsfw_tag)

        # 处理 classified 条件
        match classified:
            case 1:
                stmt = stmt.where(cls.orm_model.classified == 1)
            case 0:
                stmt = stmt.where(cls.orm_model.classified == 0)

        # 根据 acc_mode 构造关键词查询语句
        if (not keywords) or (keywords is None):
            # 无关键词则随机
            pass
        elif acc_mode:
            # 精确搜索标题, 用户和tag
            for keyword in keywords:
                stmt = stmt.where(or_(
                    func.find_in_set(keyword, cls.orm_model.tags),
                    func.find_in_set(keyword, cls.orm_model.uname),
                    func.find_in_set(keyword, cls.orm_model.title)
                ))
        else:
            # 模糊搜索标题, 用户和tag
            for keyword in keywords:
                stmt = stmt.where(or_(
                    cls.orm_model.tags.ilike(f'%{keyword}%'),
                    cls.orm_model.uname.ilike(f'%{keyword}%'),
                    cls.orm_model.title.ilike(f'%{keyword}%')
                ))

        # 根据 ratio 构造图片长宽类型查询语句
        if ratio is None:
            pass
        elif ratio < 0:
            stmt = stmt.where(cls.orm_model.width < cls.orm_model.height)
        elif ratio > 0:
            stmt = stmt.where(cls.orm_model.width > cls.orm_model.height)
        else:
            stmt = stmt.where(cls.orm_model.width == cls.orm_model.height)

        # 根据 order_mode 构造排序语句
        match order_mode:
            case 'random':
                stmt = stmt.order_by(func.random())
            case 'pid':
                stmt = stmt.order_by(cls.orm_model.pid)
            case 'pid_desc':
                stmt = stmt.order_by(desc(cls.orm_model.pid))
            case 'create_time':
                stmt = stmt.order_by(cls.orm_model.created_at)
            case 'create_time_desc':
                stmt = stmt.order_by(desc(cls.orm_model.created_at))

        # 结果数量限制
        if num is None:
            pass
        else:
            stmt = stmt.limit(num)
        return PixivArtworkModelListResult.parse_obj(await cls._query_all(stmt=stmt))

    @classmethod
    async def query_all(cls) -> PixivArtworkModelListResult:
        return PixivArtworkModelListResult.parse_obj(await cls._query_all())

    @classmethod
    async def query_all_by_uid(cls, uid: int) -> PixivArtworkModelListResult:
        stmt = select(cls.orm_model).with_for_update(read=True).\
            where(cls.orm_model.uid == uid).order_by(desc(cls.orm_model.pid))
        return PixivArtworkModelListResult.parse_obj(await cls._query_all(stmt=stmt))

    @classmethod
    async def query_all_pid_by_uid(cls, uid: int) -> IntListResult:
        stmt = select(cls.orm_model.pid).with_for_update(read=True).\
            where(cls.orm_model.uid == uid).order_by(desc(cls.orm_model.pid))
        return IntListResult(error=False, info='Success', result=(await cls._query_custom_all(stmt=stmt)))

    @classmethod
    async def count_all(
            cls,
            keywords: Optional[List[str]] = None,
            *,
            classified: Optional[int] = 1
    ) -> PixivArtworkCountResult:
        try:
            all_stmt = select(func.count(cls.orm_model.id)).with_for_update(read=True)

            if classified is not None:
                all_stmt = all_stmt.where(cls.orm_model.classified == classified)

            if keywords:
                for keyword in keywords:
                    all_stmt = all_stmt.where(or_(
                        cls.orm_model.tags.ilike(f'%{keyword}%'),
                        cls.orm_model.uname.ilike(f'%{keyword}%'),
                        cls.orm_model.title.ilike(f'%{keyword}%')
                    ))
            all_count = await cls._query_custom_all(stmt=all_stmt)

            moe_stmt = all_stmt.where(cls.orm_model.nsfw_tag == 0)
            moe_count = await cls._query_custom_all(stmt=moe_stmt)

            setu_stmt = all_stmt.where(cls.orm_model.nsfw_tag == 1)
            setu_count = await cls._query_custom_all(stmt=setu_stmt)

            r18_stmt = all_stmt.where(cls.orm_model.nsfw_tag == 2)
            r18_count = await cls._query_custom_all(stmt=r18_stmt)
            return PixivArtworkCountResult(
                error=False,
                info='Success',
                total=all_count[0],
                moe=moe_count[0],
                setu=setu_count[0],
                r18=r18_count[0]
            )
        except Exception as e:
            return PixivArtworkCountResult(error=True, info=repr(e))


__all__ = [
    'PixivArtwork',
    'PixivArtworkModel'
]
