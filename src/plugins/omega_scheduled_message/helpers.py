"""
@Author         : Ailitonia
@Date           : 2022/05/04 18:17
@FileName       : utils.py
@Project        : nonebot2_miya
@Description    : 定时消息工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""
from typing import Literal

from apscheduler.triggers.cron import CronTrigger
from nonebot import get_driver
from nonebot.log import logger
from nonebot_plugin_alconna.uniseg import UniMessage
from pydantic import BaseModel, Json, JsonValue

from src.database import EntityDAL
from src.resource import TemporaryResource
from src.service import OmegaEntityInterface, OmegaMatcherInterface, scheduler
from src.service.omega_base.internal import EntityInitParams

_SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME: Literal['OmegaScheduleMessage'] = 'OmegaScheduleMessage'
"""固定写入数据库的 module name 参数"""
_SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME: Literal['OmegaScheduleMessageJob'] = 'OmegaScheduleMessageJob'
"""固定写入数据库的 plugin name 参数"""
_SAVE_MEDIA_FOLDER_NAME: Literal['omega_scheduled_message_save_media'] = 'omega_scheduled_message_save_media'
"""暂存消息媒体的目录名"""
_SAVE_MEDIA_FOLDER: TemporaryResource = TemporaryResource(_SAVE_MEDIA_FOLDER_NAME)
"""暂存消息媒体的目录"""


class ScheduleMessageJob(BaseModel):
    schedule_job_name: str
    crontab: str
    mode: Literal['cron'] = 'cron'
    entity_init_params: EntityInitParams
    message: Json[list[dict[str, JsonValue]]]

    @property
    def job_unique_id(self) -> str:
        return (
            f'{self.entity_init_params.bot_id}'
            f'_{self.entity_init_params.entity_type}'
            f'_{self.entity_init_params.entity_id}'
            f'_{self.schedule_job_name}'
        )

def add_schedule_job(job_data: ScheduleMessageJob) -> None:
    """添加发送定时消息的计划任务"""
    send_message = UniMessage.load(data=job_data.message)

    async def _handle_send_message():
        """计划任务执行发送消息的内部函数"""
        try:
            await OmegaEntityInterface(job_data.entity_init_params).send_entity_message(message=send_message)
        except Exception as e:
            logger.error(f'ScheduleMessageJob | Job({job_data.job_unique_id}) send message failed, {e}')

    # 根据 crontab 字符串构造调度器
    trigger = CronTrigger.from_crontab(job_data.crontab)

    # 检查有没有同名计划任务
    exist_job = scheduler.get_job(job_id=job_data.job_unique_id)
    if exist_job is None:
        scheduler.add_job(
            _handle_send_message,
            trigger=trigger,
            id=job_data.job_unique_id,
            coalesce=True,
            misfire_grace_time=10
        )
        logger.success(f'ScheduleMessageJob | Add job({job_data.job_unique_id}) succeed')
    else:
        exist_job.reschedule(trigger=trigger)
        logger.success(f'ScheduleMessageJob | Reschedule job({job_data.job_unique_id}) succeed')


def remove_schedule_job(job_data: ScheduleMessageJob) -> None:
    """移除定时消息的计划任务"""
    scheduler.remove_job(job_id=job_data.job_unique_id)
    logger.success(f'ScheduleMessageJob | Remove job({job_data.job_unique_id}) succeed')


@get_driver().on_startup
async def _init_schedule_message_job() -> None:
    """启动时读取并配置所有定时消息任务"""
    async with EntityDAL.create() as dal:
        job_settings = await dal.query_module_plugin_any_auth_settings(
            module=_SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME,
            plugin=_SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME,
        )
        for job in job_settings:
            if job.available == 1 and job.value is not None:
                try:
                    add_schedule_job(job_data=ScheduleMessageJob.model_validate(job.value))
                except Exception as e:
                    logger.error(f'ScheduleMessageJob | Add job({job}) failed when init in startup, {e}')


async def generate_schedule_job_data(
        interface: OmegaMatcherInterface,
        schedule_job_name: str,
        crontab: str,
        message: UniMessage,
) -> ScheduleMessageJob:
    """生成定时消息的计划任务"""
    return ScheduleMessageJob.model_validate({
        'schedule_job_name': schedule_job_name,
        'crontab': crontab,
        'mode': 'cron',
        'entity_init_params': interface.extract_current_entity_params(),
        'message': message.dump(media_save_dir=_SAVE_MEDIA_FOLDER(schedule_job_name).path),
    })


async def get_schedule_message_job_list(interface: OmegaMatcherInterface) -> list[str]:
    """获取数据库中 Event 对应 Entity 的全部定时任务名称"""
    async with interface.create_current_entity_session() as entity:
        job_settings = await entity.query_plugin_all_auth_setting(
            module=_SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME,
            plugin=_SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME,
        )
    job_list = [
        ScheduleMessageJob.model_validate(x.value).schedule_job_name
        for x in job_settings
        if (x.available == 1 and x.value is not None)
    ]
    return job_list


async def set_schedule_message_job(interface: OmegaMatcherInterface, job_data: ScheduleMessageJob) -> None:
    """在数据库中新增或更新 Event 对应 Entity 的定时任务信息"""
    async with interface.create_current_entity_session() as entity:
        await entity.set_auth_setting(
            module=_SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME,
            plugin=_SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME,
            node=job_data.schedule_job_name,
            available=1,
            value=job_data.model_dump(mode='json'),
        )


async def remove_schedule_message_job(interface: OmegaMatcherInterface, schedule_job_name: str) -> None:
    """在数据库中停用 Event 对应 Entity 的定时任务信息"""
    async with interface.create_current_entity_session() as entity:
        job_setting = await entity.query_auth_setting(
            module=_SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME,
            plugin=_SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME,
            node=schedule_job_name,
        )
        if job_setting.available != 1:
            logger.info(f'ScheduleMessageJob | Job({schedule_job_name}) not available, ignore')
            return

        job_data = ScheduleMessageJob.model_validate(job_setting.value)
        remove_schedule_job(job_data=job_data)

        await entity.set_auth_setting(
            module=_SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME,
            plugin=_SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME,
            node=schedule_job_name,
            available=0,
            value={},
        )


__all__ = [
    'add_schedule_job',
    'generate_schedule_job_data',
    'get_schedule_message_job_list',
    'set_schedule_message_job',
    'remove_schedule_message_job',
]
