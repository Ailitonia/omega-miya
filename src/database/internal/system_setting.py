"""
@Author         : Ailitonia
@Date           : 2022/12/01 22:03
@FileName       : system_setting.py
@Project        : nonebot2_miya 
@Description    : System Setting DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy import update, delete
from typing import Optional

from pydantic import BaseModel, parse_obj_as

from ..model import BaseDataAccessLayerModel, SystemSettingOrm


class SystemSetting(BaseModel):
    """系统参数 Model"""
    id: int
    setting_name: str
    setting_value: str
    info: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        extra = 'ignore'
        orm_mode = True
        allow_mutation = False


class SystemSettingDAL(BaseDataAccessLayerModel):
    """系统参数 数据库操作对象"""

    async def query_unique(self, setting_name: str) -> SystemSetting:
        stmt = select(SystemSettingOrm).where(SystemSettingOrm.setting_name == setting_name)
        session_result = await self.db_session.execute(stmt)
        return SystemSetting.from_orm(session_result.scalar_one())

    async def query_all(self) -> list[SystemSetting]:
        stmt = select(SystemSettingOrm).order_by(SystemSettingOrm.setting_name)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[SystemSetting], session_result.scalars().all())

    async def add(self, setting_name: str, setting_value: str, info: Optional[str] = None) -> None:
        new_obj = SystemSettingOrm(setting_name=setting_name, setting_value=setting_value,
                                   info=info, created_at=datetime.now())
        self.db_session.add(new_obj)
        await self.db_session.flush()

    async def update(
            self,
            id_: int,
            *,
            setting_name: Optional[str] = None,
            setting_value: Optional[str] = None,
            info: Optional[str] = None
    ) -> None:
        stmt = update(SystemSettingOrm).where(SystemSettingOrm.id == id_)
        if setting_name is not None:
            stmt = stmt.values(setting_name=setting_name)
        if setting_value is not None:
            stmt = stmt.values(setting_value=setting_value)
        if info is not None:
            stmt = stmt.values(info=info)
        stmt = stmt.values(updated_at=datetime.now())
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)

    async def delete(self, id_: int) -> None:
        stmt = delete(SystemSettingOrm).where(SystemSettingOrm.id == id_)
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)


__all__ = [
    'SystemSetting',
    'SystemSettingDAL'
]
