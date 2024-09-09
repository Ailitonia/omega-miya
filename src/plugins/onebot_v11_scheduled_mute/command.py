"""
@Author         : Ailitonia
@Date           : 2024/9/9 19:55
@FileName       : command
@Project        : omega-miya
@Description    : 群定时禁言插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Annotated

from nonebot.adapters.onebot.v11 import (
    Bot as OneBotV11Bot,
    GroupMessageEvent as OneBotV11GroupMessageEvent,
)
from nonebot.log import logger
from nonebot.params import ArgStr, Depends
from nonebot.plugin import CommandGroup

from src.params.permission import IS_ADMIN
from src.service import OmegaMatcherInterface as OmMI, enable_processor_state
from .helpers import (
    add_schedule_job,
    generate_schedule_job_data,
    set_schedule_group_mute_job,
    remove_schedule_group_mute_job,
)


async def _check_bot_role(
        bot: OneBotV11Bot,
        event: OneBotV11GroupMessageEvent,
        interface: Annotated[OmMI, Depends(OmMI.depend())],
) -> None:
    try:
        bot_role = await bot.get_group_member_info(group_id=event.group_id, user_id=int(bot.self_id))
    except Exception as e:
        logger.error(f'SetScheduleMute | 添加前检查管理员身份失败, {e!r}')
        await interface.finish_reply('设置定时群禁言任务失败, 请稍后再试或联系管理员处理')

    if bot_role.get('role') not in ['owner', 'admin']:
        await interface.finish_reply('Bot非群管理员, 无法执行禁言操作')


schedule_group_mute = CommandGroup(
    'schedule-group-mute',
    permission=IS_ADMIN,
    priority=20,
    block=True,
    state=enable_processor_state(name='OneBotV11ScheduleMute', level=10),
)

set_ = schedule_group_mute.command(
    'set',
    aliases={'设置定时群禁言', '新增定时群禁言'},
    handlers=[_check_bot_role],
)


@set_.got('crontab_enable', prompt='请发送开始禁言时间的crontab表达式:')
@set_.got('crontab_disable', prompt='请发送结束禁言时间的crontab表达式:')
async def handle_set_schedule_group_mute(
        _bot: OneBotV11Bot,
        _event: OneBotV11GroupMessageEvent,
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        crontab_enable: Annotated[str, ArgStr('crontab_enable')],
        crontab_disable: Annotated[str, ArgStr('crontab_disable')],
) -> None:
    try:
        enable_job_data = await generate_schedule_job_data(
            interface=interface, crontab=crontab_enable.strip(), enable_mute=True
        )
        disable_job_data = await generate_schedule_job_data(
            interface=interface, crontab=crontab_disable.strip(), enable_mute=False
        )

        add_schedule_job(job_data=enable_job_data)
        add_schedule_job(job_data=disable_job_data)
    except Exception as e:
        logger.error(f'SetScheduleMute | 为 {interface} 添加定时群禁言任务到 schedule 失败, {e!r}')
        await interface.finish_reply('设置定时群禁言任务失败, 请稍后再试或联系管理员处理')

    try:
        await set_schedule_group_mute_job(interface=interface, job_data=enable_job_data)
        await set_schedule_group_mute_job(interface=interface, job_data=disable_job_data)
    except Exception as e:
        logger.error(f'SetScheduleMute | 将 {interface} 定时群禁言任务写入数据库失败, {e!r}')
        await interface.finish_reply('保存定时群禁言任务失败, 请稍后再试或联系管理员处理')

    await interface.entity.commit_session()
    await interface.finish_reply(f'添加定时群禁言任务成功!')


@schedule_group_mute.command(
    'remove',
    aliases={'删除定时群禁言', '移除定时群禁言'},
).handle()
async def handle_remove_schedule_group_mute(
        _bot: OneBotV11Bot,
        _event: OneBotV11GroupMessageEvent,
        interface: Annotated[OmMI, Depends(OmMI.depend())],
) -> None:
    try:
        await remove_schedule_group_mute_job(interface=interface)
    except Exception as e:
        logger.error(f'RemoveScheduleMute | 移除 {interface} 定时群禁言任务失败, {e!r}')
        await interface.finish_reply('移除定时群禁言任务失败, 可能是还尚未配置群禁言任务, 请稍后再试或联系管理员处理')

    await interface.entity.commit_session()
    await interface.finish_reply(f'移除定时群禁言任务成功!')


__all__ = []
