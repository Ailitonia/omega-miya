"""
@Author         : Ailitonia
@Date           : 2022/05/04 18:17
@FileName       : model.py
@Project        : nonebot2_miya 
@Description    : schedule message model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal

from pydantic import BaseModel

SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME: Literal['Omega.ScheduleMessage'] = 'Omega.ScheduleMessage'
"""固定写入数据库的 module name 参数"""
SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME: Literal['ScheduleMessage'] = 'ScheduleMessage'
"""固定写入数据库的 plugin name 参数"""


class ScheduleMessageJob(BaseModel):
    entity_index_id: int
    schedule_job_name: str
    crontab: str
    message: str
    mode: Literal['cron'] = 'cron'

    @property
    def job_name(self) -> str:
        return f'entity_index-{self.entity_index_id}_{self.schedule_job_name}'


__all__ = [
    'SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME',
    'SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME',
    'ScheduleMessageJob',
]
