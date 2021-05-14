import os
import random
from dataclasses import dataclass
from typing import Optional, List


VOICES_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), 'voices'))


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
        result = [x for x in self.voices if x.name == keyword]
        if not result:
            result = [x for x in self.voices if x.tag == keyword]
        if not result:
            return None

        voice = random.choice(result)
        return os.path.abspath(os.path.join(voice.folder_path, voice.file_name))


__all__ = [
    'VOICES_FOLDER',
    'VoiceFile',
    'Voice'
]
