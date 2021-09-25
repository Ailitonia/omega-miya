"""
@Author         : Ailitonia
@Date           : 2021/09/24 22:03
@FileName       : __init__.py.py
@Project        : nonebot2_miya 
@Description    : 速率限制及控制工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import re
from datetime import datetime, timedelta
from nonebot import logger
from nonebot.plugin.export import export
from nonebot.plugin import on_notice, CommandGroup
from nonebot.typing import T_State
from nonebot.rule import to_me
from nonebot.permission import SUPERUSER
from nonebot.adapters.cqhttp.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent, GroupMessageEvent, GroupBanNoticeEvent
from omega_miya.database import DBBot, DBBotGroup, DBCoolDownEvent
from omega_miya.utils.omega_plugin_utils import init_export, MessageDecoder


GROUP_GLOBAL_CD_SETTING_NAME: str = 'group_global_cd'  # 与 utils.omega_processor.rate_limiting 中配置保持一致


# Custom plugin usage text
__plugin_custom_name__ = '流控限制'
__plugin_usage__ = r'''【Omega 流控限制插件】
控制群组全局冷却及命令频率

以下命令均需要@机器人
**Usage**
**SuperUser Only**
/设置全局冷却时间
/删除全局冷却时间
/移除全局冷却
/Ban
/GBan
'''


# Init plugin export
init_export(export(), __plugin_custom_name__, __plugin_usage__)


# 注册事件响应器
RateLimiting = CommandGroup(
    'RateLimiting',
    rule=to_me(),
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER,
    priority=10,
    block=True
)

set_group_gcd = RateLimiting.command('set_gcd', aliases={'设置全局冷却时间'})


# 修改默认参数处理
@set_group_gcd.args_parser
async def parse(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_message()).strip()
    if not args:
        await set_group_gcd.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args
    if state[state["_current_key"]] == '取消':
        await set_group_gcd.finish('操作已取消')


@set_group_gcd.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    if isinstance(event, GroupMessageEvent):
        state['group_id'] = event.group_id


@set_group_gcd.got('group_id', prompt='请发送你要设置的群号:')
async def handle_group_id(bot: Bot, event: MessageEvent, state: T_State):
    group_id = state['group_id']
    self_bot = DBBot(self_qq=int(bot.self_id))
    group = DBBotGroup(group_id=group_id, self_bot=self_bot)
    if not re.match(r'^\d+$', str(group_id)) or not (await group.exist()):
        await set_group_gcd.finish('群组不存在或群号不正确QAQ')


@set_group_gcd.got('time', prompt='请发送你要设置的冷却时间, 单位秒:')
async def handle_time(bot: Bot, event: MessageEvent, state: T_State):
    group_id = state['group_id']
    time = state['time']
    if not re.match(r'^\d+$', str(time)):
        await set_group_gcd.finish('时间格式错误QAQ, 应当为纯数字')

    self_bot = DBBot(self_qq=int(bot.self_id))
    group = DBBotGroup(group_id=group_id, self_bot=self_bot)
    setting_result = await group.setting_set(setting_name=GROUP_GLOBAL_CD_SETTING_NAME,
                                             main_config=time,
                                             setting_info='限流配置群组全局冷却时间')
    if setting_result.success():
        logger.info(f'已为群组: {group_id} 配置限流群组全局冷却时间: {time}')
        await set_group_gcd.finish(f'已为群组: {group_id} 配置限流群组全局冷却时间: {time}')
    else:
        logger.error(f'为群组: {group_id} 配置限流群组全局冷却时间失败, error info: {setting_result.info}')
        await set_group_gcd.finish(f'为群组: {group_id} 配置限流群组全局冷却时间失败了QAQ, 详情请见日志')


remove_group_gcd = RateLimiting.command('remove_gcd', aliases={'删除全局冷却时间'})


@remove_group_gcd.args_parser
async def parse(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_message()).strip()
    if not args:
        await remove_group_gcd.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args
    if state[state["_current_key"]] == '取消':
        await remove_group_gcd.finish('操作已取消')


@remove_group_gcd.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    if isinstance(event, GroupMessageEvent):
        state['group_id'] = event.group_id


@remove_group_gcd.got('group_id', prompt='请发送你要配置的群号:')
async def handle_group_id(bot: Bot, event: MessageEvent, state: T_State):
    group_id = state['group_id']
    self_bot = DBBot(self_qq=int(bot.self_id))
    group = DBBotGroup(group_id=group_id, self_bot=self_bot)
    if not re.match(r'^\d+$', str(group_id)) or not (await group.exist()):
        await remove_group_gcd.finish('群组不存在或群号不正确QAQ')

    setting_result = await group.setting_del(setting_name=GROUP_GLOBAL_CD_SETTING_NAME)
    if setting_result.success():
        logger.info(f'已为群组: {group_id} 删除全局冷却时间')
        await remove_group_gcd.finish(f'已删除了群组: {group_id} 的全局冷却时间!')
    else:
        logger.error(f'删除群组: {group_id} 的全局冷却时间失败, error info: {setting_result.info}')
        await remove_group_gcd.finish(f'删除群组: {group_id} 的全局冷却时间失败失败了QAQ, 详情请见日志')


clear_group_exist_gcd = RateLimiting.command('clear_gcd', aliases={'移除全局冷却'})


@clear_group_exist_gcd.args_parser
async def parse(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_message()).strip()
    if not args:
        await clear_group_exist_gcd.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args
    if state[state["_current_key"]] == '取消':
        await clear_group_exist_gcd.finish('操作已取消')


@clear_group_exist_gcd.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    if isinstance(event, GroupMessageEvent):
        state['group_id'] = event.group_id


@clear_group_exist_gcd.got('group_id', prompt='请发送你要移除全局冷却的群号:')
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    group_id = state['group_id']
    self_bot = DBBot(self_qq=int(bot.self_id))
    group = DBBotGroup(group_id=group_id, self_bot=self_bot)
    if not re.match(r'^\d+$', str(group_id)) or not (await group.exist()):
        await remove_group_gcd.finish('群组不存在或群号不正确QAQ')

    result = await DBCoolDownEvent.add_global_group_cool_down_event(
        group_id=group_id,
        stop_at=datetime.now(),
        description='Remove Group Global CoolDown')

    if result.success():
        logger.success(f'已移除群组: {group_id} 全局冷却')
    else:
        logger.error(f'移除群组: {group_id} 全局冷却失败, error: {result.info}')


ban_group = RateLimiting.command('ban_group', aliases={'GBan', 'GroupBan', 'gban'})


# 修改默认参数处理
@ban_group.args_parser
async def parse(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_message()).strip()
    if not args:
        await ban_group.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args
    if state[state["_current_key"]] == '取消':
        await ban_group.finish('操作已取消')


@ban_group.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    if isinstance(event, GroupMessageEvent):
        state['group_id'] = event.group_id


@ban_group.got('group_id', prompt='请发送你要封禁的群号:')
async def handle_group_id(bot: Bot, event: MessageEvent, state: T_State):
    group_id = state['group_id']
    if not re.match(r'^\d+$', str(group_id)):
        await ban_group.finish('群号格式不正确QAQ')


@ban_group.got('time', prompt='请发送需要封禁的时间, 单位秒:')
async def handle_time(bot: Bot, event: MessageEvent, state: T_State):
    group_id = state['group_id']
    time = state['time']
    if not re.match(r'^\d+$', str(time)):
        await ban_group.finish('时间格式错误QAQ, 应当为纯数字')

    result = await DBCoolDownEvent.add_global_group_cool_down_event(
        group_id=group_id,
        stop_at=datetime.now() + timedelta(seconds=int(time)),
        description='Ban Group CoolDown')

    if result.success():
        logger.info(f'已封禁群组: {group_id}, {time} 秒')
        await ban_group.finish(f'已封禁群组: {group_id}, {time} 秒')
    else:
        logger.error(f'封禁群组: {group_id} 失败, error info: {result.info}')
        await ban_group.finish(f'封禁群组: {group_id} 失败了QAQ, 详情请见日志')


ban_user = RateLimiting.command('ban_user', aliases={'Ban', 'ban'})


# 修改默认参数处理
@ban_user.args_parser
async def parse(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_message()).strip()
    if not args:
        await ban_user.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args
    if state[state["_current_key"]] == '取消':
        await ban_user.finish('操作已取消')


@ban_user.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    # 处理@人
    at_qq_list = MessageDecoder(message=event.message).get_all_at_qq()
    if at_qq_list:
        # 取at列表中第一个
        state['user_id'] = at_qq_list[0]


@ban_user.got('user_id', prompt='请发送你要封禁的用户qq:')
async def handle_group_id(bot: Bot, event: MessageEvent, state: T_State):
    user_id = state['user_id']
    if not re.match(r'^\d+$', str(user_id)):
        await ban_user.finish('qq号格式不正确QAQ')


@ban_user.got('time', prompt='请发送需要封禁的时间, 单位秒:')
async def handle_time(bot: Bot, event: MessageEvent, state: T_State):
    user_id = state['user_id']
    time = state['time']
    if not re.match(r'^\d+$', str(time)):
        await ban_user.finish('时间格式错误QAQ, 应当为纯数字')

    result = await DBCoolDownEvent.add_global_user_cool_down_event(
        user_id=user_id,
        stop_at=datetime.now() + timedelta(seconds=int(time)),
        description='Ban User CoolDown')

    if result.success():
        logger.info(f'已封禁用户: {user_id}, {time} 秒')
        await ban_user.finish(f'已封禁用户: {user_id}, {time} 秒')
    else:
        logger.error(f'封禁用户: {user_id} 失败, error info: {result.info}')
        await ban_user.finish(f'封禁用户: {user_id} 失败了QAQ, 详情请见日志')


# 注册事件响应器, 被禁言时触发
group_ban_cd = on_notice(priority=100, rule=to_me(), block=False)


@group_ban_cd.handle()
async def handle_group_ban_cd(bot: Bot, event: GroupBanNoticeEvent, state: T_State):
    group_id = event.group_id
    operator_id = event.operator_id
    duration = event.duration

    result = await DBCoolDownEvent.add_global_group_cool_down_event(
        group_id=group_id,
        stop_at=datetime.now() + timedelta(seconds=(duration * 10)),
        description=f'Group Ban CoolDown for 10 times duration: {duration}')

    if result.success():
        logger.success(f'被群组/管理员: {group_id}/{operator_id} 禁言, 时间 {duration} 秒, 已设置全局冷却')
    else:
        logger.error(f'被群组/管理员: {group_id}/{operator_id} 禁言, 时间 {duration} 秒, 设置全局冷却失败: {result.info}')
