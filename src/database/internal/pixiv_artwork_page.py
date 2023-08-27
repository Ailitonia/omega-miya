"""
@Author         : Ailitonia
@Date           : 2022/12/04 21:44
@FileName       : pixiv_artwork_page.py
@Project        : nonebot2_miya 
@Description    : PixivArtworkPage DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy import update, delete
from typing import Optional

from pydantic import BaseModel, AnyUrl, parse_obj_as

from ..model import BaseDataAccessLayerModel, PixivArtworkPageOrm


class PixivArtworkPage(BaseModel):
    """Pixiv 作品页 Model"""
    id: int
    artwork_index_id: int
    page: int
    original: AnyUrl
    regular: AnyUrl
    small: AnyUrl
    thumb_mini: AnyUrl
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        extra = 'ignore'
        orm_mode = True
        allow_mutation = False


class PixivArtworkPageDAL(BaseDataAccessLayerModel):
    """Pixiv 作品页 数据库操作对象"""

    async def query_unique(self, artwork_index_id: int, page: int) -> PixivArtworkPage:
        stmt = select(PixivArtworkPageOrm).\
            where(PixivArtworkPageOrm.artwork_index_id == artwork_index_id).\
            where(PixivArtworkPageOrm.page == page)
        session_result = await self.db_session.execute(stmt)
        return PixivArtworkPage.from_orm(session_result.scalar_one())

    async def query_artwork_all(self, artwork_index_id: int) -> list[PixivArtworkPage]:
        stmt = select(PixivArtworkPageOrm).\
            where(PixivArtworkPageOrm.artwork_index_id == artwork_index_id).\
            order_by(PixivArtworkPageOrm.page)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[PixivArtworkPage], session_result.scalars().all())

    async def query_all(self) -> list[PixivArtworkPage]:
        raise NotImplementedError('method not supported')

    async def add(
            self,
            artwork_index_id: int,
            page: int,
            original: str,
            regular: str,
            small: str,
            thumb_mini: str
    ) -> None:
        new_obj = PixivArtworkPageOrm(artwork_index_id=artwork_index_id, page=page,
                                      original=original, regular=regular, small=small, thumb_mini=thumb_mini,
                                      created_at=datetime.now())
        self.db_session.add(new_obj)
        await self.db_session.flush()

    async def update(
            self,
            id_: int,
            *,
            artwork_index_id: Optional[int] = None,
            page: Optional[int] = None,
            original: Optional[str] = None,
            regular: Optional[str] = None,
            small: Optional[str] = None,
            thumb_mini: Optional[str] = None
    ) -> None:
        stmt = update(PixivArtworkPageOrm).where(PixivArtworkPageOrm.id == id_)
        if artwork_index_id is not None:
            stmt = stmt.values(artwork_index_id=artwork_index_id)
        if page is not None:
            stmt = stmt.values(page=page)
        if original is not None:
            stmt = stmt.values(original=original)
        if regular is not None:
            stmt = stmt.values(regular=regular)
        if small is not None:
            stmt = stmt.values(small=small)
        if thumb_mini is not None:
            stmt = stmt.values(thumb_mini=thumb_mini)
        stmt = stmt.values(updated_at=datetime.now())
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)

    async def delete(self, id_: int) -> None:
        stmt = delete(PixivArtworkPageOrm).where(PixivArtworkPageOrm.id == id_)
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)


__all__ = [
    'PixivArtworkPage',
    'PixivArtworkPageDAL'
]
