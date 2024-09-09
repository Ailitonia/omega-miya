"""
@Author         : Ailitonia
@Date           : 2024/9/9 19:21
@FileName       : model
@Project        : omega-miya
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Literal

from pydantic import BaseModel

SCHEDULE_MUTE_CUSTOM_MODULE_NAME: Literal['OneBotV11.ScheduleMute'] = 'OneBotV11.ScheduleMute'
"""固定写入数据库的 module name 参数"""
SCHEDULE_MUTE_CUSTOM_PLUGIN_NAME: Literal['ScheduleMute'] = 'ScheduleMute'
"""固定写入数据库的 plugin name 参数"""


class ScheduleMuteJob(BaseModel):
    entity_index_id: int
    crontab: str
    enable_mute: bool
    mode: Literal['cron'] = 'cron'

    @property
    def job_name(self) -> str:
        return f'entity_index-{self.entity_index_id}_ScheduleMute_{"enable" if self.enable_mute else "disable"}'


__all__ = [
    'SCHEDULE_MUTE_CUSTOM_MODULE_NAME',
    'SCHEDULE_MUTE_CUSTOM_PLUGIN_NAME',
    'ScheduleMuteJob',
]
