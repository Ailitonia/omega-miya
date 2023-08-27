"""
@Author         : Ailitonia
@Date           : 2022/12/04 14:43
@FileName       : auth_setting.py
@Project        : nonebot2_miya 
@Description    : AuthSetting DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy import update, delete
from typing import Optional

from pydantic import BaseModel, parse_obj_as

from ..model import BaseDataAccessLayerModel, AuthSettingOrm


class AuthSetting(BaseModel):
    """授权配置 Model"""
    id: int
    entity_index_id: int
    module: str
    plugin: str
    node: str
    available: int
    value: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        extra = 'ignore'
        orm_mode = True
        allow_mutation = False


class AuthSettingDAL(BaseDataAccessLayerModel):
    """授权配置 数据库操作对象"""

    async def query_unique(self, entity_index_id: int, module: str, plugin: str, node: str) -> AuthSetting:
        stmt = select(AuthSettingOrm).\
            where(AuthSettingOrm.entity_index_id == entity_index_id).\
            where(AuthSettingOrm.module == module).\
            where(AuthSettingOrm.plugin == plugin).\
            where(AuthSettingOrm.node == node)
        session_result = await self.db_session.execute(stmt)
        return AuthSetting.from_orm(session_result.scalar_one())

    async def query_entity_all(
            self,
            entity_index_id: int,
            module: Optional[str] = None,
            plugin: Optional[str] = None
    ) -> list[AuthSetting]:
        """查询 Entity 具有的全部/某个模块/插件的权限配置"""
        stmt = select(AuthSettingOrm).where(AuthSettingOrm.entity_index_id == entity_index_id)
        if module is not None:
            stmt = stmt.where(AuthSettingOrm.module == module)
        if plugin is not None:
            stmt = stmt.where(AuthSettingOrm.plugin == plugin)
        stmt = stmt.order_by(AuthSettingOrm.module)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[AuthSetting], session_result.scalars().all())

    async def query_module_plugin_all(self, module: str, plugin: str) -> list[AuthSetting]:
        """查询某个模块/插件所有已配置的权限配置"""
        stmt = select(AuthSettingOrm).\
            where(AuthSettingOrm.module == module).\
            where(AuthSettingOrm.plugin == plugin).\
            order_by(AuthSettingOrm.module)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[AuthSetting], session_result.scalars().all())

    async def query_all(self) -> list[AuthSetting]:
        stmt = select(AuthSettingOrm).order_by(AuthSettingOrm.entity_index_id)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[AuthSetting], session_result.scalars().all())

    async def add(
            self,
            entity_index_id: int,
            module: str,
            plugin: str,
            node: str,
            available: int,
            value: Optional[str] = None
    ) -> None:
        new_obj = AuthSettingOrm(entity_index_id=entity_index_id, module=module, plugin=plugin, node=node,
                                 available=available, value=value, created_at=datetime.now())
        self.db_session.add(new_obj)
        await self.db_session.flush()

    async def update(
            self,
            id_: int,
            *,
            entity_index_id: Optional[int] = None,
            module: Optional[str] = None,
            plugin: Optional[str] = None,
            node: Optional[str] = None,
            available: Optional[int] = None,
            value: Optional[str] = None
    ) -> None:
        stmt = update(AuthSettingOrm).where(AuthSettingOrm.id == id_)
        if entity_index_id is not None:
            stmt = stmt.values(entity_index_id=entity_index_id)
        if module is not None:
            stmt = stmt.values(module=module)
        if plugin is not None:
            stmt = stmt.values(plugin=plugin)
        if node is not None:
            stmt = stmt.values(node=node)
        if available is not None:
            stmt = stmt.values(available=available)
        if value is not None:
            stmt = stmt.values(value=value)
        stmt = stmt.values(updated_at=datetime.now())
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)

    async def delete(self, id_: int) -> None:
        stmt = delete(AuthSettingOrm).where(AuthSettingOrm.id == id_)
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)


__all__ = [
    'AuthSetting',
    'AuthSettingDAL'
]
