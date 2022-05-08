"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : utils.py
@Project        : nonebot2_miya
@Description    : Pixiv 助手
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import datetime, timedelta
from nonebot import on_command, on_shell_command, logger
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.rule import Namespace
from nonebot.exception import ParserExit
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent, GroupMessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP, GROUP_ADMIN, GROUP_OWNER, PRIVATE_FRIEND
from nonebot.adapters.onebot.v11 import MessageSegment, Message
from nonebot.params import CommandArg, ArgStr, ShellCommandArgs

from omega_miya.service import init_processor_state
from omega_miya.onebot_api import GoCqhttpBot
from omega_miya.web_resource.pixiv import PixivArtwork, PixivRanking, PixivDiscovery, PixivSearching, PixivUser
from omega_miya.utils.process_utils import run_async_catching_exception
from omega_miya.utils.message_tools import MessageSender

from .config import pixiv_plugin_config
from .utils import (has_allow_r18_node, get_artwork_preview, get_searching_argument_parser, parse_from_searching_parser,
                    add_pixiv_user_sub, delete_pixiv_user_sub, query_subscribed_user_sub_source)
from .monitor import scheduler


# Custom plugin usage text
__plugin_custom_name__ = 'Pixiv'
__plugin_usage__ = r'''【Pixiv助手】
查看Pixiv插画、发现与推荐、日榜、周榜、月榜以及搜索作品
订阅并跟踪画师作品更新

用法:
/pixiv <PID>
/pixiv推荐
/pixiv发现
/pixiv日榜 [页码]
/pixiv周榜 [页码]
/pixiv月榜 [页码]
/pixiv用户搜索 [用户昵称]
/pixiv用户作品 [UID]
/pixiv用户订阅列表
/pixiv下载 <PID> [页数]
/pixiv搜索 [关键词]

仅限私聊或群聊中群管理员使用:
/pixiv用户订阅 [UID]
/pixiv取消用户订阅 [UID]

搜索命令参数:
'-c', '--custom': 启用自定义参数
'-p', '--page': 搜索结果页码
'-o', '--order': 排序方式, 可选: "date_d", "popular_d"
'-l', '--like': 筛选最低收藏数
'-d', '--from-days-ago': 筛选作品发布日期, 从几天前起始发布的作品
'-s', '--safe-mode': NSFW 模式, 可选: "safe", "all", "r18"'''


_ALLOW_R18_NODE = pixiv_plugin_config.pixiv_plugin_allow_r18_node
"""允许预览 r18 作品的权限节点"""


pixiv = on_command(
    'Pixiv',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='Pixiv',
        level=50,
        auth_node='pixiv',
        extra_auth_node={_ALLOW_R18_NODE},
        cool_down=60,
        user_cool_down_override=2
    ),
    aliases={'pixiv'},
    permission=GROUP | PRIVATE_FRIEND,
    priority=20,
    block=True
)


@pixiv.handle()
async def handle_parse_pid(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    pid = cmd_arg.extract_plain_text().strip()
    if pid:
        state.update({'pid': pid})


@pixiv.got('pid', prompt='想要查看哪个作品呢? 请输入作品PID:')
async def handle_preview_artwork(bot: Bot, event: MessageEvent, matcher: Matcher, pid: str = ArgStr('pid')):
    pid = pid.strip()
    if not pid.isdigit():
        await matcher.reject('作品PID应当为纯数字, 请重新输入:')

    await matcher.send('稍等, 正在下载图片~')
    allow_r18 = await has_allow_r18_node(bot=bot, event=event, matcher=matcher)
    send_message, need_recall = await get_artwork_preview(pid=int(pid), allow_r18=allow_r18)
    if need_recall:
        await MessageSender(bot=bot).send_msgs_and_recall(event=event, message_list=[send_message],
                                                          recall_time=pixiv_plugin_config.pixiv_plugin_auto_recall_time)
    else:
        await matcher.finish(send_message)


pixiv_recommend = on_command(
    'PixivRecommend',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='PixivRecommend',
        level=60,
        auth_node='pixiv_recommend',
        cool_down=60,
        user_cool_down_override=2
    ),
    aliases={'pixiv推荐', 'Pixiv推荐'},
    permission=GROUP | PRIVATE_FRIEND,
    priority=20,
    block=True
)


@pixiv_recommend.handle()
async def handle_pixiv_recommend(matcher: Matcher):
    await matcher.send('稍等, 正在下载图片~')
    recommend_img = await run_async_catching_exception(PixivDiscovery.query_recommend_artworks_with_preview)()
    if isinstance(recommend_img, Exception):
        logger.error(f'PixivRecommend | 获取作品推荐(Recommend)失败, {recommend_img}')
        await matcher.finish('获取推荐作品失败了QAQ, 请稍后再试')
    else:
        await matcher.finish(MessageSegment.image(recommend_img.file_uri))


pixiv_discovery = on_command(
    'PixivDiscovery',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='PixivDiscovery',
        level=60,
        auth_node='pixiv_discovery',
        cool_down=60,
        user_cool_down_override=2
    ),
    aliases={'pixiv发现', 'Pixiv发现'},
    permission=GROUP | PRIVATE_FRIEND,
    priority=20,
    block=True
)


@pixiv_discovery.handle()
async def handle_pixiv_discovery(matcher: Matcher):
    await matcher.send('稍等, 正在下载图片~')
    discovery_img = await run_async_catching_exception(PixivDiscovery.query_discovery_artworks_with_preview)()
    if isinstance(discovery_img, Exception):
        logger.error(f'PixivDiscovery | 获取作品发现(Discovery)失败, {discovery_img}')
        await matcher.finish('获取发现作品失败了QAQ, 请稍后再试')
    else:
        await matcher.finish(MessageSegment.image(discovery_img.file_uri))


async def handle_parse_page(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    page = cmd_arg.extract_plain_text().strip()
    if page:
        state.update({'page': page})
    else:
        state.update({'page': '1'})


pixiv_daily_ranking = on_command(
    'PixivDailyRanking',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='PixivDailyRanking',
        level=50,
        auth_node='pixiv_daily_ranking',
        cool_down=60,
        user_cool_down_override=2
    ),
    aliases={'pixiv日榜', 'Pixiv日榜'},
    permission=GROUP | PRIVATE_FRIEND,
    priority=20,
    block=True
)
pixiv_daily_ranking.handle()(handle_parse_page)


@pixiv_daily_ranking.got('page', prompt='想看榜单的哪一页呢? 请输入页码:')
async def handle_daily_ranking(matcher: Matcher, page: str = ArgStr('page')):
    page = page.strip()
    if not page.isdigit():
        await matcher.reject('页码应当为纯数字, 请重新输入:')
    page = int(page)

    await matcher.send('稍等, 正在下载图片~')
    ranking_img = await run_async_catching_exception(PixivRanking.query_daily_illust_ranking_with_preview)(page=page)
    if isinstance(ranking_img, Exception):
        logger.error(f'PixivDailyRanking | 获取日榜内容(page={page})失败, {ranking_img}')
        await matcher.finish('获取日榜内容失败了QAQ, 请稍后再试')
    else:
        await matcher.finish(MessageSegment.image(ranking_img.file_uri))


pixiv_weekly_ranking = on_command(
    'PixivWeeklyRanking',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='PixivWeeklyRanking',
        level=50,
        auth_node='pixiv_weekly_ranking',
        cool_down=60,
        user_cool_down_override=2
    ),
    aliases={'pixiv周榜', 'Pixiv周榜'},
    permission=GROUP | PRIVATE_FRIEND,
    priority=20,
    block=True
)
pixiv_weekly_ranking.handle()(handle_parse_page)


@pixiv_weekly_ranking.got('page', prompt='想看榜单的哪一页呢? 请输入页码:')
async def handle_weekly_ranking(matcher: Matcher, page: str = ArgStr('page')):
    page = page.strip()
    if not page.isdigit():
        await matcher.reject('页码应当为纯数字, 请重新输入:')
    page = int(page)

    await matcher.send('稍等, 正在下载图片~')
    ranking_img = await run_async_catching_exception(PixivRanking.query_weekly_illust_ranking_with_preview)(page=page)
    if isinstance(ranking_img, Exception):
        logger.error(f'PixivWeeklyRanking | 获取周榜内容(page={page})失败, {ranking_img}')
        await matcher.finish('获取周榜内容失败了QAQ, 请稍后再试')
    else:
        await matcher.finish(MessageSegment.image(ranking_img.file_uri))


pixiv_monthly_ranking = on_command(
    'PixivMonthlyRanking',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='PixivMonthlyRanking',
        level=50,
        auth_node='pixiv_monthly_ranking',
        cool_down=60,
        user_cool_down_override=2
    ),
    aliases={'pixiv月榜', 'Pixiv月榜'},
    permission=GROUP | PRIVATE_FRIEND,
    priority=20,
    block=True
)
pixiv_monthly_ranking.handle()(handle_parse_page)


@pixiv_monthly_ranking.got('page', prompt='想看榜单的哪一页呢? 请输入页码:')
async def handle_monthly_ranking(matcher: Matcher, page: str = ArgStr('page')):
    page = page.strip()
    if not page.isdigit():
        await matcher.reject('页码应当为纯数字, 请重新输入:')
    page = int(page)

    await matcher.send('稍等, 正在下载图片~')
    ranking_img = await run_async_catching_exception(PixivRanking.query_monthly_illust_ranking_with_preview)(page=page)
    if isinstance(ranking_img, Exception):
        logger.error(f'PixivMonthlyRanking | 获取月榜内容(page={page})失败, {ranking_img}')
        await matcher.finish('获取月榜内容失败了QAQ, 请稍后再试')
    else:
        await matcher.finish(MessageSegment.image(ranking_img.file_uri))


pixiv_searching = on_shell_command(
    'PixivSearching',
    parser=get_searching_argument_parser(),
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='PixivSearching',
        level=50,
        auth_node='pixiv_searching',
        extra_auth_node={_ALLOW_R18_NODE},
        cool_down=60,
        user_cool_down_override=2
    ),
    aliases={'pixiv搜索', 'Pixiv搜索'},
    permission=GROUP | PRIVATE_FRIEND,
    priority=20,
    block=True
)


@pixiv_searching.handle()
async def handle_parse_failed(matcher: Matcher, args: ParserExit = ShellCommandArgs()):
    """解析命令失败"""
    await matcher.finish('命令格式错误QAQ\n' + args.message)


@pixiv_searching.handle()
async def handle_parse_success(bot: Bot, event: MessageEvent, matcher: Matcher, args: Namespace = ShellCommandArgs()):
    """解析命令成功"""
    args = parse_from_searching_parser(args=args)

    allow_r18 = await has_allow_r18_node(bot=bot, event=event, matcher=matcher)
    nsfw_mode = args.safe_mode
    if args.safe_mode in ['all', 'r18'] and not allow_r18:
        nsfw_mode = 'safe'

    word = ' '.join(args.word)
    await matcher.send(f'搜索Pixiv作品: {word}')
    blt = args.like if args.like > 0 else None
    scd = datetime.now() - timedelta(days=args.from_days_ago) if args.from_days_ago > 0 else None

    if args.custom:
        search_preview_img = await run_async_catching_exception(PixivSearching.search_with_preview)(
            word=word, mode=args.mode, page=args.page, order=args.order, mode_=nsfw_mode, blt_=blt, scd_=scd)
    else:
        search_preview_img = await run_async_catching_exception(
            PixivSearching.search_by_default_popular_condition_with_preview)(word=word)

    if isinstance(search_preview_img, Exception):
        logger.error(f'PixivSearching | 获取搜索内容({args})失败, {search_preview_img}')
        await matcher.finish('获取搜索内容失败了QAQ, 请稍后再试')

    send_message = MessageSegment.image(search_preview_img.file_uri)
    if nsfw_mode == 'safe':
        await matcher.finish(send_message)
    else:
        await MessageSender(bot=bot).send_msgs_and_recall(event=event, message_list=[send_message],
                                                          recall_time=pixiv_plugin_config.pixiv_plugin_auto_recall_time)


pixiv_download = on_command(
    'PixivDownload',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='PixivDownload',
        level=50,
        auth_node='pixiv_download',
        extra_auth_node={_ALLOW_R18_NODE},
        cool_down=60,
        user_cool_down_override=2
    ),
    aliases={'pixiv下载', 'Pixiv下载', 'pixivdl'},
    permission=GROUP,
    priority=20,
    block=True
)


@pixiv_download.handle()
async def handle_parse_download_args(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    cmd_args = cmd_arg.extract_plain_text().strip().split()
    arg_num = len(cmd_args)
    match arg_num:
        case 1:
            state.update({'pid': cmd_args[0], 'page': '1'})
        case 2:
            state.update({'pid': cmd_args[0], 'page': cmd_args[1]})
        case _:
            state.update({'page': '1'})


@pixiv_download.got('pid', prompt='想要下载哪个作品呢? 请输入作品PID:')
@pixiv_download.got('page', prompt='想要下载作品的哪一页呢? 请输入页码:')
async def handle_download(bot: Bot, event: GroupMessageEvent, matcher: Matcher,
                          pid: str = ArgStr('pid'), page: str = ArgStr('page')):
    pid = pid.strip()
    page = page.strip()
    if not pid.isdigit():
        await matcher.reject_arg(key='pid', prompt='作品PID应当为纯数字, 请重新输入:')
    if not page.isdigit():
        await matcher.reject_arg(key='page', prompt='页码应当是大于1的整数, 请重新输入:')

    pid = int(pid)
    page = int(page) - 1

    artwork = PixivArtwork(pid=pid)
    artwork_data = await run_async_catching_exception(artwork.get_artwork_model)()
    if isinstance(artwork_data, Exception):
        logger.error(f'PixivDownload | 获取作品(pid={pid})信息失败, {artwork_data}')
        await matcher.finish('获取作品信息失败了QAQ, 可能是网络原因或者作品已经被删除, 请稍后再试')

    if page not in range(artwork_data.page_count):
        await matcher.finish('请求的页码超出了作品的图片数QAQ')

    allow_r18 = await has_allow_r18_node(bot=bot, event=event, matcher=matcher)
    if artwork_data.is_r18 and not allow_r18:
        await matcher.finish('没有下载涩涩作品的权限, 不准涩涩!')

    await matcher.send('稍等, 正在下载图片~')
    download_file = await artwork.download_page(page=page)
    if isinstance(download_file, Exception):
        logger.error(f'PixivDownload | 下载作品(pid={pid})失败, {download_file}')
        await matcher.finish('下载作品失败了QAQ, 可能是网络原因导致的, 请稍后再试')

    gocq_bot = GoCqhttpBot(bot=bot)
    file_name = f'{artwork_data.pid}_p{page}_{artwork_data.title}_{artwork_data.uname}{download_file.path.suffix}'
    upload_result = await run_async_catching_exception(gocq_bot.upload_group_file)(
        group_id=event.group_id, file=download_file.resolve_path, name=file_name)
    if isinstance(upload_result, Exception):
        logger.warning(f'PixivDownload | 下载作品(pid={pid})失败, 上传群文件失败: {upload_result}')
        await matcher.finish('上传图片到群文件失败QAQ, 可能上传仍在进行中, 请等待1~2分钟后再重试')


pixiv_user_searching = on_command(
    'PixivUserSearching',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='PixivUserSearching',
        level=50,
        auth_node='pixiv_user_searching',
        cool_down=60,
        user_cool_down_override=2
    ),
    aliases={'pixiv用户搜索', 'Pixiv用户搜索'},
    permission=GROUP | PRIVATE_FRIEND,
    priority=20,
    block=True
)


@pixiv_user_searching.handle()
async def handle_parse_user_nick(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    user_nick = cmd_arg.extract_plain_text().strip()
    if user_nick:
        state.update({'user_nick': user_nick})


@pixiv_user_searching.got('user_nick', prompt='请输入想要搜索的Pixiv用户名:')
async def handle_preview_user(matcher: Matcher, user_nick: str = ArgStr('user_nick')):
    user_nick = user_nick.strip()
    await matcher.send(f'搜索Pixiv用户: {user_nick}')
    searching_image = await run_async_catching_exception(PixivUser.search_user_with_preview)(nick=user_nick)
    if isinstance(searching_image, Exception):
        logger.error(f'PixivUserSearching | 获取用户(nick={user_nick})搜索结果失败, {searching_image}')
        await matcher.finish('搜索用户失败了QAQ, 请稍后再试')
    else:
        await matcher.finish(MessageSegment.image(searching_image.file_uri))


pixiv_user_artworks = on_command(
    'PixivUserArtworks',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='PixivUserArtworks',
        level=50,
        auth_node='pixiv_user_artworks',
        cool_down=60,
        user_cool_down_override=2
    ),
    aliases={'pixiv用户作品', 'Pixiv用户作品'},
    permission=GROUP | PRIVATE_FRIEND,
    priority=20,
    block=True
)


@pixiv_user_artworks.handle()
async def handle_parse_user_id(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    user_id = cmd_arg.extract_plain_text().strip()
    if user_id:
        state.update({'user_id': user_id})


@pixiv_user_artworks.got('user_id', prompt='请输入用户的UID:')
async def handle_preview_user_artworks(matcher: Matcher, user_id: str = ArgStr('user_id')):
    user_id = user_id.strip()
    if not user_id.isdigit():
        await matcher.reject('用户UID应当为纯数字, 请重新输入:')

    await matcher.send('稍等, 正在下载图片~')
    preview_image = await PixivUser(uid=int(user_id)).query_user_artworks_with_preview()
    if isinstance(preview_image, Exception):
        logger.error(f'PixivUserArtworks | 获取用户(uid={user_id})作品失败, {preview_image}')
        await matcher.finish('获取用户作品失败了QAQ, 请稍后再试')
    else:
        await matcher.finish(MessageSegment.image(preview_image.file_uri))


pixiv_add_user_subscription = on_command(
    'PixivAddUserSubscription',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='AddPixivUserSubscription',
        level=50,
        auth_node='pixiv_add_user_subscription',
        cool_down=20,
        user_cool_down_override=2
    ),
    aliases={'pixiv用户订阅', 'Pixiv用户订阅'},
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND,
    priority=20,
    block=True
)


@pixiv_add_user_subscription.handle()
async def handle_parse_user_id(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    user_id = cmd_arg.extract_plain_text().strip()
    if user_id:
        state.update({'user_id': user_id})


@pixiv_add_user_subscription.got('user_id', prompt='请输入用户的UID:')
async def handle_check_add_user_id(matcher: Matcher, user_id: str = ArgStr('user_id')):
    user_id = user_id.strip()
    if not user_id.isdigit():
        await matcher.reject('用户UID应当为纯数字, 请重新输入:')

    user = PixivUser(uid=int(user_id))
    user_data = await run_async_catching_exception(user.get_user_model)()
    if isinstance(user_data, Exception):
        logger.error(f'PixivAddUserSubscription | 获取用户(uid={user_id})失败, {user_data}')
        await matcher.finish('获取用户信息失败了QAQ, 可能是网络原因或没有这个用户, 请稍后再试')

    await matcher.send(f'即将订阅Pixiv用户【{user_data.name}】的作品!')


@pixiv_add_user_subscription.got('check', prompt='确认吗?\n\n【是/否】')
async def handle_add_user_subscription(bot: Bot, matcher: Matcher, event: MessageEvent, state: T_State,
                                       check: str = ArgStr('check')):
    check = check.strip()
    if check != '是':
        await matcher.finish('那就不订阅了哦')
    await matcher.send('正在更新Pixiv用户订阅信息, 请稍候')
    user_id = state.get('user_id')

    user = PixivUser(uid=int(user_id))
    scheduler.pause()  # 暂停计划任务避免中途检查更新
    add_sub_result = await add_pixiv_user_sub(bot=bot, event=event, pixiv_user=user)
    scheduler.resume()

    if isinstance(add_sub_result, Exception) or add_sub_result.error:
        logger.error(f"PixivAddUserSubscription | 订阅用户(uid={user_id})失败, {add_sub_result}")
        await matcher.finish(f'订阅失败了QAQ, 可能是网络异常或发生了意外的错误, 请稍后重试或联系管理员处理')
    else:
        logger.success(f"PixivAddUserSubscription | 订阅用户(uid={user_id})成功")
        await matcher.finish(f'订阅成功!')


pixiv_delete_user_subscription = on_command(
    'PixivDeleteUserSubscription',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='DeletePixivUserSubscription',
        level=50,
        auth_node='pixiv_delete_user_subscription',
        cool_down=20,
        user_cool_down_override=2
    ),
    aliases={'pixiv取消用户订阅', 'Pixiv取消用户订阅'},
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND,
    priority=20,
    block=True
)


@pixiv_delete_user_subscription.handle()
async def handle_parse_user_id(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    user_id = cmd_arg.extract_plain_text().strip()
    if user_id:
        state.update({'user_id': user_id})


@pixiv_delete_user_subscription.got('user_id', prompt='请输入用户的UID:')
async def handle_delete_user_sub(bot: Bot, event: MessageEvent, matcher: Matcher, user_id: str = ArgStr('user_id')):
    user_id = user_id.strip()
    if not user_id.isdigit():
        await matcher.reject('用户UID应当为纯数字, 请重新输入:')

    exist_sub = await query_subscribed_user_sub_source(bot=bot, event=event)
    if isinstance(exist_sub, Exception):
        logger.error(f'PixivDeleteUserSubscription | 获取({event})已订阅用户失败, {exist_sub}')
        await matcher.finish('获取已订阅列表失败QAQ, 请稍后再试或联系管理员处理')

    for sub in exist_sub:
        if user_id == sub[0]:
            user_nick = sub[1]
            break
    else:
        exist_text = '\n'.join(f'{x[0]}: {x[1]}' for x in exist_sub)
        await matcher.reject(f'当前没有订阅这个用户哦, 请在已订阅列表中选择并重新输入用户UID:\n\n{exist_text}')
        return

    delete_result = await delete_pixiv_user_sub(bot=bot, event=event, user_id=user_id)
    if isinstance(delete_result, Exception) or delete_result.error:
        logger.error(f"PixivDeleteUserSubscription | 取消订阅用户(uid={user_id})失败, {delete_result}")
        await matcher.finish(f'取消订阅失败了QAQ, 发生了意外的错误, 请联系管理员处理')
    else:
        logger.success(f"PixivDeleteUserSubscription | 取消订阅用户(uid={user_id})成功")
        await matcher.finish(f'已取消Pixiv用户【{user_nick}】的订阅!')


pixiv_list_user_subscription = on_command(
    'PixivListUserSubscription',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='ListPixivUserSubscription',
        level=50,
        auth_node='pixiv_list_user_subscription',
        cool_down=60,
        user_cool_down_override=2
    ),
    aliases={'pixiv用户订阅列表', 'Pixiv用户订阅列表'},
    permission=GROUP | PRIVATE_FRIEND,
    priority=20,
    block=True
)


@pixiv_list_user_subscription.handle()
async def handle_list_subscription(bot: Bot, event: MessageEvent, matcher: Matcher):
    exist_sub = await query_subscribed_user_sub_source(bot=bot, event=event)
    if isinstance(exist_sub, Exception):
        logger.error(f'PixivListUserSubscription | 获取({event})已订阅用户失败, {exist_sub}')
        await matcher.finish('获取订阅列表失败QAQ, 请稍后再试或联系管理员处理')

    exist_text = '\n'.join(f'{x[0]}: {x[1]}' for x in exist_sub)
    await matcher.finish(f'当前已订阅的Pixiv用户列表:\n\n{exist_text}')
