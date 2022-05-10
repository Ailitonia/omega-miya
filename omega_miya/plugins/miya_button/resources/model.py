"""
@Author         : Ailitonia
@Date           : 2022/05/10 20:34
@FileName       : model.py
@Project        : nonebot2_miya 
@Description    : Button Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import random
from pydantic import BaseModel
from omega_miya.local_resource import LocalResource


VOICE_PATH: LocalResource = LocalResource('audio', 'button_voice')
"""资源路径"""


class VoiceFile(BaseModel):
    name: str
    file_name: str
    tag: str


class Voice(BaseModel):
    resource_name: str
    voices: list[VoiceFile]

    def get_random_voice(self, keyword: str | None = None) -> LocalResource:
        """根据关键词获取语音文件"""
        if keyword:
            result = [x for x in self.voices if x.name == keyword or x.tag == keyword]
        else:
            result = self.voices
        if not result:
            result = self.voices

        voice = VOICE_PATH(self.resource_name, random.choice(result).file_name)
        return voice


__all__ = [
    'VOICE_PATH',
    'VoiceFile',
    'Voice'
]
