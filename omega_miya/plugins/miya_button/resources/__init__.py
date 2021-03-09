import os
import random


class Voice(object):
    def __init__(self):
        self.VoicesFiles = dict()

    def get_voice_filepath(self, voice: str) -> str:
        plugin_path = os.path.dirname(os.path.abspath(__file__))
        if voice in self.VoicesFiles.keys():
            return os.path.join(plugin_path, 'voices', self.VoicesFiles[voice]['file'])
        elif voice:
            voice_list = []
            for name, content in self.VoicesFiles.items():
                if voice == content['tag']:
                    voice_list.append(content['file'])
            if not voice_list:
                return ''
            else:
                return os.path.join(plugin_path, 'voices', random.choice(voice_list))
        else:
            voice_list = []
            for name, content in self.VoicesFiles.items():
                voice_list.append(content['file'])
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
                'tag': '普通'
            },
            'iloveyou': {
                'file': '1.mp3',
                'tag': '卖萌'
            },
            '你才千岁幼猫': {
                'file': '2.mp3',
                'tag': '普通'
            },
            '坏蛋': {
                'file': '3.mp3',
                'tag': '卖萌'
            },
            '我信了你的鬼话': {
                'file': '4.mp3',
                'tag': '普通'
            },
            '来打我': {
                'file': '5.mp3',
                'tag': '普通'
            },
            '说别人憨的人': {
                'file': '6.mp3',
                'tag': '普通'
            },
            '欸嘿': {
                'file': '7.mp3',
                'tag': '卖萌'
            },
            'nya': {
                'file': '8.mp3',
                'tag': '怪叫'
            },
            '啊我输了': {
                'file': '9.mp3',
                'tag': '普通'
            },
            '嗷': {
                'file': '10.mp3',
                'tag': '怪叫'
            },
            '嗷嗷': {
                'file': '11.mp3',
                'tag': '怪叫'
            },
            '变八嘎太': {
                'file': '12.mp3',
                'tag': '普通'
            },
            '憋气': {
                'file': '13.mp3',
                'tag': '普通'
            },
            '喵啊啊': {
                'file': '14.mp3',
                'tag': '怪叫'
            },
            '喵啊啊啊': {
                'file': '15.mp3',
                'tag': '怪叫'
            },
            '喵呜': {
                'file': '16.mp3',
                'tag': '卖萌'
            },
            '那怎么可能笨蛋表': {
                'file': '17.mp3',
                'tag': '普通'
            },
            '那怎么可能笨蛋里': {
                'file': '18.mp3',
                'tag': '普通'
            },
            '勝負あったな': {
                'file': '19.mp3',
                'tag': '普通'
            },
            '哇啊啊': {
                'file': '20.mp3',
                'tag': '怪叫'
            },
            '汪': {
                'file': '21.mp3',
                'tag': '怪叫'
            },
            '呀': {
                'file': '22.mp3',
                'tag': '怪叫'
            },
            'miya起床': {
                'file': '23.mp3',
                'tag': '阴阳'
            },
            '啊啊啊': {
                'file': '24.mp3',
                'tag': '怪叫'
            },
            '嗝~啊': {
                'file': '25.mp3',
                'tag': '怪叫'
            },
            '喵~~': {
                'file': '26.mp3',
                'tag': '卖萌'
            },
            '喵~': {
                'file': '27.mp3',
                'tag': '卖萌'
            },
            '喵~~~': {
                'file': '28.mp3',
                'tag': '卖萌'
            },
            '喵喵喵喵喵喵喵喵喵': {
                'file': '29.mp3',
                'tag': '卖萌'
            },
            '嗯小哥哥人家不要了': {
                'file': '30.mp3',
                'tag': '卖萌'
            },
            '嗯~': {
                'file': '31.mp3',
                'tag': '卖萌'
            },
            '你花呗还没还': {
                'file': '32.mp3',
                'tag': '阴阳'
            },
            '你快点啊我等的花儿都谢了': {
                'file': '33.mp3',
                'tag': '阴阳'
            },
            '起床了大笨蛋': {
                'file': '34.mp3',
                'tag': '阴阳'
            },
            '起来了dd': {
                'file': '35.mp3',
                'tag': '阴阳'
            },
            '作业写了吗': {
                'file': '36.mp3',
                'tag': '阴阳'
            },
            '异世相遇尽享美味': {
                'file': '37.mp3',
                'tag': '卖萌'
            }
        }


if __name__ == '__main__':
    for key, item in MiyaVoice().VoicesFiles.items():
        print(key, '//', item.get('tag'))
