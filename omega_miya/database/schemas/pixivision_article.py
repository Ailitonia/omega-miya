"""
@Author         : Ailitonia
@Date           : 2022/03/27 15:37
@FileName       : pixivision_article.py
@Project        : nonebot2_miya 
@Description    : PixivisionArticle Model
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
from ..model import PixivisionArticleOrm


class PixivisionArticleUniqueModel(BaseDatabaseModel):
    """数据库对象唯一性模型"""
    aid: int


class PixivisionArticleRequireModel(PixivisionArticleUniqueModel):
    """数据库对象变更请求必须数据模型"""
    title: str
    description: str
    tags: str
    artworks_id: str
    url: str


class PixivisionArticleModel(PixivisionArticleRequireModel):
    """数据库对象完整模型"""
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class PixivisionArticleModelResult(DatabaseModelResult):
    """数据库查询结果基类"""
    result: Optional["PixivisionArticleModel"]


class PixivisionArticleModelListResult(DatabaseModelListResult):
    """PixivisionArticle 查询结果类"""
    result: List["PixivisionArticleModel"]


class PixivisionArticle(BaseDatabase):
    orm_model = PixivisionArticleOrm
    unique_model = PixivisionArticleUniqueModel
    require_model = PixivisionArticleRequireModel
    data_model = PixivisionArticleModel
    self_model: PixivisionArticleUniqueModel

    def __init__(self, aid: int):
        self.self_model = PixivisionArticleUniqueModel(aid=aid)

    @classmethod
    def _make_all_select(cls) -> Select:
        stmt = select(cls.orm_model).with_for_update(read=True).order_by(cls.orm_model.aid)
        return stmt

    def _make_unique_self_select(self) -> Select:
        stmt = select(self.orm_model).with_for_update(read=True).\
            where(self.orm_model.aid == self.self_model.aid).\
            order_by(self.orm_model.aid)
        return stmt

    def _make_unique_self_update(self, new_model: PixivisionArticleRequireModel) -> Update:
        stmt = update(self.orm_model).\
            where(self.orm_model.aid == self.self_model.aid).\
            values(**new_model.dict()).\
            values(updated_at=datetime.now()).\
            execution_options(synchronize_session="fetch")
        return stmt

    def _make_unique_self_delete(self) -> Delete:
        stmt = delete(self.orm_model).\
            where(self.orm_model.aid == self.self_model.aid).\
            execution_options(synchronize_session="fetch")
        return stmt

    async def update_unique_self(
            self,
            title: str,
            description: str,
            tags: str,
            artworks_id: str,
            url: str) -> BoolResult:
        return await self._update_unique_self(new_model=self.require_model(
            aid=self.self_model.aid,
            title=title,
            description=description,
            tags=tags,
            artworks_id=artworks_id,
            url=url
        ))

    async def add_upgrade_unique_self(
            self,
            title: str,
            description: str,
            tags: str,
            artworks_id: str,
            url: str) -> BoolResult:
        return await self._add_upgrade_unique_self(new_model=self.require_model(
            aid=self.self_model.aid,
            title=title,
            description=description,
            tags=tags,
            artworks_id=artworks_id,
            url=url
        ))

    async def query(self) -> PixivisionArticleModelResult:
        return PixivisionArticleModelResult.parse_obj(await self.query_unique_self())

    @classmethod
    async def query_all(cls) -> PixivisionArticleModelListResult:
        return PixivisionArticleModelListResult.parse_obj(await cls._query_all())


__all__ = [
    'PixivisionArticle'
]
