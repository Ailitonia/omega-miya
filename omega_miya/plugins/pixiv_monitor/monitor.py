"""
@Author         : Ailitonia
@Date           : 2021/06/01 22:28
@FileName       : monitor.py
@Project        : nonebot2_miya 
@Description    : Pixiv User Monitor
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import asyncio
import random
from nonebot import logger, require, get_bots, get_driver
from nonebot.adapters.cqhttp import MessageSegment, Message
from omega_miya.database import DBSubscription, DBPixivUserArtwork
from omega_miya.utils.pixiv_utils import PixivUser, PixivIllust
from omega_miya.utils.omega_plugin_utils import MsgSender, PicEffector, PicEncoder, ProcessUtils
from .config import Config


__global_config = get_driver().config
plugin_config = Config(**__global_config.dict())
ENABLE_CHECK_POOL_MODE = plugin_config.enable_check_pool_mode


# 检查队列
CHECKING_POOL = []


# 启用检查Pixiv用户作品状态的定时任务
scheduler = require("nonebot_plugin_apscheduler").scheduler


# 创建用于更新数据库里面画师名称的定时任务
@scheduler.scheduled_job(
    'cron',
    # year=None,
    # month=None,
    # day='*/1',
    # week=None,
    # day_of_week=None,
    hour='1',
    minute='15',
    second='50',
    # start_date=None,
    # end_date=None,
    # timezone=None,
    id='pixiv_user_db_upgrade',
    coalesce=True,
    misfire_grace_time=60
)
async def dynamic_db_upgrade():
    logger.debug('pixiv_user_db_upgrade: started upgrade subscription info')
    sub_res = await DBSubscription.list_sub_by_type(sub_type=9)
    for sub_id in sub_res.result:
        sub = DBSubscription(sub_type=9, sub_id=sub_id)
        user_info_result = await PixivUser(uid=int(sub_id)).get_info()
        if user_info_result.error:
            logger.error(f'pixiv_user_db_upgrade: 获取用户信息失败, uid: {sub_id}, error: {user_info_result.info}')
            continue
        user_name = user_info_result.result.get('name')
        _res = await sub.add(up_name=user_name, live_info='Pixiv用户作品订阅')
        if not _res.success():
            logger.error(f'pixiv_user_db_upgrade: 更新用户信息失败, uid: {sub_id}, error: {_res.info}')
            continue
    logger.debug('pixiv_user_db_upgrade: upgrade subscription info completed')


# 创建Pixiv用户作品检查函数
@scheduler.scheduled_job(
    'cron',
    # year=None,
    # month=None,
    # day='*/1',
    # week=None,
    # day_of_week=None,
    # hour=None,
    minute='*/5',
    # second='*/30',
    # start_date=None,
    # end_date=None,
    # timezone=None,
    id='pixiv_user_artwork_monitor',
    coalesce=True,
    misfire_grace_time=30
)
async def pixiv_user_artwork_monitor():
    logger.debug(f"pixiv_user_artwork_monitor: checking started")

    # 获取当前bot列表
    bots = [bot for bot_id, bot in get_bots().items()]

    # 获取订阅表中的所有Pixiv用户订阅
    sub_res = await DBSubscription.list_sub_by_type(sub_type=9)
    check_sub = [int(x) for x in sub_res.result]

    if not check_sub:
        logger.debug(f'pixiv_user_artwork_monitor: no dynamic subscription, ignore.')
        return

    # 注册一个异步函数用于检查Pixiv用户作品
    async def check_user_artwork(user_id: int):
        # 获取pixiv用户作品内容
        user_artwork_result = await PixivUser(uid=user_id).get_artworks_info()
        if user_artwork_result.error:
            logger.error(f'pixiv_user_artwork_monitor: 获取用户 {user_id} 作品失败, error: {user_artwork_result.info}')

        all_artwork_list = user_artwork_result.result.get('illust_list')
        manga_list = user_artwork_result.result.get('manga_list')
        all_artwork_list.extend(manga_list)

        # 用户所有的作品id
        exist_artwork_result = await DBPixivUserArtwork.list_artwork_by_uid(uid=user_id)
        if exist_artwork_result.error:
            logger.error(f'pixiv_user_artwork_monitor: 获取用户 {user_id} 已有作品失败, error: {exist_artwork_result.info}')
            return
        exist_artwork_list = [int(x) for x in exist_artwork_result.result]

        new_artwork = [pid for pid in all_artwork_list if pid not in exist_artwork_list]

        subscription = DBSubscription(sub_type=9, sub_id=str(user_id))

        for pid in new_artwork:
            illust = PixivIllust(pid=pid)
            illust_info_result = await illust.get_illust_data()
            if illust_info_result.error:
                logger.error(f'pixiv_user_artwork_monitor: 获取用户 {user_id} 作品 {pid} 信息失败, '
                             f'error: {illust_info_result.info}')
                continue

            uname = illust_info_result.result.get('uname')
            title = illust_info_result.result.get('title')
            is_r18 = illust_info_result.result.get('is_r18')

            # 下载图片
            illust_info_msg_result = await illust.get_format_info_msg()
            illust_pic_bytes_result = await illust.get_bytes()
            if illust_pic_bytes_result.error or illust_info_msg_result.error:
                logger.error(f'pixiv_user_artwork_monitor: 下载用户 {user_id} 作品 {pid} 失败, '
                             f'error: {illust_info_msg_result.info} // {illust_pic_bytes_result.info}.')
                continue

            if is_r18:
                # 添加图片处理模块, 模糊后发送
                blur_img_result = await PicEffector(image=illust_pic_bytes_result.result).gaussian_blur()
                b64_img_result = await PicEncoder.bytes_to_file(
                    image=blur_img_result.result, folder_flag='pixiv_monitor')
                img_seg = MessageSegment.image(b64_img_result.result)
            else:
                b64_img_result = await PicEncoder.bytes_to_file(
                    image=illust_pic_bytes_result.result, folder_flag='pixiv_monitor')
                img_seg = MessageSegment.image(b64_img_result.result)

            intro_msg = f'【Pixiv】{uname}发布了新的作品!\n\n'
            info_msg = illust_info_msg_result.result
            msg = Message(intro_msg).append(img_seg).append(info_msg)

            # 向群组和好友推送消息
            for _bot in bots:
                msg_sender = MsgSender(bot=_bot, log_flag='PixivUserArtworkNotice')
                await msg_sender.safe_broadcast_groups_subscription(subscription=subscription, message=msg)
                # await msg_sender.safe_broadcast_friends_subscription(subscription=subscription, message=msg)

            # 更新作品内容到数据库
            pixiv_user_artwork = DBPixivUserArtwork(pid=pid, uid=user_id)
            _res = await pixiv_user_artwork.add(uname=uname, title=title)
            if _res.success():
                logger.info(f'向数据库写入pixiv用户作品信息: {pid} 成功')
            else:
                logger.error(f'向数据库写入pixiv用户作品信息: {pid} 失败, error: {_res.info}')

    # 启用了检查池模式
    if ENABLE_CHECK_POOL_MODE:
        global CHECKING_POOL
        # checking_pool为空则上一轮检查完了, 重新往里面放新一轮的uid
        if not CHECKING_POOL:
            CHECKING_POOL.extend(check_sub)

        # 看下checking_pool里面还剩多少
        waiting_num = len(CHECKING_POOL)

        # 默认单次检查并发数为50, 默认检查间隔为5min
        logger.debug(f'Pixiv user artwork checker pool mode debug info, Before checking_pool: {CHECKING_POOL}')
        if waiting_num >= 50:
            # 抽取检查对象
            now_checking = random.sample(CHECKING_POOL, k=50)
            # 更新checking_pool
            CHECKING_POOL = [x for x in CHECKING_POOL if x not in now_checking]
        else:
            now_checking = CHECKING_POOL.copy()
            CHECKING_POOL.clear()
        logger.debug(f'Pixiv user artwork checker pool mode debug info, After checking_pool: {CHECKING_POOL}')
        logger.debug(f'Pixiv user artwork checker pool mode debug info, now_checking: {now_checking}')

        # 检查now_checking里面的直播间(异步)
        tasks = []
        for uid in now_checking:
            tasks.append(check_user_artwork(user_id=uid))
        try:
            await asyncio.gather(*tasks)
            logger.debug(f"pixiv_user_artwork_monitor: pool mode enable, checking completed, "
                         f"checked: {', '.join([str(x) for x in now_checking])}.")
        except Exception as e:
            logger.error(f'pixiv_user_artwork_monitor: error occurred in checking {repr(e)}')

    # 没有启用检查池模式
    else:
        # 检查所有在订阅表里面的画师作品(异步)
        tasks = []
        for uid in check_sub:
            tasks.append(check_user_artwork(user_id=uid))
        try:
            await asyncio.gather(*tasks)
            logger.debug(f"pixiv_user_artwork_monitor: pool mode disable, checking completed, "
                         f"checked: {', '.join([str(x) for x in check_sub])}.")
        except Exception as e:
            logger.error(f'pixiv_user_artwork_monitor: error occurred in checking {repr(e)}')


# 用于首次订阅时刷新数据库信息
async def init_new_add_sub(user_id: int):
    # 暂停计划任务避免中途检查更新
    scheduler.pause()
    try:
        # 获取pixiv用户作品内容
        user_artwork_result = await PixivUser(uid=user_id).get_artworks_info()
        if user_artwork_result.error:
            logger.error(f'init_new_add_sub: 获取用户 {user_id} 作品失败, error: {user_artwork_result.info}')

        all_artwork_list = user_artwork_result.result.get('illust_list')
        manga_list = user_artwork_result.result.get('manga_list')
        all_artwork_list.extend(manga_list)

        async def _handle(pid_: int):
            illust = PixivIllust(pid=pid_)
            illust_info_result = await illust.get_illust_data()
            if illust_info_result.error:
                logger.error(f'init_new_add_sub: 获取用户 {user_id} 作品 {pid_} 信息失败, error: {illust_info_result.info}')
                return

            uname = illust_info_result.result.get('uname')
            title = illust_info_result.result.get('title')

            # 更新作品内容到数据库
            pixiv_user_artwork = DBPixivUserArtwork(pid=pid_, uid=user_id)
            _res = await pixiv_user_artwork.add(uname=uname, title=title)
            if _res.success():
                logger.debug(f'向数据库写入pixiv用户作品信息: {pid_} 成功')
            else:
                logger.error(f'向数据库写入pixiv用户作品信息: {pid_} 失败, error: {_res.info}')

        # 开始导入操作
        # 全部一起并发网络撑不住, 做适当切分
        tasks = [_handle(pid_=pid) for pid in all_artwork_list]
        await ProcessUtils.fragment_process(tasks=tasks, fragment_size=50, log_flag='Init Pixiv User Illust')
        logger.info(f'初始化pixiv用户 {user_id} 作品完成, 已将作品信息写入数据库.')
    except Exception as e:
        logger.error(f'初始化pixiv用户 {user_id} 作品发生错误, error: {repr(e)}.')

    scheduler.resume()


__all__ = [
    'scheduler',
    'init_new_add_sub'
]
