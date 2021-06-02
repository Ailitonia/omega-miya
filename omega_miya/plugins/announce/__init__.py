import re
from nonebot import on_command, logger
from nonebot.rule import to_me
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import PrivateMessageEvent
from omega_miya.utils.Omega_Base import DBBot, DBBotGroup


# 注册事件响应器
announce = on_command('公告', rule=to_me(), aliases={'announce'}, permission=SUPERUSER, priority=10, block=True)


# 修改默认参数处理
@announce.args_parser
async def parse(bot: Bot, event: PrivateMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip()
    if not args:
        await announce.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args
    if state[state["_current_key"]] == '取消':
        await announce.finish('操作已取消')


@announce.handle()
async def handle_first_receive(bot: Bot, event: PrivateMessageEvent, state: T_State):
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


@announce.got('group', prompt='请输入通知群组:\n【all/notice/command/group_id】')
@announce.got('announce_text', prompt='请输入公告内容:')
async def handle_announce(bot: Bot, event: PrivateMessageEvent, state: T_State):
    group = state['group']
    msg = state['announce_text']
    self_bot = DBBot(self_qq=int(bot.self_id))
    if group == 'all':
        group_res = await DBBotGroup.list_exist_bot_groups(self_bot=self_bot)
        for group_id in group_res.result:
            try:
                await bot.send_group_msg(group_id=group_id, message=msg)
            except Exception as e:
                logger.warning(f'向群组发送公告失败, group: {group_id}, error: {repr(e)}')
                continue
    elif group == 'notice':
        group_res = await DBBotGroup.list_exist_bot_groups_by_notice_permissions(
            notice_permissions=1, self_bot=self_bot)
        for group_id in group_res.result:
            try:
                await bot.send_group_msg(group_id=group_id, message=msg)
            except Exception as e:
                logger.warning(f'向群组发送公告失败, group: {group_id}, error: {repr(e)}')
                continue
    elif group == 'command':
        group_res = await DBBotGroup.list_exist_bot_groups_by_command_permissions(
            command_permissions=1, self_bot=self_bot)
        for group_id in group_res.result:
            try:
                await bot.send_group_msg(group_id=group_id, message=msg)
            except Exception as e:
                logger.warning(f'向群组发送公告失败, group: {group_id}, error: {repr(e)}')
                continue
    elif re.match(r'^\d+$', group):
        group_id = int(group)
        try:
            await bot.send_group_msg(group_id=group_id, message=msg)
        except Exception as e:
            logger.warning(f'向群组发送公告失败, group: {group_id}, error: {repr(e)}')
    else:
        logger.warning(f'公告未发送, 不合规的群组类型或群号: {group}')
        await announce.finish('不合规的群组类型或群号')
    logger.info(f'公告已成功发送群组: {group}')
    await announce.finish('公告发送完成')
