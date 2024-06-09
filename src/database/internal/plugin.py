"""
@Author         : Ailitonia
@Date           : 2022/12/02 21:48
@FileName       : plugin.py
@Project        : nonebot2_miya 
@Description    : Plugin DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import update, delete
from sqlalchemy.future import select

from src.compat import parse_obj_as

from ..model import BaseDataAccessLayerModel
from ..schema import PluginOrm


class Plugin(BaseModel):
    """插件 Model"""
    id: int
    plugin_name: str
    module_name: str
    enabled: int
    info: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(extra='ignore', from_attributes=True, frozen=True)


class PluginDAL(BaseDataAccessLayerModel):
    """插件 数据库操作对象"""

    async def query_unique(self, plugin_name: str, module_name: str) -> Plugin:
        stmt = select(PluginOrm).where(PluginOrm.plugin_name == plugin_name).where(PluginOrm.module_name == module_name)
        session_result = await self.db_session.execute(stmt)
        return Plugin.model_validate(session_result.scalar_one())

    async def query_by_enable_status(self, enabled: int = 1) -> list[Plugin]:
        """按启用状态查询插件

        :param enabled: 启用状态, 1: 启用, 0: 禁用, -1: 失效或未安装
        """
        stmt = select(PluginOrm).where(PluginOrm.enabled == enabled).order_by(PluginOrm.plugin_name)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[Plugin], session_result.scalars().all())

    async def query_all(self) -> list[Plugin]:
        stmt = select(PluginOrm).order_by(PluginOrm.plugin_name)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[Plugin], session_result.scalars().all())

    async def add(self, plugin_name: str, module_name: str, enabled: int, info: Optional[str] = None) -> None:
        new_obj = PluginOrm(plugin_name=plugin_name, module_name=module_name,
                            enabled=enabled, info=info, created_at=datetime.now())
        self.db_session.add(new_obj)
        await self.db_session.flush()

    async def update(
            self,
            id_: int,
            *,
            plugin_name: Optional[str] = None,
            module_name: Optional[str] = None,
            enabled: Optional[int] = None,
            info: Optional[str] = None
    ) -> None:
        stmt = update(PluginOrm).where(PluginOrm.id == id_)
        if plugin_name is not None:
            stmt = stmt.values(plugin_name=plugin_name)
        if module_name is not None:
            stmt = stmt.values(module_name=module_name)
        if enabled is not None:
            stmt = stmt.values(enabled=enabled)
        if info is not None:
            stmt = stmt.values(info=info)
        stmt = stmt.values(updated_at=datetime.now())
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)

    async def delete(self, id_: int) -> None:
        stmt = delete(PluginOrm).where(PluginOrm.id == id_)
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)


__all__ = [
    'Plugin',
    'PluginDAL'
]
