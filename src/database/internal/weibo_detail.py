"""
@Author         : Ailitonia
@Date           : 2023/8/6 11:52
@FileName       : weibo_detail
@Project        : nonebot2_miya
@Description    : WeiboDetail DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import update, delete, desc
from sqlalchemy.future import select

from src.compat import parse_obj_as

from ..model import BaseDataAccessLayerModel, WeiboDetailOrm


class WeiboDetail(BaseModel):
    """微博内容 Model"""
    id: int
    mid: int
    uid: int
    content: str
    retweeted_content: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(extra='ignore', from_attributes=True, frozen=True)


class WeiboDetailDAL(BaseDataAccessLayerModel):
    """微博内容 数据库操作对象"""

    async def query_unique(self, mid: int) -> WeiboDetail:
        stmt = select(WeiboDetailOrm).where(WeiboDetailOrm.mid == mid)
        session_result = await self.db_session.execute(stmt)
        return WeiboDetail.model_validate(session_result.scalar_one())

    async def query_exists_ids(self, mids: list[int]) -> list[int]:
        """查询数据库中 mids 列表中已有的微博 id"""
        stmt = select(WeiboDetailOrm.mid).\
            where(WeiboDetailOrm.mid.in_(mids)).\
            order_by(desc(WeiboDetailOrm.mid))
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[int], session_result.scalars().all())

    async def query_not_exists_ids(self, mids: list[int]) -> list[int]:
        """查询数据库中 mids 列表中没有的微博 id"""
        exists_mids = await self.query_exists_ids(mids=mids)
        return sorted(list(set(mids) - set(exists_mids)), reverse=True)

    async def query_all(self) -> list[WeiboDetail]:
        stmt = select(WeiboDetailOrm).order_by(desc(WeiboDetailOrm.mid))
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[WeiboDetail], session_result.scalars().all())

    async def query_user_all(self, uid: int) -> list[WeiboDetail]:
        """查询用户的全部微博内容"""
        stmt = select(WeiboDetailOrm).where(WeiboDetailOrm.uid == uid).order_by(desc(WeiboDetailOrm.mid))
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[WeiboDetail], session_result.scalars().all())

    async def query_user_all_weibo_mids(self, uid: int) -> list[int]:
        """查询用户的全部微博id"""
        stmt = select(WeiboDetailOrm.mid).\
            where(WeiboDetailOrm.uid == uid).\
            order_by(desc(WeiboDetailOrm.mid))
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[int], session_result.scalars().all())

    async def add(self, mid: int, uid: int, content: str, retweeted_content: str = '') -> None:
        new_obj = WeiboDetailOrm(
            mid=mid, uid=uid, content=content, retweeted_content=retweeted_content, created_at=datetime.now()
        )
        self.db_session.add(new_obj)
        await self.db_session.flush()

    async def update(
            self,
            id_: int,
            *,
            mid: Optional[int] = None,
            uid: Optional[int] = None,
            content: Optional[str] = None,
            retweeted_content: Optional[str] = None
    ) -> None:
        stmt = update(WeiboDetailOrm).where(WeiboDetailOrm.id == id_)
        if mid is not None:
            stmt = stmt.values(mid=mid)
        if uid is not None:
            stmt = stmt.values(uid=uid)
        if content is not None:
            stmt = stmt.values(content=content)
        if retweeted_content is not None:
            stmt = stmt.values(retweeted_content=retweeted_content)
        stmt = stmt.values(updated_at=datetime.now())
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)

    async def delete(self, id_: int) -> None:
        stmt = delete(WeiboDetailOrm).where(WeiboDetailOrm.id == id_)
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)


__all__ = [
    'WeiboDetail',
    'WeiboDetailDAL'
]
