import asyncio
from nonebot import logger, require, get_bots
from nonebot.adapters.cqhttp import MessageSegment
from omega_miya.utils.Omega_Base import DBSubscription, DBDynamic, DBTable
from .utils import get_dynamic_info, get_user_info, get_user_dynamic, pic_2_base64


# 启用检查动态状态的定时任务
scheduler = require("nonebot_plugin_apscheduler").scheduler


# 创建用于更新数据库里面UP名称的定时任务
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
    id='dynamic_db_upgrade',
    coalesce=True,
    misfire_grace_time=60
)
async def dynamic_db_upgrade():
    logger.debug('dynamic_db_upgrade: started upgrade subscription info')
    t = DBTable(table_name='Subscription')
    for item in t.list_col_with_condition('sub_id', 'sub_type', 2).result:
        sub_id = int(item[0])
        sub = DBSubscription(sub_type=2, sub_id=sub_id)
        _res = await get_user_info(user_uid=sub_id)
        if not _res.success():
            logger.error(f'获取用户信息失败, uid: {sub_id}, error: {_res.info}')
        up_name = _res.result.get('name')
        _res = sub.add(up_name=up_name)
        if not _res.success():
            logger.error(f'dynamic_db_upgrade: 更新用户信息失败, uid: {sub_id}, error: {_res.info}')
            continue
    logger.debug('dynamic_db_upgrade: upgrade subscription info completed')


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
    id='bilibili_dynamic_monitor',
    coalesce=True,
    misfire_grace_time=45
)
async def bilibili_dynamic_monitor():

    logger.debug(f"bilibili_dynamic_monitor: checking started")

    # 获取当前bot列表
    bots = []
    for bot_id, bot in get_bots().items():
        bots.append(bot)

    # 获取所有有通知权限的群组
    all_noitce_groups = []
    t = DBTable(table_name='Group')
    for item in t.list_col_with_condition('group_id', 'notice_permissions', 1).result:
        all_noitce_groups.append(int(item[0]))

    # 获取订阅表中的所有动态订阅
    check_sub = []
    t = DBTable(table_name='Subscription')
    for item in t.list_col_with_condition('sub_id', 'sub_type', 2).result:
        check_sub.append(int(item[0]))

    # 注册一个异步函数用于检查动态
    async def check_dynamic(dy_uid):
        # 获取动态并返回动态类型及内容
        try:
            _res = await get_dynamic_info(dy_uid=dy_uid)
            if not _res.success():
                logger.error(f'bilibili_dynamic_monitor: 获取动态失败, uid: {dy_uid}, error: {_res.info}')
                return
        except Exception as e:
            logger.error(f'bilibili_dynamic_monitor: 获取动态失败, uid: {dy_uid}, error: {repr(e)}')
            return

        dynamic_info = dict(_res.result)

        # 用户所有的动态id
        _res = get_user_dynamic(user_id=dy_uid)
        if not _res.success():
            logger.error(f'bilibili_dynamic_monitor: 获取用户已有动态失败, uid: {dy_uid}, error: {_res.info}')
            return
        user_dy_id_list = list(_res.result)

        sub = DBSubscription(sub_type=2, sub_id=dy_uid)

        # 获取订阅了该直播间的所有群
        sub_group = sub.sub_group_list().result
        # 需通知的群
        notice_group = list(set(all_noitce_groups) & set(sub_group))

        for num in range(len(dynamic_info)):
            try:
                # 如果有新的动态
                if dynamic_info[num]['id'] not in user_dy_id_list:
                    logger.info(f"用户: {dy_uid}/{dynamic_info[num]['name']} 新动态: {dynamic_info[num]['id']}")
                    # 转发的动态
                    if dynamic_info[num]['type'] == 1:
                        # 原动态type=2, 带图片
                        if dynamic_info[num]['origin']['type'] == 2:
                            # 处理图片序列
                            pic_segs = ''
                            for pic_url in dynamic_info[num]['origin']['origin_pics']:
                                _res = await pic_2_base64(pic_url)
                                pic_b64 = _res.result
                                pic_segs += f'{MessageSegment.image(pic_b64)}\n'
                            msg = '{}转发了{}的动态！\n\n“{}”\n{}\n{}\n@{}: {}\n{}'.format(
                                dynamic_info[num]['name'], dynamic_info[num]['origin']['name'],
                                dynamic_info[num]['content'], dynamic_info[num]['url'], '=' * 16,
                                dynamic_info[num]['origin']['name'], dynamic_info[num]['origin']['content'],
                                pic_segs
                            )
                        # 原动态为其他类型, 无图
                        else:
                            msg = '{}转发了{}的动态！\n\n“{}”\n{}\n{}\n@{}: {}'.format(
                                dynamic_info[num]['name'], dynamic_info[num]['origin']['name'],
                                dynamic_info[num]['content'], dynamic_info[num]['url'], '=' * 16,
                                dynamic_info[num]['origin']['name'], dynamic_info[num]['origin']['content']
                            )
                        for group_id in notice_group:
                            for _bot in bots:
                                try:
                                    await _bot.call_api(api='send_group_msg', group_id=group_id, message=msg)
                                    logger.info(f"向群组: {group_id} 发送新动态通知: {dynamic_info[num]['id']}")
                                except Exception as _e:
                                    logger.warning(f"向群组: {group_id} 发送新动态通知: {dynamic_info[num]['id']} 失败, "
                                                   f"error: {repr(_e)}")
                                    continue
                    # 原创的动态（有图片）
                    elif dynamic_info[num]['type'] == 2:
                        # 处理图片序列
                        pic_segs = ''
                        for pic_url in dynamic_info[num]['pic_urls']:
                            _res = await pic_2_base64(pic_url)
                            pic_b64 = _res.result
                            pic_segs += f'{MessageSegment.image(pic_b64)}\n'
                        msg = '{}发布了新动态！\n\n“{}”\n{}\n{}'.format(
                            dynamic_info[num]['name'], dynamic_info[num]['content'],
                            dynamic_info[num]['url'], pic_segs)
                        for group_id in notice_group:
                            for _bot in bots:
                                try:
                                    await _bot.call_api(api='send_group_msg', group_id=group_id, message=msg)
                                    logger.info(f"向群组: {group_id} 发送新动态通知: {dynamic_info[num]['id']}")
                                except Exception as _e:
                                    logger.warning(f"向群组: {group_id} 发送新动态通知: {dynamic_info[num]['id']} 失败, "
                                                   f"error: {repr(_e)}")
                                    continue
                    # 原创的动态（无图片）
                    elif dynamic_info[num]['type'] == 4:
                        msg = '{}发布了新动态！\n\n“{}”\n{}'.format(
                            dynamic_info[num]['name'], dynamic_info[num]['content'], dynamic_info[num]['url'])
                        for group_id in notice_group:
                            for _bot in bots:
                                try:
                                    await _bot.call_api(api='send_group_msg', group_id=group_id, message=msg)
                                    logger.info(f"向群组: {group_id} 发送新动态通知: {dynamic_info[num]['id']}")
                                except Exception as _e:
                                    logger.warning(f"向群组: {group_id} 发送新动态通知: {dynamic_info[num]['id']} 失败, "
                                                   f"error: {repr(_e)}")
                                    continue
                    # 视频
                    elif dynamic_info[num]['type'] == 8:
                        msg = '{}发布了新的视频！\n\n《{}》\n“{}”\n{}'.format(
                            dynamic_info[num]['name'], dynamic_info[num]['origin'],
                            dynamic_info[num]['content'], dynamic_info[num]['url'])
                        for group_id in notice_group:
                            for _bot in bots:
                                try:
                                    await _bot.call_api(api='send_group_msg', group_id=group_id, message=msg)
                                    logger.info(f"向群组: {group_id} 发送新动态通知: {dynamic_info[num]['id']}")
                                except Exception as _e:
                                    logger.warning(f"向群组: {group_id} 发送新动态通知: {dynamic_info[num]['id']} 失败, "
                                                   f"error: {repr(_e)}")
                                    continue
                    # 小视频
                    elif dynamic_info[num]['type'] == 16:
                        msg = '{}发布了新的小视频动态！\n\n“{}”\n{}'.format(
                            dynamic_info[num]['name'], dynamic_info[num]['content'], dynamic_info[num]['url'])
                        for group_id in notice_group:
                            for _bot in bots:
                                try:
                                    await _bot.call_api(api='send_group_msg', group_id=group_id, message=msg)
                                    logger.info(f"向群组: {group_id} 发送新动态通知: {dynamic_info[num]['id']}")
                                except Exception as _e:
                                    logger.warning(f"向群组: {group_id} 发送新动态通知: {dynamic_info[num]['id']} 失败, "
                                                   f"error: {repr(_e)}")
                                    continue
                    # 番剧
                    elif dynamic_info[num]['type'] in [32, 512]:
                        msg = '{}发布了新的番剧！\n\n《{}》\n{}'.format(
                            dynamic_info[num]['name'], dynamic_info[num]['origin'], dynamic_info[num]['url'])
                        for group_id in notice_group:
                            for _bot in bots:
                                try:
                                    await _bot.call_api(api='send_group_msg', group_id=group_id, message=msg)
                                    logger.info(f"向群组: {group_id} 发送新动态通知: {dynamic_info[num]['id']}")
                                except Exception as _e:
                                    logger.warning(f"向群组: {group_id} 发送新动态通知: {dynamic_info[num]['id']} 失败, "
                                                   f"error: {repr(_e)}")
                                    continue
                    # 文章
                    elif dynamic_info[num]['type'] == 64:
                        msg = '{}发布了新的文章！\n\n《{}》\n“{}”\n{}'.format(
                            dynamic_info[num]['name'], dynamic_info[num]['origin'],
                            dynamic_info[num]['content'], dynamic_info[num]['url'])
                        for group_id in notice_group:
                            for _bot in bots:
                                try:
                                    await _bot.call_api(api='send_group_msg', group_id=group_id, message=msg)
                                    logger.info(f"向群组: {group_id} 发送新动态通知: {dynamic_info[num]['id']}")
                                except Exception as _e:
                                    logger.warning(f"向群组: {group_id} 发送新动态通知: {dynamic_info[num]['id']} 失败, "
                                                   f"error: {repr(_e)}")
                                    continue
                    # 音频
                    elif dynamic_info[num]['type'] == 256:
                        msg = '{}发布了新的音乐！\n\n《{}》\n“{}”\n{}'.format(
                            dynamic_info[num]['name'], dynamic_info[num]['origin'],
                            dynamic_info[num]['content'], dynamic_info[num]['url'])
                        for group_id in notice_group:
                            for _bot in bots:
                                try:
                                    await _bot.call_api(api='send_group_msg', group_id=group_id, message=msg)
                                    logger.info(f"向群组: {group_id} 发送新动态通知: {dynamic_info[num]['id']}")
                                except Exception as _e:
                                    logger.warning(f"向群组: {group_id} 发送新动态通知: {dynamic_info[num]['id']} 失败, "
                                                   f"error: {repr(_e)}")
                                    continue
                    # B站活动相关
                    elif dynamic_info[num]['type'] == 2048:
                        msg = '{}发布了一条活动相关动态！\n\n【{}】\n“{}”\n{}'.format(
                            dynamic_info[num]['name'], dynamic_info[num]['origin'],
                            dynamic_info[num]['content'], dynamic_info[num]['url'])
                        for group_id in notice_group:
                            for _bot in bots:
                                try:
                                    await _bot.call_api(api='send_group_msg', group_id=group_id, message=msg)
                                    logger.info(f"向群组: {group_id} 发送新动态通知: {dynamic_info[num]['id']}")
                                except Exception as _e:
                                    logger.warning(f"向群组: {group_id} 发送新动态通知: {dynamic_info[num]['id']} 失败, "
                                                   f"error: {repr(_e)}")
                                    continue
                    elif dynamic_info[num]['type'] == -1:
                        logger.warning(f"未知的动态类型: {dynamic_info[num]['id']}")
                    # 更新动态内容到数据库
                    dy_id = dynamic_info[num]['id']
                    dy_type = dynamic_info[num]['type']
                    content = dynamic_info[num]['content']
                    # 向数据库中写入动态信息
                    dynamic = DBDynamic(uid=dy_uid, dynamic_id=dy_id)
                    _res = dynamic.add(dynamic_type=dy_type, content=content)
                    if _res.success():
                        logger.info(f"向数据库写入动态信息: {dynamic_info[num]['id']} 成功")
                    else:
                        logger.error(f"向数据库写入动态信息: {dynamic_info[num]['id']} 失败")
            except Exception as _e:
                logger.error(f'bilibili_dynamic_monitor: 解析新动态: {dy_uid} 的时发生了错误, error info: {repr(_e)}')

    # 检查所有在订阅表里面的直播间(异步)
    tasks = []
    for uid in check_sub:
        tasks.append(check_dynamic(uid))
    try:
        await asyncio.gather(*tasks)
        logger.debug('bilibili_dynamic_monitor: checking completed')
    except Exception as e:
        logger.error(f'bilibili_dynamic_monitor: error occurred in checking  {repr(e)}')


__all__ = [
    'scheduler'
]
