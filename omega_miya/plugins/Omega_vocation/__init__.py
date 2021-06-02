import re
from datetime import datetime, timedelta
from nonebot import MatcherGroup, export, logger, require
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP
from omega_miya.utils.Omega_Base import DBSkill, DBUser, DBBot, DBBotGroup
from omega_miya.utils.Omega_plugin_utils import init_export, init_permission_state, PermissionChecker

# Custom plugin usage text
__plugin_name__ = '请假'
__plugin_usage__ = r'''【Omega 请假插件】
用来设置/查询自己以及群员的状态和假期
仅限群聊使用

**Permission**
Command
with AuthNode

**AuthNode**
basic

**Usage**
/我的状态
/重置状态
/我的假期
/请假 [时间] [理由]
/销假
/谁有空 [技能名称]
/谁在休假'''

# 声明本插件可配置的权限节点
__plugin_auth_node__ = [
    'basic'
]

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__, __plugin_auth_node__)

# 注册事件响应器
vocation = MatcherGroup(
    type='message',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_permission_state(
        name='vocation',
        command=True,
        auth_node='basic'),
    permission=GROUP,
    priority=10,
    block=True)

my_status = vocation.on_command('我的状态')


@my_status.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    user_id = event.user_id
    user = DBUser(user_id=user_id)
    result = await user.status()
    if result.success():
        status = result.result
        if status == 1:
            status = '请假中'
        elif status == 2:
            status = '工作中'
        else:
            status = '空闲中'
        logger.info(f"my_status: {event.group_id}/{user_id}, Success, {result.info}")
        await my_status.finish(f'你现在的状态是: 【{status}】')
    else:
        logger.error(f"my_status: {event.group_id}/{user_id}, Failed, {result.info}")
        await my_status.finish('没有查询到你的状态信息QAQ, 请尝试使用【/重置状态】来解决问题')


# 注册事件响应器
reset_status = vocation.on_command('重置状态', aliases={'销假'})


@reset_status.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    user_id = event.user_id
    user = DBUser(user_id=user_id)
    result = await user.status_set(status=0)
    if result.success():
        logger.info(f"reset_status: {event.group_id}/{user_id}, Success, {result.info}")
        await my_status.finish('Success')
    else:
        logger.error(f"reset_status: {event.group_id}/{user_id}, Failed, {result.info}")
        await my_status.finish('Failed QAQ')


# 注册事件响应器
my_vocation = vocation.on_command('我的假期')


@my_vocation.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    user_id = event.user_id
    user = DBUser(user_id=user_id)
    result = await user.vocation_status()
    if result.success():
        status, stop_time = result.result
        if status == 1:
            msg = f'你的假期将持续到: 【{stop_time}】'
        else:
            msg = '你似乎并不在假期中呢~需要现在请假吗？'
        logger.info(f"my_vocation: {event.group_id}/{user_id}, Success, {result.info}")
        await my_status.finish(msg)
    else:
        logger.error(f"my_vocation: {event.group_id}/{user_id}, Failed, {result.info}")
        await my_status.finish('没有查询到你的假期信息QAQ, 请尝试使用【/重置状态】来解决问题')


# 注册事件响应器
set_vocation = vocation.on_command('请假')


# 修改默认参数处理
@set_vocation.args_parser
async def parse(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await set_vocation.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await set_vocation.finish('操作已取消')


@set_vocation.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        pass
    elif args and len(args) == 1:
        state['vocation_time'] = args[0]
        state['reason'] = None
    elif args and len(args) == 2:
        state['vocation_time'] = args[0]
        state['reason'] = args[1]
    else:
        await set_vocation.finish('参数错误QAQ')


@set_vocation.got('vocation_time', prompt='请输入你想请假的时间: \n仅支持数字+周/天/小时/分/分钟/秒')
async def handle_vocation_time(bot: Bot, event: GroupMessageEvent, state: T_State):
    time = state['vocation_time']
    add_time = timedelta()
    if re.match(r'^\d+周$', time):
        time = int(re.sub(r'周$', '', time))
        add_time = timedelta(weeks=time)
    elif re.match(r'^\d+天$', time):
        time = int(re.sub(r'天$', '', time))
        add_time = timedelta(days=time)
    elif re.match(r'^\d+小时$', time):
        time = int(re.sub(r'小时$', '', time))
        add_time = timedelta(hours=time)
    elif re.match(r'^\d+(分|分钟)$', time):
        time = int(re.sub(r'(分|分钟)$', '', time))
        add_time = timedelta(minutes=time)
    elif re.match(r'^\d+秒$', time):
        time = int(re.sub(r'秒$', '', time))
        add_time = timedelta(seconds=time)
    else:
        await set_vocation.reject('仅支持数字+周/天/小时/分/分钟/秒, 请重新输入, 取消命令请发送【取消】:')
    state['stop_at'] = datetime.now() + add_time


@set_vocation.got('stop_at', prompt='stop_at?')
@set_vocation.got('reason', prompt='请输入你的请假理由:')
async def handle_vocation_stop(bot: Bot, event: GroupMessageEvent, state: T_State):
    user_id = event.user_id
    user = DBUser(user_id=user_id)
    stop_at = state['stop_at']
    reason = state['reason']
    result = await user.vocation_set(stop_time=stop_at, reason=reason)
    if result.success():
        logger.info(f"Group: {event.group_id}/{user_id}, set_vocation, Success, {result.info}")
        await set_vocation.finish(f'请假成功! 你的假期将持续到【{stop_at.strftime("%Y-%m-%d %H:%M:%S")}】')
    else:
        logger.error(f"Group: {event.group_id}/{user_id}, set_vocation, Failed, {result.info}")
        await set_vocation.finish('请假失败, 发生了意外的错误QAQ')


# 注册事件响应器
get_idle = vocation.on_command('谁有空')


# 修改默认参数处理
@get_idle.args_parser
async def parse(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await get_idle.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await get_idle.finish('操作已取消')


@get_idle.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        state['skill'] = None
    elif args and len(args) == 1:
        state['skill'] = args[0]
    else:
        await set_vocation.finish('参数错误QAQ')


@get_idle.got('skill', prompt='空闲技能组?')
async def handle_skill(bot: Bot, event: GroupMessageEvent, state: T_State):
    skill = state['skill']
    group_id = event.group_id
    self_bot = DBBot(self_qq=int(bot.self_id))
    group = DBBotGroup(group_id=group_id, self_bot=self_bot)
    if not skill:
        result = await group.idle_member_list()
        if result.success() and result.result:
            msg = ''
            for nickname, user_skill in result.result:
                msg += f'\n【{nickname}{user_skill}】'
            logger.info(f"Group: {event.group_id}, get_idle, Success, {result.info}")
            await get_idle.finish(f'现在有空的人: \n{msg}')
        elif result.success() and not result.result:
            logger.info(f"Group: {event.group_id}, get_idle, Success, {result.info}")
            await get_idle.finish(f'现在似乎没人有空呢QAQ')
        else:
            logger.error(f"Group: {event.group_id}, get_idle, Failed, {result.info}")
            await get_idle.finish(f'似乎发生了点错误QAQ')
    else:
        skill_res = await DBSkill.list_available_skill()
        if skill not in skill_res.result:
            await get_idle.reject(f'没有{skill}这个技能, 请重新输入, 取消命令请发送【取消】:')
        result = await group.idle_skill_list(skill=DBSkill(name=skill))
        if result.success() and result.result:
            msg = ''
            for nickname in result.result:
                msg += f'\n【{nickname}】'
            await get_idle.finish(f'现在有空的{skill}人: \n{msg}')
        elif result.success() and not result.result:
            logger.info(f"Group: {event.group_id}, get_idle, Success, {result.info}")
            await get_idle.finish(f'现在似乎没有{skill}人有空呢QAQ')
        else:
            logger.error(f"Group: {event.group_id}, get_idle, Failed, {result.info}")
            await get_idle.finish(f'似乎发生了点错误QAQ')


# 注册事件响应器
get_vocation = vocation.on_command('谁在休假')


@get_vocation.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    group_id = event.group_id
    self_bot = DBBot(self_qq=int(bot.self_id))
    group = DBBotGroup(group_id=group_id, self_bot=self_bot)
    result = await group.vocation_member_list()
    if result.success() and result.result:
        msg = ''
        for nickname, stop_at in result.result:
            msg += f'\n【{nickname}/休假到: {stop_at}】'
        logger.info(f"Group: {event.group_id}, get_vocation, Success, {result.info}")
        await get_vocation.finish(f'现在在休假的的人: \n{msg}')
    elif result.success() and not result.result:
        logger.info(f"Group: {event.group_id}, get_vocation, Success, {result.info}")
        await get_vocation.finish(f'现在似乎没没有人休假呢~')
    else:
        logger.error(f"Group: {event.group_id}, get_vocation, Failed, {result.info}")
        await get_idle.finish(f'似乎发生了点错误QAQ')


# 启用检查假期的定时任务
scheduler = require("nonebot_plugin_apscheduler").scheduler


@scheduler.scheduled_job(
    'cron',
    # year=None,
    # month=None,
    # day='*/1',
    # week=None,
    # day_of_week=None,
    # hour='4',
    minute='*/10',
    # second='*/10',
    # start_date=None,
    # end_date=None,
    # timezone=None,
    id='member_vocations_monitor',
    coalesce=True,
    misfire_grace_time=60
)
async def member_vocations_monitor():
    logger.debug(f"member_vocations_monitor: vocation checking started")

    from nonebot import get_bots

    over_vocation_user = set()

    for bot_id, bot in get_bots().items():
        group_list = await bot.call_api('get_group_list')
        for group in group_list:
            group_id = group.get('group_id')

            # 跳过不具备权限的组
            self_bot = DBBot(self_qq=int(bot.self_id))
            auth_check_res = await PermissionChecker(self_bot=self_bot).check_auth_node(
                auth_id=group_id, auth_type='group', auth_node='Omega_vocation.basic')
            if auth_check_res != 1:
                continue
            logger.debug(f"member_vocations_monitor: checking group: {group_id}")

            # 调用api获取群成员信息
            group_member_list = await bot.call_api(api='get_group_member_list', group_id=group_id)

            for user_info in group_member_list:
                user_nickname = user_info['card']
                if not user_nickname:
                    user_nickname = user_info['nickname']
                user_qq = user_info['user_id']
                user = DBUser(user_id=user_qq)
                user_vocation_res = await user.vocation_status()
                status, stop_time = user_vocation_res.result
                if status == 1 and datetime.now() >= stop_time:
                    msg = f'【{user_nickname}】的假期已经结束啦~\n快给他/她安排工作吧！'
                    await bot.call_api(api='send_group_msg', group_id=group_id, message=msg)
                    over_vocation_user.add(user)
    for user in over_vocation_user:
        _res = await user.status_set(status=0)
        if not _res.success():
            logger.error(f"reset user status failed: {_res.info}")
    logger.debug('member_vocations_monitor: vocation checking completed')
