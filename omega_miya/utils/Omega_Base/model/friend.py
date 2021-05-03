from omega_miya.utils.Omega_Base.database import NBdb
from omega_miya.utils.Omega_Base.class_result import Result
from omega_miya.utils.Omega_Base.tables import Friends
from .user import DBUser
from typing import Optional
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBFriend(DBUser):
    async def set_friend(
            self, nickname: str, remark: Optional[str] = None, private_permissions: Optional[int] = None
    ) -> Result.IntResult:

        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(Friends).where(Friends.user_id == user_id_result.result)
                        )
                        exist_friend = session_result.scalar_one()
                        exist_friend.nickname = nickname
                        exist_friend.remark = remark
                        if private_permissions:
                            exist_friend.private_permissions = private_permissions
                        exist_friend.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        if private_permissions:
                            new_friend = Friends(user_id=user_id_result.result, nickname=nickname, remark=remark,
                                                 private_permissions=private_permissions, created_at=datetime.now())
                        else:
                            new_friend = Friends(user_id=user_id_result.result, nickname=nickname, remark=remark,
                                                 private_permissions=0, created_at=datetime.now())
                        session.add(new_friend)
                        result = Result.IntResult(error=False, info='Success added', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def del_friend(self) -> Result.IntResult:
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(Friends).where(Friends.user_id == user_id_result.result)
                    )
                    exist_friend = session_result.scalar_one()
                    await session.delete(exist_friend)
                await session.commit()
                result = Result.IntResult(error=False, info='Success', result=0)
            except NoResultFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='NoResultFound', result=-1)
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def set_private_permission(self, private_permissions: int) -> Result.IntResult:
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(Friends).where(Friends.user_id == user_id_result.result)
                    )
                    exist_friend = session_result.scalar_one()
                    exist_friend.private_permissions = private_permissions
                    exist_friend.updated_at = datetime.now()
                await session.commit()
                result = Result.IntResult(error=False, info='Success upgraded', result=0)
            except NoResultFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='NoResultFound', result=-1)
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result
