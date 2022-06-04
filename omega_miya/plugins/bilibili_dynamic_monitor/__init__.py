"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : bilibili_dynamic_monitor.py
@Project        : nonebot2_miya
@Description    : Bilibili 用户动态订阅
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot import on_command, logger
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
from omega_miya.web_resource.bilibili import BilibiliUser
from omega_miya.utils.process_utils import run_async_catching_exception

from .utils import (add_bili_user_dynamic_sub, delete_bili_user_dynamic_sub,
                    query_subscribed_bili_user_dynamic_sub_source)
from .monitor import scheduler


# Custom plugin usage text
__plugin_custom_name__ = 'B站动态订阅'
__plugin_usage__ = r'''【B站动态订阅】
订阅并跟踪Bilibili用户动态更新

用法:
仅限私聊或群聊中群管理员使用:
/B站动态订阅 [UID]
/B站动态取消订阅 [UID]
/B站动态订阅列表'''


add_dynamic_sub = on_command(
    'BilibiliAddDynamicSubscription',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='AddDynamicSubscription',
        level=20,
        auth_node='bilibili_add_dynamic_subscription'
    ),
    aliases={'B站动态订阅', 'b站动态订阅', 'Bilibili动态订阅', 'bilibili动态订阅'},
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND,
    priority=20,
    block=True
)


@add_dynamic_sub.handle()
async def handle_parse_user_id(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    user_id = cmd_arg.extract_plain_text().strip()
    if user_id:
        state.update({'user_id': user_id})


@add_dynamic_sub.got('user_id', prompt='请输入用户的UID:')
async def handle_check_add_user_id(matcher: Matcher, user_id: str = ArgStr('user_id')):
    user_id = user_id.strip()
    if not user_id.isdigit():
        await matcher.reject('用户UID应当为纯数字, 请重新输入:')

    user = BilibiliUser(uid=int(user_id))
    user_data = await run_async_catching_exception(user.get_user_model)()
    if isinstance(user_data, Exception) or user_data.error:
        logger.error(f'BilibiliAddDynamicSubscription | 获取用户(uid={user_id})失败, {user_data}')
        await matcher.finish('获取用户信息失败了QAQ, 可能是网络原因或没有这个用户, 请稍后再试')

    await matcher.send(f'即将订阅Bilibili用户【{user_data.data.name}】的动态!')


@add_dynamic_sub.got('check', prompt='确认吗?\n\n【是/否】')
async def handle_add_user_subscription(bot: Bot, matcher: Matcher, event: MessageEvent,
                                       check: str = ArgStr('check'), user_id: str = state_plain_text('user_id')):
    check = check.strip()
    if check != '是':
        await matcher.finish('那就不订阅了哦')

    await matcher.send('正在更新Bilibili用户订阅信息, 请稍候')
    user = BilibiliUser(uid=int(user_id))
    scheduler.pause()  # 暂停计划任务避免中途检查更新
    add_sub_result = await add_bili_user_dynamic_sub(bot=bot, event=event, bili_user=user)
    scheduler.resume()

    if isinstance(add_sub_result, Exception) or add_sub_result.error:
        logger.error(f"BilibiliAddDynamicSubscription | 订阅用户(uid={user_id})失败, {add_sub_result}")
        await matcher.finish(f'订阅失败了QAQ, 可能是网络异常或发生了意外的错误, 请稍后重试或联系管理员处理')
    else:
        logger.success(f"BilibiliAddDynamicSubscription | 订阅用户(uid={user_id})成功")
        await matcher.finish(f'订阅成功!')


delete_dynamic_sub = on_command(
    'BilibiliDeleteDynamicSubscription',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='DeleteDynamicSubscription',
        level=20,
        auth_node='bilibili_delete_dynamic_subscription'
    ),
    aliases={'B站动态取消订阅', 'b站动态取消订阅', 'Bilibili动态取消订阅', 'bilibili动态取消订阅'},
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND,
    priority=20,
    block=True
)


@delete_dynamic_sub.handle()
async def handle_parse_user_id(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    user_id = cmd_arg.extract_plain_text().strip()
    if user_id:
        state.update({'user_id': user_id})


@delete_dynamic_sub.got('user_id', prompt='请输入用户的UID:')
async def handle_delete_user_sub(bot: Bot, event: MessageEvent, matcher: Matcher, user_id: str = ArgStr('user_id')):
    user_id = user_id.strip()
    if not user_id.isdigit():
        await matcher.reject('用户UID应当为纯数字, 请重新输入:')

    exist_sub = await query_subscribed_bili_user_dynamic_sub_source(bot=bot, event=event)
    if isinstance(exist_sub, Exception):
        logger.error(f'BilibiliDeleteDynamicSubscription | 获取({event})已订阅用户失败, {exist_sub}')
        await matcher.finish('获取已订阅列表失败QAQ, 请稍后再试或联系管理员处理')

    for sub in exist_sub:
        if user_id == sub[0]:
            user_nick = sub[1]
            break
    else:
        exist_text = '\n'.join(f'{x[0]}: {x[1]}' for x in exist_sub)
        await matcher.reject(f'当前没有订阅这个用户哦, 请在已订阅列表中选择并重新输入用户UID:\n\n{exist_text}')
        return

    delete_result = await delete_bili_user_dynamic_sub(bot=bot, event=event, user_id=user_id)
    if isinstance(delete_result, Exception) or delete_result.error:
        logger.error(f"BilibiliDeleteDynamicSubscription | 取消订阅用户(uid={user_id})失败, {delete_result}")
        await matcher.finish(f'取消订阅失败了QAQ, 发生了意外的错误, 请联系管理员处理')
    else:
        logger.success(f"BilibiliDeleteDynamicSubscription | 取消订阅用户(uid={user_id})成功")
        await matcher.finish(f'已取消Bilibili用户【{user_nick}】的订阅!')


list_dynamic_sub = on_command(
    'BilibiliListDynamicSubscription',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='ListDynamicSubscription',
        level=20,
        auth_node='bilibili_list_dynamic_subscription'
    ),
    aliases={'B站动态订阅列表', 'b站动态订阅列表', 'Bilibili动态订阅列表', 'bilibili动态订阅列表'},
    permission=GROUP | GUILD | PRIVATE_FRIEND,
    priority=20,
    block=True
)


@list_dynamic_sub.handle()
async def handle_list_subscription(bot: Bot, event: MessageEvent, matcher: Matcher):
    exist_sub = await query_subscribed_bili_user_dynamic_sub_source(bot=bot, event=event)
    if isinstance(exist_sub, Exception):
        logger.error(f'BilibiliListDynamicSubscription | 获取({event})已订阅用户失败, {exist_sub}')
        await matcher.finish('获取订阅列表失败QAQ, 请稍后再试或联系管理员处理')

    exist_text = '\n'.join(f'{x[0]}: {x[1]}' for x in exist_sub)
    await matcher.finish(f'当前已订阅的Bilibili用户动态:\n\n{exist_text}')
