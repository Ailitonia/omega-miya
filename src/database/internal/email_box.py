"""
@Author         : Ailitonia
@Date           : 2022/12/04 16:11
@FileName       : email_box.py
@Project        : nonebot2_miya 
@Description    : EmailBox DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import delete, select, update

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayerModel, BaseDataQueryResultModel
from ..schema import EmailBoxOrm, EmailBoxBindOrm


class EmailBox(BaseDataQueryResultModel):
    """邮箱 Model"""
    id: int
    address: str
    server_host: str
    protocol: str
    port: int
    password: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EmailBoxDAL(BaseDataAccessLayerModel[EmailBoxOrm, EmailBox]):
    """邮箱 数据库操作对象"""

    async def query_unique(self, address: str) -> EmailBox:
        stmt = select(EmailBoxOrm).where(EmailBoxOrm.address == address)
        session_result = await self.db_session.execute(stmt)
        return EmailBox.model_validate(session_result.scalar_one())

    async def query_entity_bound_all(self, entity_index_id: int) -> list[EmailBox]:
        """查询 Entity 所绑定的全部邮箱"""
        stmt = (select(EmailBoxOrm)
                .join(EmailBoxBindOrm)
                .where(EmailBoxBindOrm.entity_index_id == entity_index_id)
                .order_by(EmailBoxOrm.address))
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[EmailBox], session_result.scalars().all())

    async def query_all(self) -> list[EmailBox]:
        stmt = select(EmailBoxOrm).order_by(EmailBoxOrm.address)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[EmailBox], session_result.scalars().all())

    async def add(self, address: str, server_host: str, protocol: str, port: int, password: str) -> None:
        new_obj = EmailBoxOrm(address=address, server_host=server_host, protocol=protocol, port=port,
                              password=password, created_at=datetime.now())
        await self._add(new_obj)

    async def upsert(self, *args, **kwargs) -> None:
        raise NotImplementedError

    async def update(
            self,
            id_: int,
            *,
            address: Optional[str] = None,
            server_host: Optional[str] = None,
            protocol: Optional[str] = None,
            port: Optional[int] = None,
            password: Optional[str] = None
    ) -> None:
        stmt = update(EmailBoxOrm).where(EmailBoxOrm.id == id_)
        if address is not None:
            stmt = stmt.values(address=address)
        if server_host is not None:
            stmt = stmt.values(server_host=server_host)
        if protocol is not None:
            stmt = stmt.values(protocol=protocol)
        if port is not None:
            stmt = stmt.values(port=port)
        if password is not None:
            stmt = stmt.values(password=password)
        stmt = stmt.values(updated_at=datetime.now())
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)

    async def delete(self, id_: int) -> None:
        stmt = delete(EmailBoxOrm).where(EmailBoxOrm.id == id_)
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)


__all__ = [
    'EmailBox',
    'EmailBoxDAL',
]
