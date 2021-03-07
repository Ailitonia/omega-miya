import re
from nonebot.adapters import Event

sp_msg = {
    r'(.+)好萌好可爱$':
        {'group_id': [], 'replyMsg': r'我也觉得{}好萌好可爱', 'handle': True},
    r'^#测试群友(.+)浓度#?$':
        {'group_id': [], 'replyMsg': r'群友{}浓度已超出测量范围Σ(っ °Д °;)っ', 'handle': True},
    r'^对呀对呀$':
        {'group_id': [], 'replyMsg': r'对呀对呀', 'handle': None},
    r'^小母猫':
        {'group_id': [], 'replyMsg': r'喵喵喵~', 'handle': None}
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
