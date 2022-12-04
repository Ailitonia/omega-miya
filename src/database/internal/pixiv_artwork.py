"""
@Author         : Ailitonia
@Date           : 2022/12/04 17:40
@FileName       : pixiv_artwork.py
@Project        : nonebot2_miya 
@Description    : PixivArtwork DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import func
from sqlalchemy.future import select
from sqlalchemy import update, delete, desc, or_
from typing import Literal, Optional

from pydantic import BaseModel, parse_obj_as

from ..model import BaseDataAccessLayerModel, PixivArtworkOrm


class PixivArtwork(BaseModel):
    """Pixiv 作品 Model"""
    id: int
    pid: int
    uid: int
    title: str
    uname: str
    classified: int
    nsfw_tag: int
    width: int
    height: int
    tags: str
    url: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        extra = 'ignore'
        orm_mode = True
        allow_mutation = False


class PixivArtworkStatistic(BaseModel):
    """统计信息查询结果类"""
    total: int
    moe: int
    setu: int
    r18: int

    class Config:
        extra = 'ignore'
        allow_mutation = False


class PixivArtworkDAL(BaseDataAccessLayerModel):
    """Pixiv 作品 数据库操作对象"""

    def __init__(self, session: AsyncSession):
        self.db_session = session

    async def query_unique(self, pid: int) -> PixivArtwork:
        stmt = select(PixivArtworkOrm).where(PixivArtworkOrm.pid == pid)
        session_result = await self.db_session.execute(stmt)
        return PixivArtwork.from_orm(session_result.scalar_one())

    async def query_with_condition(
            self,
            keywords: Optional[list[str]],
            num: int = 3,
            nsfw_tag: int = 0,
            *,
            classified: int = 1,
            acc_mode: bool = False,
            ratio: Optional[int] = None,
            order_mode: Literal['random', 'pid', 'pid_desc', 'create_time', 'create_time_desc'] = 'random'
    ) -> list[PixivArtwork]:
        """按条件搜索 Pixiv 作品

        :param keywords: 关键词列表
        :param num: 数量
        :param nsfw_tag: nsfw 标签值, 0=sfw, 1=nsfw, 2=r18, -1=(sfw+nsfw), -2=(sfw+nsfw+r18), -3=(nsfw+r18)
        :param classified: 已标记标签项, 0=未标记, 1=已标记, 2=AI生成作品
        :param acc_mode: 是否启用精确搜索模式
        :param ratio: 图片长宽, 1: 横图, -1: 纵图, 0: 正方形图
        :param order_mode: 排序模式, random: 随机, pid: 按 pid 顺序, pid_desc: 按 pid 逆序,
            create_time: 按收录时间顺序, create_time_desc: 按收录时间逆序
        """
        stmt = select(PixivArtworkOrm)

        # nsfw 条件
        match nsfw_tag:
            case - 1:
                stmt = stmt.where(or_(PixivArtworkOrm.nsfw_tag == 0, PixivArtworkOrm.nsfw_tag == 1))
            case - 2:
                stmt = stmt.where(or_(PixivArtworkOrm.nsfw_tag == 0,
                                      PixivArtworkOrm.nsfw_tag == 1,
                                      PixivArtworkOrm.nsfw_tag == 2))
            case - 3:
                stmt = stmt.where(or_(PixivArtworkOrm.nsfw_tag == 1, PixivArtworkOrm.nsfw_tag == 2))
            case _:
                stmt = stmt.where(PixivArtworkOrm.nsfw_tag == nsfw_tag)

        # classified 条件
        stmt = stmt.where(PixivArtworkOrm.classified == classified)

        # 根据 acc_mode 构造关键词查询语句
        if (not keywords) or (keywords is None):
            # 无关键词则随机
            pass
        elif acc_mode:
            # 精确搜索标题, 用户和tag
            for keyword in keywords:
                stmt = stmt.where(or_(
                    func.find_in_set(keyword, PixivArtworkOrm.tags),
                    func.find_in_set(keyword, PixivArtworkOrm.uname),
                    func.find_in_set(keyword, PixivArtworkOrm.title)
                ))
        else:
            # 模糊搜索标题, 用户和tag
            for keyword in keywords:
                stmt = stmt.where(or_(
                    PixivArtworkOrm.tags.ilike(f'%{keyword}%'),
                    PixivArtworkOrm.uname.ilike(f'%{keyword}%'),
                    PixivArtworkOrm.title.ilike(f'%{keyword}%')
                ))

        # 根据 ratio 构造图片长宽类型查询语句
        if ratio is None:
            pass
        elif ratio < 0:
            stmt = stmt.where(PixivArtworkOrm.width < PixivArtworkOrm.height)
        elif ratio > 0:
            stmt = stmt.where(PixivArtworkOrm.width > PixivArtworkOrm.height)
        else:
            stmt = stmt.where(PixivArtworkOrm.width == PixivArtworkOrm.height)

        # 根据 order_mode 构造排序语句
        match order_mode:
            case 'random':
                stmt = stmt.order_by(func.random())
            case 'pid':
                stmt = stmt.order_by(PixivArtworkOrm.pid)
            case 'pid_desc':
                stmt = stmt.order_by(desc(PixivArtworkOrm.pid))
            case 'create_time':
                stmt = stmt.order_by(PixivArtworkOrm.created_at)
            case 'create_time_desc':
                stmt = stmt.order_by(desc(PixivArtworkOrm.created_at))

        # 结果数量限制
        if num is None:
            pass
        else:
            stmt = stmt.limit(num)

        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[PixivArtwork], session_result.scalars().all())

    async def query_statistic(
            self,
            keywords: Optional[list[str]] = None,
            *,
            classified: Optional[int] = 1
    ) -> PixivArtworkStatistic:
        stmt = select(func.count(PixivArtworkOrm.id))

        if classified is not None:
            stmt = stmt.where(PixivArtworkOrm.classified == classified)

        if keywords:
            for keyword in keywords:
                stmt = stmt.where(or_(
                    PixivArtworkOrm.tags.ilike(f'%{keyword}%'),
                    PixivArtworkOrm.uname.ilike(f'%{keyword}%'),
                    PixivArtworkOrm.title.ilike(f'%{keyword}%')
                ))

        total_result = await self.db_session.execute(stmt)

        moe_stmt = stmt.where(PixivArtworkOrm.nsfw_tag == 0)
        moe_result = await self.db_session.execute(moe_stmt)

        setu_stmt = stmt.where(PixivArtworkOrm.nsfw_tag == 1)
        setu_result = await self.db_session.execute(setu_stmt)

        r18_stmt = stmt.where(PixivArtworkOrm.nsfw_tag == 2)
        r18_result = await self.db_session.execute(r18_stmt)

        return PixivArtworkStatistic(
            total=total_result.scalar_one(),
            moe=moe_result.scalar_one(),
            setu=setu_result.scalar_one(),
            r18=r18_result.scalar_one()
        )

    async def query_user_all(self, uid: int) -> list[PixivArtwork]:
        stmt = select(PixivArtworkOrm).where(PixivArtworkOrm.uid == uid).order_by(desc(PixivArtworkOrm.pid))
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[PixivArtwork], session_result.scalars().all())

    async def query_user_all_pids(self, uid: int) -> list[int]:
        stmt = select(PixivArtworkOrm.pid).where(PixivArtworkOrm.uid == uid).order_by(desc(PixivArtworkOrm.pid))
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[int], session_result.scalars().all())

    async def query_all(self) -> list[PixivArtwork]:
        raise NotImplementedError('method not supported')

    async def add(
            self,
            pid: int,
            uid: int,
            title: str,
            uname: str,
            classified: int,
            nsfw_tag: int,
            width: int,
            height: int,
            tags: str,
            url: str
    ) -> None:
        new_obj = PixivArtworkOrm(pid=pid, uid=uid, title=title, uname=uname, classified=classified, nsfw_tag=nsfw_tag,
                                  width=width, height=height, tags=tags, url=url, created_at=datetime.now())
        self.db_session.add(new_obj)
        await self.db_session.flush()

    async def update(
            self,
            id_: int,
            *,
            pid: Optional[int] = None,
            uid: Optional[int] = None,
            title: Optional[str] = None,
            uname: Optional[str] = None,
            classified: Optional[int] = None,
            nsfw_tag: Optional[int] = None,
            width: Optional[int] = None,
            height: Optional[int] = None,
            tags: Optional[str] = None,
            url: Optional[str] = None
    ) -> None:
        stmt = update(PixivArtworkOrm).where(PixivArtworkOrm.id == id_)
        if pid is not None:
            stmt = stmt.values(pid=pid)
        if uid is not None:
            stmt = stmt.values(uid=uid)
        if title is not None:
            stmt = stmt.values(title=title)
        if uname is not None:
            stmt = stmt.values(uname=uname)
        if classified is not None:
            stmt = stmt.values(classified=classified)
        if nsfw_tag is not None:
            stmt = stmt.values(nsfw_tag=nsfw_tag)
        if width is not None:
            stmt = stmt.values(width=width)
        if height is not None:
            stmt = stmt.values(height=height)
        if tags is not None:
            stmt = stmt.values(tags=tags)
        if url is not None:
            stmt = stmt.values(url=url)
        stmt = stmt.values(updated_at=datetime.now())
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)

    async def delete(self, id_: int) -> None:
        stmt = delete(PixivArtworkOrm).where(PixivArtworkOrm.id == id_)
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)


__all__ = [
    'PixivArtworkDAL'
]
