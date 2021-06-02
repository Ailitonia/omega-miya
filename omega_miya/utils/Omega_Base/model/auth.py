from omega_miya.utils.Omega_Base.database import NBdb
from omega_miya.utils.Omega_Base.class_result import Result
from omega_miya.utils.Omega_Base.tables import AuthUser, AuthGroup, User, Friends, Group, BotGroup
from .friend import DBFriend
from .bot_group import DBBotGroup
from .bot_self import DBBot
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBAuth(object):
    def __init__(self, self_bot: DBBot, auth_id: int, auth_type: str, auth_node: str):
        """
        :param self_bot: 对应DBBot对象
        :param auth_id: 请求授权id, 用户qq号或群组群号
        :param auth_type:
            user: 用户授权
            group: 群组授权
        :param auth_node: 授权节点
        """
        self.self_bot = self_bot
        self.auth_id = auth_id
        self.auth_type = auth_type
        self.auth_node = auth_node

    async def id(self) -> Result.IntResult:
        self_bot_id_result = await self.self_bot.id()
        if self_bot_id_result.error:
            return Result.IntResult(error=True, info='Bot not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    if self.auth_type == 'user':
                        session_result = await session.execute(
                            select(AuthUser.id).
                            join(Friends).join(User).
                            where(AuthUser.user_id == Friends.id).
                            where(Friends.user_id == User.id).
                            where(Friends.bot_self_id == self_bot_id_result.result).
                            where(User.qq == self.auth_id).
                            where(AuthUser.auth_node == self.auth_node)
                        )
                        auth_table_id = session_result.scalar_one()
                        result = Result.IntResult(error=False, info='Success', result=auth_table_id)
                    elif self.auth_type == 'group':
                        session_result = await session.execute(
                            select(AuthGroup.id).
                            join(BotGroup).join(Group).
                            where(AuthGroup.group_id == BotGroup.id).
                            where(BotGroup.group_id == Group.id).
                            where(BotGroup.bot_self_id == self_bot_id_result.result).
                            where(Group.group_id == self.auth_id).
                            where(AuthGroup.auth_node == self.auth_node)
                        )
                        auth_table_id = session_result.scalar_one()
                        result = Result.IntResult(error=False, info='Success', result=auth_table_id)
                    else:
                        result = Result.IntResult(error=True, info='Auth type error', result=-1)
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

    async def set(self, allow_tag: int, deny_tag: int, auth_info: str = None) -> Result.IntResult:
        self_bot_id_result = await self.self_bot.id()
        if self_bot_id_result.error:
            return Result.IntResult(error=True, info='Bot not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        if self.auth_type == 'user':
                            session_result = await session.execute(
                                select(AuthUser).
                                join(Friends).join(User).
                                where(AuthUser.user_id == Friends.id).
                                where(Friends.user_id == User.id).
                                where(Friends.bot_self_id == self_bot_id_result.result).
                                where(User.qq == self.auth_id).
                                where(AuthUser.auth_node == self.auth_node)
                            )
                            auth = session_result.scalar_one()
                            auth.allow_tag = allow_tag
                            auth.deny_tag = deny_tag
                            auth.auth_info = auth_info
                            auth.updated_at = datetime.now()
                            result = Result.IntResult(error=False, info='Success upgraded', result=0)
                        elif self.auth_type == 'group':
                            session_result = await session.execute(
                                select(AuthGroup).
                                join(BotGroup).join(Group).
                                where(AuthGroup.group_id == BotGroup.id).
                                where(BotGroup.group_id == Group.id).
                                where(BotGroup.bot_self_id == self_bot_id_result.result).
                                where(Group.group_id == self.auth_id).
                                where(AuthGroup.auth_node == self.auth_node)
                            )
                            auth = session_result.scalar_one()
                            auth.allow_tag = allow_tag
                            auth.deny_tag = deny_tag
                            auth.auth_info = auth_info
                            auth.updated_at = datetime.now()
                            result = Result.IntResult(error=False, info='Success upgraded', result=0)
                        else:
                            result = Result.IntResult(error=True, info='Auth type error', result=-1)
                    except NoResultFound:
                        if self.auth_type == 'user':
                            friend = DBFriend(user_id=self.auth_id, self_bot=self.self_bot)
                            friend_id_result = await friend.friend_id()
                            if friend_id_result.error:
                                result = Result.IntResult(error=True, info='Friend not exist', result=-1)
                            else:
                                auth = AuthUser(user_id=friend_id_result.result, auth_node=self.auth_node,
                                                allow_tag=allow_tag,
                                                deny_tag=deny_tag, auth_info=auth_info, created_at=datetime.now())
                                session.add(auth)
                                result = Result.IntResult(error=False, info='Success set', result=0)
                        elif self.auth_type == 'group':
                            bot_group = DBBotGroup(group_id=self.auth_id, self_bot=self.self_bot)
                            bot_group_id_result = await bot_group.bot_group_id()
                            if bot_group_id_result.error:
                                result = Result.IntResult(error=True, info='Group not exist', result=-1)
                            else:
                                auth = AuthGroup(group_id=bot_group_id_result.result, auth_node=self.auth_node,
                                                 allow_tag=allow_tag,
                                                 deny_tag=deny_tag, auth_info=auth_info, created_at=datetime.now())
                                session.add(auth)
                                result = Result.IntResult(error=False, info='Success set', result=0)
                        else:
                            result = Result.IntResult(error=True, info='Auth type error', result=-1)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def allow_tag(self) -> Result.IntResult:
        self_bot_id_result = await self.self_bot.id()
        if self_bot_id_result.error:
            return Result.IntResult(error=True, info='Bot not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    if self.auth_type == 'user':
                        session_result = await session.execute(
                            select(AuthUser.allow_tag).
                            join(Friends).join(User).
                            where(AuthUser.user_id == Friends.id).
                            where(Friends.user_id == User.id).
                            where(Friends.bot_self_id == self_bot_id_result.result).
                            where(User.qq == self.auth_id).
                            where(AuthUser.auth_node == self.auth_node)
                        )
                        allow_tag = session_result.scalar_one()
                        result = Result.IntResult(error=False, info='Success', result=allow_tag)
                    elif self.auth_type == 'group':
                        session_result = await session.execute(
                            select(AuthGroup.allow_tag).
                            join(BotGroup).join(Group).
                            where(AuthGroup.group_id == BotGroup.id).
                            where(BotGroup.group_id == Group.id).
                            where(BotGroup.bot_self_id == self_bot_id_result.result).
                            where(Group.group_id == self.auth_id).
                            where(AuthGroup.auth_node == self.auth_node)
                        )
                        allow_tag = session_result.scalar_one()
                        result = Result.IntResult(error=False, info='Success', result=allow_tag)
                    else:
                        result = Result.IntResult(error=True, info='Auth type error', result=-1)
                except NoResultFound:
                    result = Result.IntResult(error=True, info='NoResultFound', result=-2)
                except MultipleResultsFound:
                    result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
                except Exception as e:
                    result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def deny_tag(self) -> Result.IntResult:
        self_bot_id_result = await self.self_bot.id()
        if self_bot_id_result.error:
            return Result.IntResult(error=True, info='Bot not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    if self.auth_type == 'user':
                        session_result = await session.execute(
                            select(AuthUser.deny_tag).
                            join(Friends).join(User).
                            where(AuthUser.user_id == Friends.id).
                            where(Friends.user_id == User.id).
                            where(Friends.bot_self_id == self_bot_id_result.result).
                            where(User.qq == self.auth_id).
                            where(AuthUser.auth_node == self.auth_node)
                        )
                        deny_tag = session_result.scalar_one()
                        result = Result.IntResult(error=False, info='Success', result=deny_tag)
                    elif self.auth_type == 'group':
                        session_result = await session.execute(
                            select(AuthGroup.deny_tag).
                            join(BotGroup).join(Group).
                            where(AuthGroup.group_id == BotGroup.id).
                            where(BotGroup.group_id == Group.id).
                            where(BotGroup.bot_self_id == self_bot_id_result.result).
                            where(Group.group_id == self.auth_id).
                            where(AuthGroup.auth_node == self.auth_node)
                        )
                        deny_tag = session_result.scalar_one()
                        result = Result.IntResult(error=False, info='Success', result=deny_tag)
                    else:
                        result = Result.IntResult(error=True, info='Auth type error', result=-1)
                except NoResultFound:
                    result = Result.IntResult(error=True, info='NoResultFound', result=-2)
                except MultipleResultsFound:
                    result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
                except Exception as e:
                    result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def tags_info(self) -> Result.IntTupleResult:
        self_bot_id_result = await self.self_bot.id()
        if self_bot_id_result.error:
            return Result.IntTupleResult(error=True, info='Bot not exist', result=(-1, -1))

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    if self.auth_type == 'user':
                        session_result = await session.execute(
                            select(AuthUser.allow_tag, AuthUser.deny_tag).
                            join(Friends).join(User).
                            where(AuthUser.user_id == Friends.id).
                            where(Friends.user_id == User.id).
                            where(Friends.bot_self_id == self_bot_id_result.result).
                            where(User.qq == self.auth_id).
                            where(AuthUser.auth_node == self.auth_node)
                        )
                        res = session_result.one()
                        result = Result.IntTupleResult(error=False, info='Success', result=(res[0], res[1]))
                    elif self.auth_type == 'group':
                        session_result = await session.execute(
                            select(AuthGroup.allow_tag, AuthGroup.deny_tag).
                            join(BotGroup).join(Group).
                            where(AuthGroup.group_id == BotGroup.id).
                            where(BotGroup.group_id == Group.id).
                            where(BotGroup.bot_self_id == self_bot_id_result.result).
                            where(Group.group_id == self.auth_id).
                            where(AuthGroup.auth_node == self.auth_node)
                        )
                        res = session_result.one()
                        result = Result.IntTupleResult(error=False, info='Success', result=(res[0], res[1]))
                    else:
                        result = Result.IntTupleResult(error=True, info='Auth type error', result=(-1, -1))
                except NoResultFound:
                    result = Result.IntTupleResult(error=True, info='NoResultFound', result=(-2, -2))
                except MultipleResultsFound:
                    result = Result.IntTupleResult(error=True, info='MultipleResultsFound', result=(-1, -1))
                except Exception as e:
                    result = Result.IntTupleResult(error=True, info=repr(e), result=(-1, -1))
        return result

    async def delete(self) -> Result.IntResult:
        self_bot_id_result = await self.self_bot.id()
        if self_bot_id_result.error:
            return Result.IntResult(error=True, info='Bot not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    if self.auth_type == 'user':
                        session_result = await session.execute(
                            select(AuthUser).
                            join(Friends).join(User).
                            where(AuthUser.user_id == Friends.id).
                            where(Friends.user_id == User.id).
                            where(Friends.bot_self_id == self_bot_id_result.result).
                            where(User.qq == self.auth_id).
                            where(AuthUser.auth_node == self.auth_node)
                        )
                        auth = session_result.scalar_one()
                        await session.delete(auth)
                        result = Result.IntResult(error=False, info='Success', result=0)
                    elif self.auth_type == 'group':
                        session_result = await session.execute(
                            select(AuthGroup).
                            join(BotGroup).join(Group).
                            where(AuthGroup.group_id == BotGroup.id).
                            where(BotGroup.group_id == Group.id).
                            where(BotGroup.bot_self_id == self_bot_id_result.result).
                            where(Group.group_id == self.auth_id).
                            where(AuthGroup.auth_node == self.auth_node)
                        )
                        auth = session_result.scalar_one()
                        await session.delete(auth)
                        result = Result.IntResult(error=False, info='Success', result=0)
                    else:
                        result = Result.IntResult(error=True, info='Auth type error', result=-1)
                await session.commit()
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

    @classmethod
    async def list(cls, auth_type: str, auth_id: int, self_bot: DBBot) -> Result.ListResult:
        self_bot_id_result = await self_bot.id()
        if self_bot_id_result.error:
            return Result.ListResult(error=True, info='Bot not exist', result=[])

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    if auth_type == 'user':
                        session_result = await session.execute(
                            select(AuthUser.auth_node, AuthUser.allow_tag, AuthUser.deny_tag).
                            join(Friends).join(User).
                            where(AuthUser.user_id == Friends.id).
                            where(Friends.user_id == User.id).
                            where(Friends.bot_self_id == self_bot_id_result.result).
                            where(User.qq == auth_id)
                        )
                        auth_node_list = [(x[0], x[1], x[2]) for x in session_result.all()]
                        result = Result.ListResult(error=False, info='Success', result=auth_node_list)
                    elif auth_type == 'group':
                        session_result = await session.execute(
                            select(AuthGroup.auth_node, AuthGroup.allow_tag, AuthGroup.deny_tag).
                            join(BotGroup).join(Group).
                            where(AuthGroup.group_id == BotGroup.id).
                            where(BotGroup.group_id == Group.id).
                            where(BotGroup.bot_self_id == self_bot_id_result.result).
                            where(Group.group_id == auth_id)
                        )
                        auth_node_list = [(x[0], x[1], x[2]) for x in session_result.all()]
                        result = Result.ListResult(error=False, info='Success', result=auth_node_list)
                    else:
                        result = Result.ListResult(error=True, info='Auth type error', result=[])
                except NoResultFound:
                    result = Result.ListResult(error=True, info='NoResultFound', result=[])
                except MultipleResultsFound:
                    result = Result.ListResult(error=True, info='MultipleResultsFound', result=[])
                except Exception as e:
                    result = Result.ListResult(error=True, info=repr(e), result=[])
        return result
