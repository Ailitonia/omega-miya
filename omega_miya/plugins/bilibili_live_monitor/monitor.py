import asyncio
import random
from time import sleep
from nonebot import logger, require, get_driver, get_bots
from omega_miya.utils.Omega_Base import DBSubscription, DBTable
from .utils import get_live_info, get_user_info


# 初始化直播间标题, 状态
live_title = {}
live_status = {}
live_up_name = {}


async def init_live_info():
    global live_title
    global live_status
    global live_up_name

    t = DBTable(table_name='Subscription')
    for item in t.list_col_with_condition('sub_id', 'sub_type', 1).result:
        sub_id = int(item[0])
        try:
            # 获取直播间信息
            _res = await get_live_info(room_id=sub_id)
            if not _res.success():
                logger.error(f'init_live_info: 获取直播间信息失败, room_id: {sub_id}, error: {_res.info}')
                continue
            live_info = _res.result
            up_uid = _res.result.get('uid')
            _res = await get_user_info(user_uid=up_uid)
            if not _res.success():
                logger.error(f'init_live_info: 获取直播间UP用户信息失败, room_id: {sub_id}, error: {_res.info}')
                continue
            up_name = _res.result.get('name')

            # 直播状态放入live_status全局变量中
            live_status[sub_id] = int(live_info['status'])

            # 直播间标题放入live_title全局变量中
            live_title[sub_id] = str(live_info['title'])

            # 直播间up名称放入live_up_name全局变量中
            live_up_name[sub_id] = str(up_name)
        except Exception as e:
            logger.error(f'init_live_info: 获取直播间信息错误, room_id: {sub_id}, error: {repr(e)}')
            continue
    logger.info('init_live_info: 初始化完成')


# 初始化任务加入启动序列
get_driver().on_startup(init_live_info)


# 启用检查直播间状态的定时任务
scheduler = require("nonebot_plugin_apscheduler").scheduler


# 创建用于更新数据库里面直播间UP名称的定时任务
@scheduler.scheduled_job(
    'cron',
    # year=None,
    # month=None,
    day='*/1',
    # week=None,
    # day_of_week=None,
    # hour='*/8',
    # minute='*/1',
    # second='*/20',
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
    for item in t.list_col_with_condition('sub_id', 'sub_type', 1).result:
        sub_id = int(item[0])
        sub = DBSubscription(sub_type=1, sub_id=sub_id)
        _res = await get_live_info(room_id=sub_id)
        if not _res.success():
            logger.error(f'live_db_upgrade: 获取直播间信息失败, room_id: {sub_id}, error: {_res.info}')
            continue
        up_uid = _res.result.get('uid')
        _res = await get_user_info(user_uid=up_uid)
        if not _res.success():
            logger.error(f'live_db_upgrade: 获取直播间UP用户信息失败, room_id: {sub_id}, error: {_res.info}')
            continue
        up_name = _res.result.get('name')
        _res = sub.add(up_name=up_name)
        if not _res.success():
            logger.error(f'live_db_upgrade: 更新直播间信息失败, room_id: {sub_id}, error: {_res.info}')
            continue
    logger.debug('live_db_upgrade: upgrade subscription info completed')


@scheduler.scheduled_job(
    'cron',
    # year=None,
    # month=None,
    # day='*/1',
    # week=None,
    # day_of_week=None,
    # hour='4',
    minute='*/2',
    # second='*/30',
    # start_date=None,
    # end_date=None,
    # timezone=None,
    id='bilibili_live_monitor',
    coalesce=True,
    misfire_grace_time=30
)
async def bilibili_live_monitor():
    sleep(random.randint(1, 4))

    logger.debug(f"bilibili_live_monitor: checking started")
    global live_title
    global live_status
    global live_up_name

    # 获取当前bot列表
    bots = []
    for bot_id, bot in get_bots().items():
        bots.append(bot)

    # 获取所有有通知权限的群组
    all_noitce_groups = []
    t = DBTable(table_name='Group')
    for item in t.list_col_with_condition('group_id', 'notice_permissions', 1).result:
        all_noitce_groups.append(int(item[0]))

    # 获取订阅表中的所有直播间订阅
    check_sub = []
    t = DBTable(table_name='Subscription')
    for item in t.list_col_with_condition('sub_id', 'sub_type', 1).result:
        check_sub.append(int(item[0]))

    # 注册一个异步函数用于检查直播间状态
    async def check_live(room_id: int):
        # 获取直播间信息
        _res = await get_live_info(room_id=room_id)
        if not _res.success():
            logger.error(f'bilibili_live_monitor: 获取直播间信息失败, room_id: {room_id}, error: {_res.info}')
            return
        live_info = _res.result

        sub = DBSubscription(sub_type=1, sub_id=room_id)

        # 获取订阅了该直播间的所有群
        sub_group = sub.sub_group_list().result
        # 需通知的群
        notice_group = list(set(all_noitce_groups) & set(sub_group))

        up_name = live_up_name[room_id]

        # 检查是否是已开播状态, 若已开播则监测直播间标题变动
        # 为避免开播时同时出现标题变更通知和开播通知, 在检测到直播状态变化时更新标题, 且仅在直播状态为直播中时发送标题变更通知
        if live_info['status'] != live_status[room_id]\
                and live_info['status'] == 1\
                and live_info['title'] != live_title[room_id]:
            # 更新标题
            live_title[room_id] = live_info['title']
            logger.info(f"直播间: {room_id}/{up_name} 标题变更为: {live_info['title']}")
        elif live_info['status'] == 1 and live_info['title'] != live_title[room_id]:
            # 通知有通知权限且订阅了该直播间的群
            msg = f"{up_name}的直播间换标题啦！\n\n【{live_info['title']}】\n{live_info['url']}"
            for group_id in notice_group:
                for _bot in bots:
                    try:
                        await _bot.call_api(api='send_group_msg', group_id=group_id, message=msg)
                        logger.info(f"向群组: {group_id} 发送直播间: {room_id} 标题变更通知")
                    except Exception as _e:
                        logger.warning(f"向群组: {group_id} 发送直播间: {room_id} 标题变更通知失败, error: {repr(_e)}")
                        continue
            live_title[room_id] = live_info['title']
            logger.info(f"直播间: {room_id}/{up_name} 标题变更为: {live_info['title']}")

        # 检测开播/下播
        # 检查直播间状态与原状态是否一致
        if live_info['status'] != live_status[room_id]:
            try:
                # 现在状态为未开播
                if live_info['status'] == 0:
                    msg = f'{up_name}下播了'
                    # 通知有通知权限且订阅了该直播间的群
                    for group_id in notice_group:
                        for _bot in bots:
                            try:
                                await _bot.call_api(api='send_group_msg', group_id=group_id, message=msg)
                                logger.info(f"向群组: {group_id} 发送直播间: {room_id} 下播通知")
                            except Exception as _e:
                                logger.warning(f"向群组: {group_id} 发送直播间: {room_id} 下播通知失败, error: {repr(_e)}")
                                continue
                    # 更新直播间状态
                    live_status[room_id] = live_info['status']
                    logger.info(f"直播间: {room_id}/{up_name} 下播了")
                # 现在状态为直播中
                elif live_info['status'] == 1:
                    # 打一条log记录准确开播信息
                    logger.info(f"开播记录: LiveStart! Room: {room_id}/{up_name}, Title: {live_info['title']}, "
                                f"TrueTime: {live_info['time']}")

                    msg = f"{live_info['time']}\n{up_name}开播啦！\n\n【{live_info['title']}】\n{live_info['url']}"
                    for group_id in notice_group:
                        for _bot in bots:
                            try:
                                await _bot.call_api(api='send_group_msg', group_id=group_id, message=msg)
                                logger.info(f"向群组: {group_id} 发送直播间: {room_id} 开播通知")
                            except Exception as _e:
                                logger.warning(f"向群组: {group_id} 发送直播间: {room_id} 开播通知失败, error: {repr(_e)}")
                                continue
                    live_status[room_id] = live_info['status']
                    logger.info(f"直播间: {room_id}/{up_name} 开播了")
                # 现在状态为未开播（轮播中）
                elif live_info['status'] == 2:
                    msg = f'{up_name}下播了（轮播中）'
                    for group_id in notice_group:
                        for _bot in bots:
                            try:
                                await _bot.call_api(api='send_group_msg', group_id=group_id, message=msg)
                                logger.info(f"向群组: {group_id} 发送直播间: {room_id} 下播通知")
                            except Exception as _e:
                                logger.warning(f"向群组: {group_id} 发送直播间: {room_id} 下播通知失败, error: {repr(_e)}")
                                continue
                    live_status[room_id] = live_info['status']
                    logger.info(f"直播间: {room_id}/{up_name} 下播了（轮播中）")
            except Exception as _e:
                logger.warning(f'试图向群组发送直播间: {room_id}/{up_name} 的直播通知时发生了错误: {repr(_e)}')

    # 检查所有在订阅表里面的直播间(异步)
    tasks = []
    for rid in check_sub:
        tasks.append(check_live(rid))
    try:
        await asyncio.gather(*tasks)
        logger.debug('bilibili_live_monitor: checking completed')
    except Exception as e:
        logger.error(f'bilibili_live_monitor: error occurred in checking  {repr(e)}')


__all__ = [
    'scheduler',
    'init_live_info'
]
