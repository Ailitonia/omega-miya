"""
@Author         : Ailitonia
@Date           : 2022/03/27 14:36
@FileName       : pixiv_artwork_page.py
@Project        : nonebot2_miya 
@Description    : PixivArtworkPage Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import update, delete
from sqlalchemy.future import select
from omega_miya.result import BoolResult
from .base_model import (BaseDatabaseModel, BaseDatabase, Select, Update, Delete,
                         DatabaseModelResult, DatabaseModelListResult)
from ..model import PixivArtworkPageOrm, PixivArtworkOrm


class PixivArtworkPageUniqueModel(BaseDatabaseModel):
    """数据库对象唯一性模型"""
    artwork_id: int
    page: int


class PixivArtworkPageRequireModel(PixivArtworkPageUniqueModel):
    """数据库对象变更请求必须数据模型"""
    original: str
    regular: str
    small: str
    thumb_mini: str


class PixivArtworkPageModel(PixivArtworkPageRequireModel):
    """数据库对象完整模型"""
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class PixivArtworkPageModelResult(DatabaseModelResult):
    """数据库查询结果基类"""
    result: Optional["PixivArtworkPageModel"]


class PixivArtworkPageModelListResult(DatabaseModelListResult):
    """PixivArtworkPage 查询结果类"""
    result: List["PixivArtworkPageModel"]


class PixivArtworkPage(BaseDatabase):
    orm_model = PixivArtworkPageOrm
    unique_model = PixivArtworkPageUniqueModel
    require_model = PixivArtworkPageRequireModel
    data_model = PixivArtworkPageModel
    self_model: PixivArtworkPageUniqueModel

    def __init__(self, artwork_id: int, page: int):
        self.self_model = PixivArtworkPageUniqueModel(artwork_id=artwork_id, page=page)

    @classmethod
    def _make_all_select(cls) -> Select:
        stmt = select(cls.orm_model).with_for_update(read=True).order_by(cls.orm_model.artwork_id)
        return stmt

    def _make_unique_self_select(self) -> Select:
        stmt = select(self.orm_model).\
            where(self.orm_model.artwork_id == self.self_model.artwork_id).\
            where(self.orm_model.page == self.self_model.page).\
            order_by(self.orm_model.artwork_id)
        return stmt

    def _make_unique_self_update(self, new_model: PixivArtworkPageRequireModel) -> Update:
        stmt = update(self.orm_model).\
            where(self.orm_model.artwork_id == self.self_model.artwork_id).\
            where(self.orm_model.page == self.self_model.page).\
            values(**new_model.dict()).\
            values(updated_at=datetime.now()).\
            execution_options(synchronize_session="fetch")
        return stmt

    def _make_unique_self_delete(self) -> Delete:
        stmt = delete(self.orm_model).\
            where(self.orm_model.artwork_id == self.self_model.artwork_id).\
            where(self.orm_model.page == self.self_model.page).\
            execution_options(synchronize_session="fetch")
        return stmt

    async def update_unique_self(self, original: str, regular: str, small: str, thumb_mini: str) -> BoolResult:
        return await self._update_unique_self(new_model=self.require_model(
            artwork_id=self.self_model.artwork_id,
            page=self.self_model.page,
            original=original,
            regular=regular,
            small=small,
            thumb_mini=thumb_mini
        ))

    async def add_upgrade_unique_self(self, original: str, regular: str, small: str, thumb_mini: str) -> BoolResult:
        return await self._add_upgrade_unique_self(new_model=self.require_model(
            artwork_id=self.self_model.artwork_id,
            page=self.self_model.page,
            original=original,
            regular=regular,
            small=small,
            thumb_mini=thumb_mini
        ))

    async def query(self) -> PixivArtworkPageModelResult:
        return PixivArtworkPageModelResult.parse_obj(await self.query_unique_self())

    @classmethod
    async def query_all_pages_by_artwork_index_id(cls, id_: int) -> PixivArtworkPageModelListResult:
        stmt = select(cls.orm_model).with_for_update(read=True).\
            where(cls.orm_model.artwork_id == id_).order_by(cls.orm_model.page)
        return PixivArtworkPageModelListResult.parse_obj(await cls._query_all(stmt=stmt))

    @classmethod
    async def query_all_pages_by_pid(cls, pid: int) -> PixivArtworkPageModelListResult:
        stmt = select(cls.orm_model).with_for_update(read=True).\
            join(PixivArtworkOrm).\
            where(PixivArtworkOrm.pid == pid).\
            order_by(cls.orm_model.page)
        return PixivArtworkPageModelListResult.parse_obj(await cls._query_all(stmt=stmt))


__all__ = [
    'PixivArtworkPage',
    'PixivArtworkPageModel'
]
