"""
各类bot后台任务
"""
import nonebot
from nonebot import logger, require
from omega_miya.utils.Omega_Base import DBBot, DBBotGroup, DBUser, DBFriend, DBStatus, DBCoolDownEvent
from omega_miya.utils.Omega_plugin_utils import HttpFetcher

global_config = nonebot.get_driver().config
ENABLE_PROXY = global_config.enable_proxy
PROXY_CHECK_URL = global_config.proxy_check_url
PROXY_CHECK_TIMEOUT = global_config.proxy_check_timeout

# 获取scheduler
scheduler = require("nonebot_plugin_apscheduler").scheduler

logger.opt(colors=True).debug('<lg>初始化 Omega 后台任务...</lg>')


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
    logger.debug('refresh_group_info: Start task')
    from nonebot import get_bots

    for bot_id, bot in get_bots().items():
        self_bot = DBBot(self_qq=int(bot.self_id))
        group_list = await bot.call_api('get_group_list')

        # 首先获取所有群组列表 禁用不在的群组
        exist_group_result = await DBBotGroup.list_exist_bot_groups(self_bot=self_bot)
        exist_group_list = [int(x) for x in exist_group_result.result]

        actual_group_list = [int(x.get('group_id')) for x in group_list]
        disable_group_list = list(set(exist_group_list).difference(set(actual_group_list)))

        for group in disable_group_list:
            disable_result = await DBBotGroup(group_id=group, self_bot=self_bot).\
                permission_set(notice=-1, command=-1, level=-1)
            if disable_result.error:
                logger.warning(f'Disable expire group {group} failed, {disable_result.info}')

        # 执行群组信息更新
        for group in group_list:
            group_id = group.get('group_id')
            # 调用api获取群信息
            group_info = await bot.call_api(api='get_group_info', group_id=group_id)
            group_name = group_info['group_name']
            group_memo = group_info.get('group_memo')
            group = DBBotGroup(group_id=group_id, self_bot=self_bot)

            # 更新群信息
            add_group_res = await group.add(name=group_name)
            if add_group_res.error:
                logger.error(f'Add group {group_id} failed, {add_group_res.info}')
                continue
            set_bot_group_res = await group.set_bot_group(group_memo=group_memo)
            if set_bot_group_res.error:
                logger.error(f'Add group {group_id} failed, {set_bot_group_res.info}')
                continue

            # 更新用户
            group_member_list = await bot.call_api(api='get_group_member_list', group_id=group_id)

            # 首先清除数据库中退群成员
            exist_member_list = [int(x.get('user_id')) for x in group_member_list]
            member_res = await group.member_list()
            db_member_list = [user_id for user_id, nickname in member_res.result]
            del_member_list = list(set(db_member_list).difference(set(exist_member_list)))

            for user_id in del_member_list:
                await group.member_del(user=DBUser(user_id=user_id))

            # 更新群成员
            for user_info in group_member_list:
                # 用户信息
                user_qq = user_info.get('user_id')
                user_nickname = user_info.get('nickname')
                user_group_nickmane = user_info.get('card')
                if not user_group_nickmane:
                    user_group_nickmane = user_nickname
                _user = DBUser(user_id=user_qq)
                _result = await _user.add(nickname=user_nickname)
                if not _result.success():
                    logger.warning(f'Refresh group info, Add group user: {user_qq}, {_result.info}')
                    continue
                _result = await group.member_add(user=_user, user_group_nickname=user_group_nickmane)
                if not _result.success():
                    logger.warning(f'Refresh group info, Upgrade group user: {user_qq}, {_result.info}')

            await group.init_member_status()
            logger.info(f'Refresh group info completed, Bot: {bot_id}, Group: {group_id}')
    logger.debug('refresh_group_info: Task finish')


# 创建自动更新好友信息的定时任务
@scheduler.scheduled_job(
    'cron',
    # year=None,
    # month=None,
    # day='*/1',
    # week=None,
    # day_of_week=None,
    hour='*/1',
    # minute='*/1',
    # second='*/10',
    # start_date=None,
    # end_date=None,
    # timezone=None,
    id='refresh_friends_info',
    coalesce=True,
    misfire_grace_time=120
)
async def refresh_friends_info():
    logger.debug('refresh_friends_info: Start task')
    from nonebot import get_bots

    for bot_id, bot in get_bots().items():
        self_bot = DBBot(self_qq=int(bot.self_id))
        friends_list = await bot.call_api('get_friend_list')
        # 首先清除非好友
        exist_friend_result = await DBFriend.list_exist_friends(self_bot=self_bot)
        if exist_friend_result.error:
            logger.error(f'Refresh friends info failed, get exist friend list failed: {exist_friend_result.info}')
            return

        exist_friend_list = exist_friend_result.result
        actual_friend_list = [int(x.get('user_id')) for x in friends_list]
        del_member_list = list(set(exist_friend_list).difference(set(actual_friend_list)))

        for user in del_member_list:
            del_result = await DBFriend(user_id=user, self_bot=self_bot).del_friend()
            if del_result.error:
                logger.warning(f'Del expire friend user {user} failed, {del_result.info}')

        # 更新好友信息
        for friend in friends_list:
            user_id = int(friend.get('user_id'))
            nickname = friend.get('nickname')
            remark = friend.get('remark')

            friend = DBFriend(user_id=user_id, self_bot=self_bot)
            # 更新用户表
            add_user_result = await friend.add(nickname=nickname)
            if add_user_result.error:
                logger.error(f'Add user {user_id} failed, {add_user_result.info}')
                continue

            # 更新好友表
            add_friend_result = await friend.set_friend(nickname=nickname, remark=remark)
            if add_friend_result.error:
                logger.error(f'Add friend user {user_id} failed, {add_user_result.info}')

            logger.debug(f'Refresh friends info, upgrade friend user {user_id} info')

        logger.info(f'Refresh friends info completed, Bot: {bot_id}')
    logger.debug('refresh_friends_info: Task finish')


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
async def cool_down_refresh():
    await DBCoolDownEvent.clear_time_out_event()
    logger.debug('cool_down_refresh: cleaning time out event')


# 创建用于检查代理可用性的状态的定时任务
if ENABLE_PROXY:
    logger.opt(colors=True).info('<ly>HTTP 代理:</ly> <lg>已启用!</lg>')

    # 检查代理可用性的状态的任务
    @scheduler.scheduled_job(
        'cron',
        # year=None,
        # month=None,
        # day=None,
        # week=None,
        # day_of_week=None,
        # hour=None,
        minute='*/1',
        # second=None,
        # start_date=None,
        # end_date=None,
        # timezone=None,
        id='check_proxy',
        coalesce=True,
        misfire_grace_time=20
    )
    async def check_proxy():
        timeout = 5
        test_url = 'https://api.bilibili.com/x/web-interface/nav'
        headers = {'accept': 'application/json; charset=utf-8',
                   'accept-encoding': 'gzip, deflate',
                   'accept-language': 'zh-CN,zh;q=0.9',
                   'origin': 'https://www.bilibili.com',
                   'referer': 'https://www.bilibili.com/',
                   'sec-ch-ua': '"Google Chrome";v="89", "Chromium";v="89", ";Not A Brand";v="99"',
                   'sec-ch-ua-mobile': '?0',
                   'sec-fetch-dest': 'empty',
                   'sec-fetch-mode': 'cors',
                   'sec-fetch-site': 'same-site',
                   'sec-gpc': '1',
                   'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                 'Chrome/89.0.4389.114 Safari/537.36'
                   }

        if PROXY_CHECK_URL and type(PROXY_CHECK_URL) == str:
            test_url = str(PROXY_CHECK_URL)
            headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/89.0.4389.114 Safari/537.36'}

        if PROXY_CHECK_TIMEOUT and type(PROXY_CHECK_TIMEOUT) == int:
            timeout = PROXY_CHECK_TIMEOUT

        fetcher = HttpFetcher(timeout=timeout, flag='Omega_proxy_test', headers=headers)
        fetcher_result = await fetcher.get_text(url=test_url, force_proxy=True)

        if fetcher_result.success() and fetcher_result.status == 200:
            db_res = await DBStatus(name='PROXY_AVAILABLE').set_status(status=1, info='代理可用')
            logger.opt(colors=True).info(f'代理检查: <g>成功! status: {fetcher_result.status}</g>, DB info: {db_res.info}')
        else:
            db_res = await DBStatus(name='PROXY_AVAILABLE').set_status(status=0, info='代理不可用')
            logger.opt(colors=True).error(f'代理检查: <r>失败! status: {fetcher_result.status}, '
                                          f'info: {fetcher_result.info}</r>, DB info: {db_res.info}')

    # 初始化任务加入启动序列
    nonebot.get_driver().on_startup(check_proxy)

    logger.opt(colors=True).debug('后台任务: <lg>check_proxy</lg>, <ly>已启用!</ly>')
else:
    logger.opt(colors=True).info('<ly>HTTP 代理:</ly> <lr>已禁用!</lr>')


__all__ = [
    'scheduler'
]
