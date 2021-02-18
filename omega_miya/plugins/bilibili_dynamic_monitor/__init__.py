import re
from nonebot import on_command, export, logger
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP_ADMIN, GROUP_OWNER
from omega_miya.utils.Omega_Base import DBGroup, DBSubscription, Result
from omega_miya.utils.Omega_plugin_utils import init_export
from omega_miya.utils.Omega_plugin_utils import has_command_permission, permission_level
from .utils import get_user_info
from .monitor import *


# Custom plugin usage text
__plugin_name__ = 'B站动态订阅'
__plugin_usage__ = r'''【B站动态订阅】
随时更新up动态

**Permission**
Command & Lv.20

**Usage**
**GroupAdmin and SuperUser Only**
/B站动态 订阅 [UID]
/B站动态 取消订阅 [UID]
/B站动态 清空订阅
/B站动态 订阅列表'''

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__)


# 注册事件响应器
bilibili_dynamic = on_command('B站动态', rule=has_command_permission() & permission_level(level=20), aliases={'b站动态'},
                              permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER, priority=20, block=True)


# 修改默认参数处理
@bilibili_dynamic.args_parser
async def parse(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await bilibili_dynamic.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await bilibili_dynamic.finish('操作已取消')


@bilibili_dynamic.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        pass
    elif args and len(args) == 1:
        state['sub_command'] = args[0]
    elif args and len(args) == 2:
        state['sub_command'] = args[0]
        state['uid'] = args[1]
    else:
        await bilibili_dynamic.finish('参数错误QAQ')


@bilibili_dynamic.got('sub_command', prompt='执行操作?\n【订阅/取消订阅/清空订阅/订阅列表】')
async def handle_sub_command_args(bot: Bot, event: GroupMessageEvent, state: T_State):
    if state['sub_command'] not in ['订阅', '取消订阅', '清空订阅', '订阅列表']:
        await bilibili_dynamic.reject('没有这个命令哦, 请在【订阅/取消订阅/清空订阅/订阅列表】中选择并重新发送, 取消命令请发送【取消】:')
    if state['sub_command'] == '订阅列表':
        _res = await sub_list(bot=bot, event=event, state=state)
        if not _res.success():
            logger.error(f"查询群组动态订阅失败, group_id: {event.group_id}, error: {_res.info}")
            await bilibili_dynamic.finish('查询群组动态订阅失败QAQ, 请稍后再试吧')
        msg = '本群已订阅以下动态:\n'
        for sub_id, up_name in _res.result:
            msg += f'\n【{sub_id}/{up_name}】'
        await bilibili_dynamic.finish(msg)
    elif state['sub_command'] == '清空订阅':
        state['uid'] = None


@bilibili_dynamic.got('uid', prompt='请输入订阅动态用户UID:')
async def handle_uid(bot: Bot, event: GroupMessageEvent, state: T_State):
    sub_command = state['sub_command']
    # 针对清空动态操作, 跳过获取动态信息
    if state['sub_command'] == '清空订阅':
        await bilibili_dynamic.pause('【警告!】\n即将清空本群组的所有订阅!\n请发送任意消息以继续操作:')
    # 动态信息获取部分
    uid = state['uid']
    if not re.match(r'^\d+$', uid):
        await bilibili_dynamic.reject('这似乎不是UID呢, 请重新输入:')
    _res = await get_user_info(user_uid=uid)
    if not _res.success():
        logger.error(f'获取用户信息失败, uid: {uid}, error: {_res.info}')
        await bilibili_dynamic.finish('获取用户信息失败了QAQ, 请稍后再试~')
    up_name = _res.result.get('name')
    state['up_name'] = up_name
    msg = f'即将{sub_command}【{up_name}】的动态!'
    await bilibili_dynamic.send(msg)


@bilibili_dynamic.got('check', prompt='确认吗?\n\n【是/否】')
async def handle_check(bot: Bot, event: GroupMessageEvent, state: T_State):
    check_msg = state['check']
    uid = state['uid']
    if check_msg != '是':
        await bilibili_dynamic.finish('操作已取消')
    sub_command = state['sub_command']
    if sub_command == '订阅':
        _res = await sub_add(bot=bot, event=event, state=state)
    elif sub_command == '取消订阅':
        _res = await sub_del(bot=bot, event=event, state=state)
    elif sub_command == '清空订阅':
        _res = await sub_clear(bot=bot, event=event, state=state)
    else:
        _res = Result(error=True, info='Unknown error, except sub_command', result=-1)
    if _res.success():
        logger.info(f"{sub_command}动态成功, group_id: {event.group_id}, uid: {uid}")
        await bilibili_dynamic.finish(f'{sub_command}成功!')
    else:
        logger.error(f"{sub_command}动态失败, group_id: {event.group_id}, uid: {uid},"
                     f"info: {_res.info}")
        await bilibili_dynamic.finish(f'{sub_command}失败了QAQ, 可能并未订阅该用户, 或请稍后再试~')


async def sub_list(bot: Bot, event: GroupMessageEvent, state: T_State) -> Result:
    group_id = event.group_id
    group = DBGroup(group_id=group_id)
    _res = group.subscription_list()
    dynamic_sub = []
    if not _res.success():
        return _res
    for sub_type, sub_id, up_name in _res.result:
        if sub_type == 2:
            dynamic_sub.append([sub_id, up_name])
    result = Result(error=False, info='Success', result=dynamic_sub)
    return result


async def sub_add(bot: Bot, event: GroupMessageEvent, state: T_State) -> Result:
    group_id = event.group_id
    group = DBGroup(group_id=group_id)
    uid = state['uid']
    sub = DBSubscription(sub_type=2, sub_id=uid)
    _res = sub.add(up_name=state.get('up_name'), live_info='动态')
    if not _res.success():
        return _res
    _res = group.subscription_add(sub=sub)
    if not _res.success():
        return _res
    result = Result(error=False, info='Success', result=0)
    return result


async def sub_del(bot: Bot, event: GroupMessageEvent, state: T_State) -> Result:
    group_id = event.group_id
    group = DBGroup(group_id=group_id)
    uid = state['uid']
    _res = group.subscription_del(sub=DBSubscription(sub_type=2, sub_id=uid))
    if not _res.success():
        return _res
    result = Result(error=False, info='Success', result=0)
    return result


async def sub_clear(bot: Bot, event: GroupMessageEvent, state: T_State) -> Result:
    group_id = event.group_id
    group = DBGroup(group_id=group_id)
    _res = group.subscription_clear_by_type(sub_type=2)
    if not _res.success():
        return _res
    result = Result(error=False, info='Success', result=0)
    return result
