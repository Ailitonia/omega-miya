from nonebot import on_command, export, logger, require
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.adapters import Bot, Event
from nonebot.adapters.cqhttp.permission import GROUP_ADMIN
from omega_miya.utils.Omega_Base import DBGroup, DBUser, Result
from omega_miya.utils.Omega_plugin_utils import init_export

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
/Omega ResetPermission'''

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__)

# 注册事件响应器
omega = on_command('Omega', rule=None, aliases={'omega'}, permission=GROUP_ADMIN | SUPERUSER, priority=1, block=True)


# 修改默认参数处理
@omega.args_parser
async def parse(bot: Bot, event: Event, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await omega.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await omega.finish('操作已取消')


@omega.handle()
async def handle_first_receive(bot: Bot, event: Event, state: T_State):
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
async def handle_sub_command(bot: Bot, event: Event, state: T_State):
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
        logger.info(f"Group: {event.dict().get('group_id')}, {sub_command}, Success, {result.info}")
        if sub_command in need_reply:
            await omega.finish(result.result)
        else:
            await omega.finish('Success')
    else:
        logger.error(f"Group: {event.dict().get('group_id')}, {sub_command}, Failed, {result.info}")
        await omega.finish('Failed QAQ')


async def group_init(bot: Bot, event: Event, state: T_State) -> Result:
    group_id = event.dict().get('group_id')
    # 调用api获取群信息
    group_info = await bot.call_api(api='get_group_info', group_id=group_id)
    group_name = group_info['group_name']
    group = DBGroup(group_id=group_id)

    # 添加并初始化群信息
    _result = group.add(name=group_name)
    if not _result.success():
        return Result(True, _result.info, -1)

    _result = group.permission_set(notice=1, command=1, level=10)
    if not _result.success():
        return Result(True, _result.info, -1)

    _result = group.member_clear()
    if not _result.success():
        return Result(True, _result.info, -1)

    # 添加用户
    group_member_list = await bot.call_api(api='get_group_member_list', group_id=group_id)
    failed_user = []
    for user_info in group_member_list:
        # 用户信息
        user_qq = user_info['user_id']
        user_nickname = user_info['nickname']
        user_group_nickmane = user_info['card']
        if not user_group_nickmane:
            user_group_nickmane = user_nickname

        _user = DBUser(user_id=user_qq)
        _result = _user.add(nickname=user_nickname)
        if not _result.success():
            failed_user.append(_user.qq)
            logger.warning(f'User: {user_qq}, {_result.info}')
            continue

        _result = group.member_add(user=_user, user_group_nickname=user_group_nickmane)
        if not _result.success():
            failed_user.append(_user.qq)
            logger.warning(f'User: {user_qq}, {_result.info}')

    group.init_member_status()

    return Result(False, f'Success with ignore user: {failed_user}', 0)


async def group_upgrade(bot: Bot, event: Event, state: T_State) -> Result:
    group_id = event.dict().get('group_id')
    # 调用api获取群信息
    group_info = await bot.call_api(api='get_group_info', group_id=group_id)
    group_name = group_info['group_name']
    group = DBGroup(group_id=group_id)

    # 添加并初始化群信息
    _result = group.add(name=group_name)
    if not _result.success():
        return Result(True, _result.info, -1)

    # 更新用户
    group_member_list = await bot.call_api(api='get_group_member_list', group_id=group_id)
    failed_user = []

    # 首先清除数据库中退群成员
    exist_member_list = []
    for user_info in group_member_list:
        user_qq = user_info['user_id']
        exist_member_list.append(int(user_qq))

    db_member_list = []
    for user_id, nickname in group.member_list().result:
        db_member_list.append(user_id)
    del_member_list = list(set(db_member_list).difference(set(exist_member_list)))

    for user_id in del_member_list:
        group.member_del(user=DBUser(user_id=user_id))

    # 更新群成员
    for user_info in group_member_list:
        # 用户信息
        user_qq = user_info['user_id']
        user_nickname = user_info['nickname']
        user_group_nickmane = user_info['card']
        if not user_group_nickmane:
            user_group_nickmane = user_nickname

        _user = DBUser(user_id=user_qq)
        _result = _user.add(nickname=user_nickname)
        if not _result.success():
            failed_user.append(_user.qq)
            logger.warning(f'User: {user_qq}, {_result.info}')
            continue

        _result = group.member_add(user=_user, user_group_nickname=user_group_nickmane)
        if not _result.success():
            failed_user.append(_user.qq)
            logger.warning(f'User: {user_qq}, {_result.info}')

    group.init_member_status()

    return Result(False, f'Success with ignore user: {failed_user}', 0)


async def set_group_notice(bot: Bot, event: Event, state: T_State) -> Result:
    group_id = event.dict().get('group_id')
    group = DBGroup(group_id=group_id)
    group_command = group.permission_command().result
    group_level = group.permission_level().result

    if state['sub_arg'] == 'on':
        result = group.permission_set(notice=1, command=group_command, level=group_level)
    elif state['sub_arg'] == 'off':
        result = group.permission_set(notice=0, command=group_command, level=group_level)
    else:
        result = Result(True, 'Missing parameters or Illegal parameter', -1)

    return result


async def set_group_command(bot: Bot, event: Event, state: T_State) -> Result:
    group_id = event.dict().get('group_id')
    group = DBGroup(group_id=group_id)
    group_notice = group.permission_notice().result
    group_level = group.permission_level().result

    if state['sub_arg'] == 'on':
        result = group.permission_set(notice=group_notice, command=1, level=group_level)
    elif state['sub_arg'] == 'off':
        result = group.permission_set(notice=group_notice, command=0, level=group_level)
    else:
        result = Result(True, 'Missing parameters or Illegal parameter', -1)

    return result


async def set_group_level(bot: Bot, event: Event, state: T_State) -> Result:
    group_id = event.dict().get('group_id')
    group = DBGroup(group_id=group_id)
    group_notice = group.permission_notice().result
    group_command = group.permission_command().result
    try:
        group_level = int(state['sub_arg'])
        result = group.permission_set(notice=group_notice, command=group_command, level=group_level)
    except Exception as e:
        result = Result(True, f'Missing parameters or Illegal parameter, {e}', -1)

    return result


async def show_group_permission(bot: Bot, event: Event, state: T_State) -> Result:
    group_id = event.dict().get('group_id')
    group = DBGroup(group_id=group_id)
    group_notice = group.permission_notice()
    group_command = group.permission_command()
    group_level = group.permission_level()

    if group_notice.success() and group_command.success() and group_level.success():
        msg = f'当前群组权限: \n\nNotice: {group_notice.result}\n' \
              f'Command: {group_command.result}\nPermissionLevel: {group_level.result}'
        result = Result(False, 'Success', msg)
    else:
        result = Result(True, 'Failed', '')

    return result


async def reset_group_permission(bot: Bot, event: Event, state: T_State) -> Result:
    group_id = event.dict().get('group_id')
    group = DBGroup(group_id=group_id)

    result = group.permission_reset()

    return result


# 启用自动更新群组的定时任务
scheduler = require("nonebot_plugin_apscheduler").scheduler


@scheduler.scheduled_job(
    'cron',
    # year=None,
    # month=None,
    # day='*/1',
    # week=None,
    # day_of_week=None,
    hour='4',
    # minute=None,
    # second='*/10',
    # start_date=None,
    # end_date=None,
    # timezone=None,
    id='refresh_group_info',
    coalesce=True,
    misfire_grace_time=600
)
async def refresh_group_info():
    from nonebot import get_bots

    for bot_id, bot in get_bots().items():
        group_list = await bot.call_api('get_group_list')
        for group in group_list:
            group_id = group.get('group_id')
            # 调用api获取群信息
            group_info = await bot.call_api(api='get_group_info', group_id=group_id)
            group_name = group_info['group_name']
            group = DBGroup(group_id=group_id)

            # 添加并初始化群信息
            group.add(name=group_name)

            # 更新用户
            group_member_list = await bot.call_api(api='get_group_member_list', group_id=group_id)

            # 首先清除数据库中退群成员
            exist_member_list = []
            for user_info in group_member_list:
                user_qq = user_info['user_id']
                exist_member_list.append(int(user_qq))

            db_member_list = []
            for user_id, nickname in group.member_list().result:
                db_member_list.append(user_id)
            del_member_list = list(set(db_member_list).difference(set(exist_member_list)))

            for user_id in del_member_list:
                group.member_del(user=DBUser(user_id=user_id))

            # 更新群成员
            for user_info in group_member_list:
                # 用户信息
                user_qq = user_info['user_id']
                user_nickname = user_info['nickname']
                user_group_nickmane = user_info['card']
                if not user_group_nickmane:
                    user_group_nickmane = user_nickname
                _user = DBUser(user_id=user_qq)
                _result = _user.add(nickname=user_nickname)
                if not _result.success():
                    logger.warning(f'Refresh group info, User: {user_qq}, {_result.info}')
                    continue
                _result = group.member_add(user=_user, user_group_nickname=user_group_nickmane)
                if not _result.success():
                    logger.warning(f'Refresh group info, User: {user_qq}, {_result.info}')

            group.init_member_status()
            logger.info(f'Refresh group info completed, Bot: {bot_id}, Group: {group_id}')
