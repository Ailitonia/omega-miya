"""
@Author         : Ailitonia
@Date           : 2021/09/24 22:03
@FileName       : __init__.py.py
@Project        : nonebot2_miya 
@Description    : 速率限制及控制工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime, timedelta
from nonebot import logger
from nonebot.plugin import on_notice, CommandGroup
from nonebot.typing import T_State
from nonebot.rule import to_me
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.message import Message
from nonebot.adapters.onebot.v11.event import MessageEvent, GroupMessageEvent, GroupBanNoticeEvent
from nonebot.params import CommandArg, ArgStr

from omega_miya.database import InternalBotUser, InternalBotGroup
from omega_miya.service import init_processor_state
from omega_miya.utils.process_utils import run_async_catching_exception
from omega_miya.utils.message_tools import MessageTools


# Custom plugin usage text
__plugin_custom_name__ = '流控限制'
__plugin_usage__ = r'''【OmegaRateLimiting 流控限制插件】
用户及群组流控限制

用法:
/Ban [用户]
/GBan [群组]'''


_log_prefix: str = '<lc>OmegaRateLimiting</lc> | '


# 注册事件响应器
RateLimiting = CommandGroup(
    'RateLimiting',
    rule=to_me(),
    state=init_processor_state(name='OmegaRateLimiting', enable_processor=False),
    permission=SUPERUSER,
    priority=10,
    block=True
)


ban_group = RateLimiting.command('ban_group', aliases={'GBan', 'gban', 'BanGroup', 'bangroup', 'set_group_ban'})
ban_user = RateLimiting.command('ban_user', aliases={'Ban', 'ban', 'BanUser', 'banuser', 'set_user_ban'})


@ban_group.handle()
async def handle_parse_group_id(event: MessageEvent, state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    cmd_args = cmd_arg.extract_plain_text().strip().split()
    arg_num = len(cmd_args)
    match arg_num:
        case 1:
            state.update({'group_id': cmd_args[0]})
        case 2:
            state.update({'group_id': cmd_args[0], 'ban_time': cmd_args[1]})
        case _:
            if isinstance(event, GroupMessageEvent):
                state.update({'group_id': str(event.group_id)})


@ban_group.got('group_id', prompt='请输入你要封禁的群号:')
@ban_group.got('ban_time', prompt='请发送需要封禁的时间, 单位秒:')
async def handle_enable_plugin(bot: Bot, group_id: str = ArgStr('group_id'), ban_time: str = ArgStr('ban_time')):
    """处理流控操作"""
    group_id = group_id.strip()
    ban_time = ban_time.strip()
    if not group_id.isdigit():
        await ban_group.reject_arg(key='group_id', prompt='群号应为数字, 请重新输入:')
    if not ban_time.isdigit():
        await ban_group.reject_arg(key='ban_time', prompt='封禁时间应为整数, 单位秒, 请重新输入:')

    group = InternalBotGroup(bot_id=bot.self_id, parent_id=bot.self_id, entity_id=group_id)
    expired_time = datetime.now() + timedelta(seconds=int(ban_time))
    ban_result = await run_async_catching_exception(group.set_rate_limiting_cooldown)(expired_time=expired_time)
    if isinstance(ban_result, Exception) or ban_result.error:
        logger.opt(colors=True).error(f'{_log_prefix}Ban Group({group_id}) failed, {ban_result}')
        await ban_group.finish(f'封禁群组 {group_id} 失败, 详情请查看日志')
    else:
        logger.opt(colors=True).success(f'{_log_prefix}Ban Group({group_id}) succeed')
        await ban_group.finish(f'已封禁群组 {group_id}, {ban_time} 秒')


@ban_user.handle()
async def handle_parse_user_id(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    cmd_args = cmd_arg.extract_plain_text().strip().split()
    arg_num = len(cmd_args)
    match arg_num:
        case 1:
            state.update({'user_id': cmd_args[0]})
        case 2:
            state.update({'user_id': cmd_args[0], 'ban_time': cmd_args[1]})
        case _:
            at_list = MessageTools(message=cmd_arg).get_all_at_qq()
            if at_list:
                state.update({'user_id': str(at_list[0])})


@ban_user.got('user_id', prompt='请输入你要封禁的用户qq:')
@ban_user.got('ban_time', prompt='请发送需要封禁的时间, 单位秒:')
async def handle_enable_plugin(bot: Bot, user_id: str = ArgStr('user_id'), ban_time: str = ArgStr('ban_time')):
    """处理流控操作"""
    user_id = user_id.strip()
    ban_time = ban_time.strip()
    if not user_id.isdigit():
        await ban_user.reject_arg(key='user_id', prompt='qq应为数字, 请重新输入:')
    if not ban_time.isdigit():
        await ban_user.reject_arg(key='ban_time', prompt='封禁时间应为整数, 单位秒, 请重新输入:')

    user = InternalBotUser(bot_id=bot.self_id, parent_id=bot.self_id, entity_id=user_id)
    expired_time = datetime.now() + timedelta(seconds=int(ban_time))
    ban_result = await run_async_catching_exception(user.set_rate_limiting_cooldown)(expired_time=expired_time)
    if isinstance(ban_result, Exception) or ban_result.error:
        logger.opt(colors=True).error(f'{_log_prefix}Ban User({user_id}) failed, {ban_result}')
        await ban_user.finish(f'封禁用户 {user_id} 失败, 详情请查看日志')
    else:
        logger.opt(colors=True).success(f'{_log_prefix}Ban User({user_id}) succeed')
        await ban_user.finish(f'已封禁用户 {user_id}, {ban_time} 秒')


rate_limiting_after_group_ban = on_notice(priority=100, rule=to_me(), block=False)


@rate_limiting_after_group_ban.handle()
async def handle_group_ban_cd(bot: Bot, event: GroupBanNoticeEvent):
    group_id = str(event.group_id)
    operator_id = event.operator_id
    duration = event.duration

    if duration == 0:
        logger.opt(colors=True).info(f'{_log_prefix}被群组/管理员: {group_id}/{operator_id} 解除禁言')
        return

    group = InternalBotGroup(bot_id=bot.self_id, parent_id=bot.self_id, entity_id=group_id)
    expired_time = datetime.now() + timedelta(seconds=duration * 24)
    ban_result = await run_async_catching_exception(group.set_rate_limiting_cooldown)(expired_time=expired_time)

    if isinstance(ban_result, Exception) or ban_result.error:
        logger.opt(colors=True).error(
            f'{_log_prefix}被群组/管理员: {group_id}/{operator_id} 禁言, 时间 {duration} 秒, 设置全局冷却失败, {ban_result}')
    else:
        logger.opt(colors=True).success(
            f'{_log_prefix}被群组/管理员: {group_id}/{operator_id} 禁言, 时间 {duration} 秒, 已设置流控冷却')
