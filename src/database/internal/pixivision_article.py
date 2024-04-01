"""
@Author         : Ailitonia
@Date           : 2022/12/04 22:14
@FileName       : pixivision_article.py
@Project        : nonebot2_miya 
@Description    : PixivisionArticle DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import update, delete, desc
from sqlalchemy.future import select

from src.compat import AnyUrlStr as AnyUrl, parse_obj_as

from ..model import BaseDataAccessLayerModel, PixivisionArticleOrm


class PixivisionArticle(BaseModel):
    """Pixivision 特辑 Model"""
    id: int
    aid: int
    title: str
    description: str
    tags: str
    artworks_id: str
    url: AnyUrl
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(extra='ignore', from_attributes=True, frozen=True)


class PixivisionArticleDAL(BaseDataAccessLayerModel):
    """Pixivision 特辑 数据库操作对象"""

    async def query_unique(self, aid: int) -> PixivisionArticle:
        stmt = select(PixivisionArticleOrm).where(PixivisionArticleOrm.aid == aid)
        session_result = await self.db_session.execute(stmt)
        return PixivisionArticle.model_validate(session_result.scalar_one())

    async def query_all_aids(self) -> list[int]:
        stmt = select(PixivisionArticleOrm.aid).order_by(desc(PixivisionArticleOrm.aid))
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[int], session_result.scalars().all())

    async def query_exists_ids(self, aids: list[int]) -> list[int]:
        """查询数据库中已有的特辑文章 aid"""
        stmt = select(PixivisionArticleOrm.aid).\
            where(PixivisionArticleOrm.aid.in_(aids)).\
            order_by(desc(PixivisionArticleOrm.aid))
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[int], session_result.scalars().all())

    async def query_not_exists_ids(self, aids: list[int]) -> list[int]:
        """查询数据库中没有的特辑文章 aid"""
        exists_aids = await self.query_exists_ids(aids=aids)
        return sorted(list(set(aids) - set(exists_aids)), reverse=True)

    async def query_all(self) -> list[PixivisionArticle]:
        stmt = select(PixivisionArticleOrm).order_by(desc(PixivisionArticleOrm.aid))
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[PixivisionArticle], session_result.scalars().all())

    async def add(
            self,
            aid: int,
            title: str,
            description: str,
            tags: str,
            artworks_id: str,
            url: str
    ) -> None:
        new_obj = PixivisionArticleOrm(aid=aid, title=title, description=description, tags=tags,
                                       artworks_id=artworks_id, url=url, created_at=datetime.now())
        self.db_session.add(new_obj)
        await self.db_session.flush()

    async def update(
            self,
            id_: int,
            *,
            aid: Optional[int] = None,
            title: Optional[str] = None,
            description: Optional[str] = None,
            tags: Optional[str] = None,
            artworks_id: Optional[str] = None,
            url: Optional[str] = None
    ) -> None:
        stmt = update(PixivisionArticleOrm).where(PixivisionArticleOrm.id == id_)
        if aid is not None:
            stmt = stmt.values(aid=aid)
        if title is not None:
            stmt = stmt.values(title=title)
        if description is not None:
            stmt = stmt.values(description=description)
        if tags is not None:
            stmt = stmt.values(tags=tags)
        if artworks_id is not None:
            stmt = stmt.values(artworks_id=artworks_id)
        if url is not None:
            stmt = stmt.values(url=url)
        stmt = stmt.values(updated_at=datetime.now())
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)

    async def delete(self, id_: int) -> None:
        stmt = delete(PixivisionArticleOrm).where(PixivisionArticleOrm.id == id_)
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)


__all__ = [
    'PixivisionArticle',
    'PixivisionArticleDAL'
]
