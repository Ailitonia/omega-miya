import os
import random
from dataclasses import dataclass
from typing import Optional, List
from nonebot import get_driver


__global_config = get_driver().config
RESOURCES_PATH = __global_config.resources_path_
VOICES_FOLDER = os.path.abspath(os.path.join(RESOURCES_PATH, 'audio', 'buttom_voices'))


@dataclass
class VoiceFile:
    name: str
    file_name: str
    folder_path: str
    tag: str


@dataclass
class Voice:
    user_name: str
    voices: List[VoiceFile]

    def get_voice(self, keyword: str) -> Optional[str]:
        if keyword:
            result = [x for x in self.voices if x.name == keyword]
            if not result:
                result = [x for x in self.voices if x.tag == keyword]
        else:
            result = self.voices
        if not result:
            return None

        voice = random.choice(result)
        return os.path.abspath(os.path.join(voice.folder_path, voice.file_name))


__all__ = [
    'VOICES_FOLDER',
    'VoiceFile',
    'Voice'
]
