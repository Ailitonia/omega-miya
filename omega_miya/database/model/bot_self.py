"""
@Author         : Ailitonia
@Date           : 2021/05/23 19:32
@FileName       : bot_self.py
@Project        : nonebot2_miya 
@Description    : BotSelf Table Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from omega_miya.database.database import BaseDB
from omega_miya.database.class_result import Result
from omega_miya.database.tables import BotSelf
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBBot(object):
    def __init__(self, self_qq: int):
        self.self_qq = self_qq

    async def id(self) -> Result.IntResult:
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(BotSelf.id).where(BotSelf.self_qq == self.self_qq)
                    )
                    bot_table_id = session_result.scalar_one()
                    result = Result.IntResult(error=False, info='Success', result=bot_table_id)
                except NoResultFound:
                    result = Result.IntResult(error=True, info='NoResultFound', result=-1)
                except MultipleResultsFound:
                    result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
                except Exception as e:
                    result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def exist(self) -> bool:
        result = await self.id()
        return result.success()

    async def upgrade(self, status: int = 0, info: str = None) -> Result.IntResult:
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        # 已存在则更新表中已有信息
                        session_result = await session.execute(
                            select(BotSelf).where(BotSelf.self_qq == self.self_qq)
                        )
                        exist_bot = session_result.scalar_one()
                        exist_bot.status = status
                        if info:
                            exist_bot.info = info
                        exist_bot.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        # 不存在则在表中添加新信息
                        new_bot = BotSelf(self_qq=self.self_qq, status=status, info=info,
                                          created_at=datetime.now())
                        session.add(new_bot)
                        result = Result.IntResult(error=False, info='Success added', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result
