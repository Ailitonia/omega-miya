"""
@Author         : Ailitonia
@Date           : 2023/8/4 2:50
@FileName       : command
@Project        : nonebot2_miya
@Description    : Bilibili 直播间订阅
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Annotated

from nonebot.log import logger
from nonebot.params import ArgStr, Depends
from nonebot.plugin import CommandGroup

from src.params.handler import get_command_str_single_arg_parser_handler, get_set_default_state_handler
from src.params.permission import IS_ADMIN
from src.service import OmegaMatcherInterface as OmMI
from src.service import enable_processor_state
from .consts import NOTICE_AT_ALL
from .data_source import query_live_room_status
from .helpers import add_live_room_sub, delete_live_room_sub, query_subscribed_live_room_sub_source
from .monitor import scheduler

bili_live = CommandGroup(
    'bili-live',
    permission=IS_ADMIN,
    priority=20,
    block=True,
    state=enable_processor_state(
        name='BilibiliLiveRoomSubscriptionManager',
        level=20,
        extra_auth_node={NOTICE_AT_ALL}
    ),
)


@bili_live.command(
    'add-subscription',
    aliases={'B站直播间订阅', 'b站直播间订阅', 'Bilibili直播间订阅', 'bilibili直播间订阅'},
    handlers=[
        get_set_default_state_handler('ensure', value=None),
        get_command_str_single_arg_parser_handler('room_id', ensure_key=True)
    ]
).got('ensure')
async def handle_add_subscription(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        ensure: Annotated[str | None, ArgStr('ensure')],
        room_id: Annotated[str | None, ArgStr('room_id')]
) -> None:
    # 检查是否收到确认消息后执行新增订阅
    if ensure is None or room_id is None:
        pass
    elif ensure in ['是', '确认', 'Yes', 'yes', 'Y', 'y']:
        await interface.send_reply('正在更新Bilibili直播间订阅信息, 请稍候')

        scheduler.pause()  # 暂停计划任务避免中途检查更新
        try:
            await add_live_room_sub(interface=interface, room_id=room_id)
            await interface.entity.commit_session()
            logger.success(f'{interface.entity}订阅直播间(rid={room_id})成功')
            msg = f'订阅直播间{room_id!r}成功'
        except Exception as e:
            logger.error(f'{interface.entity}订阅直播间(rid={room_id})失败, {e!r}')
            msg = f'订阅直播间{room_id!r}失败, 可能是网络异常或发生了意外的错误, 请稍后再试或联系管理员处理'
        scheduler.resume()
        await interface.finish_reply(msg)
    else:
        await interface.finish_reply('已取消操作')

    # 未收到确认消息后则为首次触发命令执行直播间信息检查
    if room_id is None:
        await interface.finish_reply('未提供直播间房间号参数, 已取消操作')
    room_id = room_id.strip()
    if not room_id.isdigit():
        await interface.finish_reply('非有效的直播间房间号, 直播间房间号应当为纯数字, 已取消操作')

    try:
        room_status = await query_live_room_status(room_id=room_id)
        # 针对直播间短号进行处理
        if room_id != room_status.live_room_id:
            logger.debug(f'订阅直播间短号{room_id}, 已转换为直播间房间号{room_status.live_room_id}')
            interface.matcher.state.update({'room_id': room_status.live_room_id})
    except Exception as e:
        logger.error(f'获取直播间{room_id!r}用户信息失败, {e!r}')
        await interface.finish_reply('获取直播间用户信息失败, 可能是网络原因或没有这个直播间, 请稍后再试')

    ensure_msg = f'即将订阅Bilibili用户【{room_status.live_user_name}】的直播间\n\n确认吗?\n【是/否】'
    await interface.reject_arg_reply('ensure', ensure_msg)


@bili_live.command(
    'del-subscription',
    aliases={'取消B站直播间订阅', '取消b站直播间订阅', '取消Bilibili直播间订阅', '取消bilibili直播间订阅'},
    handlers=[
        get_set_default_state_handler('ensure', value=None),
        get_command_str_single_arg_parser_handler('room_id', ensure_key=True)
    ]
).got('ensure')
async def handle_del_subscription(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        ensure: Annotated[str | None, ArgStr('ensure')],
        room_id: Annotated[str | None, ArgStr('room_id')]
) -> None:
    # 检查是否收到确认消息后执行删除订阅
    if ensure is None or room_id is None:
        pass
    elif ensure in ['是', '确认', 'Yes', 'yes', 'Y', 'y']:
        try:
            await delete_live_room_sub(interface=interface, room_id=room_id)
            await interface.entity.commit_session()
            logger.success(f'{interface.entity}取消订阅直播间(rid={room_id})成功')
            msg = f'取消订阅直播间{room_id!r}成功'
        except Exception as e:
            logger.error(f'{interface.entity}取消订阅直播间(rid={room_id})失败, {e!r}')
            msg = f'取消订阅直播间{room_id!r}失败, 请稍后再试或联系管理员处理'

        await interface.finish_reply(msg)
    else:
        await interface.finish_reply('已取消操作')

    # 未收到确认消息后则为首次触发命令执行直播间信息检查
    if room_id is None:
        await interface.finish_reply('未提供直播间房间号参数, 已取消操作')
    room_id = room_id.strip()
    if not room_id.isdigit():
        await interface.finish_reply('非有效的直播间房间号, 直播间房间号应当为纯数字, 已取消操作')

    try:
        exist_sub = await query_subscribed_live_room_sub_source(interface=interface)
        if room_id in exist_sub.keys():
            ensure_msg = f'取消订阅Bilibili用户【{exist_sub.get(room_id)}】的直播间\n\n确认吗?\n【是/否】'
            reject_key = 'ensure'
        else:
            exist_text = '\n'.join(f'{sub_id}: {user_nickname}' for sub_id, user_nickname in exist_sub.items())
            ensure_msg = f'未订阅直播间{room_id!r}, 请确认已订阅的直播间列表:\n\n{exist_text if exist_text else "无"}'
            reject_key = None
    except Exception as e:
        logger.error(f'获取{interface.entity}已订阅直播间失败, {e!r}')
        await interface.finish_reply('获取已订阅直播间列表失败, 请稍后再试或联系管理员处理')

    await interface.send_reply(ensure_msg)
    if reject_key is not None:
        await interface.matcher.reject_arg(reject_key)
    else:
        await interface.matcher.finish()


@bili_live.command(
    'list-subscription',
    aliases={'B站直播间订阅列表', 'b站直播间订阅列表', 'Bilibili直播间订阅列表', 'bilibili直播间订阅列表'},
    permission=None,
    priority=10
).handle()
async def handle_list_subscription(interface: Annotated[OmMI, Depends(OmMI.depend())]) -> None:
    try:
        exist_sub = await query_subscribed_live_room_sub_source(interface=interface)
        exist_text = '\n'.join(f'{sub_id}: {user_nickname}' for sub_id, user_nickname in exist_sub.items())
        await interface.send_reply(f'当前已订阅的Bilibili直播间:\n\n{exist_text if exist_text else "无"}')
    except Exception as e:
        logger.error(f'获取{interface.entity}已订阅直播间失败, {e!r}')
        await interface.send_reply('获取已订阅直播间列表失败, 请稍后再试或联系管理员处理')


__all__ = []
