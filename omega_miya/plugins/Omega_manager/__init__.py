"""
Omega Miya 使用指南

- /Omega Init - bot首次加入新群组/首次添加bot好友后, 须使用本命令进行初始化
- /Omega Upgrade - 手动更新本群组信息
- /Omega Notice <on|off> - 为本群组配置通知权限(订阅类插件是否通知)
- /Omega Command <on|off> - 为本群组配置命令权限(是否允许使用命令)
- /Omega SetLevel <PermissionLevel> - 为本群组配置命令等级(对于低于命令要求等级的群组, 该命令不会被响应)
"""
from dataclasses import dataclass
from nonebot import on_command, export, logger
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent, GroupMessageEvent, PrivateMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP_ADMIN, GROUP_OWNER, PRIVATE_FRIEND
from omega_miya.utils.Omega_Base import DBBot, DBBotGroup, DBUser, DBAuth, DBFriend, Result
from omega_miya.utils.Omega_plugin_utils import init_export
from .sys_background_scheduled import scheduler

# Custom plugin usage text
__plugin_name__ = 'Omega'
__plugin_usage__ = r'''【Omega 管理插件】
Omega机器人管理

**Usage**
**GroupAdmin and SuperUser Only**
/Omega Init
/Omega Upgrade
/Omega Notice <on|off>
/Omega Command <on|off>
/Omega SetLevel <PermissionLevel>
/Omega ShowPermission
/Omega ResetPermission

**Friend Private Only**
/Omega Init
/Omega Enable
/Omega Disable'''

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__)

# 注册事件响应器
omega = on_command('Omega', rule=None, aliases={'omega'},
                   permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER | PRIVATE_FRIEND, priority=10, block=True)


# 修改默认参数处理
@omega.args_parser
async def parse(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await omega.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await omega.finish('操作已取消')


@omega.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if args and len(args) == 1:
        state['sub_command'] = args[0]
        state['sub_arg'] = None
    elif args and len(args) == 2:
        state['sub_command'] = args[0]
        state['sub_arg'] = args[1]
    else:
        await omega.finish('你好呀~ 我是Omega Miya~ 请问您今天要来点喵娘吗?')


@omega.got('sub_command', prompt='执行操作?\n【Init/Upgrade/Notice/Command/SetLevel/ShowPermission/ResetPermission】')
async def handle_sub_command(bot: Bot, event: GroupMessageEvent, state: T_State):
    if not isinstance(event, GroupMessageEvent):
        return
    # 子命令列表
    command = {
        'init': group_init,
        'upgrade': group_upgrade,
        'notice': set_group_notice,
        'command': set_group_command,
        'setlevel': set_group_level,
        'showpermission': show_group_permission,
        'resetpermission': reset_group_permission
    }
    # 需要回复信息的命令列表
    need_reply = [
        'showpermission'
    ]
    sub_command = state["sub_command"]
    # 在这里对参数进行验证
    if sub_command not in command.keys():
        await omega.finish('没有这个命令哦QAQ')
    result = await command[sub_command](bot=bot, event=event, state=state)
    if result.success():
        logger.info(f"Group: {event.group_id}, {sub_command}, Success, {result.info}")
        if sub_command in need_reply:
            await omega.finish(result.result)
        else:
            await omega.finish('Success')
    else:
        logger.error(f"Group: {event.group_id}, {sub_command}, Failed, {result.info}")
        await omega.finish('Failed QAQ')


@omega.got('sub_command', prompt='执行操作?\n【Init/Enable/Disable】')
async def handle_sub_command(bot: Bot, event: PrivateMessageEvent, state: T_State):
    if not isinstance(event, PrivateMessageEvent):
        return
    # 子命令列表
    command = {
        'init': friend_init,
        'enable': friend_private_enable,
        'disable': friend_private_disable
    }
    # 需要回复信息的命令列表
    need_reply = [
        'init',
        'enable',
        'disable'
    ]
    sub_command = state["sub_command"]
    # 在这里对参数进行验证
    if sub_command not in command.keys():
        await omega.finish('没有这个命令哦QAQ')
    result = await command[sub_command](bot=bot, event=event, state=state)
    if result.success():
        logger.info(f"Private friend: {event.user_id}, {sub_command}, Success, {result.info}")
        if sub_command in need_reply:
            await omega.finish(result.result)
        else:
            await omega.finish('Success')
    else:
        logger.error(f"Private friend: {event.user_id}, {sub_command}, Failed, {result.info}")
        if sub_command in need_reply:
            await omega.finish(result.result)
        else:
            await omega.finish('Failed QAQ')


async def friend_init(bot: Bot, event: PrivateMessageEvent, state: T_State) -> Result.TextResult:
    user_id = event.user_id
    self_bot = DBBot(self_qq=int(bot.self_id))
    # 调用api获取好友列表
    friends_list = await bot.get_friend_list()
    actual_friend_list = [int(x.get('user_id')) for x in friends_list]
    if user_id not in actual_friend_list:
        return Result.TextResult(error=True, info='Not in friends list', result='错误, 不在好友列表中')

    user_info = [x for x in friends_list if int(x.get('user_id')) == user_id][0]
    nickname = user_info.get('nickname')
    remark = user_info.get('remark')

    friend = DBFriend(user_id=user_id, self_bot=self_bot)

    # 更新用户表
    add_user_result = await friend.add(nickname=nickname)
    if add_user_result.error:
        return Result.TextResult(error=True, info=add_user_result.info, result='错误, 请联系管理员处理')

    # 初始化好友authnode
    await init_user_auth_node(user_id=user_id, self_bot=self_bot)

    set_friend_result = await friend.set_friend(nickname=nickname, remark=remark, private_permissions=1)
    if set_friend_result.success():
        return Result.TextResult(error=False, info='Success', result='成功, 现在可以使用私聊命令了')
    else:
        return Result.TextResult(error=True, info=set_friend_result.info, result='错误, 请联系管理员处理')


async def friend_private_enable(bot: Bot, event: PrivateMessageEvent, state: T_State) -> Result.TextResult:
    user_id = event.user_id
    self_bot = DBBot(self_qq=int(bot.self_id))
    # 初始化好友authnode
    await init_user_auth_node(user_id=user_id, self_bot=self_bot)

    friend = DBFriend(user_id=user_id, self_bot=self_bot)
    result = await friend.set_private_permission(private_permissions=1)
    if result.success():
        return Result.TextResult(error=False, info='Success', result='成功, 已启用私聊功能, 权限节点已设置为默认值')
    else:
        return Result.TextResult(error=True, info=result.info, result='失败, 请先尝试"/Omega Init", 若仍失败请联系管理员处理')


async def friend_private_disable(bot: Bot, event: PrivateMessageEvent, state: T_State) -> Result.TextResult:
    user_id = event.user_id
    self_bot = DBBot(self_qq=int(bot.self_id))
    # 初始化好友authnode
    await init_user_auth_node(user_id=user_id, self_bot=self_bot)

    friend = DBFriend(user_id=user_id, self_bot=self_bot)
    result = await friend.set_private_permission(private_permissions=0)
    if result.success():
        return Result.TextResult(error=False, info='Success', result='成功, 已禁用私聊功能, 权限节点已重置为默认值')
    else:
        return Result.TextResult(error=True, info=result.info, result='失败, 请先尝试"/Omega Init", 若仍失败请联系管理员处理')


async def group_init(bot: Bot, event: GroupMessageEvent, state: T_State) -> Result.IntResult:
    group_id = event.group_id
    self_bot = DBBot(self_qq=int(bot.self_id))
    # 调用api获取群信息
    group_info = await bot.get_group_info(group_id=group_id)
    group_name = group_info['group_name']
    group_memo = group_info.get('group_memo')
    group = DBBotGroup(group_id=group_id, self_bot=self_bot)

    # 添加并初始化群信息
    _result = await group.add(name=group_name)
    if not _result.success():
        return Result.IntResult(True, _result.info, -1)

    _result = await group.set_bot_group(group_memo=group_memo)
    if not _result.success():
        return Result.IntResult(True, _result.info, -1)

    _result = await group.permission_set(notice=1, command=1, level=10)
    if not _result.success():
        return Result.IntResult(True, _result.info, -1)

    # 初始化群组authnode
    await init_group_auth_node(group_id=group_id, self_bot=self_bot)

    _result = await group.member_clear()
    if not _result.success():
        return Result.IntResult(True, _result.info, -1)

    # 添加用户
    group_member_list = await bot.get_group_member_list(group_id=group_id)
    failed_user = []
    for user_info in group_member_list:
        # 用户信息
        user_qq = user_info['user_id']
        user_nickname = user_info['nickname']
        user_group_nickmane = user_info['card']
        if not user_group_nickmane:
            user_group_nickmane = user_nickname

        _user = DBUser(user_id=user_qq)
        _result = await _user.add(nickname=user_nickname)
        if not _result.success():
            failed_user.append(_user.qq)
            logger.warning(f'Add group user: {user_qq}, {_result.info}')
            continue

        _result = await group.member_add(user=_user, user_group_nickname=user_group_nickmane)
        if not _result.success():
            failed_user.append(_user.qq)
            logger.warning(f'Upgrade group user: {user_qq}, {_result.info}')

    await group.init_member_status()

    return Result.IntResult(False, f'Success with ignore user: {failed_user}', 0)


async def group_upgrade(bot: Bot, event: GroupMessageEvent, state: T_State) -> Result.IntResult:
    group_id = event.group_id
    self_bot = DBBot(self_qq=int(bot.self_id))
    # 调用api获取群信息
    group_info = await bot.get_group_info(group_id=group_id)
    group_name = group_info['group_name']
    group_memo = group_info.get('group_memo')
    group = DBBotGroup(group_id=group_id, self_bot=self_bot)

    # 更新群信息
    _result = await group.add(name=group_name)
    if not _result.success():
        return Result.IntResult(True, _result.info, -1)

    _result = await group.set_bot_group(group_memo=group_memo)
    if not _result.success():
        return Result.IntResult(True, _result.info, -1)

    # 更新用户
    group_member_list = await bot.get_group_member_list(group_id=group_id)
    failed_user = []

    # 首先清除数据库中退群成员
    exist_member_list = [int(x.get('user_id')) for x in group_member_list]
    member_res = await group.member_list()
    db_member_list = [user_id for user_id, nickname in member_res.result]
    del_member_list = list(set(db_member_list).difference(set(exist_member_list)))

    for user_id in del_member_list:
        await group.member_del(user=DBUser(user_id=user_id))

    # 更新群成员
    for user_info in group_member_list:
        # 用户信息
        user_qq = user_info.get('user_id')
        user_nickname = user_info.get('nickname')
        user_group_nickmane = user_info.get('card')
        if not user_group_nickmane:
            user_group_nickmane = user_nickname

        _user = DBUser(user_id=user_qq)
        _result = await _user.add(nickname=user_nickname)
        if not _result.success():
            failed_user.append(_user.qq)
            logger.warning(f'Add group user: {user_qq}, {_result.info}')
            continue

        _result = await group.member_add(user=_user, user_group_nickname=user_group_nickmane)
        if not _result.success():
            failed_user.append(_user.qq)
            logger.warning(f'Upgrade group user: {user_qq}, {_result.info}')

    await group.init_member_status()

    return Result.IntResult(False, f'Success with ignore user: {failed_user}', 0)


async def set_group_notice(bot: Bot, event: GroupMessageEvent, state: T_State) -> Result.IntResult:
    group_id = event.group_id
    self_bot = DBBot(self_qq=int(bot.self_id))
    group = DBBotGroup(group_id=group_id, self_bot=self_bot)
    permission_res = await group.permission_info()
    if permission_res.error:
        return Result.IntResult(True, permission_res.info, -1)

    _notice, group_command, group_level = permission_res.result

    if state['sub_arg'] == 'on':
        result = await group.permission_set(notice=1, command=group_command, level=group_level)
    elif state['sub_arg'] == 'off':
        result = await group.permission_set(notice=0, command=group_command, level=group_level)
    else:
        result = Result.IntResult(True, 'Missing parameters or Illegal parameter', -1)

    return result


async def set_group_command(bot: Bot, event: GroupMessageEvent, state: T_State) -> Result.IntResult:
    group_id = event.group_id
    self_bot = DBBot(self_qq=int(bot.self_id))
    group = DBBotGroup(group_id=group_id, self_bot=self_bot)
    permission_res = await group.permission_info()
    if permission_res.error:
        return Result.IntResult(True, permission_res.info, -1)

    group_notice, _command, group_level = permission_res.result

    if state['sub_arg'] == 'on':
        # 初始化群组authnode
        await init_group_auth_node(group_id=group_id, self_bot=self_bot)
        result = await group.permission_set(notice=group_notice, command=1, level=group_level)
    elif state['sub_arg'] == 'off':
        # 初始化群组authnode
        await init_group_auth_node(group_id=group_id, self_bot=self_bot)
        result = await group.permission_set(notice=group_notice, command=0, level=group_level)
    else:
        result = Result.IntResult(True, 'Missing parameters or Illegal parameter', -1)

    return result


async def set_group_level(bot: Bot, event: GroupMessageEvent, state: T_State) -> Result.IntResult:
    group_id = event.group_id
    self_bot = DBBot(self_qq=int(bot.self_id))
    group = DBBotGroup(group_id=group_id, self_bot=self_bot)
    permission_res = await group.permission_info()
    if permission_res.error:
        return Result.IntResult(True, permission_res.info, -1)

    group_notice, group_command, _level = permission_res.result

    try:
        group_level = int(state['sub_arg'])
        result = await group.permission_set(notice=group_notice, command=group_command, level=group_level)
    except Exception as e:
        result = Result.IntResult(True, f'Missing parameters or Illegal parameter, {e}', -1)

    return result


async def show_group_permission(bot: Bot, event: GroupMessageEvent, state: T_State) -> Result.TextResult:
    group_id = event.group_id
    self_bot = DBBot(self_qq=int(bot.self_id))
    group = DBBotGroup(group_id=group_id, self_bot=self_bot)
    permission_res = await group.permission_info()
    if permission_res.error:
        return Result.TextResult(True, permission_res.info, '')

    group_notice, group_command, group_level = permission_res.result

    msg = f'当前群组权限: \n\nNotice: {group_notice}\nCommand: {group_command}\nPermissionLevel: {group_level}'
    result = Result.TextResult(False, 'Success', msg)
    return result


async def reset_group_permission(bot: Bot, event: GroupMessageEvent, state: T_State) -> Result.IntResult:
    group_id = event.group_id
    self_bot = DBBot(self_qq=int(bot.self_id))
    group = DBBotGroup(group_id=group_id, self_bot=self_bot)
    result = await group.permission_reset()
    return result


async def init_group_auth_node(group_id: int, self_bot: DBBot):
    """
    为群组配置权限节点默认值
    """
    @dataclass
    class AuthNode:
        node: str
        allow_tag: int
        deny_tag: int
        auth_info: str

    default_auth_nodes = [
        AuthNode(node='Omega_help.skip_cd', allow_tag=1, deny_tag=0, auth_info='默认规则: help免cd'),
        AuthNode(node='nhentai.basic', allow_tag=0, deny_tag=1, auth_info='默认规则: 禁用nhentai'),
        AuthNode(node='setu.setu', allow_tag=0, deny_tag=1, auth_info='默认规则: 禁用setu'),
        AuthNode(node='pixiv.allow_r18', allow_tag=0, deny_tag=1, auth_info='默认规则: 禁用pivix r18')
    ]

    for auth_node in default_auth_nodes:
        auth = DBAuth(self_bot=self_bot, auth_id=group_id, auth_type='group', auth_node=auth_node.node)
        res = await auth.set(allow_tag=auth_node.allow_tag, deny_tag=auth_node.deny_tag, auth_info=auth_node.auth_info)
        if res.error:
            logger.opt(colors=True).error(f'配置默认权限失败, <ly>{auth_node.node}/{group_id}</ly>, error: {res.info}')


async def init_user_auth_node(user_id: int, self_bot: DBBot):
    """
    为好友配置权限节点默认值
    """
    @dataclass
    class AuthNode:
        node: str
        allow_tag: int
        deny_tag: int
        auth_info: str

    default_auth_nodes = [
        AuthNode(node='Omega_help.skip_cd', allow_tag=1, deny_tag=0, auth_info='默认规则: 好友help免cd')
    ]

    for auth_node in default_auth_nodes:
        auth = DBAuth(self_bot=self_bot, auth_id=user_id, auth_type='user', auth_node=auth_node.node)
        res = await auth.set(allow_tag=auth_node.allow_tag, deny_tag=auth_node.deny_tag, auth_info=auth_node.auth_info)
        if res.error:
            logger.opt(colors=True).error(f'配置默认权限失败, <ly>{auth_node.node}/{user_id}</ly>, error: {res.info}')
