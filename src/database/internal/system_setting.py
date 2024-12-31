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

from sqlalchemy import delete, select, update

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayerModel, BaseDataQueryResultModel
from ..schema import SystemSettingOrm


class SystemSetting(BaseDataQueryResultModel):
    """系统参数 Model"""
    setting_name: str
    setting_key: str
    setting_value: str
    info: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SystemSettingDAL(BaseDataAccessLayerModel[SystemSettingOrm, SystemSetting]):
    """系统参数 数据库操作对象"""

    async def query_unique(self, setting_name: str, setting_key: str) -> SystemSetting:
        stmt = (select(SystemSettingOrm)
                .where(SystemSettingOrm.setting_name == setting_name)
                .where(SystemSettingOrm.setting_key == setting_key))
        session_result = await self.db_session.execute(stmt)
        return SystemSetting.model_validate(session_result.scalar_one())

    async def query_series(self, setting_name: str) -> list[SystemSetting]:
        stmt = select(SystemSettingOrm).where(SystemSettingOrm.setting_name == setting_name)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[SystemSetting], session_result.scalars().all())

    async def query_all(self) -> list[SystemSetting]:
        stmt = select(SystemSettingOrm).order_by(SystemSettingOrm.setting_name)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[SystemSetting], session_result.scalars().all())

    async def add(
            self,
            setting_name: str,
            setting_key: str,
            setting_value: str,
            info: str | None = None,
    ) -> None:
        new_obj = SystemSettingOrm(setting_name=setting_name, setting_key=setting_key,
                                   setting_value=setting_value, info=info, created_at=datetime.now())
        await self._add(new_obj)

    async def upsert(
            self,
            setting_name: str,
            setting_key: str,
            setting_value: str,
            info: str | None = None,
    ) -> None:
        obj_attrs = {
            'setting_name': setting_name,
            'setting_key': setting_key,
            'setting_value': setting_value,
            'updated_at': datetime.now()
        }
        if info is not None:
            obj_attrs.update({'info': info})
        await self._merge(SystemSettingOrm(**obj_attrs))

    async def update(
            self,
            setting_name: str,
            setting_key: str,
            *,
            setting_value: str | None = None,
            info: str | None = None,
    ) -> None:
        stmt = (update(SystemSettingOrm)
                .where(SystemSettingOrm.setting_name == setting_name)
                .where(SystemSettingOrm.setting_key == setting_key))
        if setting_value is not None:
            stmt = stmt.values(setting_value=setting_value)
        if info is not None:
            stmt = stmt.values(info=info)
        stmt = stmt.values(updated_at=datetime.now())
        stmt.execution_options(synchronize_session='fetch')
        await self.db_session.execute(stmt)

    async def delete(self, setting_name: str, setting_key: str) -> None:
        stmt = (delete(SystemSettingOrm)
                .where(SystemSettingOrm.setting_name == setting_name)
                .where(SystemSettingOrm.setting_key == setting_key))
        stmt.execution_options(synchronize_session='fetch')
        await self.db_session.execute(stmt)


__all__ = [
    'SystemSetting',
    'SystemSettingDAL',
]
