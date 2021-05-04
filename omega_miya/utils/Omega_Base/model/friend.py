from omega_miya.utils.Omega_Base.database import NBdb
from omega_miya.utils.Omega_Base.class_result import Result
from omega_miya.utils.Omega_Base.tables import Friends, User, Subscription, UserSub
from .user import DBUser
from .subscription import DBSubscription
from typing import Optional
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBFriend(DBUser):
    @classmethod
    async def list_exist_friends(cls) -> Result.ListResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(User.qq).
                        join(Friends).
                        where(User.id == Friends.user_id)
                    )
                    exist_friends = [x for x in session_result.scalars().all()]
                result = Result.ListResult(error=False, info='Success', result=exist_friends)
            except NoResultFound:
                result = Result.ListResult(error=True, info='NoResultFound', result=[])
            except MultipleResultsFound:
                result = Result.ListResult(error=True, info='MultipleResultsFound', result=[])
            except Exception as e:
                result = Result.ListResult(error=True, info=repr(e), result=[])
        return result

    async def exist(self) -> bool:
        user_id_result = await self.id()
        if user_id_result.error:
            return False

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(Friends.id).
                        join(User).
                        where(Friends.user_id == User.id).
                        where(Friends.user_id == user_id_result.result)
                    )
                    exist_friend = session_result.scalar_one()
                return True
            except Exception:
                return False

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
                    # 清空订阅
                    session_result = await session.execute(
                        select(UserSub).where(UserSub.user_id == user_id_result.result)
                    )
                    for exist_user_sub in session_result.scalars().all():
                        await session.delete(exist_user_sub)

                    # 删除好友表中该群组
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

    async def get_private_permission(self) -> Result.IntResult:
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(Friends.private_permissions).where(Friends.user_id == user_id_result.result)
                    )
                    private_permissions = session_result.scalar_one()
                result = Result.IntResult(error=False, info='Success', result=private_permissions)
            except NoResultFound:
                result = Result.IntResult(error=True, info='NoResultFound', result=-2)
            except MultipleResultsFound:
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def subscription_list(self) -> Result.ListResult:
        """
        :return: Result: List[Tuple[sub_type, sub_id, up_name]]
        """
        friend_check = await self.exist()
        if not friend_check:
            return Result.ListResult(error=True, info='Not friend', result=[])

        user_id_result = await self.id()
        if user_id_result.error:
            return Result.ListResult(error=True, info='User not exist', result=[])

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Subscription.sub_type, Subscription.sub_id, Subscription.up_name).
                        join(UserSub).
                        where(Subscription.id == UserSub.sub_id).
                        where(UserSub.user_id == user_id_result.result)
                    )
                    res = [(x[0], x[1], x[2]) for x in session_result.all()]
                    result = Result.ListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.ListResult(error=True, info=repr(e), result=[])
        return result

    async def subscription_list_by_type(self, sub_type: int) -> Result.ListResult:
        """
        :param sub_type: 订阅类型
        :return: Result: List[Tuple[sub_id, up_name]]
        """
        friend_check = await self.exist()
        if not friend_check:
            return Result.ListResult(error=True, info='Not friend', result=[])

        user_id_result = await self.id()
        if user_id_result.error:
            return Result.ListResult(error=True, info='User not exist', result=[])

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Subscription.sub_id, Subscription.up_name).
                        join(UserSub).
                        where(Subscription.sub_type == sub_type).
                        where(Subscription.id == UserSub.sub_id).
                        where(UserSub.user_id == user_id_result.result)
                    )
                    res = [(x[0], x[1]) for x in session_result.all()]
                    result = Result.ListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.ListResult(error=True, info=repr(e), result=[])
        return result

    async def subscription_add(self, sub: DBSubscription, user_sub_info: str = None) -> Result.IntResult:
        friend_check = await self.exist()
        if not friend_check:
            return Result.IntResult(error=True, info='Not friend', result=-1)

        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        sub_id_result = await sub.id()
        if sub_id_result.error:
            return Result.IntResult(error=True, info='Subscription not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(UserSub).
                            where(UserSub.user_id == user_id_result.result).
                            where(UserSub.sub_id == sub_id_result.result)
                        )
                        # 订阅关系已存在, 更新信息
                        exist_subscription = session_result.scalar_one()
                        exist_subscription.user_sub_info = user_sub_info
                        exist_subscription.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        subscription = UserSub(sub_id=sub_id_result.result, user_id=user_id_result.result,
                                               user_sub_info=user_sub_info, created_at=datetime.now())
                        session.add(subscription)
                        result = Result.IntResult(error=False, info='Success added', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def subscription_del(self, sub: DBSubscription) -> Result.IntResult:
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        sub_id_result = await sub.id()
        if sub_id_result.error:
            return Result.IntResult(error=True, info='Subscription not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(UserSub).
                        where(UserSub.user_id == user_id_result.result).
                        where(UserSub.sub_id == sub_id_result.result)
                    )
                    exist_subscription = session_result.scalar_one()
                    await session.delete(exist_subscription)
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

    async def subscription_clear(self) -> Result.IntResult:
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(UserSub).where(UserSub.user_id == user_id_result.result)
                    )
                    for exist_user_sub in session_result.scalars().all():
                        await session.delete(exist_user_sub)
                await session.commit()
                result = Result.IntResult(error=False, info='Success', result=0)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def subscription_clear_by_type(self, sub_type: int) -> Result.IntResult:
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(UserSub).join(Subscription).
                        where(UserSub.sub_id == Subscription.id).
                        where(Subscription.sub_type == sub_type).
                        where(UserSub.user_id == user_id_result.result)
                    )
                    for exist_user_sub in session_result.scalars().all():
                        await session.delete(exist_user_sub)
                await session.commit()
                result = Result.IntResult(error=False, info='Success', result=0)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result
