"""
@Author         : Ailitonia
@Date           : 2021/06/22 20:38
@FileName       : schedule_message.py
@Project        : nonebot2_miya 
@Description    : 定时消息插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import nonebot
import re
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from nonebot import MatcherGroup, logger, require
from nonebot.plugin.export import export
from nonebot.typing import T_State
from nonebot.permission import SUPERUSER
from nonebot.adapters.cqhttp.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.message import Message
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from omega_miya.database import DBBot, DBBotGroup, Result
from omega_miya.utils.omega_plugin_utils import init_export, init_processor_state


# Custom plugin usage text
__plugin_custom_name__ = '定时消息'
__plugin_usage__ = r'''【定时消息】
设置群组定时通知消息
仅限群聊使用

**Permission**
Command & Lv.10
or AuthNode

**AuthNode**
basic

**Usage**
**GroupAdmin and SuperUser Only**
/设置定时消息
/查看定时消息
/删除定时消息'''


# Init plugin export
init_export(export(), __plugin_custom_name__, __plugin_usage__)


driver = nonebot.get_driver()
scheduler: AsyncIOScheduler = require("nonebot_plugin_apscheduler").scheduler

# 注册事件响应器
ScheduleMsg = MatcherGroup(
    type='message',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='schedule_message',
        command=True,
        level=10),
    permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER,
    priority=10,
    block=True)


set_schedule_message = ScheduleMsg.on_command('设置定时消息', aliases={'添加定时消息'})
list_schedule_message = ScheduleMsg.on_command('查看定时消息')
del_schedule_message = ScheduleMsg.on_command('删除定时消息', aliases={'移除定时消息'})


# 设置定时消息部分
# 修改默认参数处理
@set_schedule_message.args_parser
async def parse(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_message()).strip()
    if not args:
        await set_schedule_message.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args
    if state[state["_current_key"]] == '取消':
        await set_schedule_message.finish('操作已取消')


@set_schedule_message.got('mode', prompt='请发送设置定时消息的模式:\n【 cron / interval 】\n\n模式说明:\n'
                                         'cron(闹钟) - 每天某个具体时间发送消息\n'
                                         'interval(定时器) - 每间隔一定时间发送消息')
async def handle_mode(bot: Bot, event: GroupMessageEvent, state: T_State):
    mode = state['mode']
    if mode not in ['cron', 'interval']:
        await set_schedule_message.finish('您发送的不是有效的模式QAQ')
    if mode == 'interval':
        state['repeat'] = 'all'


@set_schedule_message.got('name', prompt='请发送为当前定时任务设置的名称:')
async def handle_time(bot: Bot, event: GroupMessageEvent, state: T_State):
    _name = state['name']
    if len(_name) > 100:
        await set_schedule_message.finish('设置的名称过长QAQ')


@set_schedule_message.got('time', prompt='请发送你要设置定时时间, 时间格式为24小时制四位数字:\n\n设置说明:\n'
                                         '若模式为cron(闹钟), 则“1830”代表每天下午六点半发送定时消息\n'
                                         '若模式为interval(定时器), 则“0025”代表每隔25分钟发送定时消息')
async def handle_time(bot: Bot, event: GroupMessageEvent, state: T_State):
    time = state['time']
    mode = state['mode']
    try:
        _time = datetime.strptime(time, '%H%M')
        _hour = _time.hour
        _minute = _time.minute
    except ValueError:
        await set_schedule_message.finish('输入的时间格式错误QAQ, 应该为24小时制四位数字')
        return
    if mode == 'interval' and _hour == 0 and _minute == 0:
        await set_schedule_message.finish('输入的时间格式错误QAQ, interval模式不允许时间为0000')
        return
    state['hour'] = _hour
    state['minute'] = _minute


@set_schedule_message.got('repeat', prompt='是否按星期重复?\n\n若只想在一周的某一天执行请以下日期中选择:\n'
                                           '【mon/tue/wed/thu/fri/sat/sun】\n\n'
                                           '若想每一天都执行请输入:\n【all】')
async def handle_time(bot: Bot, event: GroupMessageEvent, state: T_State):
    repeat = state['repeat']
    if repeat not in ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun', 'all']:
        await set_schedule_message.finish('输入的日期格式错误QAQ, 请在【mon/tue/wed/thu/fri/sat/sun/all】中选择输入')


@set_schedule_message.got('message', prompt='请发送你要设置的消息内容:')
async def handle_message(bot: Bot, event: GroupMessageEvent, state: T_State):
    message = state['message']
    name = state['name']
    mode = state['mode']
    hour = state['hour']
    minute = state['minute']
    repeat = state['repeat']
    group_id = event.group_id
    self_bot = DBBot(self_qq=int(bot.self_id))
    group = DBBotGroup(group_id=group_id, self_bot=self_bot)
    try:
        await add_scheduler(
            group=group, schedule_name=name, mode=mode, hour=hour, minute=minute, repeat=repeat, message=message)
    except Exception as e:
        logger.error(f'为群组: {group_id} 设置群组定时消息失败任务, 添加计划任务时发生错误: {repr(e)}')
        await set_schedule_message.finish(f'为本群组设定群组定时消息失败了QAQ, 请稍后再试或联系管理员处理')

    msg_set_result = await add_db_group_schedule_message(
        group=group, schedule_name=name, mode=mode, hour=hour, minute=minute, repeat=repeat, message=message)

    if msg_set_result.success():
        logger.info(f'已为群组: {group_id} 设置群组定时消息: {name}{mode}/{hour}:{minute}')
        await set_schedule_message.finish(f'已为本群组设定了群组定时消息:\n{name}/{mode}/{repeat}:{hour}:{minute}')
    else:
        logger.error(f'为群组: {group_id} 设置群组定时消息失败, error info: {msg_set_result.info}')
        await set_schedule_message.finish(f'为本群组设定了群组定时消息失败了QAQ, 请稍后再试或联系管理员处理')


# 查看定时消息部分
@list_schedule_message.handle()
async def handle(bot: Bot, event: GroupMessageEvent, state: T_State):
    self_bot = DBBot(self_qq=int(bot.self_id))
    group = DBBotGroup(group_id=event.group_id, self_bot=self_bot)
    schedule_result = await list_db_group_schedule_message(group=group)
    if schedule_result.error:
        logger.error(f'Get group {event.group_id} message schedule list failed: {schedule_result.info}')
        await list_schedule_message.finish(f'获取群定时消息失败了QAQ, 请稍后再试或联系管理员处理')
    msg = f'本群已设置的定时消息任务:\n{"="*12}'
    for _name, _mode, _time, _message in schedule_result.result:
        _name = re.sub(r'^ScheduleMsg_', '', str(_name))
        msg += f'\n【{_name}】 - {_mode}({_time})'
    await list_schedule_message.finish(msg)


# 删除定时消息部分
# 修改默认参数处理
@del_schedule_message.args_parser
async def parse(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_message()).strip()
    if not args:
        await del_schedule_message.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args
    if state[state["_current_key"]] == '取消':
        await del_schedule_message.finish('操作已取消')


@del_schedule_message.handle()
async def handle_jobs(bot: Bot, event: GroupMessageEvent, state: T_State):
    self_bot = DBBot(self_qq=int(bot.self_id))
    group = DBBotGroup(group_id=event.group_id, self_bot=self_bot)
    schedule_result = await list_db_group_schedule_message(group=group)
    if schedule_result.error:
        logger.error(f'Get group {event.group_id} message schedule list failed: {schedule_result.info}')
        await list_schedule_message.finish(f'获取群定时消息列表失败了QAQ, 请稍后再试或联系管理员处理')
    msg = f'本群已设置的定时消息任务有:\n{"="*12}'
    for _name, _mode, _time, _message in schedule_result.result:
        _name = re.sub(r'^ScheduleMsg_', '', str(_name))
        msg += f'\n【{_name}】 - {_mode}({_time})'
    await list_schedule_message.send(msg)


@del_schedule_message.got('name', prompt='请发送将要移除的定时任务的名称:')
async def handle_remove(bot: Bot, event: GroupMessageEvent, state: T_State):
    name = state['name']
    group_id = event.group_id
    self_bot = DBBot(self_qq=int(bot.self_id))
    group = DBBotGroup(group_id=group_id, self_bot=self_bot)
    try:
        await remove_scheduler(group=group, schedule_name=name)
    except Exception as e:
        logger.error(f'移除群组: {group_id} 定时消息失败, 移除计划任务时发生错误: {repr(e)}')
        await del_schedule_message.finish(f'移除群组定时消息失败了QAQ, 请稍后再试或联系管理员处理')

    msg_del_result = await del_db_group_schedule_message(group=group, schedule_name=name)

    if msg_del_result.success():
        logger.info(f'已移除群组: {group_id} 群组定时消息: {name}')
        await del_schedule_message.finish(f'已移除群组定时消息: {name}')
    else:
        logger.error(f'移除群组: {group_id} 群组定时消息失败, error info: {msg_del_result.info}')
        await del_schedule_message.finish(f'移除群组定时消息失败了QAQ, 请稍后再试或联系管理员处理')


async def add_db_group_schedule_message(
        group: DBBotGroup,
        schedule_name: str,
        mode: str,
        hour: int,
        minute: int,
        repeat: str,
        message: str) -> Result.IntResult:
    # 初始化计划任务设置ID
    _schedule_setting_id = f'ScheduleMsg_{schedule_name}'
    schedule_set_result = await group.setting_set(setting_name=_schedule_setting_id, main_config=mode,
                                                  secondary_config=f'{repeat}:{hour}:{minute}',
                                                  extra_config=message, setting_info='群组定时消息')
    return schedule_set_result


async def list_db_group_schedule_message(group: DBBotGroup) -> Result.ListResult:
    exist_setting = await group.setting_list()
    if exist_setting.error:
        return Result.ListResult(error=True, info=f'Get config wrong: {exist_setting.info}', result=[])
    else:
        result = [x for x in exist_setting.result if str(x[0]).startswith('ScheduleMsg_')]
        return Result.ListResult(error=False, info=f'Success', result=result)


async def del_db_group_schedule_message(group: DBBotGroup, schedule_name: str) -> Result.IntResult:
    _schedule_setting_id = f'ScheduleMsg_{schedule_name}'
    result = await group.setting_del(setting_name=_schedule_setting_id)
    return result


async def add_scheduler(
        group: DBBotGroup,
        schedule_name: str,
        mode: str,
        hour: int,
        minute: int,
        repeat: str,
        message: str):
    global scheduler
    _schedule_setting_id = f'ScheduleMsg_{group.self_bot.self_qq}_{schedule_name}'
    self_bot: Bot = nonebot.get_bots().get(str(group.self_bot.self_qq), None)
    if not self_bot:
        raise ValueError('Can not get Bot')

    async def _scheduler_handle():
        await self_bot.send_group_msg(group_id=group.group_id, message=Message(f'【定时消息】\n{"="*12}\n{message}'))

    if mode == 'cron':
        if repeat == 'all':
            scheduler.add_job(
                _scheduler_handle,
                'cron',
                hour=hour,
                minute=minute,
                id=_schedule_setting_id,
                coalesce=True,
                misfire_grace_time=10
            )
        else:
            scheduler.add_job(
                _scheduler_handle,
                'cron',
                day_of_week=repeat,
                hour=hour,
                minute=minute,
                id=_schedule_setting_id,
                coalesce=True,
                misfire_grace_time=10
            )
    elif mode == 'interval':
        if hour == 0 and minute != 0:
            scheduler.add_job(
                _scheduler_handle,
                'interval',
                minutes=minute,
                id=_schedule_setting_id,
                coalesce=True,
                misfire_grace_time=10
            )
        elif minute == 0:
            scheduler.add_job(
                _scheduler_handle,
                'interval',
                hours=hour,
                id=_schedule_setting_id,
                coalesce=True,
                misfire_grace_time=10
            )
        else:
            scheduler.add_job(
                _scheduler_handle,
                'interval',
                hours=hour,
                minutes=minute,
                id=_schedule_setting_id,
                coalesce=True,
                misfire_grace_time=10
            )
    else:
        raise ValueError(f'Unknown mode {mode}')


async def remove_scheduler(group: DBBotGroup, schedule_name: str):
    global scheduler
    _schedule_setting_id = f'ScheduleMsg_{group.self_bot.self_qq}_{schedule_name}'
    scheduler.remove_job(_schedule_setting_id)


# Bot 连接时初始化其消息任务
@driver.on_bot_connect
async def init_bot_message_schedule(bot: Bot):
    self_bot = DBBot(self_qq=int(bot.self_id))
    group_list_result = await DBBotGroup.list_exist_bot_groups(self_bot=self_bot)
    if group_list_result.error:
        logger.error(f'Init bot message schedule failed, get bot group list failed: {group_list_result.info}')
    for group in group_list_result.result:
        _bot_group = DBBotGroup(group_id=group, self_bot=self_bot)
        schedule_result = await list_db_group_schedule_message(group=_bot_group)
        if schedule_result.error:
            logger.error(f'Error occurred in init bot message schedule, '
                         f'get group {_bot_group.group_id} message schedule list failed: {schedule_result.info}')
            continue
        for _name, _mode, _time, _message in schedule_result.result:
            _name = re.sub(r'^ScheduleMsg_', '', str(_name))
            _repeat, _hour, _minute = [x for x in str(_time).split(':', maxsplit=3)]
            _hour = int(_hour)
            _minute = int(_minute)
            try:
                await add_scheduler(group=_bot_group, schedule_name=_name,
                                    mode=_mode, hour=_hour, minute=_minute, repeat=_repeat, message=_message)
            except Exception as e:
                logger.error(f'Init bot message schedule failed, '
                             f'为群组: {_bot_group.group_id} 添加群组定时消息任务失败, 添加计划任务时发生错误: {repr(e)}')
            continue


# Bot 断开连接时移除其消息任务
@driver.on_bot_disconnect
async def remove_bot_message_schedule(bot: Bot):
    self_bot = DBBot(self_qq=int(bot.self_id))
    group_list_result = await DBBotGroup.list_exist_bot_groups(self_bot=self_bot)
    if group_list_result.error:
        logger.error(f'Remove bot message schedule failed, get bot group list failed: {group_list_result.info}')
    for group in group_list_result.result:
        _bot_group = DBBotGroup(group_id=group, self_bot=self_bot)
        schedule_result = await list_db_group_schedule_message(group=_bot_group)
        if schedule_result.error:
            logger.error(f'Error occurred in remove bot message schedule, '
                         f'get group {_bot_group.group_id} message schedule list failed: {schedule_result.info}')
            continue
        for _name, _mode, _time, _message in schedule_result.result:
            _repeat, _hour, _minute = [x for x in str(_time).split(':', maxsplit=3)]
            _hour = int(_hour)
            _minute = int(_minute)
            try:
                await remove_scheduler(group=_bot_group, schedule_name=_name)
            except Exception as e:
                logger.error(f'Remove bot message schedule failed, '
                             f'移除群组: {_bot_group.group_id} 定时消息任务失败, 移除计划任务时发生错误: {repr(e)}')
            continue
