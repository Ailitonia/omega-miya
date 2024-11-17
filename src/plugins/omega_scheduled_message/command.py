"""
@Author         : Ailitonia
@Date           : 2021/06/22 20:38
@FileName       : schedule_message.py
@Project        : nonebot2_miya
@Description    : 定时消息插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Annotated

from nonebot.adapters import Message
from nonebot.log import logger
from nonebot.params import Arg, ArgStr, Depends
from nonebot.plugin import CommandGroup

from src.params.handler import get_command_message_arg_parser_handler
from src.params.permission import IS_ADMIN
from src.service import OmegaMatcherInterface as OmMI
from src.service import OmegaMessageTransfer, enable_processor_state
from .helpers import (
    add_schedule_job,
    generate_schedule_job_data,
    get_schedule_message_job_list,
    remove_schedule_message_job,
    set_schedule_message_job,
)

schedule_message = CommandGroup(
    'schedule-message',
    permission=IS_ADMIN,
    priority=20,
    block=True,
    state=enable_processor_state(name='OmegaScheduleMessage', level=10),
)


set_ = schedule_message.command(
    'set',
    aliases={'设置定时消息', '新增定时消息'},
    handlers=[get_command_message_arg_parser_handler('job_name')]
)


@set_.got('job_name', prompt='请发送为当前定时消息设置的任务名称:')
@set_.got('crontab', prompt='请发送定时任务crontab表达式:')
@set_.got('message', prompt='请发送你要设置的定时消息:')
async def handle_set_schedule_message(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        job_name: Annotated[str, ArgStr('job_name')],
        crontab: Annotated[str, ArgStr('crontab')],
        message: Annotated[Message, Arg('message')],
) -> None:
    job_name = job_name.strip()
    if len(job_name) > 50:
        await interface.reject_arg_reply('job_name', '设置的定时消息任务名称过长(超过50字), 请重新输入:')

    try:
        parsed_message = await OmegaMessageTransfer(interface=interface, origin_message=message).dumps()
        job_data = await generate_schedule_job_data(
            interface=interface, job_name=job_name, crontab=crontab, message=parsed_message
        )
    except Exception as e:
        logger.error(f'SetScheduleMessage | 处理定时消息数据错误, {e!r}')
        await interface.finish_reply('处理定时消息数据错误, 请稍后再试或联系管理员处理')

    try:
        add_schedule_job(job_data=job_data)
    except Exception as e:
        logger.error(f'SetScheduleMessage | 添加定时消息任务({job_data.job_name})到 schedule 失败, {e!r}')
        await interface.finish_reply('设置消息定时任务失败, 请稍后再试或联系管理员处理')

    try:
        await set_schedule_message_job(interface=interface, job_data=job_data)
    except Exception as e:
        logger.error(f'SetScheduleMessage | 将定时消息任务({job_data.job_name})写入数据库失败, {e!r}')
        await interface.finish_reply('保存定时消息失败, 请稍后再试或联系管理员处理')

    await interface.entity.commit_session()
    await interface.finish_reply(f'添加定时消息"{job_data.schedule_job_name}"成功!')


@schedule_message.command(
    'remove', aliases={'删除定时消息', '移除定时消息'}, handlers=[get_command_message_arg_parser_handler('job_name')]
).got('job_name', prompt='请输入想要删除的定时消息任务名称:')
async def handle_remove_schedule_message(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        job_name: Annotated[str, ArgStr('job_name')]
) -> None:
    job_name = job_name.strip()

    try:
        exist_jobs = await get_schedule_message_job_list(interface=interface)
    except Exception as e:
        logger.error(f'RemoveScheduleMessage | 获取{interface.entity}已配置任务列表失败, {e!r}')
        await interface.finish_reply('获取已配置任务列表失败, 请稍后再试或联系管理员处理')

    if job_name not in exist_jobs:
        exist_text = '\n'.join(exist_jobs) if exist_jobs else '无已配置的定时消息'
        await interface.finish_reply(f'没有名为"{job_name}"定时消息任务, 请确认已配置的定时消息:\n\n{exist_text}')

    try:
        await remove_schedule_message_job(interface=interface, job_name=job_name)
    except Exception as e:
        logger.error(f'RemoveScheduleMessage | 移除定时消息任务({job_name})失败, {e!r}')
        await interface.finish_reply('移除定时消息任务失败, 请稍后再试或联系管理员处理')

    await interface.entity.commit_session()
    await interface.finish_reply(f'移除定时消息"{job_name}"成功!')


@schedule_message.command('list', aliases={'定时消息列表', '查看定时消息'}).handle()
async def handle_list_schedule_message(interface: Annotated[OmMI, Depends(OmMI.depend())]) -> None:
    try:
        exist_jobs = await get_schedule_message_job_list(interface=interface)
    except Exception as e:
        logger.error(f'ListScheduleMessage | 获取{interface.entity}已配置任务列表失败, {e!r}')
        await interface.finish_reply('获取已配置任务列表失败, 请稍后再试或联系管理员处理')

    exist_text = '\n'.join(exist_jobs) if exist_jobs else '无已配置的定时消息'
    await interface.finish_reply(f'当前已配置定时消息任务有:\n\n{exist_text}')


__all__ = []
