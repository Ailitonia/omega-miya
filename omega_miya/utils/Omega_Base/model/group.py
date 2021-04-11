from omega_miya.utils.Omega_Base.database import NBdb, DBResult
from omega_miya.utils.Omega_Base.tables import \
    User, Group, UserGroup, Vocation, Skill, UserSkill, Subscription, GroupSub, AuthGroup, EmailBox, GroupEmailBox
from .user import DBUser, DBSkill
from .subscription import DBSubscription
from .mail import DBEmailBox
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBGroup(object):
    def __init__(self, group_id: int):
        self.group_id = group_id

    async def id(self) -> DBResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Group.id).where(Group.group_id == self.group_id)
                    )
                    group_table_id = session_result.scalar_one()
                    result = DBResult(error=False, info='Success', result=group_table_id)
                except NoResultFound:
                    result = DBResult(error=True, info='NoResultFound', result=-1)
                except MultipleResultsFound:
                    result = DBResult(error=True, info='MultipleResultsFound', result=-1)
                except Exception as e:
                    result = DBResult(error=True, info=repr(e), result=-1)
        return result

    async def exist(self) -> bool:
        result = await self.id()
        return result.success()

    async def name(self) -> DBResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Group.name).where(Group.group_id == self.group_id)
                    )
                    group_name = session_result.scalar_one()
                    result = DBResult(error=False, info='Success', result=group_name)
                except NoResultFound:
                    result = DBResult(error=True, info='NoResultFound', result='')
                except MultipleResultsFound:
                    result = DBResult(error=True, info='MultipleResultsFound', result='')
                except Exception as e:
                    result = DBResult(error=True, info=repr(e), result='')
        return result

    async def add(self, name: str) -> DBResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(Group).where(Group.group_id == self.group_id)
                        )
                        exist_group = session_result.scalar_one()
                        exist_group.name = name
                        exist_group.updated_at = datetime.now()
                        result = DBResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        new_group = Group(group_id=self.group_id, name=name, notice_permissions=0,
                                          command_permissions=0, permission_level=0, created_at=datetime.now())
                        session.add(new_group)
                        result = DBResult(error=False, info='Success added', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = DBResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = DBResult(error=True, info=repr(e), result=-1)
        return result

    async def delete(self) -> DBResult:
        id_result = await self.id()
        if id_result.error:
            return DBResult(error=True, info='Group not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    # 清空权限节点
                    session_result = await session.execute(
                        select(AuthGroup).where(AuthGroup.group_id == id_result.result)
                    )
                    for exist_auth_node in session_result.scalars().all():
                        await session.delete(exist_auth_node)

                    # 清空群成员列表
                    session_result = await session.execute(
                        select(UserGroup).where(UserGroup.group_id == id_result.result)
                    )
                    for exist_user in session_result.scalars().all():
                        await session.delete(exist_user)

                    # 清空订阅
                    session_result = await session.execute(
                        select(GroupSub).where(GroupSub.group_id == id_result.result)
                    )
                    for exist_group_sub in session_result.scalars().all():
                        await session.delete(exist_group_sub)

                    # 清空绑定邮箱
                    session_result = await session.execute(
                        select(GroupEmailBox).where(GroupEmailBox.group_id == id_result.result)
                    )
                    for exist_mailbox in session_result.scalars().all():
                        await session.delete(exist_mailbox)

                    # 删除群组表中该群组
                    session_result = await session.execute(
                        select(Group).where(Group.group_id == self.group_id)
                    )
                    exist_group = session_result.scalar_one()
                    await session.delete(exist_group)
                await session.commit()
                result = DBResult(error=False, info='Success Delete', result=0)
            except NoResultFound:
                await session.rollback()
                result = DBResult(error=True, info='NoResultFound', result=-1)
            except MultipleResultsFound:
                await session.rollback()
                result = DBResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = DBResult(error=True, info=repr(e), result=-1)
        return result

    async def member_list(self) -> DBResult:
        id_result = await self.id()
        if id_result.error:
            return DBResult(error=True, info='Group not exist', result=[])

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(User.qq, UserGroup.user_group_nickname).
                        join(UserGroup).
                        where(UserGroup.group_id == id_result.result)
                    )
                    res = [(x[0], x[1]) for x in session_result.all()]
                    result = DBResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = DBResult(error=True, info=repr(e), result=[])
        return result

    async def member_add(self, user: DBUser, user_group_nickname: str) -> DBResult:
        group_id_result = await self.id()
        if group_id_result.error:
            return DBResult(error=True, info='Group not exist', result=-1)

        user_id_result = await user.id()
        if user_id_result.error:
            return DBResult(error=True, info='User not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    # 查询成员-群组表中用户-群关系
                    try:
                        # 用户-群关系已存在, 更新用户群昵称
                        session_result = await session.execute(
                            select(UserGroup).
                            where(UserGroup.user_id == user_id_result.result).
                            where(UserGroup.group_id == group_id_result.result)
                        )
                        exist_user = session_result.scalar_one()
                        exist_user.user_group_nickname = user_group_nickname
                        exist_user.updated_at = datetime.now()
                        result = DBResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        # 不存在关系则添加新成员
                        new_user = UserGroup(user_id=user_id_result.result, group_id=group_id_result.result,
                                             user_group_nickname=user_group_nickname, created_at=datetime.now())
                        session.add(new_user)
                        result = DBResult(error=False, info='Success added', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = DBResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = DBResult(error=True, info=repr(e), result=-1)
        return result

    async def member_del(self, user: DBUser) -> DBResult:
        group_id_result = await self.id()
        if group_id_result.error:
            return DBResult(error=True, info='Group not exist', result=-1)

        user_id_result = await user.id()
        if user_id_result.error:
            return DBResult(error=True, info='User not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(UserGroup).
                        where(UserGroup.user_id == user_id_result.result).
                        where(UserGroup.group_id == group_id_result.result)
                    )
                    exist_user = session_result.scalar_one()
                    await session.delete(exist_user)
                await session.commit()
                result = DBResult(error=False, info='Success', result=0)
            except NoResultFound:
                await session.rollback()
                result = DBResult(error=True, info='NoResultFound', result=-1)
            except MultipleResultsFound:
                await session.rollback()
                result = DBResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = DBResult(error=True, info=repr(e), result=-1)
        return result

    async def member_clear(self) -> DBResult:
        group_id_result = await self.id()
        if group_id_result.error:
            return DBResult(error=True, info='Group not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(UserGroup).where(UserGroup.group_id == group_id_result.result)
                    )
                    for exist_user in session_result.scalars().all():
                        await session.delete(exist_user)
                await session.commit()
                result = DBResult(error=False, info='Success', result=0)
            except Exception as e:
                await session.rollback()
                result = DBResult(error=True, info=repr(e), result=-1)
        return result

    async def permission_reset(self) -> DBResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(Group).where(Group.group_id == self.group_id)
                    )
                    exist_group = session_result.scalar_one()
                    exist_group.notice_permissions = 0
                    exist_group.command_permissions = 0
                    exist_group.permission_level = 0
                    exist_group.updated_at = datetime.now()
                    result = DBResult(error=False, info='Success upgraded', result=0)
                await session.commit()
            except NoResultFound:
                await session.rollback()
                result = DBResult(error=True, info='NoResultFound', result=-1)
            except MultipleResultsFound:
                await session.rollback()
                result = DBResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = DBResult(error=True, info=repr(e), result=-1)
        return result

    async def permission_set(self, notice: int = 0, command: int = 0, level: int = 0) -> DBResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(Group).where(Group.group_id == self.group_id)
                    )
                    exist_group = session_result.scalar_one()
                    exist_group.notice_permissions = notice
                    exist_group.command_permissions = command
                    exist_group.permission_level = level
                    exist_group.updated_at = datetime.now()
                    result = DBResult(error=False, info='Success upgraded', result=0)
                await session.commit()
            except NoResultFound:
                await session.rollback()
                result = DBResult(error=True, info='NoResultFound', result=-1)
            except MultipleResultsFound:
                await session.rollback()
                result = DBResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = DBResult(error=True, info=repr(e), result=-1)
        return result

    async def permission_info(self) -> DBResult:
        """
        :return: Result: Tuple[Notice_permission, Command_permission, Permission_level]
        """
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Group.notice_permissions, Group.command_permissions, Group.permission_level).
                        where(Group.group_id == self.group_id)
                    )
                    notice, command, level = session_result.one()
                    result = DBResult(error=False, info='Success', result=(notice, command, level))
                except NoResultFound:
                    result = DBResult(error=True, info='NoResultFound', result=(-1, -1, -1))
                except MultipleResultsFound:
                    result = DBResult(error=True, info='MultipleResultsFound', result=(-1, -1, -1))
                except Exception as e:
                    result = DBResult(error=True, info=repr(e), result=(-1, -1, -1))
        return result

    async def permission_notice(self) -> DBResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Group.notice_permissions).where(Group.group_id == self.group_id)
                    )
                    res = session_result.scalar_one()
                    result = DBResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = DBResult(error=True, info=repr(e), result=-1)
        return result

    async def permission_command(self) -> DBResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Group.command_permissions).where(Group.group_id == self.group_id)
                    )
                    res = session_result.scalar_one()
                    result = DBResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = DBResult(error=True, info=repr(e), result=-1)
        return result

    async def permission_level(self) -> DBResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Group.permission_level).where(Group.group_id == self.group_id)
                    )
                    res = session_result.scalar_one()
                    result = DBResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = DBResult(error=True, info=repr(e), result=-1)
        return result

    async def idle_member_list(self) -> DBResult:
        group_id_result = await self.id()
        if group_id_result.error:
            return DBResult(error=True, info='Group not exist', result=[])

        res = []
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    # 查询该群组中所有没有假的人
                    session_result = await session.execute(
                        select(User.id, UserGroup.user_group_nickname).
                        join(Vocation).join(UserGroup).
                        where(User.id == Vocation.user_id).
                        where(User.id == UserGroup.user_id).
                        where(Vocation.status == 0).
                        where(UserGroup.group_id == group_id_result.result)
                    )
                    user_res = [(x[0], x[1]) for x in session_result.all()]
                    # 查对应每个人的技能
                    for user_id, nickname in user_res:
                        session_result = await session.execute(
                            select(Skill.name).join(UserSkill).join(User).
                            where(Skill.id == UserSkill.skill_id).
                            where(UserSkill.user_id == User.id).
                            where(User.id == user_id)
                        )
                        user_skill_res = [x for x in session_result.scalars().all()]
                        if user_skill_res:
                            user_skill_text = '/'.join(user_skill_res)
                        else:
                            user_skill_text = '暂无技能'
                        res.append((nickname, user_skill_text))
                    result = DBResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = DBResult(error=True, info=repr(e), result=[])
        return result

    async def idle_skill_list(self, skill: DBSkill) -> DBResult:
        group_id_result = await self.id()
        if group_id_result.error:
            return DBResult(error=True, info='Group not exist', result=[])

        skill_id_result = await skill.id()
        if skill_id_result.error:
            return DBResult(error=True, info='Skill not exist', result=[])

        res = []
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    # 查询这这个技能有那些人会
                    session_result = await session.execute(
                        select(User.id, UserGroup.user_group_nickname).
                        join(UserSkill).join(UserGroup).
                        where(User.id == UserSkill.user_id).
                        where(User.id == UserGroup.user_id).
                        where(UserSkill.skill_id == skill_id_result.result).
                        where(UserGroup.group_id == group_id_result.result)
                    )
                    user_res = [(x[0], x[1]) for x in session_result.all()]
                    # 查这个人是不是空闲
                    for user_id, nickname in user_res:
                        session_result = await session.execute(
                            select(Vocation.status).where(Vocation.user_id == user_id)
                        )
                        # 如果空闲则把这个人昵称放进结果列表里面
                        if session_result.scalar_one() == 0:
                            res.append(nickname)
                    result = DBResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = DBResult(error=True, info=repr(e), result=[])
        return result

    async def vocation_member_list(self) -> DBResult:
        group_id_result = await self.id()
        if group_id_result.error:
            return DBResult(error=True, info='Group not exist', result=[])

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    # 查询所有没有假的人
                    session_result = await session.execute(
                        select(UserGroup.user_group_nickname, Vocation.stop_at).
                        select_from(UserGroup).join(User).
                        where(UserGroup.user_id == User.id).
                        where(User.id == Vocation.user_id).
                        where(Vocation.status == 1).
                        where(UserGroup.group_id == group_id_result.result)
                    )
                    res = [(x[0], x[1]) for x in session_result.all()]
                    result = DBResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = DBResult(error=True, info=repr(e), result=[])
        return result

    async def init_member_status(self) -> DBResult:
        member_list_res = await self.member_list()
        for user_qq, nickname in member_list_res.result:
            user = DBUser(user_id=user_qq)
            user_status_res = await user.status()
            if user_status_res.error:
                await user.status_set(status=0)
        return DBResult(error=False, info='ignore', result=0)

    async def subscription_list(self) -> DBResult:
        """
        :return: Result: List[Tuple[sub_type, sub_id, up_name]]
        """
        group_id_result = await self.id()
        if group_id_result.error:
            return DBResult(error=True, info='Group not exist', result=[])

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Subscription.sub_type, Subscription.sub_id, Subscription.up_name).
                        join(GroupSub).
                        where(Subscription.id == GroupSub.sub_id).
                        where(GroupSub.group_id == group_id_result.result)
                    )
                    res = [(x[0], x[1], x[2]) for x in session_result.all()]
                    result = DBResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = DBResult(error=True, info=repr(e), result=[])
        return result

    async def subscription_list_by_type(self, sub_type: int) -> DBResult:
        """
        :param sub_type: 订阅类型
        :return: Result: List[Tuple[sub_id, up_name]]
        """
        group_id_result = await self.id()
        if group_id_result.error:
            return DBResult(error=True, info='Group not exist', result=[])

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Subscription.sub_id, Subscription.up_name).
                        join(GroupSub).
                        where(Subscription.sub_type == sub_type).
                        where(Subscription.id == GroupSub.sub_id).
                        where(GroupSub.group_id == group_id_result.result)
                    )
                    res = [(x[0], x[1]) for x in session_result.all()]
                    result = DBResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = DBResult(error=True, info=repr(e), result=[])
        return result

    async def subscription_add(self, sub: DBSubscription, group_sub_info: str = None) -> DBResult:
        group_id_result = await self.id()
        if group_id_result.error:
            return DBResult(error=True, info='Group not exist', result=-1)

        sub_id_result = await sub.id()
        if sub_id_result.error:
            return DBResult(error=True, info='Subscription not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(GroupSub).
                            where(GroupSub.group_id == group_id_result.result).
                            where(GroupSub.sub_id == sub_id_result.result)
                        )
                        # 订阅关系已存在, 更新信息
                        exist_subscription = session_result.scalar_one()
                        exist_subscription.group_sub_info = group_sub_info
                        exist_subscription.updated_at = datetime.now()
                        result = DBResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        subscription = GroupSub(sub_id=sub_id_result.result, group_id=group_id_result.result,
                                                group_sub_info=group_sub_info, created_at=datetime.now())
                        session.add(subscription)
                        result = DBResult(error=False, info='Success added', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = DBResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = DBResult(error=True, info=repr(e), result=-1)
        return result

    async def subscription_del(self, sub: DBSubscription) -> DBResult:
        group_id_result = await self.id()
        if group_id_result.error:
            return DBResult(error=True, info='Group not exist', result=-1)

        sub_id_result = await sub.id()
        if sub_id_result.error:
            return DBResult(error=True, info='Subscription not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(GroupSub).
                        where(GroupSub.group_id == group_id_result.result).
                        where(GroupSub.sub_id == sub_id_result.result)
                    )
                    exist_subscription = session_result.scalar_one()
                    await session.delete(exist_subscription)
                await session.commit()
                result = DBResult(error=False, info='Success', result=0)
            except NoResultFound:
                await session.rollback()
                result = DBResult(error=True, info='NoResultFound', result=-1)
            except MultipleResultsFound:
                await session.rollback()
                result = DBResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = DBResult(error=True, info=repr(e), result=-1)
        return result

    async def subscription_clear(self) -> DBResult:
        group_id_result = await self.id()
        if group_id_result.error:
            return DBResult(error=True, info='Group not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(GroupSub).where(GroupSub.group_id == group_id_result.result)
                    )
                    for exist_group_sub in session_result.scalars().all():
                        await session.delete(exist_group_sub)
                await session.commit()
                result = DBResult(error=False, info='Success', result=0)
            except Exception as e:
                await session.rollback()
                result = DBResult(error=True, info=repr(e), result=-1)
        return result

    async def subscription_clear_by_type(self, sub_type: int) -> DBResult:
        group_id_result = await self.id()
        if group_id_result.error:
            return DBResult(error=True, info='Group not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(GroupSub).join(Subscription).
                        where(GroupSub.sub_id == Subscription.id).
                        where(Subscription.sub_type == sub_type).
                        where(GroupSub.group_id == group_id_result.result)
                    )
                    for exist_group_sub in session_result.scalars().all():
                        await session.delete(exist_group_sub)
                await session.commit()
                result = DBResult(error=False, info='Success', result=0)
            except Exception as e:
                await session.rollback()
                result = DBResult(error=True, info=repr(e), result=-1)
        return result

    async def mailbox_list(self) -> DBResult:
        group_id_result = await self.id()
        if group_id_result.error:
            return DBResult(error=True, info='Group not exist', result=[])

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(EmailBox.address).
                        join(GroupEmailBox).
                        where(EmailBox.id == GroupEmailBox.email_box_id).
                        where(GroupEmailBox.group_id == group_id_result.result)
                    )
                    res = [x for x in session_result.scalars().all()]
                    result = DBResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = DBResult(error=True, info=repr(e), result=[])
        return result

    async def mailbox_add(self, mailbox: DBEmailBox, mailbox_info: str = None) -> DBResult:
        group_id_result = await self.id()
        if group_id_result.error:
            return DBResult(error=True, info='Group not exist', result=-1)

        mailbox_id_result = await mailbox.id()
        if mailbox_id_result.error:
            return DBResult(error=True, info='Mailbox not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(GroupEmailBox).
                            where(GroupEmailBox.group_id == group_id_result.result).
                            where(GroupEmailBox.email_box_id == mailbox_id_result.result)
                        )
                        # 群邮箱已存在, 更新信息
                        exist_mailbox = session_result.scalar_one()
                        exist_mailbox.box_info = mailbox_info
                        exist_mailbox.updated_at = datetime.now()
                        result = DBResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        new_mailbox = GroupEmailBox(email_box_id=mailbox_id_result.result,
                                                    group_id=group_id_result.result,
                                                    box_info=mailbox_info, created_at=datetime.now())
                        session.add(new_mailbox)
                        result = DBResult(error=False, info='Success added', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = DBResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = DBResult(error=True, info=repr(e), result=-1)
        return result

    async def mailbox_del(self, mailbox: DBEmailBox) -> DBResult:
        group_id_result = await self.id()
        if group_id_result.error:
            return DBResult(error=True, info='Group not exist', result=-1)

        mailbox_id_result = await mailbox.id()
        if mailbox_id_result.error:
            return DBResult(error=True, info='Mailbox not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(GroupEmailBox).
                        where(GroupEmailBox.group_id == group_id_result.result).
                        where(GroupEmailBox.email_box_id == mailbox_id_result.result)
                    )
                    exist_mailbox = session_result.scalar_one()
                    await session.delete(exist_mailbox)
                await session.commit()
                result = DBResult(error=False, info='Success', result=0)
            except NoResultFound:
                await session.rollback()
                result = DBResult(error=True, info='NoResultFound', result=-1)
            except MultipleResultsFound:
                await session.rollback()
                result = DBResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = DBResult(error=True, info=repr(e), result=-1)
        return result

    async def mailbox_clear(self) -> DBResult:
        group_id_result = await self.id()
        if group_id_result.error:
            return DBResult(error=True, info='Group not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(GroupEmailBox).where(GroupEmailBox.group_id == group_id_result.result)
                    )
                    for exist_mailbox in session_result.scalars().all():
                        await session.delete(exist_mailbox)
                await session.commit()
                result = DBResult(error=False, info='Success', result=0)
            except Exception as e:
                await session.rollback()
                result = DBResult(error=True, info=repr(e), result=-1)
        return result
