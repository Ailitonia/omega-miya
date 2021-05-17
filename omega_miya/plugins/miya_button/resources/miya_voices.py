import os
from .data_classes import VOICES_FOLDER, VoiceFile, Voice

__voices_folder = os.path.abspath(os.path.join(VOICES_FOLDER, 'miya_voices'))

miya_voices = Voice(
    user_name='miya',
    voices=[
        VoiceFile(name='表演绝活', file_name='0.mp3', folder_path=__voices_folder, tag='普通'),
        VoiceFile(name='iloveyou', file_name='1.mp3', folder_path=__voices_folder, tag='卖萌'),
        VoiceFile(name='你才千岁幼猫', file_name='2.mp3', folder_path=__voices_folder, tag='普通'),
        VoiceFile(name='坏蛋', file_name='3.mp3', folder_path=__voices_folder, tag='卖萌'),
        VoiceFile(name='我信了你的鬼话', file_name='4.mp3', folder_path=__voices_folder, tag='普通'),
        VoiceFile(name='来打我', file_name='5.mp3', folder_path=__voices_folder, tag='普通'),
        VoiceFile(name='说别人憨的人', file_name='6.mp3', folder_path=__voices_folder, tag='普通'),
        VoiceFile(name='欸嘿', file_name='7.mp3', folder_path=__voices_folder, tag='卖萌'),
        VoiceFile(name='nya', file_name='8.mp3', folder_path=__voices_folder, tag='怪叫'),
        VoiceFile(name='啊我输了', file_name='9.mp3', folder_path=__voices_folder, tag='普通'),
        VoiceFile(name='嗷', file_name='10.mp3', folder_path=__voices_folder, tag='怪叫'),
        VoiceFile(name='嗷嗷', file_name='11.mp3', folder_path=__voices_folder, tag='怪叫'),
        VoiceFile(name='变八嘎太', file_name='12.mp3', folder_path=__voices_folder, tag='普通'),
        VoiceFile(name='憋气', file_name='13.mp3', folder_path=__voices_folder, tag='普通'),
        VoiceFile(name='喵啊啊', file_name='14.mp3', folder_path=__voices_folder, tag='怪叫'),
        VoiceFile(name='喵啊啊啊', file_name='15.mp3', folder_path=__voices_folder, tag='怪叫'),
        VoiceFile(name='喵呜', file_name='16.mp3', folder_path=__voices_folder, tag='卖萌'),
        VoiceFile(name='那怎么可能笨蛋表', file_name='17.mp3', folder_path=__voices_folder, tag='普通'),
        VoiceFile(name='那怎么可能笨蛋里', file_name='18.mp3', folder_path=__voices_folder, tag='普通'),
        VoiceFile(name='勝負あったな', file_name='19.mp3', folder_path=__voices_folder, tag='普通'),
        VoiceFile(name='哇啊啊', file_name='20.mp3', folder_path=__voices_folder, tag='怪叫'),
        VoiceFile(name='汪', file_name='21.mp3', folder_path=__voices_folder, tag='怪叫'),
        VoiceFile(name='呀', file_name='22.mp3', folder_path=__voices_folder, tag='怪叫'),
        VoiceFile(name='miya起床', file_name='23.mp3', folder_path=__voices_folder, tag='阴阳'),
        VoiceFile(name='啊啊啊', file_name='24.mp3', folder_path=__voices_folder, tag='怪叫'),
        VoiceFile(name='嗝~啊', file_name='25.mp3', folder_path=__voices_folder, tag='怪叫'),
        VoiceFile(name='喵~~', file_name='26.mp3', folder_path=__voices_folder, tag='卖萌'),
        VoiceFile(name='喵~', file_name='27.mp3', folder_path=__voices_folder, tag='卖萌'),
        VoiceFile(name='喵~~~', file_name='28.mp3', folder_path=__voices_folder, tag='卖萌'),
        VoiceFile(name='喵喵喵喵喵喵喵喵喵', file_name='29.mp3', folder_path=__voices_folder, tag='卖萌'),
        VoiceFile(name='嗯小哥哥人家不要了', file_name='30.mp3', folder_path=__voices_folder, tag='卖萌'),
        VoiceFile(name='嗯~', file_name='31.mp3', folder_path=__voices_folder, tag='卖萌'),
        VoiceFile(name='你花呗还没还', file_name='32.mp3', folder_path=__voices_folder, tag='阴阳'),
        VoiceFile(name='你快点啊我等的花儿都谢了', file_name='33.mp3', folder_path=__voices_folder, tag='阴阳'),
        VoiceFile(name='起床了大笨蛋', file_name='34.mp3', folder_path=__voices_folder, tag='阴阳'),
        VoiceFile(name='起来了dd', file_name='35.mp3', folder_path=__voices_folder, tag='阴阳'),
        VoiceFile(name='作业写了吗', file_name='36.mp3', folder_path=__voices_folder, tag='阴阳'),
        VoiceFile(name='异世相遇尽享美味', file_name='37.mp3', folder_path=__voices_folder, tag='卖萌')
    ]
)


__all__ = [
    'miya_voices'
]
