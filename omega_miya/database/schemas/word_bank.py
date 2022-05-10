"""
@Author         : Ailitonia
@Date           : 2022/03/27 17:31
@FileName       : word_bank.py
@Project        : nonebot2_miya 
@Description    : WordBank Model
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
from ..model import WordBankOrm


class WordBankUniqueModel(BaseDatabaseModel):
    """数据库对象唯一性模型"""
    key_word: str
    reply_entity: str


class WordBankRequireModel(WordBankUniqueModel):
    """数据库对象变更请求必须数据模型"""
    result_word: str


class WordBankModel(WordBankRequireModel):
    """数据库对象完整模型"""
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class WordBankModelResult(DatabaseModelResult):
    """数据库查询结果基类"""
    result: Optional["WordBankModel"]


class WordBankModelListResult(DatabaseModelListResult):
    """WordBank 查询结果类"""
    result: List["WordBankModel"]


class WordBank(BaseDatabase):
    orm_model = WordBankOrm
    unique_model = WordBankUniqueModel
    require_model = WordBankRequireModel
    data_model = WordBankModel
    self_model: WordBankUniqueModel

    def __init__(self, key_word: str, reply_entity: str):
        self.self_model = WordBankUniqueModel(key_word=key_word, reply_entity=reply_entity)

    @classmethod
    def _make_all_select(cls) -> Select:
        stmt = select(cls.orm_model).with_for_update(read=True).order_by(cls.orm_model.reply_entity)
        return stmt

    def _make_unique_self_select(self) -> Select:
        stmt = select(self.orm_model).with_for_update(read=True).\
            where(self.orm_model.key_word == self.self_model.key_word).\
            where(self.orm_model.reply_entity == self.self_model.reply_entity).\
            order_by(self.orm_model.reply_entity)
        return stmt

    def _make_unique_self_update(self, new_model: WordBankRequireModel) -> Update:
        stmt = update(self.orm_model).\
            where(self.orm_model.key_word == self.self_model.key_word).\
            where(self.orm_model.reply_entity == self.self_model.reply_entity).\
            values(**new_model.dict()).\
            values(updated_at=datetime.now()).\
            execution_options(synchronize_session="fetch")
        return stmt

    def _make_unique_self_delete(self) -> Delete:
        stmt = delete(self.orm_model).\
            where(self.orm_model.key_word == self.self_model.key_word).\
            where(self.orm_model.reply_entity == self.self_model.reply_entity).\
            execution_options(synchronize_session="fetch")
        return stmt

    async def update_unique_self(self, result_word: str) -> BoolResult:
        return await self._update_unique_self(new_model=self.require_model(
            key_word=self.self_model.key_word,
            reply_entity=self.self_model.reply_entity,
            result_word=result_word
        ))

    async def add_upgrade_unique_self(self, result_word: str) -> BoolResult:
        return await self._add_upgrade_unique_self(new_model=self.require_model(
            key_word=self.self_model.key_word,
            reply_entity=self.self_model.reply_entity,
            result_word=result_word
        ))

    async def query(self) -> WordBankModelResult:
        return WordBankModelResult.parse_obj(await self.query_unique_self())

    @classmethod
    async def query_all(cls) -> WordBankModelListResult:
        return WordBankModelListResult.parse_obj(await cls._query_all())

    @classmethod
    async def query_all_by_reply_entity(cls, reply_entity: str) -> WordBankModelListResult:
        stmt = select(cls.orm_model).with_for_update(read=True).\
            where(cls.orm_model.reply_entity == reply_entity).order_by(cls.orm_model.key_word)
        return WordBankModelListResult.parse_obj(await cls._query_all(stmt=stmt))


__all__ = [
    'WordBank'
]
