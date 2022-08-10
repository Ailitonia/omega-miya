"""
@Author         : Ailitonia
@Date           : 2021/06/22 20:38
@FileName       : schedule_message.py
@Project        : nonebot2_miya
@Description    : 定时消息插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.log import logger
from nonebot.plugin import on_command, PluginMetadata
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.message import Message
from nonebot.adapters.onebot.v11.event import MessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER, PRIVATE_FRIEND
from nonebot.params import CommandArg, Arg, ArgStr

from omega_miya.service import init_processor_state

from .utils import (add_schedule_job, generate_schedule_job_data,
                    get_schedule_message_job_list, set_schedule_message_job, remove_schedule_message_job)


__plugin_meta__ = PluginMetadata(
    name="定时消息",
    description="【定时消息插件】\n"
                "设置定时消息",
    usage="/设置定时消息\n"
          "/删除定时消息\n"
          "/定时消息列表\n\n"
          "Crontab格式说明:\n"
          " * | * | * | * | *\n"
          "分|时|日|月|星期",
    extra={"author": "Ailitonia"},
)


set_schedule_message = on_command(
    'SetScheduleMessage',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='SetScheduleMessage', level=10),
    aliases={'设置定时消息', '添加定时消息'},
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND,
    priority=10,
    block=True
)


@set_schedule_message.got('job_name', prompt='请发送为当前定时消息设置的任务名称:')
@set_schedule_message.got('crontab', prompt='请发送定时任务crontab表达式:')
@set_schedule_message.got('message', prompt='请发送你要设置的定时消息:')
async def handle_set_schedule_message(
        bot: Bot, matcher: Matcher, event: MessageEvent,
        job_name: str = ArgStr('job_name'),
        crontab: str = ArgStr('crontab'),
        message: Message = Arg('message')
):
    job_name = job_name.strip()
    if len(job_name) > 50:
        await matcher.reject_arg('job_name', '设置的定时消息任务名称过长(超过50字), 请重新输入:')

    job_data = await generate_schedule_job_data(bot=bot, event=event, job_name=job_name,
                                                crontab=crontab, message=message)
    if isinstance(job_data, Exception):
        logger.error(f'SetScheduleMessage | 处理定时消息数据错误, {job_data}')
        await matcher.finish('发生了意外的错误QAQ, 请联系管理员处理')

    add_database_result = await set_schedule_message_job(bot=bot, event=event, job_data=job_data)
    if isinstance(add_database_result, Exception):
        logger.error(f'SetScheduleMessage | 将定时消息任务({job_data.job_name})写入数据库失败, {add_database_result}')
        await matcher.finish('发生了意外的错误QAQ, 请联系管理员处理')

    add_job_result = await add_schedule_job(job_data=job_data)
    if isinstance(add_job_result, Exception):
        logger.error(f'SetScheduleMessage | 添加定时消息任务({job_data.job_name})失败, {add_job_result}')
        await matcher.finish('发生了意外的错误QAQ, 请联系管理员处理')

    await matcher.finish(f'添加定时消息“{job_data.schedule_job_name}”成功!')


remove_schedule_message = on_command(
    'RemoveScheduleMessage',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='RemoveScheduleMessage', level=10),
    aliases={'删除定时消息', '移除定时消息'},
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND,
    priority=10,
    block=True
)


@remove_schedule_message.handle()
async def handle_parse_job_name(bot: Bot, event: MessageEvent, matcher: Matcher, state: T_State,
                                cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    exist_jobs = await get_schedule_message_job_list(bot=bot, event=event)
    if isinstance(exist_jobs, Exception):
        logger.error(f'RemoveScheduleMessage | 获取已有定时消息列表错误, {exist_jobs}')
        await matcher.finish('发生了意外的错误QAQ, 请联系管理员处理')
    state.update({'exist_jobs': exist_jobs})

    job_name = cmd_arg.extract_plain_text().strip()
    if job_name:
        state.update({'job_name': job_name})
    else:
        exist_text = '\n'.join(exist_jobs)
        await matcher.send(f'当前已配置定时消息任务有:\n\n{exist_text}')


@remove_schedule_message.got('job_name', prompt='请输入想要删除的定时消息任务名称:')
async def handle_remove_schedule_message(bot: Bot, event: MessageEvent, matcher: Matcher, state: T_State,
                                         job_name: str = ArgStr('job_name')):
    job_name = job_name.strip()
    exist_jobs: list[str] = state.get('exist_jobs', [])
    exist_text = '\n'.join(exist_jobs)
    if job_name not in exist_jobs:
        await matcher.reject(f'当前没有“{job_name}”定时消息任务哦, 请在已配置任务列表中选择并重新输入:\n\n{exist_text}')

    remove_database_result = await remove_schedule_message_job(bot=bot, event=event, job_name=job_name)
    if isinstance(remove_database_result, Exception):
        logger.error(f'RemoveScheduleMessage | 移除定时消息任务({remove_database_result})失败, {remove_database_result}')
        await matcher.finish('发生了意外的错误QAQ, 请联系管理员处理')

    await matcher.finish(f'移除定时消息“{job_name}”成功!')


list_schedule_message = on_command(
    'ListScheduleMessage',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='ListScheduleMessage', level=10),
    aliases={'定时消息列表', '查看定时消息'},
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND,
    priority=10,
    block=True
)


@list_schedule_message.handle()
async def handle_list_schedule_message(bot: Bot, event: MessageEvent, matcher: Matcher):
    exist_jobs = await get_schedule_message_job_list(bot=bot, event=event)
    if isinstance(exist_jobs, Exception):
        logger.error(f'ListScheduleMessage | 获取已有定时消息列表错误, {exist_jobs}')
        await matcher.finish('发生了意外的错误QAQ, 请联系管理员处理')

    exist_text = '\n'.join(exist_jobs)
    await matcher.send(f'当前已配置定时消息任务有:\n\n{exist_text}')
