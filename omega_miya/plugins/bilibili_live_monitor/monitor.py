import asyncio
import random
from nonebot import logger, require, get_driver, get_bots
from omega_miya.utils.Omega_Base import DBFriend, DBSubscription, DBTable
from omega_miya.utils.bilibili_utils import BiliLiveRoom
from .data_source import BiliLiveChecker
from .config import Config


__global_config = get_driver().config
plugin_config = Config(**__global_config.dict())
ENABLE_NEW_LIVE_API = plugin_config.enable_new_live_api
ENABLE_LIVE_CHECK_POOL_MODE = plugin_config.enable_live_check_pool_mode

# 检查池模式使用的检查队列
checking_pool = []

# 初始化任务加入启动序列
get_driver().on_startup(BiliLiveChecker.init_global_live_info)

# 启用检查直播间状态的定时任务
scheduler = require("nonebot_plugin_apscheduler").scheduler


# 创建用于更新数据库里面直播间UP名称的定时任务
@scheduler.scheduled_job(
    'cron',
    # year=None,
    # month=None,
    # day='*/1',
    # week=None,
    # day_of_week=None,
    hour='2',
    minute='2',
    second='33',
    # start_date=None,
    # end_date=None,
    # timezone=None,
    id='live_db_upgrade',
    coalesce=True,
    misfire_grace_time=60
)
async def live_db_upgrade():
    logger.debug('live_db_upgrade: started upgrade subscription info')
    t = DBTable(table_name='Subscription')
    sub_res = await t.list_col_with_condition('sub_id', 'sub_type', 1)
    for sub_id in sub_res.result:
        sub = DBSubscription(sub_type=1, sub_id=sub_id)
        live_user_info_result = await BiliLiveRoom(room_id=sub_id).get_user_info()
        if live_user_info_result.error:
            logger.error(f'live_db_upgrade: 更新直播间信息失败, room_id: {sub_id}, error: {live_user_info_result.info}')
            continue
        up_name = live_user_info_result.result.name
        _res = await sub.add(up_name=up_name, live_info='B站直播间')
        if not _res.success():
            logger.error(f'live_db_upgrade: 更新直播间信息失败, room_id: {sub_id}, error: {_res.info}')
            continue
    logger.debug('live_db_upgrade: upgrade subscription info completed')


# 创建直播检查函数
async def bilibili_live_monitor():
    logger.debug(f"bilibili_live_monitor: checking started")

    # 获取当前bot列表
    bots = []
    for bot_id, bot in get_bots().items():
        bots.append(bot)

    # 获取所有有通知权限的群组
    t = DBTable(table_name='Group')
    group_res = await t.list_col_with_condition('group_id', 'notice_permissions', 1)
    all_noitce_groups = [int(x) for x in group_res.result]

    # 获取所有启用了私聊功能的好友
    friend_res = await DBFriend.list_exist_friends_by_private_permission(private_permission=1)
    all_noitce_friends = [int(x) for x in friend_res.result]

    # 获取订阅表中的所有直播间订阅
    t = DBTable(table_name='Subscription')
    sub_res = await t.list_col_with_condition('sub_id', 'sub_type', 1)
    check_sub = [int(x) for x in sub_res.result]

    if not check_sub:
        logger.debug(f'bilibili_live_monitor: no live subscription, ignore.')
        return

    # 检查单个直播间状态
    async def check_live(room_id: int):
        # 获取直播间信息
        live_info_result = await BiliLiveRoom(room_id=room_id).get_info()
        if live_info_result.error:
            logger.error(f'bilibili_live_monitor: 获取直播间信息失败, room_id: {room_id}, error: {live_info_result.info}')
            return
        live_info = live_info_result.result
        try:
            await BiliLiveChecker(room_id=room_id).broadcaster(
                live_info=live_info, bots=bots, all_groups=all_noitce_groups, all_friends=all_noitce_friends)
        except Exception as _e:
            logger.error(f'bilibili_live_monitor: 处理直播间 {room_id} 状态信息是发生错误: {repr(_e)}')

    # 检查列表uid全部用户的直播间状态
    async def check_live_by_rids(room_id_list: list):
        uid_list = []
        for room_id in room_id_list:
            uid = BiliLiveChecker.live_uid_by_rid().get(room_id)
            if not uid:
                await BiliLiveChecker(room_id=room_id).init_live_info()
                uid = BiliLiveChecker.live_uid_by_rid().get(room_id)
            if not uid:
                logger.warning(f'bilibili_live_monitor: get uid from room_id failed, room_id: {room_id}')
                continue
            uid_list.append(uid)

        # 获取直播间信息
        live_info_result = await BiliLiveRoom.get_info_by_uids(uid_list=uid_list)
        if live_info_result.error:
            logger.error(f'bilibili_live_monitor: 获取直播间信息失败: error info: {live_info_result.info}')
            return

        # 处理直播间短号, 否则会出现订阅短号的群组无法收到通知
        live_info_ = live_info_result.result
        for room_id, live_info in live_info_.copy().items():
            short_id = live_info.short_id
            if short_id and short_id != 0:
                live_info_.update({short_id: live_info})

        # 依次处理各直播间信息
        for room_id, live_info in live_info_.items():
            try:
                await BiliLiveChecker(room_id=room_id).broadcaster(
                    live_info=live_info, bots=bots, all_groups=all_noitce_groups, all_friends=all_noitce_friends)
            except Exception as _e:
                logger.error(f'bilibili_live_monitor: 处理直播间 {room_id} 状态信息是发生错误: {repr(_e)}')
                continue

    # 使用了新的API
    if ENABLE_NEW_LIVE_API:
        # 检查所有在订阅表里面的直播间(异步)
        try:
            await check_live_by_rids(room_id_list=check_sub)
            logger.debug(f"bilibili_live_monitor: enable new api, checking completed, "
                         f"checked: {', '.join([str(x) for x in check_sub])}.")
        except Exception as e:
            logger.error(f'bilibili_live_monitor: enable new api, error occurred in checking  {repr(e)}')
    # 启用了检查池模式
    elif ENABLE_LIVE_CHECK_POOL_MODE:
        global checking_pool

        # checking_pool为空则上一轮检查完了, 重新往里面放新一轮的room_id
        if not checking_pool:
            checking_pool.extend(check_sub)

        # 看下checking_pool里面还剩多少
        waiting_num = len(checking_pool)

        # 默认单次检查并发数为3, 默认检查间隔为20s
        logger.debug(f'bili live pool mode debug info, B_checking_pool: {checking_pool}')
        if waiting_num >= 3:
            # 抽取检查对象
            now_checking = random.sample(checking_pool, k=3)
            # 更新checking_pool
            checking_pool = [x for x in checking_pool if x not in now_checking]
        else:
            now_checking = checking_pool.copy()
            checking_pool.clear()
        logger.debug(f'bili live pool mode debug info, A_checking_pool: {checking_pool}')
        logger.debug(f'bili live pool mode debug info, now_checking: {now_checking}')

        # 检查now_checking里面的直播间(异步)
        tasks = []
        for rid in now_checking:
            tasks.append(check_live(rid))
        try:
            await asyncio.gather(*tasks)
            logger.debug(f"bilibili_live_monitor: pool mode enable, checking completed, "
                         f"checked: {', '.join([str(x) for x in now_checking])}.")
        except Exception as e:
            logger.error(f'bilibili_live_monitor: pool mode enable, error occurred in checking {repr(e)}')
    # 没有启用检查池模式
    else:
        # 检查所有在订阅表里面的直播间(异步)
        tasks = []
        for rid in check_sub:
            tasks.append(check_live(rid))
        try:
            await asyncio.gather(*tasks)
            logger.debug(f"bilibili_live_monitor: pool mode disable, checking completed, "
                         f"checked: {', '.join([str(x) for x in check_sub])}.")
        except Exception as e:
            logger.error(f'bilibili_live_monitor: pool mode disable, error occurred in checking  {repr(e)}')


# 根据检查池模式初始化检查时间间隔
if ENABLE_NEW_LIVE_API:
    # 使用新api
    scheduler.add_job(
        bilibili_live_monitor,
        'cron',
        # year=None,
        # month=None,
        # day='*/1',
        # week=None,
        # day_of_week=None,
        # hour=None,
        # minute=None,
        second='*/30',
        # start_date=None,
        # end_date=None,
        # timezone=None,
        id='bilibili_live_monitor_enable_new_api',
        coalesce=True,
        misfire_grace_time=30
    )
elif ENABLE_LIVE_CHECK_POOL_MODE:
    # 检查池启用
    scheduler.add_job(
        bilibili_live_monitor,
        'cron',
        # year=None,
        # month=None,
        # day='*/1',
        # week=None,
        # day_of_week=None,
        # hour='9-23',
        # minute='*/2',
        second='10-50/20',
        # start_date=None,
        # end_date=None,
        # timezone=None,
        id='bilibili_live_monitor_pool_enable',
        coalesce=True,
        misfire_grace_time=20
    )
else:
    # 检查池禁用
    scheduler.add_job(
        bilibili_live_monitor,
        'cron',
        # year=None,
        # month=None,
        # day='*/1',
        # week=None,
        # day_of_week=None,
        # hour=None,
        minute='*/1',
        # second=None,
        # start_date=None,
        # end_date=None,
        # timezone=None,
        id='bilibili_live_monitor_pool_disable',
        coalesce=True,
        misfire_grace_time=30
    )

__all__ = [
    'scheduler'
]
