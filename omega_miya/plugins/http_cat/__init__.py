"""
@Author         : Ailitonia
@Date           : 2021/05/30 16:47
@FileName       : __init__.py.py
@Project        : nonebot2_miya 
@Description    : Get http cat
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import re
from nonebot import on_command, export, logger
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent, GroupMessageEvent, PrivateMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP, PRIVATE_FRIEND
from nonebot.adapters.cqhttp.message import MessageSegment
from omega_miya.utils.Omega_plugin_utils import init_export, init_permission_state
from .data_source import get_http_cat


# Custom plugin usage text
__plugin_name__ = 'HttpCat'
__plugin_usage__ = r'''【Http Cat】
就是喵喵喵

**Permission**
Friend Private
Command & Lv.30
or AuthNode

**AuthNode**
basic

**Usage**
/HttpCat <code>'''

# 声明本插件可配置的权限节点
__plugin_auth_node__ = [
    'basic'
]

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__, __plugin_auth_node__)


# 注册事件响应器
httpcat = on_command(
    'HttpCat',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_permission_state(
        name='httpcat',
        command=True,
        level=30,
        auth_node='basic'),
    aliases={'httpcat', 'HTTPCAT'},
    permission=GROUP | PRIVATE_FRIEND,
    priority=20,
    block=True)


# 修改默认参数处理
@httpcat.args_parser
async def parse(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await httpcat.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await httpcat.finish('操作已取消')


@httpcat.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        pass
    elif args and len(args) == 1:
        state['code'] = args[0]
    else:
        await httpcat.finish('参数错误QAQ')


@httpcat.got('code', prompt='http code?')
async def handle_httpcat(bot: Bot, event: MessageEvent, state: T_State):
    code = state['code']
    if not re.match(r'^\d+$', code):
        await httpcat.finish('Http code is number!')
    res = await get_http_cat(http_code=code)
    if res.success() and res.result:
        img_seg = MessageSegment.image(res.result)
        await httpcat.finish(img_seg)
    else:
        await httpcat.finish('^QAQ^')
