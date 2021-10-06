"""
@Author         : Ailitonia
@Date           : 2021/08/14 18:14
@FileName       : statistic.py
@Project        : nonebot2_miya 
@Description    : 数据库统计表model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Optional
from omega_miya.database.database import BaseDB
from omega_miya.database.class_result import Result
from omega_miya.database.tables import OmegaStatistics
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.sql.expression import func


class DBStatistic(object):
    def __init__(self, self_bot_id: int):
        self.self_bot_id = self_bot_id

    async def add(self,
                  module_name: str,
                  plugin_name: str,
                  group_id: int,
                  user_id: int,
                  using_datetime: datetime,
                  *,
                  raw_message: Optional[str] = None,
                  info: Optional[str] = None) -> Result.IntResult:
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    new_statistic = OmegaStatistics(module_name=module_name, plugin_name=plugin_name,
                                                    self_bot_id=self.self_bot_id, group_id=group_id, user_id=user_id,
                                                    using_datetime=using_datetime, raw_message=raw_message, info=info,
                                                    created_at=datetime.now())
                    session.add(new_statistic)
                await session.commit()
                result = Result.IntResult(error=False, info='Success add', result=0)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    @classmethod
    async def get_total_statistic(cls, *, start_time: Optional[datetime] = None) -> Result.TupleListResult:
        """
        :param start_time: 统计起始时间, 为空则返回全部
        :return: List[Tuple[plugin_name, count]]
        """
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    # 构造查询
                    query = select(func.count(OmegaStatistics.module_name), OmegaStatistics.plugin_name)
                    if start_time:
                        query = query.where(OmegaStatistics.using_datetime >= start_time)
                    query = query.group_by(OmegaStatistics.plugin_name)
                    # 执行查询
                    session_result = await session.execute(query)
                    res = [(plugin_name, count) for count, plugin_name in session_result.all()]
                    result = Result.TupleListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.TupleListResult(error=True, info=repr(e), result=[])
        return result

    async def get_bot_statistic(self, *, start_time: Optional[datetime] = None) -> Result.TupleListResult:
        """
        :param start_time: 统计起始时间, 为空则返回全部
        :return: List[Tuple[plugin_name, count]]
        """
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    # 构造查询
                    query = select(func.count(OmegaStatistics.module_name), OmegaStatistics.plugin_name)
                    if start_time:
                        query = query.where(OmegaStatistics.using_datetime >= start_time)
                    query = query.where(
                        OmegaStatistics.self_bot_id == self.self_bot_id).group_by(OmegaStatistics.plugin_name)
                    # 执行查询
                    session_result = await session.execute(query)
                    res = [(plugin_name, count) for count, plugin_name in session_result.all()]
                    result = Result.TupleListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.TupleListResult(error=True, info=repr(e), result=[])
        return result

    async def get_user_statistic(
            self, user_id: int, *, start_time: Optional[datetime] = None) -> Result.TupleListResult:
        """
        :param user_id: 用户qq号
        :param start_time: 统计起始时间, 为空则返回全部
        :return: List[Tuple[plugin_name, count]]
        """
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    # 构造查询
                    query = select(func.count(OmegaStatistics.module_name), OmegaStatistics.plugin_name)
                    if start_time:
                        query = query.where(OmegaStatistics.using_datetime >= start_time)
                    query = query.where(
                        OmegaStatistics.self_bot_id == self.self_bot_id).where(OmegaStatistics.user_id == user_id)
                    query = query.group_by(OmegaStatistics.plugin_name)
                    # 执行查询
                    session_result = await session.execute(query)
                    res = [(plugin_name, count) for count, plugin_name in session_result.all()]
                    result = Result.TupleListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.TupleListResult(error=True, info=repr(e), result=[])
        return result

    async def get_group_statistic(
            self, group_id: int, *, start_time: Optional[datetime] = None) -> Result.TupleListResult:
        """
        :param group_id: 群号
        :param start_time: 统计起始时间, 为空则返回全部
        :return: List[Tuple[plugin_name, count]]
        """
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    # 构造查询
                    query = select(func.count(OmegaStatistics.module_name), OmegaStatistics.plugin_name)
                    if start_time:
                        query = query.where(OmegaStatistics.using_datetime >= start_time)
                    query = query.where(
                        OmegaStatistics.self_bot_id == self.self_bot_id).where(OmegaStatistics.group_id == group_id)
                    query = query.group_by(OmegaStatistics.plugin_name)
                    # 执行查询
                    session_result = await session.execute(query)
                    res = [(plugin_name, count) for count, plugin_name in session_result.all()]
                    result = Result.TupleListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.TupleListResult(error=True, info=repr(e), result=[])
        return result
