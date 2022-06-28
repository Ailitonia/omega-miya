"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : bilibili_live_monitor.py
@Project        : nonebot2_miya
@Description    : Bilibili 直播间订阅
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.log import logger
from nonebot.plugin import on_command, PluginMetadata
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP, GROUP_ADMIN, GROUP_OWNER, PRIVATE_FRIEND
from nonebot.adapters.onebot.v11.message import Message
from nonebot.params import CommandArg, ArgStr

from omega_miya.service import init_processor_state
from omega_miya.service.gocqhttp_guild_patch.permission import GUILD
from omega_miya.params import state_plain_text
from omega_miya.web_resource.bilibili import BilibiliLiveRoom
from omega_miya.utils.process_utils import run_async_catching_exception

from .monitor import scheduler
from .utils import add_bili_live_room_sub, delete_bili_live_room_sub, query_subscribed_bili_live_room_sub_source


__plugin_meta__ = PluginMetadata(
    name="B站直播间订阅",
    description="【B站直播间订阅插件】\n"
                "订阅并监控Bilibili直播间状态\n"
                "提供开播、下播、直播间换标题提醒",
    usage="仅限私聊或群聊中群管理员使用:\n"
          "/B站直播间订阅 [RoomID]\n"
          "/B站直播间取消订阅 [RoomID]\n"
          "/B站直播间订阅列表",
    extra={"author": "Ailitonia"},
)


add_live_sub = on_command(
    'BilibiliAddLiveSubscription',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='AddLiveSubscription',
        level=20,
        auth_node='bilibili_add_live_subscription'
    ),
    aliases={'B站直播间订阅', 'b站直播间订阅', 'Bilibili直播间订阅', 'bilibili直播间订阅'},
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND,
    priority=20,
    block=True
)


@add_live_sub.handle()
async def handle_parse_room_id(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    room_id = cmd_arg.extract_plain_text().strip()
    if room_id:
        state.update({'room_id': room_id})


@add_live_sub.got('room_id', prompt='请输入直播间房间号:')
async def handle_check_add_room_id(matcher: Matcher, room_id: str = ArgStr('room_id')):
    room_id = room_id.strip()
    if not room_id.isdigit():
        await matcher.reject('直播间房间号应当为纯数字, 请重新输入:')

    room = BilibiliLiveRoom(room_id=int(room_id))
    room_user_data = await run_async_catching_exception(room.get_live_room_user_model)()
    if isinstance(room_user_data, Exception) or room_user_data.error:
        logger.error(f'BilibiliAddLiveSubscription | 获取直播间(room_id={room_id})用户信息失败, {room_user_data}')
        await matcher.finish('获取直播间用户信息失败了QAQ, 可能是网络原因或没有这个直播间, 请稍后再试')

    await matcher.send(f'即将订阅Bilibili用户【{room_user_data.data.name}】的直播间!')


@add_live_sub.got('check', prompt='确认吗?\n\n【是/否】')
async def handle_add_live_subscription(bot: Bot, matcher: Matcher, event: MessageEvent,
                                       check: str = ArgStr('check'), room_id: str = state_plain_text('room_id')):
    check = check.strip()
    if check != '是':
        await matcher.finish('那就不订阅了哦')

    await matcher.send('正在更新Bilibili用户订阅信息, 请稍候')
    room = BilibiliLiveRoom(room_id=int(room_id))
    scheduler.pause()  # 暂停计划任务避免中途检查更新
    add_sub_result = await add_bili_live_room_sub(bot=bot, event=event, live_room=room)
    scheduler.resume()

    if isinstance(add_sub_result, Exception) or add_sub_result.error:
        logger.error(f"BilibiliAddLiveSubscription | 订阅直播间(rid={room_id})失败, {add_sub_result}")
        await matcher.finish(f'订阅失败了QAQ, 可能是网络异常或发生了意外的错误, 请稍后重试或联系管理员处理')
    else:
        logger.success(f"BilibiliAddLiveSubscription | 订阅直播间(rid={room_id})成功")
        await matcher.finish(f'订阅成功!')


delete_live_sub = on_command(
    'BilibiliDeleteLiveSubscription',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='DeleteLiveSubscription',
        level=20,
        auth_node='bilibili_delete_live_sub'
    ),
    aliases={'B站直播间取消订阅', 'b站直播间取消订阅', 'Bilibili直播间取消订阅', 'bilibili直播间取消订阅'},
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND,
    priority=20,
    block=True
)


@delete_live_sub.handle()
async def handle_parse_room_id(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    room_id = cmd_arg.extract_plain_text().strip()
    if room_id:
        state.update({'room_id': room_id})


@delete_live_sub.got('room_id', prompt='请输入直播间房间号:')
async def handle_delete_user_sub(bot: Bot, event: MessageEvent, matcher: Matcher, room_id: str = ArgStr('room_id')):
    room_id = room_id.strip()
    if not room_id.isdigit():
        await matcher.reject('直播间房间号应当为纯数字, 请重新输入:')

    exist_sub = await query_subscribed_bili_live_room_sub_source(bot=bot, event=event)
    if isinstance(exist_sub, Exception):
        logger.error(f'BilibiliDeleteLiveSubscription | 获取({event})已订阅直播间失败, {exist_sub}')
        await matcher.finish('获取已订阅列表失败QAQ, 请稍后再试或联系管理员处理')

    for sub in exist_sub:
        if room_id == sub[0]:
            user_nick = sub[1]
            break
    else:
        exist_text = '\n'.join(f'{x[0]}: {x[1]}' for x in exist_sub)
        await matcher.reject(f'当前没有订阅这个直播间哦, 请在已订阅列表中选择并重新输入直播间房间号:\n\n{exist_text}')
        return

    delete_result = await delete_bili_live_room_sub(bot=bot, event=event, room_id=room_id)
    if isinstance(delete_result, Exception) or delete_result.error:
        logger.error(f"BilibiliDeleteLiveSubscription | 取消订阅直播间(rid={room_id})失败, {delete_result}")
        await matcher.finish(f'取消订阅失败了QAQ, 发生了意外的错误, 请联系管理员处理')
    else:
        logger.success(f"BilibiliDeleteLiveSubscription | 取消订阅直播间(rid={room_id})成功")
        await matcher.finish(f'已取消Bilibili直播间【{user_nick}】的订阅!')


list_live_sub = on_command(
    'BilibiliListLiveSubscription',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='ListLiveSubscription',
        level=20,
        auth_node='bilibili_list_live_subscription'
    ),
    aliases={'B站直播间订阅列表', 'b站直播间订阅列表', 'Bilibili直播间订阅列表', 'bilibili直播间订阅列表'},
    permission=GROUP | GUILD | PRIVATE_FRIEND,
    priority=20,
    block=True
)


@list_live_sub.handle()
async def handle_list_subscription(bot: Bot, event: MessageEvent, matcher: Matcher):
    exist_sub = await query_subscribed_bili_live_room_sub_source(bot=bot, event=event)
    if isinstance(exist_sub, Exception):
        logger.error(f'BilibiliListLiveSubscription | 获取({event})已订阅直播间失败, {exist_sub}')
        await matcher.finish('获取订阅列表失败QAQ, 请稍后再试或联系管理员处理')

    exist_text = '\n'.join(f'{x[0]}: {x[1]}' for x in exist_sub)
    await matcher.finish(f'当前已订阅的Bilibili直播间:\n\n{exist_text}')
