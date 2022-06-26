"""
@Author         : Ailitonia
@Date           : 2022/03/26 15:15
@FileName       : auth_setting.py
@Project        : nonebot2_miya 
@Description    : AuthSetting Model
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
from ..model import AuthSettingOrm


class AuthSettingUniqueModel(BaseDatabaseModel):
    """数据库对象唯一性模型"""
    entity_id: int
    module: str
    plugin: str
    node: str


class AuthSettingRequireModel(AuthSettingUniqueModel):
    """数据库对象变更请求必须数据模型"""
    available: int
    value: Optional[str]


class AuthSettingModel(AuthSettingRequireModel):
    """数据库对象完整模型"""
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class AuthSettingModelResult(DatabaseModelResult):
    """数据库查询结果基类"""
    result: Optional["AuthSettingModel"]


class AuthSettingModelListResult(DatabaseModelListResult):
    """AuthSetting 查询结果类"""
    result: List["AuthSettingModel"]


class AuthSetting(BaseDatabase):
    orm_model = AuthSettingOrm
    unique_model = AuthSettingUniqueModel
    require_model = AuthSettingRequireModel
    data_model = AuthSettingModel
    self_model: AuthSettingUniqueModel

    def __init__(self, entity_id: int, module: str, plugin: str, node: str):
        self.self_model = AuthSettingUniqueModel(entity_id=entity_id, module=module, plugin=plugin, node=node)

    @classmethod
    def _make_all_select(cls) -> Select:
        stmt = select(cls.orm_model).with_for_update(read=True).order_by(cls.orm_model.entity_id)
        return stmt

    def _make_unique_self_select(self) -> Select:
        stmt = select(self.orm_model).with_for_update(read=True).\
            where(self.orm_model.entity_id == self.self_model.entity_id).\
            where(self.orm_model.module == self.self_model.module).\
            where(self.orm_model.plugin == self.self_model.plugin).\
            where(self.orm_model.node == self.self_model.node). \
            order_by(self.orm_model.entity_id)
        return stmt

    def _make_unique_self_update(self, new_model: AuthSettingRequireModel) -> Update:
        stmt = update(self.orm_model).\
            where(self.orm_model.entity_id == self.self_model.entity_id).\
            where(self.orm_model.module == self.self_model.module).\
            where(self.orm_model.plugin == self.self_model.plugin).\
            where(self.orm_model.node == self.self_model.node). \
            values(**new_model.dict()).\
            values(updated_at=datetime.now()).\
            execution_options(synchronize_session="fetch")
        return stmt

    def _make_unique_self_delete(self) -> Delete:
        stmt = delete(self.orm_model).\
            where(self.orm_model.entity_id == self.self_model.entity_id).\
            where(self.orm_model.module == self.self_model.module).\
            where(self.orm_model.plugin == self.self_model.plugin).\
            where(self.orm_model.node == self.self_model.node).\
            execution_options(synchronize_session="fetch")
        return stmt

    async def update_unique_self(self, available: int, value: Optional[str] = None) -> BoolResult:
        return await self._update_unique_self(new_model=self.require_model(
            entity_id=self.self_model.entity_id,
            module=self.self_model.module,
            plugin=self.self_model.plugin,
            node=self.self_model.node,
            available=available,
            value=value
        ))

    async def add_upgrade_unique_self(self, available: int, value: Optional[str] = None) -> BoolResult:
        return await self._add_upgrade_unique_self(new_model=self.require_model(
            entity_id=self.self_model.entity_id,
            module=self.self_model.module,
            plugin=self.self_model.plugin,
            node=self.self_model.node,
            available=available,
            value=value
        ))

    async def query(self) -> AuthSettingModelResult:
        return AuthSettingModelResult.parse_obj(await self.query_unique_self())

    @classmethod
    async def query_all(cls) -> AuthSettingModelListResult:
        return AuthSettingModelListResult.parse_obj(await cls._query_all())

    @classmethod
    async def query_all_by_entity_id(cls, entity_id: int) -> AuthSettingModelListResult:
        stmt = select(cls.orm_model).with_for_update(read=True).\
            where(cls.orm_model.entity_id == entity_id).order_by(cls.orm_model.node)
        return AuthSettingModelListResult.parse_obj(await cls._query_all(stmt=stmt))

    @classmethod
    async def query_entity_plugin_auth_nodes(
            cls,
            entity_id: int,
            module: str,
            plugin: str
    ) -> AuthSettingModelListResult:
        """查 Entity 具有的某个插件的权限配置"""
        stmt = select(cls.orm_model).with_for_update(read=True).\
            where(cls.orm_model.entity_id == entity_id).\
            where(cls.orm_model.module == module).\
            where(cls.orm_model.plugin == plugin).\
            order_by(cls.orm_model.node)
        return AuthSettingModelListResult.parse_obj(await cls._query_all(stmt=stmt))

    @classmethod
    async def query_plugin_auth_nodes(
            cls,
            module: str,
            plugin: str
    ) -> AuthSettingModelListResult:
        """查某个插件的所有已配置的权限配置"""
        stmt = select(cls.orm_model).with_for_update(read=True).\
            where(cls.orm_model.module == module).\
            where(cls.orm_model.plugin == plugin).\
            order_by(cls.orm_model.node)
        return AuthSettingModelListResult.parse_obj(await cls._query_all(stmt=stmt))


__all__ = [
    'AuthSetting',
    'AuthSettingModel'
]
