import re
import operator
from nonebot.adapters import Event

sp_msg = {
    r'.+好萌好可爱$':
        {'group_id': [], 'replyMsg': '', 'handle': operator.add, 're': r'我也觉得', 'seq': 'prefix'},
    r'^对呀对呀$':
        {'group_id': [123456789], 'replyMsg': '对呀对呀', 'handle': None, 're': None, 'seq': None}
}


async def sp_event_check(event: Event) -> (bool, str):
    msg = str(event.get_message())
    group_id = event.dict().get('group_id')
    for key in sp_msg.keys():
        if re.match(key, msg):
            if group_id in sp_msg.get(key).get('group_id') or not sp_msg.get(key).get('group_id'):
                handle = sp_msg.get(key).get('handle')
                if not handle:
                    msg = sp_msg.get(key).get('replyMsg')
                    return True, msg
                else:
                    if sp_msg.get(key).get('seq') == 'prefix':
                        r = sp_msg.get(key).get('re')
                        msg = handle(r, msg)
                        return True, msg
                    elif sp_msg.get(key).get('seq') == 'suffix':
                        r = sp_msg.get(key).get('re')
                        msg = handle(msg, r)
                        return True, msg
    return False, ''
