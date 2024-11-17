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

from sqlalchemy import delete, select, update

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayerModel, BaseDataQueryResultModel
from ..schema import PluginOrm


class Plugin(BaseDataQueryResultModel):
    """插件 Model"""
    plugin_name: str
    module_name: str
    enabled: int
    info: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PluginDAL(BaseDataAccessLayerModel[PluginOrm, Plugin]):
    """插件 数据库操作对象"""

    async def query_unique(self, plugin_name: str, module_name: str) -> Plugin:
        stmt = (select(PluginOrm)
                .where(PluginOrm.plugin_name == plugin_name)
                .where(PluginOrm.module_name == module_name))
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

    async def add(
            self,
            plugin_name: str,
            module_name: str,
            enabled: int,
            info: str | None = None,
    ) -> None:
        new_obj = PluginOrm(plugin_name=plugin_name, module_name=module_name,
                            enabled=enabled, info=info, created_at=datetime.now())
        await self._add(new_obj)

    async def upsert(
            self,
            plugin_name: str,
            module_name: str,
            enabled: int,
            info: str | None = None,
    ) -> None:
        obj_attrs = {
            'plugin_name': plugin_name,
            'module_name': module_name,
            'enabled': enabled,
            'updated_at': datetime.now()
        }
        if info is not None:
            obj_attrs.update({'info': info})
        await self._merge(PluginOrm(**obj_attrs))

    async def update(
            self,
            plugin_name: str,
            module_name: str,
            *,
            enabled: int | None = None,
            info: str | None = None,
    ) -> None:
        stmt = (update(PluginOrm)
                .where(PluginOrm.plugin_name == plugin_name)
                .where(PluginOrm.module_name == module_name))
        if enabled is not None:
            stmt = stmt.values(enabled=enabled)
        if info is not None:
            stmt = stmt.values(info=info)
        stmt = stmt.values(updated_at=datetime.now())
        stmt.execution_options(synchronize_session='fetch')
        await self.db_session.execute(stmt)

    async def delete(self, plugin_name: str, module_name: str) -> None:
        stmt = (delete(PluginOrm)
                .where(PluginOrm.plugin_name == plugin_name)
                .where(PluginOrm.module_name == module_name))
        stmt.execution_options(synchronize_session='fetch')
        await self.db_session.execute(stmt)


__all__ = [
    'Plugin',
    'PluginDAL',
]
