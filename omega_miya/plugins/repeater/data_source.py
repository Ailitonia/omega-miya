"""
@Author         : Ailitonia
@Date           : 2021/06/11 22:39
@FileName       : data_source.py
@Project        : nonebot2_miya 
@Description    : Auto-Reply utils
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import os
import re
import pathlib
from dataclasses import dataclass
from typing import Dict, List, Tuple, Union
from nonebot.adapters.cqhttp.message import Message, MessageSegment

RESOURCE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'resources'))


class ResourceMsg(object):
    def __init__(self, resource_name: str):
        self.resource_name: str = resource_name

    def img_msg(self) -> MessageSegment:
        img_file_path = os.path.abspath(os.path.join(RESOURCE_PATH, self.resource_name))
        file_url = pathlib.Path(img_file_path).as_uri()
        return MessageSegment.image(file=file_url)

    def record_msg(self) -> MessageSegment:
        record_file_path = os.path.abspath(os.path.join(RESOURCE_PATH, self.resource_name))
        file_url = pathlib.Path(record_file_path).as_uri()
        return MessageSegment.record(file=file_url)


@dataclass
class Reply:
    group_id: List[int]
    handle: bool
    reply_msg: Union[str, Message, MessageSegment]


@dataclass
class ReplyRules:
    rules: Dict[str, Reply]

    def check_rule(self, group_id: int, message: str) -> Tuple[bool, Union[str, Message, MessageSegment]]:
        for regular, reply in self.rules.items():
            try:
                # 使用正则规格匹配消息
                if re.match(regular, message):
                    # 使用回复群组限制匹配是否回复群组, 空则为无限制
                    if not reply.group_id or group_id in reply.group_id:
                        # 判断回复消息是否是需要处理占位符的信息, 目前暂时只支持单组匹配及占位符填充
                        if reply.handle:
                            reply_msg = reply.reply_msg.format(re.findall(regular, message)[0])
                        else:
                            reply_msg = reply.reply_msg
                        # 按顺序匹配中立即返回, 忽略后续规则
                        return True, reply_msg
            except Exception:
                continue
        return False, ''


REPLY_RULES: ReplyRules = ReplyRules(rules={
    r'(.+)好萌好可爱$': Reply(group_id=[], handle=True, reply_msg=r'我也觉得{}好萌好可爱~'),
    r'^#测试群友(.+)浓度#?$': Reply(group_id=[], handle=True, reply_msg=r'群友{}浓度已超出测量范围Σ(っ °Д °;)っ'),
    r'^对呀对呀$': Reply(group_id=[], handle=False, reply_msg=r'对呀对呀~'),
    r'^小母猫$': Reply(group_id=[], handle=False, reply_msg=r'喵喵喵~'),
    r'^优质(解答|回答)(\.jpg)?$': Reply(group_id=[], handle=False, reply_msg=ResourceMsg('good_answer.jpg').img_msg()),
    r'^[Dd]{2}们都是变态吗[\?？]?$': Reply(group_id=[], handle=False, reply_msg=r'你好，是的')
})


__all__ = [
    'REPLY_RULES'
]
