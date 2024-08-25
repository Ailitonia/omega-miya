"""
@Author         : Ailitonia
@Date           : 2022/05/04 18:17
@FileName       : utils.py
@Project        : nonebot2_miya 
@Description    : 定时消息工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING

import ujson as json
from apscheduler.triggers.cron import CronTrigger
from nonebot import get_driver
from nonebot.log import logger

from src.database import AuthSettingDAL, begin_db_session
from src.service import (
    OmegaEntityInterface as OmEI,
    OmegaEntity,
    OmegaMessage,
    scheduler
)
from .model import SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME, SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME, ScheduleMessageJob

if TYPE_CHECKING:
    from src.service import OmegaMatcherInterface


def add_schedule_job(job_data: ScheduleMessageJob) -> None:
    """添加发送定时消息的计划任务"""
    send_message = OmegaMessage.loads(message_data=job_data.message)

    async def _handle_send_message():
        """执行发送消息的内部函数"""
        try:
            async with begin_db_session() as session:
                entity = await OmegaEntity.init_from_entity_index_id(session=session, index_id=job_data.entity_index_id)
                await OmEI(entity=entity).send_entity_message(message=send_message)
        except Exception as e:
            logger.error(f'ScheduleMessageJob | Sending schedule message job({job_data.job_name}) failed, {e!r}')

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
    logger.success(f'ScheduleMessageJob | Remove job({job_data.job_name}) successful')


@get_driver().on_startup
async def _init_schedule_message_job() -> None:
    """启动时读取并配置所有定时消息任务"""
    async with begin_db_session() as session:
        all_jobs = await AuthSettingDAL(session=session).query_module_plugin_all(
            module=SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME, plugin=SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME
        )
        for job in all_jobs:
            if job.available == 1 and job.value is not None:
                try:
                    add_schedule_job(job_data=ScheduleMessageJob.model_validate(json.loads(job.value)))
                except Exception as e:
                    logger.error(f'ScheduleMessageJob | Add job({job}) failed when init in startup, {e!r}')


async def generate_schedule_job_data(
        interface: "OmegaMatcherInterface",
        job_name: str,
        crontab: str,
        message: OmegaMessage
) -> ScheduleMessageJob:
    """生成定时消息的计划任务"""
    entity_data = await interface.entity.query_entity_self()
    job_data = {
        'entity_index_id': entity_data.id,
        'schedule_job_name': job_name,
        'crontab': crontab,
        'message': message.dumps(),
        'mode': 'cron'
    }
    return ScheduleMessageJob.model_validate(job_data)


async def get_schedule_message_job_list(interface: "OmegaMatcherInterface") -> list[str]:
    """获取数据库中 Event 对应 Entity 的全部定时任务名称"""
    all_jobs = await interface.entity.query_plugin_all_auth_setting(
        module=SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME, plugin=SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME
    )
    job_list = [
        ScheduleMessageJob.model_validate(json.loads(x.value)).schedule_job_name
        for x in all_jobs
        if (x.available == 1 and x.value is not None)
    ]
    return job_list


async def set_schedule_message_job(interface: "OmegaMatcherInterface", job_data: ScheduleMessageJob) -> None:
    """在数据库中新增或更新 Event 对应 Entity 的定时任务信息"""
    await interface.entity.set_auth_setting(
        module=SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME,
        plugin=SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME,
        node=job_data.schedule_job_name,
        available=1,
        value=json.dumps(job_data.model_dump(), ensure_ascii=False)
    )


async def remove_schedule_message_job(interface: "OmegaMatcherInterface", job_name: str) -> None:
    """在数据库中停用 Event 对应 Entity 的定时任务信息"""
    job_setting = await interface.entity.query_auth_setting(
        module=SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME,
        plugin=SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME,
        node=job_name
    )
    if job_setting.value is None:
        raise ValueError(f'{interface.entity} job({job_name}) not confined')

    job_data = ScheduleMessageJob.model_validate(json.loads(job_setting.value))

    await interface.entity.set_auth_setting(
        module=SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME,
        plugin=SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME,
        node=job_name,
        available=0
    )
    remove_schedule_job(job_data=job_data)


__all__ = [
    'add_schedule_job',
    'generate_schedule_job_data',
    'get_schedule_message_job_list',
    'set_schedule_message_job',
    'remove_schedule_message_job',
]
