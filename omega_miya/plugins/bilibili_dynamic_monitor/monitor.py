import asyncio
import random
from typing import List
from nonebot import logger, require, get_bots, get_driver
from nonebot.adapters.cqhttp import MessageSegment
from nonebot.adapters.cqhttp.bot import Bot
from omega_miya.utils.Omega_Base import DBSubscription, DBDynamic
from omega_miya.utils.bilibili_utils import BiliUser, BiliDynamic, BiliRequestUtils
from omega_miya.utils.Omega_plugin_utils import MsgSender
from .config import Config


__global_config = get_driver().config
plugin_config = Config(**__global_config.dict())
ENABLE_DYNAMIC_CHECK_POOL_MODE = plugin_config.enable_dynamic_check_pool_mode


# 检查池模式使用的检查队列
checking_pool = []

# 启用检查动态状态的定时任务
scheduler = require("nonebot_plugin_apscheduler").scheduler


# 创建用于更新数据库里面UP名称的定时任务
@scheduler.scheduled_job(
    'cron',
    # year=None,
    # month=None,
    # day='*/1',
    # week=None,
    # day_of_week=None,
    hour='3',
    minute='3',
    second='22',
    # start_date=None,
    # end_date=None,
    # timezone=None,
    id='dynamic_db_upgrade',
    coalesce=True,
    misfire_grace_time=60
)
async def dynamic_db_upgrade():
    logger.debug('dynamic_db_upgrade: started upgrade subscription info')
    sub_res = await DBSubscription.list_sub_by_type(sub_type=2)
    for sub_id in sub_res.result:
        sub = DBSubscription(sub_type=2, sub_id=sub_id)
        user_info_result = await BiliUser(user_id=sub_id).get_info()
        if user_info_result.error:
            logger.error(f'dynamic_db_upgrade: 更新用户信息失败, uid: {sub_id}, error: {user_info_result.info}')
            continue
        up_name = user_info_result.result.name
        _res = await sub.add(up_name=up_name, live_info='B站动态')
        if not _res.success():
            logger.error(f'dynamic_db_upgrade: 更新用户信息失败, uid: {sub_id}, error: {_res.info}')
            continue
    logger.debug('dynamic_db_upgrade: upgrade subscription info completed')


# 处理图片序列
async def pic_to_seg(pic_list: list) -> str:
    # 处理图片序列
    pic_segs = []
    for pic_url in pic_list:
        pic_result = await BiliRequestUtils.pic_to_file(url=pic_url)
        if pic_result.error:
            logger.warning(f'BiliDynamic get base64pic failed, error: {pic_result.info}, pic url: {pic_url}')
        pic_segs.append(str(MessageSegment.image(pic_result.result)))
    pic_seg = '\n'.join(pic_segs)
    return pic_seg


# 检查单个用户动态的函数
async def dynamic_checker(user_id: int, bots: List[Bot]):
    # 获取动态并返回动态类型及内容
    user_dynamic_result = await BiliUser(user_id=user_id).get_dynamic_history()
    if user_dynamic_result.error:
        logger.error(f'bilibili_dynamic_monitor: 获取用户 {user_id} 动态失败, error: {user_dynamic_result.info}')

    # 解析动态内容
    dynamics_data = []
    for data in user_dynamic_result.result:
        data_parse_result = BiliDynamic.data_parser(dynamic_data=data)
        if data_parse_result.error:
            logger.error(f'bilibili_dynamic_monitor: 解析新动态时发生了错误, error: {data_parse_result.info}')
            continue
        dynamics_data.append(data_parse_result)

    # 用户所有的动态id
    exist_dynamic_result = await DBDynamic.list_dynamic_by_uid(uid=user_id)
    if exist_dynamic_result.error:
        logger.error(f'bilibili_dynamic_monitor: 获取用户 {user_id} 已有动态失败, error: {exist_dynamic_result.info}')
        return
    user_dynamic_list = [int(x) for x in exist_dynamic_result.result]

    new_dynamic_data = [data for data in dynamics_data if data.result.dynamic_id not in user_dynamic_list]

    subscription = DBSubscription(sub_type=2, sub_id=user_id)

    for data in new_dynamic_data:
        dynamic_info = data.result
        dynamic_card = dynamic_info.data

        dynamic_id = dynamic_info.dynamic_id
        user_name = dynamic_info.user_name
        desc = dynamic_info.desc
        url = dynamic_info.url

        content = dynamic_card.content
        title = dynamic_card.title
        description = dynamic_card.description

        # 转发的动态
        if dynamic_info.type == 1:
            # 转发的动态还需要获取原动态信息
            orig_dy_info_result = await BiliDynamic(dynamic_id=dynamic_info.orig_dy_id).get_info()
            if orig_dy_info_result.success():
                orig_dy_data_result = BiliDynamic.data_parser(dynamic_data=orig_dy_info_result.result)
                if orig_dy_data_result.success():
                    # 原动态type=2, 8 或 4200, 带图片
                    if orig_dy_data_result.result.type in [2, 8, 4200]:
                        # 处理图片序列
                        pic_seg = await pic_to_seg(pic_list=orig_dy_data_result.result.data.pictures)
                        orig_user = orig_dy_data_result.result.user_name
                        orig_contant = orig_dy_data_result.result.data.content
                        if not orig_contant:
                            orig_contant = orig_dy_data_result.result.data.title
                        msg = f"{user_name}{desc}!\n\n“{content}”\n{url}\n{'=' * 16}\n" \
                              f"@{orig_user}: {orig_contant}\n{pic_seg}"
                    # 原动态type=32 或 512, 为番剧类型
                    elif orig_dy_data_result.result.type in [32, 512]:
                        # 处理图片序列
                        pic_seg = await pic_to_seg(pic_list=orig_dy_data_result.result.data.pictures)
                        orig_user = orig_dy_data_result.result.user_name
                        orig_title = orig_dy_data_result.result.data.title
                        msg = f"{user_name}{desc}!\n\n“{content}”\n{url}\n{'=' * 16}\n" \
                              f"@{orig_user}: {orig_title}\n{pic_seg}"
                    # 原动态为其他类型, 无图
                    else:
                        orig_user = orig_dy_data_result.result.user_name
                        orig_contant = orig_dy_data_result.result.data.content
                        if not orig_contant:
                            orig_contant = orig_dy_data_result.result.data.title
                        msg = f"{user_name}{desc}!\n\n“{content}”\n{url}\n{'=' * 16}\n" \
                              f"@{orig_user}: {orig_contant}"
                else:
                    msg = f"{user_name}{desc}!\n\n“{content}”\n{url}\n{'=' * 16}\n@Unknown: 获取原动态失败"
            else:
                msg = f"{user_name}{desc}!\n\n“{content}”\n{url}\n{'=' * 16}\n@Unknown: 获取原动态失败"
        # 原创的动态（有图片）
        elif dynamic_info.type == 2:
            # 处理图片序列
            pic_seg = await pic_to_seg(pic_list=dynamic_info.data.pictures)
            msg = f"{user_name}{desc}!\n\n“{content}”\n{url}\n{pic_seg}"
        # 原创的动态（无图片）
        elif dynamic_info.type == 4:
            msg = f"{user_name}{desc}!\n\n“{content}”\n{url}"
        # 视频
        elif dynamic_info.type == 8:
            # 处理图片序列
            pic_seg = await pic_to_seg(pic_list=dynamic_info.data.pictures)
            if content:
                msg = f"{user_name}{desc}!\n\n《{title}》\n\n“{content}”\n{url}\n{pic_seg}"
            else:
                msg = f"{user_name}{desc}!\n\n《{title}》\n\n{description}\n{url}\n{pic_seg}"
        # 小视频
        elif dynamic_info.type == 16:
            msg = f"{user_name}{desc}!\n\n“{content}”\n{url}"
        # 番剧
        elif dynamic_info.type in [32, 512]:
            # 处理图片序列
            pic_seg = await pic_to_seg(pic_list=dynamic_info.data.pictures)
            msg = f"{user_name}{desc}!\n\n《{title}》\n\n{content}\n{url}\n{pic_seg}"
        # 文章
        elif dynamic_info.type == 64:
            # 处理图片序列
            pic_seg = await pic_to_seg(pic_list=dynamic_info.data.pictures)
            msg = f"{user_name}{desc}!\n\n《{title}》\n\n{content}\n{url}\n{pic_seg}"
        # 音频
        elif dynamic_info.type == 256:
            # 处理图片序列
            pic_seg = await pic_to_seg(pic_list=dynamic_info.data.pictures)
            msg = f"{user_name}{desc}!\n\n《{title}》\n\n{content}\n{url}\n{pic_seg}"
        # B站活动相关
        elif dynamic_info.type == 2048:
            if description:
                msg = f"{user_name}{desc}!\n\n【{title} - {description}】\n\n“{content}”\n{url}"
            else:
                msg = f"{user_name}{desc}!\n\n【{title}】\n“{content}”\n\n{url}"
        else:
            logger.warning(f"未知的动态类型: {type}, id: {dynamic_id}")
            continue

        # 向群组和好友推送消息
        for _bot in bots:
            msg_sender = MsgSender(bot=_bot, log_flag='BiliDynamicNotice')
            await msg_sender.safe_broadcast_groups_subscription(subscription=subscription, message=msg)
            await msg_sender.safe_broadcast_friends_subscription(subscription=subscription, message=msg)

        # 更新动态内容到数据库
        # 向数据库中写入动态信息
        dynamic = DBDynamic(uid=user_id, dynamic_id=dynamic_id)
        _res = await dynamic.add(dynamic_type=dynamic_info.type, content=content)
        if _res.success():
            logger.info(f"向数据库写入动态信息: {dynamic_id} 成功")
        else:
            logger.error(f"向数据库写入动态信息: {dynamic_id} 失败, error: {_res.info}")


# 用于首次订阅时刷新数据库动态信息
async def init_user_dynamic(user_id: int):
    # 暂停计划任务避免中途检查更新
    scheduler.pause()
    await dynamic_checker(user_id=user_id, bots=[])
    scheduler.resume()
    logger.info(f'Init new subscription user {user_id} dynamic completed.')


# 动态检查主函数
async def bilibili_dynamic_monitor():

    logger.debug(f"bilibili_dynamic_monitor: checking started")

    # 获取当前bot列表
    bots = [bot for bot_id, bot in get_bots().items()]

    # 获取订阅表中的所有动态订阅
    sub_res = await DBSubscription.list_sub_by_type(sub_type=2)
    check_sub = [int(x) for x in sub_res.result]

    if not check_sub:
        logger.debug(f'bilibili_dynamic_monitor: no dynamic subscription, ignore.')
        return

    # 启用了检查池模式
    if ENABLE_DYNAMIC_CHECK_POOL_MODE:
        global checking_pool

        # checking_pool为空则上一轮检查完了, 重新往里面放新一轮的uid
        if not checking_pool:
            checking_pool.extend(check_sub)

        # 看下checking_pool里面还剩多少
        waiting_num = len(checking_pool)

        # 默认单次检查并发数为3, 默认检查间隔为20s
        logger.debug(f'bili dynamic pool mode debug info, B_checking_pool: {checking_pool}')
        if waiting_num >= 3:
            # 抽取检查对象
            now_checking = random.sample(checking_pool, k=3)
            # 更新checking_pool
            checking_pool = [x for x in checking_pool if x not in now_checking]
        else:
            now_checking = checking_pool.copy()
            checking_pool.clear()
        logger.debug(f'bili dynamic pool mode debug info, A_checking_pool: {checking_pool}')
        logger.debug(f'bili dynamic pool mode debug info, now_checking: {now_checking}')

        # 检查now_checking里面的直播间(异步)
        tasks = []
        for uid in now_checking:
            tasks.append(dynamic_checker(user_id=uid, bots=bots))
        try:
            await asyncio.gather(*tasks)
            logger.debug(f"bilibili_dynamic_monitor: pool mode enable, checking completed, "
                         f"checked: {', '.join([str(x) for x in now_checking])}.")
        except Exception as e:
            logger.error(f'bilibili_dynamic_monitor: pool mode enable, error occurred in checking: {repr(e)}')

    # 没有启用检查池模式
    else:
        # 检查所有在订阅表里面的动态(异步)
        tasks = []
        for uid in check_sub:
            tasks.append(dynamic_checker(user_id=uid, bots=bots))
        try:
            await asyncio.gather(*tasks)
            logger.debug(f"bilibili_dynamic_monitor: pool mode disable, checking completed, "
                         f"checked: {', '.join([str(x) for x in check_sub])}.")
        except Exception as e:
            logger.error(f'bilibili_dynamic_monitor: pool mode disable, error occurred in checking {repr(e)}')


# 根据检查池模式初始化检查时间间隔
if ENABLE_DYNAMIC_CHECK_POOL_MODE:
    # 检查池启用
    scheduler.add_job(
        bilibili_dynamic_monitor,
        'cron',
        # year=None,
        # month=None,
        # day='*/1',
        # week=None,
        # day_of_week=None,
        # hour='9-23',
        # minute='*/3',
        second='*/20',
        # start_date=None,
        # end_date=None,
        # timezone=None,
        id='bilibili_dynamic_monitor_pool_enable',
        coalesce=True,
        misfire_grace_time=20
    )
else:
    # 检查池禁用
    scheduler.add_job(
        bilibili_dynamic_monitor,
        'cron',
        # year=None,
        # month=None,
        # day='*/1',
        # week=None,
        # day_of_week=None,
        # hour=None,
        minute='*/3',
        # second='*/30',
        # start_date=None,
        # end_date=None,
        # timezone=None,
        id='bilibili_dynamic_monitor_pool_disable',
        coalesce=True,
        misfire_grace_time=30
    )

__all__ = [
    'scheduler',
    'init_user_dynamic'
]
