"""Omega Miya 使用指南

- /Omega Init - bot 首次加入新群组/首次添加 bot 好友后, 须使用本命令进行初始化 (初始化并启用基本功能, 不会覆盖已有信息, 仅供第一次使用bot时执行)
- /Omega Enable - 启用 bot 功能
- /Omega Disable - 禁用用 bot 功能
- /Omega SetLevel <PermissionLevel> - 设置权限等级
- /Omega ShowPermission - 查询权限状态
- /Omega QuitGroup - 命令 bot 退群, 会有一段取消时间延迟
- /Omega CancelQuitGroup - 取消 bot 退群命令
"""

from datetime import datetime, timedelta
from nonebot import on_command, logger
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.message import Message
from nonebot.adapters.onebot.v11.event import MessageEvent, GroupMessageEvent, PrivateMessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER, PRIVATE_FRIEND
from nonebot.params import CommandArg, ArgStr

from omega_miya.database import InternalBotUser, InternalBotGroup
from omega_miya.service import init_processor_state
from omega_miya.utils.process_utils import run_async_catching_exception
from omega_miya.onebot_api import GoCqhttpBot
from omega_miya.utils.apscheduler import scheduler


# Custom plugin usage text
__plugin_custom_name__ = '核心管理'
__plugin_usage__ = r'''【Omega 机器人核心管理插件】
机器人开关、维护、功能及基础权限管理
仅限管理员或私聊使用

用法:
/omega Init
/omega Enable
/omega Disable
/omega SetLevel <PermissionLevel>
/omega ShowPermission
/omega QuitGroup
/omega CancelQuitGroup

说明:
Init: 初始化并启用基本功能, 不会覆盖已有信息, 仅供第一次使用bot时执行
Enable: 启用 bot 功能
Disable: 禁用 bot 功能
SetLevel: 设置权限等级
ShowPermission: 查询权限状态
QuitGroup: 命令bot退群
CancelQuitGroup: 取消bot退群'''


DEFAULT_PERMISSION_LEVEL: int = 10
"""初始化时默认的权限等级"""
MAX_PERMISSION_LEVEL: int = 100
"""通过本命令可以设置的最高权限等级"""
QUIT_GROUP_DELAY: int = 90
"""退群命令延迟时间, 单位秒"""
QUIT_GROUP_JOB_PREFIX: str = 'quit_group_countdown_'
"""退群倒计时任务名前缀"""


# 注册事件响应器
omega = on_command(
    'Omega',
    state=init_processor_state(name='OmegaManager', enable_processor=False),
    aliases={'omega'},
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND,
    priority=10,
    block=True
)


@omega.handle()
async def handle_parse_operating(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    cmd_args = cmd_arg.extract_plain_text().strip().lower().split()
    arg_num = len(cmd_args)
    match arg_num:
        case 1:
            state.update({'operating': cmd_args[0], 'operation_arg': ''})
        case 2:
            state.update({'operating': cmd_args[0], 'operation_arg': cmd_args[1]})
        case _:
            await omega.finish('你好呀~\n我是Omega Miya~\n请问您今天要来点喵娘吗?')


@omega.got('operating', prompt='请输入要执行的操作:')
@omega.got('operation_arg', prompt='请输入要执行操作的参数:')
async def handle_operating(
        bot: Bot,
        event: MessageEvent,
        matcher: Matcher,
        operating: str = ArgStr('operating'),
        operation_arg: str = ArgStr('operation_arg')
):
    """处理需要执行的不同操作"""
    await verify_friend(bot=bot, event=event, matcher=matcher)
    operating = operating.strip().lower()
    match operating:
        case 'init':
            result = await operation_init(bot=bot, event=event)
            result_prefix = '初始化'
            msg = None
        case 'enable':
            result = await operation_enable(event=event)
            result_prefix = '启用'
            msg = None
        case 'disable':
            result = await operation_disable(event=event)
            result_prefix = '禁用'
            msg = None
        case 'setlevel':
            if not operation_arg.isdigit():
                await omega.reject_arg(key='operation_arg', prompt='权限等级应为整数, 请重新输入:')
            level = int(operation_arg)
            if level < 0 or level > MAX_PERMISSION_LEVEL:
                await omega.reject_arg(key='operation_arg',
                                       prompt=f'可设定的权限等级范围为 0~{MAX_PERMISSION_LEVEL}, 请重新输入:')
            result = await operation_set_permission_level(event=event, level=level)
            result_prefix = '设置权限等级'
            msg = None
        case 'showpermission':
            result = await operation_show_permission(event=event)
            result_prefix = '查询权限状态'
            msg = f'当前权限状态:\n\n{result}'
        case 'quitgroup':
            if not isinstance(event, GroupMessageEvent):
                await omega.finish('退群命令仅限在群聊中使用')
            result = await operation_quit_group(bot=bot, event=event)
            result_prefix = '命令退群'
            msg = f'退群命令已接受\n注意: Bot 将在 {QUIT_GROUP_DELAY} 秒后退群!'
        case 'cancelquitgroup':
            if not isinstance(event, GroupMessageEvent):
                await omega.finish('取消退群命令仅限在群聊中使用')
            result = await operation_cancel_quit_group(event=event)
            result_prefix = '取消退群'
            msg = f'已取消退群'
        case _:
            await omega.finish('你好呀~\n我是Omega Miya~\n请问您今天要来点喵娘吗?')
            return

    if isinstance(result, Exception) or not result:
        logger.error(f'Omega {result_prefix}失败, {result}')
        await omega.finish(f'Omega {result_prefix}失败, 请联系管理员处理')
    else:
        logger.success(f'Omega {result_prefix}成功')
        await omega.finish(f'Omega {result_prefix}成功' if not msg else msg)


def get_entity_from_event(event: MessageEvent) -> InternalBotUser | InternalBotGroup:
    """根据 event 中获取授权操作对象"""
    bot_self_id = str(event.self_id)
    if isinstance(event, GroupMessageEvent):
        entity = InternalBotGroup(bot_id=bot_self_id, parent_id=bot_self_id, entity_id=str(event.group_id))
    else:
        entity = InternalBotUser(bot_id=bot_self_id, parent_id=bot_self_id, entity_id=str(event.user_id))
    return entity


async def verify_friend(bot: Bot, event: MessageEvent, matcher: Matcher) -> None:
    """验证当前会话如果是私聊则用户必须是 bot 好友, 否则中止会话"""
    if isinstance(event, PrivateMessageEvent):
        gocq_bot = GoCqhttpBot(bot=bot)
        friend_list = await gocq_bot.get_friend_list()
        if str(event.user_id) not in (x.user_id for x in friend_list):
            await matcher.finish(f'用户: {event.user_id} 不是 bot 好友, 会话中止')


@run_async_catching_exception
async def operation_init(bot: Bot, event: MessageEvent) -> bool:
    """执行 Init 初始化并启用基本功能"""
    entity = get_entity_from_event(event=event)
    gocq_bot = GoCqhttpBot(bot=bot)
    if isinstance(entity, InternalBotGroup):
        group_data = await gocq_bot.get_group_info(group_id=entity.entity_id, no_cache=True)
        entity_name = group_data.group_name
        entity_info = group_data.group_memo
        related_entity_name = group_data.group_name
    else:
        user_data = await gocq_bot.get_stranger_info(user_id=entity.entity_id, no_cache=True)
        entity_name = user_data.nickname
        entity_info = user_data.nickname
        related_entity_name = user_data.nickname
    result_add = await entity.add_only(
        entity_name=entity_name, entity_info=entity_info, related_entity_name=related_entity_name)
    result_global_permission = await entity.enable_global_permission()
    result_permission_level = await entity.set_permission_level(level=DEFAULT_PERMISSION_LEVEL)
    return all([result_add.success, result_global_permission, result_permission_level])


@run_async_catching_exception
async def operation_enable(event: MessageEvent) -> bool:
    """执行 Enable 启用基本功能"""
    entity = get_entity_from_event(event=event)
    result = await entity.enable_global_permission()
    return result.success


@run_async_catching_exception
async def operation_disable(event: MessageEvent) -> bool:
    """执行 Disable 禁用基本功能"""
    entity = get_entity_from_event(event=event)
    result = await entity.disable_global_permission()
    return result.success


@run_async_catching_exception
async def operation_set_permission_level(event: MessageEvent, level: int) -> bool:
    """执行 SetLevel 设置权限等级"""
    entity = get_entity_from_event(event=event)
    result = await entity.set_permission_level(level=level)
    return result.success


@run_async_catching_exception
async def operation_show_permission(event: MessageEvent) -> str:
    """执行 SetLevel 设置权限等级"""
    entity = get_entity_from_event(event=event)

    global_permission = await entity.query_global_permission()
    if global_permission is None:
        global_permission_text = '未配置'
    elif global_permission.available == 1:
        global_permission_text = '已启用'
    else:
        global_permission_text = '已禁用'

    permission_level = await entity.query_permission_level()
    if permission_level is None:
        permission_level_text = '未配置'
    else:
        permission_level_text = f'Level: {permission_level.available}'

    result_text = f'功能开关:\n{global_permission_text}\n\n权限等级:\n{permission_level_text}'
    return result_text


@run_async_catching_exception
async def operation_quit_group(bot: Bot, event: MessageEvent) -> bool:
    """执行 QuitGroup 退群"""
    if not isinstance(event, GroupMessageEvent):
        return False
    group_id = event.group_id
    gocq_bot = GoCqhttpBot(bot=bot)
    group = InternalBotGroup(bot_id=bot.self_id, parent_id=bot.self_id, entity_id=str(group_id))
    quit_group_job_id = f'{QUIT_GROUP_JOB_PREFIX}{group_id}'

    async def _quit_group_job():
        """用于延迟退群的计划任务"""
        await run_async_catching_exception(gocq_bot.set_group_leave)(group_id=group_id)
        await run_async_catching_exception(group.set_rate_limiting_cooldown)(expired_time=timedelta(days=1))
        await run_async_catching_exception(group.set_global_cooldown)(expired_time=timedelta(days=1))
        await run_async_catching_exception(group.set_permission_level)(level=-1)
        await run_async_catching_exception(group.disable_global_permission)()

    quit_exec_time = datetime.now() + timedelta(seconds=QUIT_GROUP_DELAY)
    scheduler.add_job(_quit_group_job, 'date', run_date=quit_exec_time, id=quit_group_job_id, coalesce=True)
    return True


@run_async_catching_exception
async def operation_cancel_quit_group(event: MessageEvent) -> bool:
    """执行 CancelQuitGroup 取消退群"""
    if not isinstance(event, GroupMessageEvent):
        return False
    group_id = event.group_id
    quit_group_job_id = f'{QUIT_GROUP_JOB_PREFIX}{group_id}'
    scheduler.remove_job(job_id=quit_group_job_id)
    return True
