"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : bilibili_dynamic_monitor.py
@Project        : nonebot2_miya
@Description    : Bilibili 用户动态订阅
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Annotated

from nonebot.log import logger
from nonebot.params import ArgStr, Depends
from nonebot.plugin import CommandGroup

from src.params.handler import get_command_str_single_arg_parser_handler, get_set_default_state_handler
from src.params.permission import IS_ADMIN
from src.service import EntityInterface, MatcherInterface, enable_processor_state
from src.utils.bilibili_api import BilibiliUser
from src.utils.bilibili_api.exception import BilibiliApiError

from .monitor import scheduler
from .helpers import add_dynamic_sub, delete_dynamic_sub, query_entity_subscribed_dynamic_sub_source


bili_dynamic = CommandGroup(
    'bili_dynamic',
    permission=IS_ADMIN,
    priority=20,
    block=True,
    state=enable_processor_state(name='BilibiliDynamicSubscriptionManager', level=20),
)


@bili_dynamic.command(
    'add-subscription',
    aliases={'B站动态订阅', 'b站动态订阅', 'Bilibili动态订阅', 'bilibili动态订阅'},
    handlers=[
        get_set_default_state_handler('ensure', value=None),
        get_command_str_single_arg_parser_handler('uid', ensure_key=True)
    ]
).got('ensure')
async def handle_add_subscription(
        entity_interface: Annotated[EntityInterface, Depends(EntityInterface())],
        ensure: Annotated[str | None, ArgStr('ensure')],
        uid: Annotated[str | None, ArgStr('uid')]
) -> None:
    matcher_interface = MatcherInterface()

    # 检查是否收到确认消息后执行新增订阅
    if ensure is None:
        pass
    elif ensure in ['是', '确认', 'Yes', 'yes', 'Y', 'y']:
        await matcher_interface.send_at_sender('正在更新Bilibili用户动态订阅信息, 请稍候')

        user = BilibiliUser(uid=int(uid))
        scheduler.pause()  # 暂停计划任务避免中途检查更新
        try:
            await add_dynamic_sub(entity_interface=entity_interface, bili_user=user)
            await entity_interface.entity.commit_session()
            logger.success(f'{entity_interface.entity}订阅用户{user}动态成功')
            msg = f'订阅用户{uid}动态成功'
        except Exception as e:
            logger.error(f'{entity_interface.entity}订阅用户{user}动态失败, {e!r}')
            msg = f'订阅用户{user}动态失败, 可能是网络异常或发生了意外的错误, 请稍后再试或联系管理员处理'
        scheduler.resume()
        await matcher_interface.send_at_sender(msg)
        return
    else:
        await matcher_interface.send_at_sender('已取消操作')
        return

    # 未收到确认消息后则为首次触发命令执行用户动态信息检查
    if uid is None:
        await matcher_interface.send_at_sender('未提供用户UID参数, 已取消操作')
        return
    uid = uid.strip()
    if not uid.isdigit():
        await matcher_interface.send_at_sender('非有效的用户UID, 用户UID应当为纯数字, 已取消操作')
        return

    try:
        user = BilibiliUser(uid=int(uid))
        user_data = await user.query_user_data()
        if user_data.error:
            raise BilibiliApiError(f'query {user} data failed, {user_data.message}')
    except Exception as e:
        logger.error(f'获取用户{uid}信息失败, {e!r}')
        await matcher_interface.send_at_sender('获取用户信息失败, 可能是网络原因或没有这个用户, 请稍后再试')
        return

    ensure_msg = f'即将订阅Bilibili用户【{user_data.data.name}】的动态\n\n确认吗?\n【是/否】'
    await matcher_interface.send_at_sender(ensure_msg)
    await matcher_interface.matcher.reject_arg('ensure')


@bili_dynamic.command(
    'del-subscription',
    aliases={'取消B站动态订阅', '取消b站动态订阅', '取消Bilibili动态订阅', '取消bilibili动态订阅'},
    handlers=[
        get_set_default_state_handler('ensure', value=None),
        get_command_str_single_arg_parser_handler('uid', ensure_key=True)
    ]
).got('ensure')
async def handle_del_subscription(
        entity_interface: Annotated[EntityInterface, Depends(EntityInterface())],
        ensure: Annotated[str | None, ArgStr('ensure')],
        uid: Annotated[str | None, ArgStr('uid')]
) -> None:
    matcher_interface = MatcherInterface()

    # 检查是否收到确认消息后执行删除订阅
    if ensure is None:
        pass
    elif ensure in ['是', '确认', 'Yes', 'yes', 'Y', 'y']:
        try:
            await delete_dynamic_sub(entity_interface=entity_interface, uid=int(uid))
            await entity_interface.entity.commit_session()
            logger.success(f'{entity_interface.entity}取消订阅用户(uid={uid})动态成功')
            msg = f'取消订阅用户{uid}动态成功'
        except Exception as e:
            logger.error(f'{entity_interface.entity}取消订阅用户(uid={uid})动态失败, {e!r}')
            msg = f'取消订阅用户{uid}动态失败, 请稍后再试或联系管理员处理'
        await matcher_interface.send_at_sender(msg)
        return
    else:
        await matcher_interface.send_at_sender('已取消操作')
        return

    # 未收到确认消息后则为首次触发命令执行用户动态信息检查
    if uid is None:
        await matcher_interface.send_at_sender('未提供用户UID参数, 已取消操作')
        return
    uid = uid.strip()
    if not uid.isdigit():
        await matcher_interface.send_at_sender('非有效的用户UID, 用户UID应当为纯数字, 已取消操作')
        return

    try:
        exist_sub = await query_entity_subscribed_dynamic_sub_source(entity_interface=entity_interface)
        if uid in exist_sub.keys():
            ensure_msg = f'取消订阅Bilibili用户【{exist_sub.get(uid)}】的动态\n\n确认吗?\n【是/否】'
            reject_key = 'ensure'
        else:
            exist_text = '\n'.join(f'{sub_id}: {user_nickname}' for sub_id, user_nickname in exist_sub.items())
            ensure_msg = f'未订阅用户{uid}, 请确认已订阅的用户动态列表:\n\n{exist_text if exist_text else "无"}'
            reject_key = None
    except Exception as e:
        logger.error(f'获取{entity_interface.entity}已订阅用户动态列表失败, {e!r}')
        await matcher_interface.send_at_sender('获取已订阅用户动态列表失败, 请稍后再试或联系管理员处理')
        return

    await matcher_interface.send_at_sender(ensure_msg)
    if reject_key is not None:
        await matcher_interface.matcher.reject_arg(reject_key)
    else:
        await matcher_interface.matcher.finish()


@bili_dynamic.command(
    'list-subscription',
    aliases={'B站动态订阅列表', 'b站动态订阅列表', 'Bilibili动态订阅列表', 'bilibili动态订阅列表'},
    permission=None,
    priority=10
).handle()
async def handle_list_subscription(entity_interface: Annotated[EntityInterface, Depends(EntityInterface())]) -> None:
    matcher_interface = MatcherInterface()

    try:
        exist_sub = await query_entity_subscribed_dynamic_sub_source(entity_interface=entity_interface)
        exist_text = '\n'.join(f'{sub_id}: {user_nickname}' for sub_id, user_nickname in exist_sub.items())
        await matcher_interface.send_at_sender(f'当前已订阅的Bilibili用户动态:\n\n{exist_text if exist_text else "无"}')
    except Exception as e:
        logger.error(f'获取{entity_interface.entity}已订阅用户动态列表失败, {e!r}')
        await matcher_interface.send_at_sender('获取已订阅用户动态列表失败, 请稍后再试或联系管理员处理')


__all__ = []
