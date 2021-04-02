"""
各类bot后台任务
"""
import nonebot
from nonebot import logger, require
from omega_miya.utils.Omega_Base import DBGroup, DBUser, DBCoolDownEvent
from .Omega_proxy import ENABLE_PROXY, check_proxy

# 获取scheduler
scheduler = require("nonebot_plugin_apscheduler").scheduler


# 创建自动更新群组信息的定时任务
@scheduler.scheduled_job(
    'cron',
    # year=None,
    # month=None,
    # day='*/1',
    # week=None,
    # day_of_week=None,
    hour='3',
    minute='47',
    # second='*/10',
    # start_date=None,
    # end_date=None,
    # timezone=None,
    id='refresh_group_info',
    coalesce=True,
    misfire_grace_time=300
)
async def refresh_group_info():
    from nonebot import get_bots

    for bot_id, bot in get_bots().items():
        group_list = await bot.call_api('get_group_list')
        for group in group_list:
            group_id = group.get('group_id')
            # 调用api获取群信息
            group_info = await bot.call_api(api='get_group_info', group_id=group_id)
            group_name = group_info['group_name']
            group = DBGroup(group_id=group_id)

            # 添加并初始化群信息
            group.add(name=group_name)

            # 更新用户
            group_member_list = await bot.call_api(api='get_group_member_list', group_id=group_id)

            # 首先清除数据库中退群成员
            exist_member_list = []
            for user_info in group_member_list:
                user_qq = user_info['user_id']
                exist_member_list.append(int(user_qq))

            db_member_list = []
            for user_id, nickname in group.member_list().result:
                db_member_list.append(user_id)
            del_member_list = list(set(db_member_list).difference(set(exist_member_list)))

            for user_id in del_member_list:
                group.member_del(user=DBUser(user_id=user_id))

            # 更新群成员
            for user_info in group_member_list:
                # 用户信息
                user_qq = user_info['user_id']
                user_nickname = user_info['nickname']
                user_group_nickmane = user_info['card']
                if not user_group_nickmane:
                    user_group_nickmane = user_nickname
                _user = DBUser(user_id=user_qq)
                _result = _user.add(nickname=user_nickname)
                if not _result.success():
                    logger.warning(f'Refresh group info, User: {user_qq}, {_result.info}')
                    continue
                _result = group.member_add(user=_user, user_group_nickname=user_group_nickmane)
                if not _result.success():
                    logger.warning(f'Refresh group info, User: {user_qq}, {_result.info}')

            group.init_member_status()
            logger.info(f'Refresh group info completed, Bot: {bot_id}, Group: {group_id}')


logger.opt(colors=True).debug('后台任务: <lg>refresh_group_info</lg>, <ly>已启用!</ly>')


# 创建用于刷新冷却事件的定时任务
@scheduler.scheduled_job(
    'cron',
    # year=None,
    # month=None,
    # day='*/1',
    # week=None,
    # day_of_week=None,
    # hour='*/8',
    # minute='*/1',
    second='*/20',
    # start_date=None,
    # end_date=None,
    # timezone=None,
    id='cool_down_refresh',
    coalesce=True,
    misfire_grace_time=10
)
def cool_down_refresh():
    logger.debug('cool_down_refresh: cleaning time out event')
    DBCoolDownEvent.clear_time_out_event()


logger.opt(colors=True).debug('后台任务: <lg>cool_down_refresh</lg>, <ly>已启用!</ly>')


# 创建用于检查代理可用性的状态的定时任务
if ENABLE_PROXY:
    # 初始化任务加入启动序列
    nonebot.get_driver().on_startup(check_proxy)

    scheduler.add_job(
        check_proxy,
        'cron',
        # year=None,
        # month=None,
        # day=None,
        # week=None,
        # day_of_week=None,
        # hour=None,
        # minute=None,
        second='*/30',
        # start_date=None,
        # end_date=None,
        # timezone=None,
        id='check_proxy',
        coalesce=True,
        misfire_grace_time=20
    )
    logger.opt(colors=True).debug('后台任务: <lg>check_proxy</lg>, <ly>已启用!</ly>')


__all__ = [
    'scheduler'
]
