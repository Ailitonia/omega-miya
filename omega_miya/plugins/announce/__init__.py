import re
from nonebot import on_command, logger
from nonebot.rule import to_me
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import Event
from omega_miya.utils.Omega_Base import DBTable


# 注册事件响应器
announce = on_command('公告', rule=to_me(), aliases={'announce'}, permission=SUPERUSER, priority=1, block=True)


# 修改默认参数处理
@announce.args_parser
async def parse(bot: Bot, event: Event, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await announce.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await announce.finish('操作已取消')


@announce.handle()
async def handle_first_receive(bot: Bot, event: Event, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        pass
    elif args and len(args) == 1:
        state['group'] = args[0]
    elif args and len(args) == 2:
        state['group'] = args[0]
        state['announce_text'] = args[1]
    else:
        await announce.finish('参数错误QAQ')


@announce.got('group', prompt='请输入通知群组:')
@announce.got('announce_text', prompt='请输入公告内容:')
async def handle_announce(bot: Bot, event: Event, state: T_State):
    group = state['group']
    msg = state['announce_text']
    if group == 'all':
        t = DBTable(table_name='Group')
        group_res = await t.list_col(col_name='group_id')
        for group_id in group_res.result:
            await bot.call_api(api='send_group_msg', group_id=group_id, message=msg)
    elif group == 'notice':
        t = DBTable(table_name='Group')
        group_res = await t.list_col_with_condition('group_id', 'notice_permissions', 1)
        for group_id in group_res.result:
            await bot.call_api(api='send_group_msg', group_id=group_id, message=msg)
    elif group == 'command':
        t = DBTable(table_name='Group')
        group_res = await t.list_col_with_condition('group_id', 'command_permissions', 1)
        for group_id in group_res.result:
            await bot.call_api(api='send_group_msg', group_id=group_id, message=msg)
    elif re.match(r'^\d+$', group):
        group_id = int(group)
        await bot.call_api(api='send_group_msg', group_id=group_id, message=msg)
    else:
        logger.warning(f'公告未发送, 不合规的群组类型或群号: {group}')
        await announce.finish('不合规的群组类型或群号')
    logger.warning(f'公告已成功发送群组: {group}')
    await announce.finish('公告发送完成')
