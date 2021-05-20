import asyncio
import random
from nonebot import logger, require, get_bots, get_driver
from nonebot.adapters.cqhttp import MessageSegment
from omega_miya.utils.Omega_Base import DBFriend, DBSubscription, DBDynamic, DBTable
from omega_miya.utils.bilibili_utils import BiliUser, BiliDynamic, BiliRequestUtils
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
    t = DBTable(table_name='Subscription')
    sub_res = await t.list_col_with_condition('sub_id', 'sub_type', 2)
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


# 创建动态检查函数
async def bilibili_dynamic_monitor():

    logger.debug(f"bilibili_dynamic_monitor: checking started")

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

    # 获取订阅表中的所有动态订阅
    t = DBTable(table_name='Subscription')
    sub_res = await t.list_col_with_condition('sub_id', 'sub_type', 2)
    check_sub = [int(x) for x in sub_res.result]

    if not check_sub:
        logger.debug(f'bilibili_dynamic_monitor: no dynamic subscription, ignore.')
        return

    # 处理图片序列
    async def pic2base64(pic_list: list) -> str:
        # 处理图片序列
        pic_segs = []
        for pic_url in pic_list:
            pic_result = await BiliRequestUtils.pic_2_base64(url=pic_url)
            pic_b64 = pic_result.result
            pic_segs.append(str(MessageSegment.image(pic_b64)))
        pic_seg = '\n'.join(pic_segs)
        return pic_seg

    # 注册一个异步函数用于检查动态
    async def check_dynamic(user_id: int):
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
        dynamic_table = DBTable(table_name='Bilidynamic')
        exist_dynamic_result = await dynamic_table.list_col_with_condition('dynamic_id', 'uid', user_id)
        if exist_dynamic_result.error:
            logger.error(f'bilibili_dynamic_monitor: 获取用户 {user_id} 已有动态失败, error: {exist_dynamic_result.info}')
            return
        user_dynamic_list = [int(x) for x in exist_dynamic_result.result]

        new_dynamic_data = [data for data in dynamics_data if data.result.dynamic_id not in user_dynamic_list]

        sub = DBSubscription(sub_type=2, sub_id=user_id)

        # 获取订阅了该直播间的所有群
        sub_group_res = await sub.sub_group_list()
        sub_group = sub_group_res.result
        # 需通知的群
        notice_groups = list(set(all_noitce_groups) & set(sub_group))

        # 获取订阅了该直播间的所有好友
        sub_friend_res = await sub.sub_user_list()
        sub_friend = sub_friend_res.result
        # 需通知的好友
        notice_friends = list(set(all_noitce_friends) & set(sub_friend))

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
                        # 原动态type=2 或 8, 带图片
                        if orig_dy_data_result.result.type in [2, 8]:
                            # 处理图片序列
                            pic_seg = await pic2base64(pic_list=orig_dy_data_result.result.data.pictures)
                            orig_user = orig_dy_data_result.result.user_name
                            orig_contant = orig_dy_data_result.result.data.content
                            msg = f"{user_name}{desc}!\n\n“{content}”\n{url}\n{'=' * 16}\n" \
                                  f"@{orig_user}: {orig_contant}\n{pic_seg}"
                        # 原动态为其他类型, 无图
                        else:
                            orig_user = orig_dy_data_result.result.user_name
                            orig_contant = orig_dy_data_result.result.data.content
                            msg = f"{user_name}{desc}!\n\n“{content}”\n{url}\n{'=' * 16}\n" \
                                  f"@{orig_user}: {orig_contant}"
                    else:
                        msg = f"{user_name}{desc}!\n\n“{content}”\n{url}\n{'=' * 16}\n@Unknown: 获取原动态失败"
                else:
                    msg = f"{user_name}{desc}!\n\n“{content}”\n{url}\n{'=' * 16}\n@Unknown: 获取原动态失败"
            # 原创的动态（有图片）
            elif dynamic_info.type == 2:
                # 处理图片序列
                pic_seg = await pic2base64(pic_list=dynamic_info.data.pictures)
                msg = f"{user_name}{desc}!\n\n“{content}”\n{url}\n{pic_seg}"
            # 原创的动态（无图片）
            elif dynamic_info.type == 4:
                msg = f"{user_name}{desc}!\n\n“{content}”\n{url}"
            # 视频
            elif dynamic_info.type == 8:
                # 处理图片序列
                pic_seg = await pic2base64(pic_list=dynamic_info.data.pictures)
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
                pic_seg = await pic2base64(pic_list=dynamic_info.data.pictures)
                msg = f"{user_name}{desc}!\n\n《{title}》\n\n{content}\n{url}\n{pic_seg}"
            # 文章
            elif dynamic_info.type == 64:
                # 处理图片序列
                pic_seg = await pic2base64(pic_list=dynamic_info.data.pictures)
                msg = f"{user_name}{desc}!\n\n《{title}》\n\n{content}\n{url}\n{pic_seg}"
            # 音频
            elif dynamic_info.type == 256:
                # 处理图片序列
                pic_seg = await pic2base64(pic_list=dynamic_info.data.pictures)
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

            # 向群组发送消息
            for group_id in notice_groups:
                for _bot in bots:
                    try:
                        await _bot.call_api(api='send_group_msg', group_id=group_id, message=msg)
                        logger.info(f"向群组: {group_id} 发送新动态通知: {dynamic_id}")
                    except Exception as _e:
                        logger.warning(f"向群组: {group_id} 发送新动态通知: {dynamic_id} 失败, error: {repr(_e)}")
                        continue
            # 向好友发送消息
            for friend_user_id in notice_friends:
                for _bot in bots:
                    try:
                        await _bot.call_api(api='send_private_msg', user_id=friend_user_id, message=msg)
                        logger.info(f"向好友: {friend_user_id} 发送新动态通知: {dynamic_id}")
                    except Exception as _e:
                        logger.warning(f"向好友: {friend_user_id} 发送新动态通知: {dynamic_id} 失败, error: {repr(_e)}")
                        continue

            # 更新动态内容到数据库
            # 向数据库中写入动态信息
            dynamic = DBDynamic(uid=user_id, dynamic_id=dynamic_id)
            _res = await dynamic.add(dynamic_type=dynamic_info.type, content=content)
            if _res.success():
                logger.info(f"向数据库写入动态信息: {dynamic_id} 成功")
            else:
                logger.error(f"向数据库写入动态信息: {dynamic_id} 失败, error: {_res.info}")

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
            tasks.append(check_dynamic(uid))
        try:
            await asyncio.gather(*tasks)
            logger.debug(f"bilibili_dynamic_monitor: pool mode enable, checking completed, "
                         f"checked: {', '.join([str(x) for x in now_checking])}.")
        except Exception as e:
            logger.error(f'bilibili_dynamic_monitor: pool mode enable, error occurred in checking: {repr(e)}')

    # 没有启用检查池模式
    else:
        # 检查所有在订阅表里面的直播间(异步)
        tasks = []
        for uid in check_sub:
            tasks.append(check_dynamic(uid))
        try:
            await asyncio.gather(*tasks)
            logger.debug(f"bilibili_dynamic_monitor: pool mode disable, checking completed, "
                         f"checked: {', '.join([str(x) for x in check_sub])}.")
        except Exception as e:
            logger.error(f'bilibili_dynamic_monitor: pool mode disable, error occurred in checking  {repr(e)}')


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
    'scheduler'
]
