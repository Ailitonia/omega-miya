import re
import os
from nonebot.adapters import Event
from nonebot.adapters.cqhttp import Message, MessageSegment


def img_message(img_name: str) -> Message:
    img_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'img_res', img_name))
    return Message(MessageSegment.image(f'file:///{img_path}'))


sp_msg = {
    r'(.+)好萌好可爱$':
        {'group_id': [], 'replyMsg': r'我也觉得{}好萌好可爱', 'handle': True},
    r'^#测试群友(.+)浓度#?$':
        {'group_id': [], 'replyMsg': r'群友{}浓度已超出测量范围Σ(っ °Д °;)っ', 'handle': True},
    r'^对呀对呀$':
        {'group_id': [], 'replyMsg': r'对呀对呀', 'handle': False},
    r'^小母猫':
        {'group_id': [], 'replyMsg': r'喵喵喵~', 'handle': False},
    r'^优质(解答|回答)(\.jpg)?$':
        {'group_id': [], 'replyMsg': img_message('good_answer.jpg'), 'handle': False},
    r'^[Dd]{2}们都是变态吗[\?？]?$':
        {'group_id': [], 'replyMsg': r'你好，是的', 'handle': False},
}


async def sp_event_check(event: Event) -> (bool, str):
    msg = str(event.get_message())
    group_id = event.dict().get('group_id')
    for key in sp_msg.keys():
        if re.match(key, msg):
            if group_id in sp_msg.get(key).get('group_id') or not sp_msg.get(key).get('group_id'):
                handle = sp_msg.get(key).get('handle')
                if handle:
                    msg = sp_msg.get(key).get('replyMsg').format(re.findall(key, msg)[0])
                    return True, msg
                else:
                    msg = sp_msg.get(key).get('replyMsg')
                    return True, msg
    return False, ''
