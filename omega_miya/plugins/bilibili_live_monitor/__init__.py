import re
from nonebot import on_command, export, logger
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent, GroupMessageEvent, PrivateMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP_ADMIN, GROUP_OWNER, PRIVATE_FRIEND
from omega_miya.utils.Omega_Base import DBGroup, DBFriend, DBSubscription, Result
from omega_miya.utils.Omega_plugin_utils import init_export, init_permission_state
from omega_miya.utils.bilibili_utils import BiliLiveRoom
from .data_source import BiliLiveChecker
from .monitor import scheduler


# Custom plugin usage text
__plugin_name__ = 'B站直播间订阅'
__plugin_usage__ = r'''【B站直播间订阅】
监控直播间状态
开播、下播、直播间换标题提醒
群组/私聊可用

**Permission**
Friend Private
Command & Lv.20

**Usage**
**GroupAdmin and SuperUser Only**
/B站直播间 订阅 [房间号]
/B站直播间 取消订阅 [房间号]
/B站直播间 清空订阅
/B站直播间 订阅列表'''

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__)


# 注册事件响应器
bilibili_live = on_command(
    'B站直播间',
    aliases={'b站直播间'},
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_permission_state(
        name='bilibili_live',
        command=True,
        level=20),
    permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER | PRIVATE_FRIEND,
    priority=20,
    block=True)


# 修改默认参数处理
@bilibili_live.args_parser
async def parse(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await bilibili_live.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await bilibili_live.finish('操作已取消')


@bilibili_live.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        pass
    elif args and len(args) == 1:
        state['sub_command'] = args[0]
    elif args and len(args) == 2:
        state['sub_command'] = args[0]
        state['room_id'] = args[1]
    else:
        await bilibili_live.finish('参数错误QAQ')


@bilibili_live.got('sub_command', prompt='执行操作?\n【订阅/取消订阅/清空订阅/订阅列表】')
async def handle_sub_command_args(bot: Bot, event: MessageEvent, state: T_State):
    if isinstance(event, GroupMessageEvent):
        group_id = event.group_id
        msg = '本群已订阅以下直播间:\n'
    else:
        group_id = 'Private event'
        msg = '你已订阅以下直播间:\n'

    if state['sub_command'] not in ['订阅', '取消订阅', '清空订阅', '订阅列表']:
        await bilibili_live.finish('没有这个命令哦, 请在【订阅/取消订阅/清空订阅/订阅列表】中选择并重新发送')
    if state['sub_command'] == '订阅列表':
        _res = await sub_list(bot=bot, event=event, state=state)
        if not _res.success():
            logger.error(f"查询直播间订阅失败, {group_id} / {event.user_id}, error: {_res.info}")
            await bilibili_live.finish('查询直播间订阅失败QAQ, 请稍后再试吧')
        if not _res.result:
            msg = '当前没有任何直播间订阅'
        else:
            for sub_id, up_name in _res.result:
                msg += f'\n【{sub_id}/{up_name}】'
        await bilibili_live.finish(msg)
    elif state['sub_command'] == '清空订阅':
        state['room_id'] = None


@bilibili_live.got('room_id', prompt='请输入直播间房间号:')
async def handle_room_id(bot: Bot, event: MessageEvent, state: T_State):
    sub_command = state['sub_command']
    # 针对清空直播间操作, 跳过获取直播间信息
    if state['sub_command'] == '清空订阅':
        await bilibili_live.pause('【警告!】\n即将清空本的所有订阅!\n请发送任意消息以继续操作:')
    # 直播间信息获取部分
    room_id = state['room_id']
    if not re.match(r'^\d+$', room_id):
        await bilibili_live.reject('这似乎不是房间号呢, 房间号应为纯数字, 请重新输入:')
    up_name_result = await BiliLiveRoom(room_id=int(room_id)).get_user_info()
    if up_name_result.error:
        logger.error(f'获取直播间信息失败, room_id: {room_id}, error: {up_name_result.info}')
        await bilibili_live.finish('获取直播间信息失败了QAQ, 请稍后再试~')
    up_name = up_name_result.result.name
    state['up_name'] = up_name
    msg = f'即将{sub_command}【{up_name}】的直播间!'
    await bilibili_live.send(msg)


@bilibili_live.got('check', prompt='确认吗?\n\n【是/否】')
async def handle_check(bot: Bot, event: MessageEvent, state: T_State):
    if isinstance(event, GroupMessageEvent):
        group_id = event.group_id
    else:
        group_id = 'Private event'

    check_msg = state['check']
    room_id = state['room_id']
    if check_msg != '是':
        await bilibili_live.finish('操作已取消')
    sub_command = state['sub_command']
    if sub_command == '订阅':
        _res = await sub_add(bot=bot, event=event, state=state)
    elif sub_command == '取消订阅':
        _res = await sub_del(bot=bot, event=event, state=state)
    elif sub_command == '清空订阅':
        _res = await sub_clear(bot=bot, event=event, state=state)
    else:
        _res = Result.IntResult(error=True, info='Unknown error, except sub_command', result=-1)
    if _res.success():
        logger.info(f"{sub_command}直播间成功, {group_id} / {event.user_id}, room_id: {room_id}")
        await bilibili_live.finish(f'{sub_command}成功!')
    else:
        logger.error(f"{sub_command}直播间失败, {group_id} / {event.user_id}, room_id: {room_id},"
                     f"info: {_res.info}")
        await bilibili_live.finish(f'{sub_command}失败了QAQ, 可能并未订阅该用户, 或请稍后再试~')


async def sub_list(bot: Bot, event: MessageEvent, state: T_State) -> Result.ListResult:
    if isinstance(event, GroupMessageEvent):
        group_id = event.group_id
        group = DBGroup(group_id=group_id)
        result = await group.subscription_list_by_type(sub_type=1)
        return result
    elif isinstance(event, PrivateMessageEvent):
        user_id = event.user_id
        friend = DBFriend(user_id=user_id)
        result = await friend.subscription_list_by_type(sub_type=1)
        return result
    else:
        return Result.ListResult(error=True, info='Illegal event', result=[])


async def sub_add(bot: Bot, event: MessageEvent, state: T_State) -> Result.IntResult:
    if isinstance(event, GroupMessageEvent):
        group_id = event.group_id
        group = DBGroup(group_id=group_id)
        room_id = state['room_id']
        sub = DBSubscription(sub_type=1, sub_id=room_id)
        _res = await sub.add(up_name=state.get('up_name'), live_info='B站直播间')
        if not _res.success():
            return _res
        _res = await group.subscription_add(sub=sub)
        if not _res.success():
            return _res
        # 添加直播间时需要刷新全局监控列表
        # 执行一次初始化
        await BiliLiveChecker(room_id=int(room_id)).init_live_info()
        result = Result.IntResult(error=False, info='Success', result=0)
        return result
    elif isinstance(event, PrivateMessageEvent):
        user_id = event.user_id
        friend = DBFriend(user_id=user_id)
        room_id = state['room_id']
        sub = DBSubscription(sub_type=1, sub_id=room_id)
        _res = await sub.add(up_name=state.get('up_name'), live_info='B站直播间')
        if not _res.success():
            return _res
        _res = await friend.subscription_add(sub=sub)
        if not _res.success():
            return _res
        # 添加直播间时需要刷新全局监控列表
        # 执行一次初始化
        await BiliLiveChecker(room_id=int(room_id)).init_live_info()
        result = Result.IntResult(error=False, info='Success', result=0)
        return result
    else:
        return Result.IntResult(error=True, info='Illegal event', result=-1)


async def sub_del(bot: Bot, event: MessageEvent, state: T_State) -> Result.IntResult:
    if isinstance(event, GroupMessageEvent):
        group_id = event.group_id
        group = DBGroup(group_id=group_id)
        room_id = state['room_id']
        _res = await group.subscription_del(sub=DBSubscription(sub_type=1, sub_id=room_id))
        if not _res.success():
            return _res
        result = Result.IntResult(error=False, info='Success', result=0)
        return result
    elif isinstance(event, PrivateMessageEvent):
        user_id = event.user_id
        friend = DBFriend(user_id=user_id)
        room_id = state['room_id']
        _res = await friend.subscription_del(sub=DBSubscription(sub_type=1, sub_id=room_id))
        if not _res.success():
            return _res
        result = Result.IntResult(error=False, info='Success', result=0)
        return result
    else:
        return Result.IntResult(error=True, info='Illegal event', result=-1)


async def sub_clear(bot: Bot, event: MessageEvent, state: T_State) -> Result.IntResult:
    if isinstance(event, GroupMessageEvent):
        group_id = event.group_id
        group = DBGroup(group_id=group_id)
        _res = await group.subscription_clear_by_type(sub_type=1)
        if not _res.success():
            return _res
        result = Result.IntResult(error=False, info='Success', result=0)
        return result
    elif isinstance(event, PrivateMessageEvent):
        user_id = event.user_id
        friend = DBFriend(user_id=user_id)
        _res = await friend.subscription_clear_by_type(sub_type=1)
        if not _res.success():
            return _res
        result = Result.IntResult(error=False, info='Success', result=0)
        return result
    else:
        return Result.IntResult(error=True, info='Illegal event', result=-1)
