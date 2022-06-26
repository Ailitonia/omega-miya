"""
@Author         : Ailitonia
@Date           : 2022/03/09 22:48
@FileName       : plugin.py
@Project        : nonebot2_miya 
@Description    : Plugin model
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
from ..model import PluginOrm


class PluginUniqueModel(BaseDatabaseModel):
    """数据库对象唯一性模型"""
    plugin_name: str
    module_name: str


class PluginRequireModel(PluginUniqueModel):
    """数据库对象变更请求必须数据模型"""
    enabled: int
    info: Optional[str]


class PluginModel(PluginRequireModel):
    """数据库对象完整模型"""
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class PluginModelResult(DatabaseModelResult):
    """数据库查询结果基类"""
    result: Optional["PluginModel"]


class PluginModelListResult(DatabaseModelListResult):
    """Plugin 查询结果类"""
    result: List["PluginModel"]


class Plugin(BaseDatabase):
    orm_model = PluginOrm
    unique_model = PluginUniqueModel
    require_model = PluginRequireModel
    data_model = PluginModel
    self_model: PluginUniqueModel

    def __init__(self, plugin_name: str, module_name: str):
        self.self_model = PluginUniqueModel(plugin_name=plugin_name, module_name=module_name)

    @classmethod
    def _make_all_select(cls) -> Select:
        stmt = select(cls.orm_model).with_for_update(read=True).order_by(cls.orm_model.plugin_name)
        return stmt

    def _make_unique_self_select(self) -> Select:
        stmt = select(self.orm_model).with_for_update(read=True).\
            where(self.orm_model.plugin_name == self.self_model.plugin_name).\
            where(self.orm_model.module_name == self.self_model.module_name).\
            order_by(self.orm_model.plugin_name)
        return stmt

    def _make_unique_self_update(self, new_model: PluginRequireModel) -> Update:
        stmt = update(self.orm_model).\
            where(self.orm_model.plugin_name == self.self_model.plugin_name).\
            where(self.orm_model.module_name == self.self_model.module_name).\
            values(**new_model.dict()).\
            values(updated_at=datetime.now()).\
            execution_options(synchronize_session="fetch")
        return stmt

    def _make_unique_self_delete(self) -> Delete:
        stmt = delete(self.orm_model).\
            where(self.orm_model.plugin_name == self.self_model.plugin_name).\
            where(self.orm_model.module_name == self.self_model.module_name).\
            execution_options(synchronize_session="fetch")
        return stmt

    async def update_unique_self(self, enabled: int, info: Optional[str] = None) -> BoolResult:
        return await self._update_unique_self(new_model=self.require_model(
            plugin_name=self.self_model.plugin_name,
            module_name=self.self_model.module_name,
            enabled=enabled,
            info=info
        ))

    async def add_upgrade_unique_self(self, enabled: int, info: Optional[str] = None) -> BoolResult:
        return await self._add_upgrade_unique_self(new_model=self.require_model(
            plugin_name=self.self_model.plugin_name,
            module_name=self.self_model.module_name,
            enabled=enabled,
            info=info
        ))

    async def add_only(self, enabled: int = 1, info: Optional[str] = None) -> BoolResult:
        return await self._add_only_without_upgrade_unique_self(new_model=self.require_model(
            plugin_name=self.self_model.plugin_name,
            module_name=self.self_model.module_name,
            enabled=enabled,
            info=info
        ))

    async def query(self) -> PluginModelResult:
        return PluginModelResult.parse_obj(await self.query_unique_self())

    @classmethod
    async def query_all(cls) -> PluginModelListResult:
        return PluginModelListResult.parse_obj(await cls._query_all())

    @classmethod
    async def query_by_enabled(cls, enabled: int = 1) -> PluginModelListResult:
        stmt = select(cls.orm_model).with_for_update(read=True).\
            where(cls.orm_model.enabled == enabled).order_by(cls.orm_model.plugin_name)
        return PluginModelListResult.parse_obj(await cls._query_all(stmt=stmt))


__all__ = [
    'Plugin'
]
