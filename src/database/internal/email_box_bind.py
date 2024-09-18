"""
@Author         : Ailitonia
@Date           : 2022/12/04 16:29
@FileName       : email_box_bind.py
@Project        : nonebot2_miya 
@Description    : EmailBoxBind DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import update, delete
from sqlalchemy.future import select

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayerModel, BaseDataQueryResultModel
from ..schema import EmailBoxBindOrm


class EmailBoxBind(BaseDataQueryResultModel):
    """邮箱绑定 Model"""
    id: int
    email_box_index_id: int
    entity_index_id: int
    bind_info: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EmailBoxBindDAL(BaseDataAccessLayerModel[EmailBoxBind]):
    """邮箱绑定 数据库操作对象"""

    async def query_unique(self, email_box_index_id: int, entity_index_id: int) -> EmailBoxBind:
        stmt = (select(EmailBoxBindOrm)
                .where(EmailBoxBindOrm.email_box_index_id == email_box_index_id)
                .where(EmailBoxBindOrm.entity_index_id == entity_index_id))
        session_result = await self.db_session.execute(stmt)
        return EmailBoxBind.model_validate(session_result.scalar_one())

    async def query_all(self) -> list[EmailBoxBind]:
        stmt = select(EmailBoxBindOrm).order_by(EmailBoxBindOrm.email_box_index_id)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[EmailBoxBind], session_result.scalars().all())

    async def add(self, email_box_index_id: int, entity_index_id: int, bind_info: Optional[str] = None) -> None:
        new_obj = EmailBoxBindOrm(email_box_index_id=email_box_index_id, entity_index_id=entity_index_id,
                                  bind_info=bind_info, created_at=datetime.now())
        self.db_session.add(new_obj)
        await self.db_session.flush()

    async def update(
            self,
            id_: int,
            *,
            email_box_index_id: Optional[int] = None,
            entity_index_id: Optional[int] = None,
            bind_info: Optional[str] = None
    ) -> None:
        stmt = update(EmailBoxBindOrm).where(EmailBoxBindOrm.id == id_)
        if email_box_index_id is not None:
            stmt = stmt.values(email_box_index_id=email_box_index_id)
        if entity_index_id is not None:
            stmt = stmt.values(entity_index_id=entity_index_id)
        if bind_info is not None:
            stmt = stmt.values(bind_info=bind_info)
        stmt = stmt.values(updated_at=datetime.now())
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)

    async def delete(self, id_: int) -> None:
        stmt = delete(EmailBoxBindOrm).where(EmailBoxBindOrm.id == id_)
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)


__all__ = [
    'EmailBoxBind',
    'EmailBoxBindDAL',
]
