"""
@Author         : Ailitonia
@Date           : 2024/9/9 19:20
@FileName       : helpers
@Project        : omega-miya
@Description    : 群定时禁言工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import TYPE_CHECKING

from apscheduler.triggers.cron import CronTrigger
from nonebot import get_driver
from nonebot.log import logger

from src.compat import parse_json_as
from src.database import AuthSettingDAL, begin_db_session
from src.service import OmegaEntity, scheduler
from src.service import OmegaEntityInterface as OmEI
from .model import SCHEDULE_MUTE_CUSTOM_MODULE_NAME, SCHEDULE_MUTE_CUSTOM_PLUGIN_NAME, ScheduleMuteJob

if TYPE_CHECKING:
    from nonebot.adapters.onebot.v11 import Bot as OneBotV11Bot

    from src.service import OmegaMatcherInterface


def add_schedule_job(job_data: ScheduleMuteJob) -> None:
    """添加执行群禁言的计划任务"""

    async def _handle_group_mute():
        """执行群禁言的内部函数"""
        try:
            async with begin_db_session() as session:
                entity = await OmegaEntity.init_from_entity_index_id(session=session, index_id=job_data.entity_index_id)
                bot: OneBotV11Bot = await OmEI(entity=entity).get_bot()  # type: ignore
                await bot.set_group_whole_ban(group_id=int(entity.entity_id), enable=job_data.enable_mute)
        except Exception as e:
            logger.error(f'ScheduleMuteJob | Handling group mute job({job_data.job_name}) failed, {e!r}')

    trigger = CronTrigger.from_crontab(job_data.crontab)
    # 检查有没有同名计划任务
    exist_job = scheduler.get_job(job_id=job_data.job_name)
    if exist_job is None:
        scheduler.add_job(
            _handle_group_mute,
            trigger=trigger,
            id=job_data.job_name,
            coalesce=True,
            misfire_grace_time=10
        )
        logger.success(f'ScheduleMuteJob | Add group mute job({job_data.job_name}) successful')
    else:
        exist_job.reschedule(trigger=trigger)
        logger.success(f'ScheduleMuteJob | Reschedule group mute job({job_data.job_name}) successful')


def remove_schedule_job(job_data: ScheduleMuteJob) -> None:
    """移除群禁言的计划任务"""
    scheduler.remove_job(job_id=job_data.job_name)
    logger.success(f'ScheduleMuteJob | Remove group mute job({job_data.job_name}) successful')


@get_driver().on_startup
async def _init_schedule_group_mute_job() -> None:
    """启动时读取并配置所有定时群禁言任务"""
    async with begin_db_session() as session:
        all_jobs = await AuthSettingDAL(session=session).query_module_plugin_all(
            module=SCHEDULE_MUTE_CUSTOM_MODULE_NAME, plugin=SCHEDULE_MUTE_CUSTOM_PLUGIN_NAME
        )
        for job in all_jobs:
            if job.available == 1 and job.value is not None:
                try:
                    add_schedule_job(job_data=parse_json_as(ScheduleMuteJob, job.value))
                except Exception as e:
                    logger.error(f'ScheduleMuteJob | Add group mute job({job}) failed when init in startup, {e!r}')


async def generate_schedule_job_data(
        interface: 'OmegaMatcherInterface',
        crontab: str,
        enable_mute: bool,
) -> ScheduleMuteJob:
    """生成定时群禁言的计划任务"""
    entity_data = await interface.entity.query_entity_self()
    job_data = {
        'entity_index_id': entity_data.id,
        'crontab': crontab,
        'enable_mute': enable_mute,
        'mode': 'cron',
    }
    return ScheduleMuteJob.model_validate(job_data)


async def set_schedule_group_mute_job(interface: 'OmegaMatcherInterface', job_data: ScheduleMuteJob) -> None:
    """在数据库中新增或更新 Event 对应 Entity 的定时任务信息"""
    await interface.entity.set_auth_setting(
        module=SCHEDULE_MUTE_CUSTOM_MODULE_NAME,
        plugin=SCHEDULE_MUTE_CUSTOM_PLUGIN_NAME,
        node='enable' if job_data.enable_mute else 'disable',
        available=1,
        value=job_data.model_dump_json()
    )


async def remove_schedule_group_mute_job(interface: 'OmegaMatcherInterface') -> None:
    """在数据库中停用 Event 对应 Entity 的定时任务信息"""
    jobs_setting = await interface.entity.query_plugin_all_auth_setting(
        module=SCHEDULE_MUTE_CUSTOM_MODULE_NAME,
        plugin=SCHEDULE_MUTE_CUSTOM_PLUGIN_NAME,
    )
    if not jobs_setting:
        raise ValueError(f'{interface.entity} group mute job not confined')

    for job_setting in jobs_setting:
        if job_setting.value is None:
            raise ValueError(f'{interface.entity} group mute job({job_setting.node}) not confined')

        job_data = parse_json_as(ScheduleMuteJob, job_setting.value)

        await interface.entity.set_auth_setting(
            module=SCHEDULE_MUTE_CUSTOM_MODULE_NAME,
            plugin=SCHEDULE_MUTE_CUSTOM_PLUGIN_NAME,
            node=job_setting.node,
            available=0
        )
        remove_schedule_job(job_data=job_data)


__all__ = [
    'add_schedule_job',
    'generate_schedule_job_data',
    'set_schedule_group_mute_job',
    'remove_schedule_group_mute_job',
]
