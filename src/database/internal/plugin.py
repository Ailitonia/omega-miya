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

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayer, BaseDataOutModel
from ..schema import PluginOrm


class Plugin(BaseDataOutModel):
    """插件数据"""
    plugin_name: str
    module_name: str
    enabled: int
    info: str | None
    created_at: datetime | None
    updated_at: datetime | None


class PluginDAL(BaseDataAccessLayer[PluginOrm, Plugin]):
    """插件"""

    async def _count_all(self) -> int:
        """查询全表行数"""
        stmt = select(func.count()).select_from(PluginOrm)
        return (await self.db_session.execute(stmt)).scalar_one()

    async def _clear_all(self) -> None:
        """清空全表, 敏感操作, 方法内不执行 commit, 可由外层事务 rollback"""
        await self.db_session.execute(delete(PluginOrm))
        self.db_session.expunge_all()

    async def _select_unique(
            self,
            plugin_name: str,
            module_name: str,
            *,
            populate_existing: bool = False,
            with_for_update: bool = False,
            nowait_for_update: bool = False,
    ) -> PluginOrm:
        stmt = (select(PluginOrm)
                .where(PluginOrm.plugin_name == plugin_name)
                .where(PluginOrm.module_name == module_name))

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        if with_for_update:
            stmt = stmt.with_for_update(nowait=nowait_for_update)

        return (await self.db_session.execute(stmt)).scalar_one()

    async def query_unique(
            self,
            plugin_name: str,
            module_name: str,
            *,
            populate_existing: bool = False,
    ) -> Plugin:
        item = await self._select_unique(
            plugin_name,
            module_name,
            populate_existing=populate_existing,
        )
        return Plugin.model_validate(item)

    async def query_by_enable_status(
            self,
            enabled: int = 1,
            *,
            populate_existing: bool = False,
    ) -> list[Plugin]:
        """按启用状态查询插件

        启用状态, 1: 启用, 0: 禁用, -1: 失效或未安装
        """
        stmt = select(PluginOrm).where(PluginOrm.enabled == enabled).order_by(PluginOrm.plugin_name)

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        return parse_obj_as(list[Plugin], (await self.db_session.execute(stmt)).scalars().all())

    async def query_all(self, *, populate_existing: bool = False) -> list[Plugin]:
        stmt = select(PluginOrm).order_by(PluginOrm.plugin_name)

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        return parse_obj_as(list[Plugin], (await self.db_session.execute(stmt)).scalars().all())

    async def add(
            self,
            plugin_name: str,
            module_name: str,
            enabled: int,
            info: str | None = None,
    ) -> Plugin:
        """向数据库插入新行, 不校验唯一性

        尽量保证插入的是新数据时才使用, 冲突直接抛出异常
        """
        new_obj = PluginOrm(
            plugin_name=plugin_name,
            module_name=module_name,
            enabled=enabled,
            info=info,
        )
        self.db_session.add(new_obj)
        await self.db_session.flush()
        await self.db_session.refresh(new_obj)
        return Plugin.model_validate(new_obj)

    async def add_update_exist(
            self,
            plugin_name: str,
            module_name: str,
            enabled: int,
            info: str | None = None,
    ) -> Plugin:
        """向数据库插入新行, 存在则更新

        通过捕获异常实现, 性能较差, 且并发时仍可能出现死锁或需要重试
        """
        new_obj = PluginOrm(
            plugin_name=plugin_name,
            module_name=module_name,
            enabled=enabled,
            info=info,
        )

        try:
            async with self.safe_begin_transaction() as session:
                session.add(new_obj)
                await session.flush()
            await session.refresh(new_obj)
            return Plugin.model_validate(new_obj)
        except IntegrityError:
            if new_obj in self.db_session:
                self.db_session.expunge(new_obj)
            async with self.safe_begin_transaction() as session:
                exist_obj = await self._select_unique(
                    plugin_name,
                    module_name,
                    populate_existing=True,
                    with_for_update=True,
                )
                exist_obj.enabled = enabled
                exist_obj.info = info
                await session.flush()
            await session.refresh(exist_obj)
            return Plugin.model_validate(exist_obj)

    async def delete(
            self,
            plugin_name: str,
            module_name: str,
    ) -> None:
        stmt = (delete(PluginOrm)
                .where(PluginOrm.plugin_name == plugin_name)
                .where(PluginOrm.module_name == module_name))
        await self.db_session.execute(stmt)


__all__ = [
    'Plugin',
    'PluginDAL',
]
