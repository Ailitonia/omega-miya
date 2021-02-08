import os
import random


class Voice(object):
    def __init__(self):
        self.VoicesFiles = None

    def get_voice_filepath(self, voice: str) -> str:
        plugin_path = os.path.dirname(os.path.abspath(__file__))
        if voice in self.VoicesFiles.keys():
            return os.path.join(plugin_path, 'voices', self.VoicesFiles[voice]['file'])
        else:
            voice_list = []
            for name, content in self.VoicesFiles.items():
                if voice == content['tag']:
                    voice_list.append(content['file'])
            if not voice_list:
                return ''
            else:
                return os.path.join(plugin_path, 'voices', random.choice(voice_list))


class MiyaVoice(Voice):
    def __init__(self):
        """
        硬编码音频素材文件
        先暂时这样以后有空再改
        """
        super().__init__()
        self.VoicesFiles = {
            '表演绝活': {
                'file': '0.mp3',
                'tag': ''
            },
            '你才千岁幼猫': {
                'file': '2.mp3',
                'tag': ''
            },
            '坏蛋': {
                'file': '3.mp3',
                'tag': ''
            },
            '我信了你的鬼话': {
                'file': '4.mp3',
                'tag': ''
            },
            '来打我': {
                'file': '5.mp3',
                'tag': ''
            },
            '说别人憨的人': {
                'file': '6.mp3',
                'tag': ''
            }
        }
