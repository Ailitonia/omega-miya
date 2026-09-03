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

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayer, BaseDataOutModel
from ..schema import SystemSettingOrm


class SystemSetting(BaseDataOutModel):
    """系统参数数据"""
    setting_name: str
    setting_key: str
    setting_value: str
    info: str | None
    created_at: datetime | None
    updated_at: datetime | None


class SystemSettingDAL(BaseDataAccessLayer[SystemSettingOrm, SystemSetting]):
    """系统参数"""

    async def _count_all(self) -> int:
        """查询全表行数"""
        stmt = select(func.count()).select_from(SystemSettingOrm)
        return (await self.db_session.execute(stmt)).scalar_one()

    async def _clear_all(self) -> None:
        """清空全表, 敏感操作, 方法内不执行 commit, 可由外层事务 rollback"""
        await self.db_session.execute(delete(SystemSettingOrm))
        self.db_session.expunge_all()

    async def _select_unique(
            self,
            setting_name: str,
            setting_key: str,
            *,
            populate_existing: bool = False,
            with_for_update: bool = False,
            nowait_for_update: bool = False,
    ) -> SystemSettingOrm:
        stmt = (select(SystemSettingOrm)
                .where(SystemSettingOrm.setting_name == setting_name)
                .where(SystemSettingOrm.setting_key == setting_key))

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        if with_for_update:
            stmt = stmt.with_for_update(nowait=nowait_for_update)

        return (await self.db_session.execute(stmt)).scalar_one()

    async def query_unique(
            self,
            setting_name: str,
            setting_key: str,
            *,
            populate_existing: bool = False,
    ) -> SystemSetting:
        item = await self._select_unique(
            setting_name,
            setting_key,
            populate_existing=populate_existing,
        )
        return SystemSetting.model_validate(item)

    async def query_series(
            self,
            setting_name: str,
            *,
            populate_existing: bool = False,
    ) -> list[SystemSetting]:
        stmt = select(SystemSettingOrm).where(SystemSettingOrm.setting_name == setting_name)

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        return parse_obj_as(list[SystemSetting], (await self.db_session.execute(stmt)).scalars().all())

    async def query_all(self, *, populate_existing: bool = False) -> list[SystemSetting]:
        stmt = select(SystemSettingOrm).order_by(SystemSettingOrm.setting_name)

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        return parse_obj_as(list[SystemSetting], (await self.db_session.execute(stmt)).scalars().all())

    async def add(
            self,
            setting_name: str,
            setting_key: str,
            setting_value: str,
            info: str | None = None,
    ) -> SystemSetting:
        """向数据库插入新行, 不校验唯一性

        尽量保证插入的是新数据时才使用, 冲突直接抛出异常
        """
        new_obj = SystemSettingOrm(
            setting_name=setting_name,
            setting_key=setting_key,
            setting_value=setting_value,
            info=info,
        )
        self.db_session.add(new_obj)
        await self.db_session.flush()
        return SystemSetting.model_validate(new_obj)

    async def add_update_exist(
            self,
            setting_name: str,
            setting_key: str,
            setting_value: str,
            info: str | None = None,
    ) -> SystemSetting:
        """向数据库插入新行, 存在则更新

        通过捕获异常实现, 性能较差, 且并发时仍可能出现死锁或需要重试
        """
        new_obj = SystemSettingOrm(
            setting_name=setting_name,
            setting_key=setting_key,
            setting_value=setting_value,
            info=info,
        )

        try:
            async with self.safe_begin_transaction() as session:
                session.add(new_obj)
                await session.flush()
            return SystemSetting.model_validate(new_obj)
        except IntegrityError as e:
            # 只有唯一约束冲突才进入"已存在则更新"分支, 其他完整性冲突(外键/非空等)原样抛出
            if not self._is_unique_conflict_error(e):
                raise
            if new_obj in self.db_session:
                self.db_session.expunge(new_obj)
            async with self.safe_begin_transaction() as session:
                exist_obj = await self._select_unique(
                    setting_name,
                    setting_key,
                    populate_existing=True,
                    with_for_update=True,
                )
                exist_obj.setting_value = setting_value
                exist_obj.info = info
                await session.flush()
            return SystemSetting.model_validate(exist_obj)

    async def delete(
            self,
            setting_name: str,
            setting_key: str,
    ) -> None:
        stmt = (delete(SystemSettingOrm)
                .where(SystemSettingOrm.setting_name == setting_name)
                .where(SystemSettingOrm.setting_key == setting_key))
        await self.db_session.execute(stmt)


__all__ = [
    'SystemSetting',
    'SystemSettingDAL',
]
