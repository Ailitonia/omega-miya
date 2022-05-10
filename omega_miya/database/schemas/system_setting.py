"""
@Author         : Ailitonia
@Date           : 2022/03/09 20:37
@FileName       : system_setting.py
@Project        : nonebot2_miya 
@Description    : SystemSetting model
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
from ..model import SystemSettingOrm


class SystemSettingUniqueModel(BaseDatabaseModel):
    """数据库对象唯一性模型"""
    setting_name: str


class SystemSettingRequireModel(SystemSettingUniqueModel):
    """数据库对象变更请求必须数据模型"""
    setting_value: str
    info: Optional[str]


class SystemSettingModel(SystemSettingRequireModel):
    """数据库对象完整模型"""
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class SystemSettingModelResult(DatabaseModelResult):
    """数据库查询结果基类"""
    result: Optional["SystemSettingModel"]


class SystemSettingModelListResult(DatabaseModelListResult):
    """SystemSetting 查询结果类"""
    result: List["SystemSettingModel"]


class SystemSetting(BaseDatabase):
    orm_model = SystemSettingOrm
    unique_model = SystemSettingUniqueModel
    require_model = SystemSettingRequireModel
    data_model = SystemSettingModel
    self_model: SystemSettingUniqueModel

    def __init__(self, setting_name: str):
        self.self_model = SystemSettingUniqueModel(setting_name=setting_name)

    @classmethod
    def _make_all_select(cls) -> Select:
        stmt = select(cls.orm_model).with_for_update(read=True).order_by(cls.orm_model.setting_name)
        return stmt

    def _make_unique_self_select(self) -> Select:
        stmt = select(self.orm_model).with_for_update(read=True).\
            where(self.orm_model.setting_name == self.self_model.setting_name).\
            order_by(self.orm_model.setting_name)
        return stmt

    def _make_unique_self_update(self, new_model: SystemSettingRequireModel) -> Update:
        stmt = update(self.orm_model).\
            where(self.orm_model.setting_name == self.self_model.setting_name).\
            values(**new_model.dict()).\
            values(updated_at=datetime.now()).\
            execution_options(synchronize_session="fetch")
        return stmt

    def _make_unique_self_delete(self) -> Delete:
        stmt = delete(self.orm_model).\
            where(self.orm_model.setting_name == self.self_model.setting_name).\
            execution_options(synchronize_session="fetch")
        return stmt

    async def update_unique_self(self, setting_value: str, info: Optional[str] = None) -> BoolResult:
        return await self._update_unique_self(new_model=self.require_model(
            setting_name=self.self_model.setting_name,
            setting_value=setting_value,
            info=info
        ))

    async def add_upgrade_unique_self(self, setting_value: str, info: Optional[str] = None) -> BoolResult:
        return await self._add_upgrade_unique_self(new_model=self.require_model(
            setting_name=self.self_model.setting_name,
            setting_value=setting_value,
            info=info
        ))

    async def query(self) -> SystemSettingModelResult:
        return SystemSettingModelResult.parse_obj(await self.query_unique_self())

    @classmethod
    async def query_all(cls) -> SystemSettingModelListResult:
        return SystemSettingModelListResult.parse_obj(await cls._query_all())


__all__ = [
    'SystemSetting'
]
