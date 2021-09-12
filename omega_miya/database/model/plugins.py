"""
@Author         : Ailitonia
@Date           : 2021/09/12 12:19
@FileName       : plugins.py
@Project        : nonebot2_miya 
@Description    : 数据库 plugins 表 module
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Optional
from omega_miya.database.database import BaseDB
from omega_miya.database.class_result import Result
from omega_miya.database.tables import OmegaPlugins
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBPlugin(object):
    def __init__(self, plugin_name: str):
        self.plugin_name = plugin_name

    async def update(
            self,
            enabled: Optional[int] = None,
            *,
            matchers: Optional[int] = None,
            info: Optional[str] = None
    ) -> Result.IntResult:
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        # 已存在则更新
                        session_result = await session.execute(
                            select(OmegaPlugins).where(OmegaPlugins.plugin_name == self.plugin_name)
                        )
                        exist_plugin = session_result.scalar_one()
                        if enabled is not None:
                            exist_plugin.enabled = enabled
                        if matchers is not None:
                            exist_plugin.matchers = matchers
                        if info is not None:
                            exist_plugin.info = info
                        exist_plugin.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        # 不存在则添加信息
                        if enabled is None:
                            enabled = 1
                        new_plugin = OmegaPlugins(
                            plugin_name=self.plugin_name,
                            enabled=enabled,
                            matchers=matchers,
                            info=info,
                            created_at=datetime.now())
                        session.add(new_plugin)
                        result = Result.IntResult(error=False, info='Success added', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info=f'{self.plugin_name} MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=f'{self.plugin_name} update failed, {repr(e)}', result=-1)
        return result

    async def get_enabled_status(self) -> Result.IntResult:
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(OmegaPlugins.enabled).where(OmegaPlugins.plugin_name == self.plugin_name)
                    )
                    enabled = session_result.scalar_one()
                    result = Result.IntResult(error=False, info='Success', result=enabled)
                except NoResultFound:
                    result = Result.IntResult(error=True, info='NoResultFound', result=-1)
                except MultipleResultsFound:
                    result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
                except Exception as e:
                    result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result


__all__ = [
    'DBPlugin'
]
