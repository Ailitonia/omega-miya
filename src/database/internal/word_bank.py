"""
@Author         : Ailitonia
@Date           : 2022/12/04 22:28
@FileName       : word_bank.py
@Project        : nonebot2_miya 
@Description    : WordBank DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime

from sqlalchemy import delete, select, update

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayerModel, BaseDataQueryResultModel
from ..schema import WordBankOrm


class WordBank(BaseDataQueryResultModel):
    """问答语料词句 Model"""
    id: int
    key_word: str
    reply_entity: str
    result_word: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class WordBankDAL(BaseDataAccessLayerModel[WordBankOrm, WordBank]):
    """问答语料词句 数据库操作对象"""

    async def query_unique(self, key_word: str, reply_entity: str) -> WordBank:
        stmt = (select(WordBankOrm)
                .where(WordBankOrm.key_word == key_word)
                .where(WordBankOrm.reply_entity == reply_entity))
        session_result = await self.db_session.execute(stmt)
        return WordBank.model_validate(session_result.scalar_one())

    async def query_reply_entity_all(self, reply_entity: str) -> list[WordBank]:
        """查询指定响应对象的问答"""
        stmt = select(WordBankOrm).where(WordBankOrm.reply_entity == reply_entity).order_by(WordBankOrm.reply_entity)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[WordBank], session_result.scalars().all())

    async def query_all(self) -> list[WordBank]:
        stmt = select(WordBankOrm).order_by(WordBankOrm.reply_entity)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[WordBank], session_result.scalars().all())

    async def add(self, key_word: str, reply_entity: str, result_word: str) -> None:
        new_obj = WordBankOrm(key_word=key_word, reply_entity=reply_entity,
                              result_word=result_word, created_at=datetime.now())
        await self._add(new_obj)

    async def upsert(self, *args, **kwargs) -> None:
        raise NotImplementedError

    async def update(
            self,
            id_: int,
            *,
            key_word: str | None = None,
            reply_entity: str | None = None,
            result_word: str | None = None
    ) -> None:
        stmt = update(WordBankOrm).where(WordBankOrm.id == id_)
        if key_word is not None:
            stmt = stmt.values(key_word=key_word)
        if reply_entity is not None:
            stmt = stmt.values(reply_entity=reply_entity)
        if result_word is not None:
            stmt = stmt.values(result_word=result_word)
        stmt = stmt.values(updated_at=datetime.now())
        stmt.execution_options(synchronize_session='fetch')
        await self.db_session.execute(stmt)

    async def delete(self, id_: int) -> None:
        stmt = delete(WordBankOrm).where(WordBankOrm.id == id_)
        stmt.execution_options(synchronize_session='fetch')
        await self.db_session.execute(stmt)


__all__ = [
    'WordBank',
    'WordBankDAL',
]
