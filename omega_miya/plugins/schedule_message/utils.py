"""
@Author         : Ailitonia
@Date           : 2022/05/04 18:17
@FileName       : utils.py
@Project        : nonebot2_miya 
@Description    : schedule message utils
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import ujson as json
from nonebot import get_driver
from nonebot.log import logger
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent, GroupMessageEvent
from nonebot.adapters.onebot.v11 import Message

from apscheduler.triggers.cron import CronTrigger
from omega_miya.utils.apscheduler import scheduler

from omega_miya.result import BoolResult
from omega_miya.database import InternalBotUser, InternalBotGroup, AuthSetting
from omega_miya.database.internal.entity import BaseInternalEntity
from omega_miya.utils.process_utils import run_async_catching_exception, semaphore_gather
from omega_miya.utils.message_tools import MessageSender, MessageTools


from .model import SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME, SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME, ScheduleMessageJob


def _get_event_entity(bot: Bot, event: MessageEvent) -> BaseInternalEntity:
    """根据 event 获取不同 entity 对象"""
    if isinstance(event, GroupMessageEvent):
        entity = InternalBotGroup(bot_id=bot.self_id, parent_id=bot.self_id, entity_id=str(event.group_id))
    else:
        entity = InternalBotUser(bot_id=bot.self_id, parent_id=bot.self_id, entity_id=str(event.user_id))
    return entity


@run_async_catching_exception
async def add_schedule_job(job_data: ScheduleMessageJob) -> None:
    """添加定时消息的计划任务"""
    match job_data.entity_type:
        case 'bot_group':
            entity = await InternalBotGroup.init_from_index_id(id_=job_data.entity_index_id)
        case 'bot_user':
            entity = await InternalBotUser.init_from_index_id(id_=job_data.entity_index_id)
        case _:
            raise ValueError('invalid job data')
    send_message = MessageTools.loads(message_data=job_data.message)

    async def _handle_send_message():
        """执行发送消息的内部函数"""
        try:
            msg_sender = MessageSender.init_from_bot_id(bot_id=entity.bot_id)
        except KeyError:
            logger.debug(f'ScheduleMessageJob | Bot({entity.bot_id}) not online, '
                         f'ignored schedule message job({job_data.job_name})')
            return
        await msg_sender.send_internal_entity_msg(entity=entity, message=send_message)

    trigger = CronTrigger.from_crontab(job_data.crontab)
    # 检查有没有同名计划任务
    exist_job = scheduler.get_job(job_id=job_data.job_name)
    if exist_job is None:
        scheduler.add_job(
            _handle_send_message,
            trigger=trigger,
            id=job_data.job_name,
            coalesce=True,
            misfire_grace_time=10
        )
        logger.success(f'ScheduleMessageJob | Add job({job_data.job_name}) successful')
    else:
        exist_job.reschedule(trigger=trigger)
        logger.success(f'ScheduleMessageJob | Reschedule job({job_data.job_name}) successful')


def remove_schedule_job(job_data: ScheduleMessageJob) -> None:
    """移除定时消息的计划任务"""
    scheduler.remove_job(job_id=job_data.job_name)
    logger.info(f'ScheduleMessageJob | Remove job({job_data.job_name}) successful')


@run_async_catching_exception
async def generate_schedule_job_data(
        bot: Bot,
        event: MessageEvent,
        job_name: str,
        crontab: str,
        message: Message
) -> ScheduleMessageJob:
    """生成定时消息的计划任务"""
    entity = _get_event_entity(bot=bot, event=event)
    entity_data = await entity.query()
    dumps_message = MessageTools.dumps(message=message)
    job_data = {
        'entity_index_id': entity_data.id,
        'entity_type': entity_data.relation_type,
        'schedule_job_name': job_name,
        'crontab': crontab,
        'message': dumps_message,
        'mode': 'cron'
    }
    return ScheduleMessageJob.parse_obj(job_data)


@get_driver().on_startup
@run_async_catching_exception
async def _init_schedule_message_job() -> None:
    """启动时读取并配置所有定时消息任务"""
    query_jobs_result = await AuthSetting.query_plugin_auth_nodes(module=SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME,
                                                                  plugin=SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME)
    if query_jobs_result.success:
        add_tasks = [add_schedule_job(job_data=ScheduleMessageJob.parse_obj(json.loads(x.value)))
                     for x in query_jobs_result.result if x.available == 1]
        await semaphore_gather(tasks=add_tasks, semaphore_num=10)


@run_async_catching_exception
async def get_schedule_message_job_list(bot: Bot, event: MessageEvent) -> list[str]:
    """获取数据库中 Event 对应 Entity 的全部定时任务名称"""
    entity = _get_event_entity(bot=bot, event=event)
    result = await entity.query_plugin_auth_settings(module=SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME,
                                                     plugin=SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME)
    job_list = [ScheduleMessageJob.parse_obj(json.loads(x.value)).schedule_job_name for x in result if x.available == 1]
    return job_list


@run_async_catching_exception
async def set_schedule_message_job(bot: Bot, event: MessageEvent, job_data: ScheduleMessageJob) -> BoolResult:
    """在数据库中新增或更新 Event 对应 Entity 的定时任务信息"""
    entity = _get_event_entity(bot=bot, event=event)
    add_result = await entity.set_auth_setting(
        module=SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME, plugin=SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME,
        node=job_data.schedule_job_name, available=1, value=json.dumps(job_data.dict(), ensure_ascii=False)
    )
    return add_result


@run_async_catching_exception
async def remove_schedule_message_job(bot: Bot, event: MessageEvent, job_name: str) -> BoolResult:
    """在数据库中停用 Event 对应 Entity 的定时任务信息"""
    entity = _get_event_entity(bot=bot, event=event)
    setting = await entity.query_auth_setting(module=SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME,
                                              plugin=SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME,
                                              node=job_name)
    job_data = ScheduleMessageJob.parse_obj(json.loads(setting.value))
    remove_result = await entity.set_auth_setting(
        module=SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME, plugin=SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME,
        node=job_name, available=0
    )
    remove_schedule_job(job_data=job_data)
    return remove_result


__all__ = [
    'add_schedule_job',
    'generate_schedule_job_data',
    'get_schedule_message_job_list',
    'set_schedule_message_job',
    'remove_schedule_message_job'
]
