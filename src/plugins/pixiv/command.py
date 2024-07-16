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
from typing import Annotated, Callable, Coroutine, Literal

from nonebot.matcher import Matcher
from nonebot.log import logger
from nonebot.params import ArgStr, Depends, ShellCommandArgs
from nonebot.plugin import CommandGroup
from nonebot.rule import Namespace
from nonebot.typing import T_State

from src.params.handler import (get_command_str_single_arg_parser_handler,
                                get_command_str_multi_args_parser_handler,
                                get_set_default_state_handler,
                                get_shell_command_parse_failed_handler)
from src.params.permission import IS_ADMIN
from src.resource import TemporaryResource
from src.service import OmegaInterface, OmegaMessageSegment, enable_processor_state
from src.utils.pixiv_api import PixivArtwork, PixivUser
from src.utils.pixiv_api.helper import parse_pid_from_url

from .config import pixiv_plugin_config
from .consts import ALLOW_R18_NODE
from .helpers import (has_allow_r18_node, get_artwork_preview,
                      get_searching_argument_parser, parse_from_searching_parser,
                      add_pixiv_user_sub, delete_pixiv_user_sub,
                      query_entity_subscribed_user_sub_source)
from .monitor import scheduler


pixiv = CommandGroup(
    'pixiv',
    priority=10,
    block=True,
    state=enable_processor_state(
        name='Pixiv',
        level=50,
        auth_node='pixiv',
        extra_auth_node={ALLOW_R18_NODE},
        cooldown=60
    ),
)


@pixiv.command(
    tuple(),
    aliases={'Pixiv'},
    handlers=[get_command_str_single_arg_parser_handler('pid')],
).got('pid', prompt='想要查看哪个作品呢? 请输入作品PID:')
async def handle_preview_artwork(
        matcher: Matcher,
        interface: Annotated[OmegaInterface, Depends(OmegaInterface())],
        pid: Annotated[str, ArgStr('pid')]
) -> None:
    interface.refresh_matcher_state()

    pid = pid.strip()
    if not pid.isdigit():
        await interface.finish('作品PID应当为纯数字, 请确认后再重试吧')

    await interface.send_reply('稍等, 正在下载图片~')

    try:
        artwork = PixivArtwork(pid=int(pid))
        is_r18 = (await artwork.query_artwork()).is_r18
        allow_r18 = await has_allow_r18_node(matcher=matcher, interface=interface)
        send_message = await get_artwork_preview(artwork=artwork, allow_r18=allow_r18)

        if is_r18 and allow_r18:
            await interface.send_msg_auto_revoke(message=send_message,
                                                 revoke_interval=pixiv_plugin_config.pixiv_plugin_auto_recall_time)
        else:
            await interface.send(message=send_message)
    except Exception as e:
        logger.error(f'Pixiv | 获取作品(pid={pid})预览失败, {e}')
        await interface.send_reply(message='获取作品失败了QAQ, 可能是网络原因或者作品已经被删除, 请稍后再试')


@pixiv.command(
    'recommend',
    aliases={'pixiv推荐', 'Pixiv推荐'},
    handlers=[get_command_str_single_arg_parser_handler('source', ensure_key=True)],
).got('source')
async def handle_pixiv_recommend(
        interface: Annotated[OmegaInterface, Depends(OmegaInterface())],
        source: Annotated[str | None, ArgStr('source')]
) -> None:
    interface.refresh_interface_state()

    recommend_pid: int | None = None
    if source is not None:
        if source.isdigit():
            recommend_pid = int(source)
        elif pid := parse_pid_from_url(text=source, url_mode=False):
            recommend_pid = int(pid)
    else:
        if reply_msg_test := interface.get_event_handler().get_reply_msg_plain_text():
            if pid := parse_pid_from_url(text=reply_msg_test, url_mode=False):
                recommend_pid = int(pid)

    await interface.send_reply('稍等, 正在下载图片~')

    try:
        if recommend_pid:
            recommend_img = await PixivArtwork(pid=recommend_pid).query_recommend_with_preview()
        else:
            recommend_img = await PixivArtwork.query_recommend_artworks_with_preview()
        await interface.send(OmegaMessageSegment.image(recommend_img.path))
    except Exception as e:
        logger.error(f'PixivRecommend | 获取作品推荐({source})失败, {e}')
        await interface.send_reply('获取推荐作品失败了QAQ, 请稍后再试')


@pixiv.command(
    'discovery',
    aliases={'pixiv发现', 'Pixiv发现'},
).handle()
async def handle_pixiv_discovery(interface: Annotated[OmegaInterface, Depends(OmegaInterface())]):
    interface.refresh_matcher_state()

    await interface.send_reply('稍等, 正在下载图片~')

    try:
        discovery_img = await PixivArtwork.query_discovery_artworks_with_preview()
        await interface.send(OmegaMessageSegment.image(discovery_img.path))
    except Exception as e:
        logger.error(f'PixivDiscovery | 获取作品发现(Discovery)失败, {e}')
        await interface.send_reply('获取发现作品失败了QAQ, 请稍后再试')


async def _handle_ranking(
        interface: OmegaInterface,
        page: str,
        ranking_preview_factory: Callable[[int], Coroutine[None, None, TemporaryResource]]
) -> None:
    interface.refresh_interface_state()

    page = page.strip()
    if not page.isdigit():
        await interface.finish('榜单页码应当为纯数字, 请确认后再重试吧')

    await interface.send_reply('稍等, 正在下载图片~')

    try:
        ranking_img = await ranking_preview_factory(int(page))
        await interface.send(OmegaMessageSegment.image(ranking_img.path))
    except Exception as e:
        logger.error(f'PixivRanking | 获取榜单内容(page={ranking_preview_factory!r})失败, {e}')
        await interface.send_reply('获取榜单内容失败了QAQ, 请稍后再试')


@pixiv.command(
    'daily-ranking',
    aliases={'pixiv日榜', 'Pixiv日榜'},
    handlers=[get_command_str_single_arg_parser_handler('page', default='1')],
).got('page', prompt='想看榜单的哪一页呢? 请输入页码:')
async def handle_daily_ranking(
        interface: Annotated[OmegaInterface, Depends(OmegaInterface())],
        page: Annotated[str, ArgStr('page')]
) -> None:
    await _handle_ranking(
        interface=interface,
        page=page,
        ranking_preview_factory=PixivArtwork.query_daily_illust_ranking_with_preview
    )


@pixiv.command(
    'weekly-ranking',
    aliases={'pixiv周榜', 'Pixiv周榜'},
    handlers=[get_command_str_single_arg_parser_handler('page', default='1')],
).got('page', prompt='想看榜单的哪一页呢? 请输入页码:')
async def handle_daily_ranking(
        interface: Annotated[OmegaInterface, Depends(OmegaInterface())],
        page: Annotated[str, ArgStr('page')]
) -> None:
    await _handle_ranking(
        interface=interface,
        page=page,
        ranking_preview_factory=PixivArtwork.query_weekly_illust_ranking_with_preview
    )


@pixiv.command(
    'monthly-ranking',
    aliases={'pixiv月榜', 'Pixiv月榜'},
    handlers=[get_command_str_single_arg_parser_handler('page', default='1')],
).got('page', prompt='想看榜单的哪一页呢? 请输入页码:')
async def handle_daily_ranking(
        interface: Annotated[OmegaInterface, Depends(OmegaInterface())],
        page: Annotated[str, ArgStr('page')]
) -> None:
    await _handle_ranking(
        interface=interface,
        page=page,
        ranking_preview_factory=PixivArtwork.query_monthly_illust_ranking_with_preview
    )


@pixiv.shell_command(
    'searching',
    aliases={'pixiv搜索', 'Pixiv搜索'},
    parser=get_searching_argument_parser(),
    handlers=[get_shell_command_parse_failed_handler()],
).handle()
async def handle_pixiv_searching(
        matcher: Matcher,
        interface: Annotated[OmegaInterface, Depends(OmegaInterface())],
        args: Annotated[Namespace, ShellCommandArgs()]
) -> None:
    searching_args = parse_from_searching_parser(args=args)
    interface.refresh_matcher_state()

    allow_r18 = await has_allow_r18_node(matcher=matcher, interface=interface)
    nsfw_mode = searching_args.safe_mode
    if not allow_r18:
        nsfw_mode: Literal['safe', 'all', 'r18'] = 'safe'

    word = ' '.join(searching_args.word)
    await interface.send_reply(f'搜索Pixiv作品: {word}')

    blt = searching_args.like if searching_args.like > 0 else None
    scd = datetime.now() - timedelta(days=searching_args.from_days_ago) if searching_args.from_days_ago > 0 else None

    try:
        if searching_args.custom:
            search_preview_img = await PixivArtwork.search_with_preview(
                word=word, mode=searching_args.mode, page=searching_args.page,
                order=searching_args.order, mode_=nsfw_mode, ai_type=searching_args.ai_type, blt_=blt, scd_=scd
            )
        else:
            search_preview_img = await PixivArtwork.search_by_default_popular_condition_with_preview(word=word)

        if nsfw_mode == 'safe':
            await interface.send(OmegaMessageSegment.image(search_preview_img.path))
        else:
            await interface.send_msg_auto_revoke(OmegaMessageSegment.image(search_preview_img.path))
    except Exception as e:
        logger.error(f'PixivSearching | 获取搜索内容({searching_args})失败, {e}')
        await interface.send_reply('获取搜索内容失败了QAQ, 请稍后再试')


@pixiv.command(
    'user-searching',
    aliases={'pixiv用户搜索', 'Pixiv用户搜索', 'pixiv画师搜索', 'Pixiv画师搜索'},
    handlers=[get_command_str_single_arg_parser_handler('user_nick')],
).got('user_nick', prompt='请输入想要搜索的Pixiv用户名:')
async def handle_searching_user(
        interface: Annotated[OmegaInterface, Depends(OmegaInterface())],
        user_nick: Annotated[str, ArgStr('user_nick')]
) -> None:
    interface.refresh_matcher_state()
    user_nick = user_nick.strip()

    await interface.send_reply(f'搜索Pixiv用户: {user_nick}')

    try:
        searching_image = await PixivUser.search_user_with_preview(nick=user_nick)
        await interface.send(OmegaMessageSegment.image(searching_image.path))
    except Exception as e:
        logger.error(f'PixivUserSearching | 获取用户(nick={user_nick})搜索结果失败, {e}')
        await interface.send_reply('搜索用户失败了QAQ, 请稍后再试')


@pixiv.command(
    'user-artworks',
    aliases={'pixiv用户作品', 'Pixiv用户作品', 'pixiv画师作品', 'Pixiv画师作品'},
    handlers=[get_command_str_multi_args_parser_handler('user_id_page')],
).got('user_id_page_0', prompt='请输入用户的UID:')
async def handle_preview_user_artworks(
        interface: Annotated[OmegaInterface, Depends(OmegaInterface())],
        user_id: Annotated[str, ArgStr('user_id_page_0')],
        state: T_State
) -> None:
    interface.refresh_matcher_state()

    user_id = user_id.strip()
    if not user_id.isdigit():
        await interface.finish('用户UID应当为纯数字, 请确认后再重试吧')

    page = str(state.get('user_id_page_1', 1))
    if not page.isdigit():
        await interface.finish('页码应当为纯数字, 请确认后再重试吧')

    await interface.send_reply('稍等, 正在下载图片~')

    try:
        preview_image = await PixivUser(uid=int(user_id)).query_user_artworks_with_preview(page=int(page))
        await interface.send(OmegaMessageSegment.image(preview_image.path))
    except Exception as e:
        logger.error(f'PixivUserArtworks | 获取用户(uid={user_id})作品失败, {e}')
        await interface.send_reply('获取用户作品失败了QAQ, 请稍后再试')


@pixiv.command(
    'user-bookmark',
    aliases={'pixiv用户收藏', 'Pixiv用户收藏'},
    handlers=[get_command_str_multi_args_parser_handler('user_id_page', ensure_keys_num=2)],
).handle()
async def handle_preview_user_bookmark(
        interface: Annotated[OmegaInterface, Depends(OmegaInterface())],
        state: T_State
) -> None:
    interface.refresh_matcher_state()

    user_id = state.get('user_id_page_0')
    if user_id is None:
        try:
            bot_owner_user_data = await PixivArtwork.query_global_data()
            user_id = bot_owner_user_data.uid
        except Exception as e:
            logger.debug(f'PixivUserBookmark | 获取 Bot 所有者用户信息失败, 未配置或 cookies 失效, {e}')
    user_id = str(user_id)
    if not user_id.isdigit():
        await interface.finish('用户UID应当为纯数字, 请确认后再重试吧')

    page = state.get('user_id_page_1')
    page = '1' if page is None else str(page)
    if not page.isdigit():
        await interface.finish('页码应当为纯数字, 请确认后再重试吧')

    await interface.send_reply('稍等, 正在下载图片~')

    try:
        preview_image = await PixivUser(uid=int(user_id)).query_user_bookmarks_with_preview(page=int(page))
        await interface.send(OmegaMessageSegment.image(preview_image.path))
    except Exception as e:
        logger.error(f'PixivUserBookmark | 获取用户(uid={user_id})收藏失败, {e}')
        await interface.send_reply('获取用户收藏失败了QAQ, 请稍后再试')


pixiv_subscription = CommandGroup(
    'pixiv-subscription',
    permission=IS_ADMIN,
    priority=20,
    block=True,
    state=enable_processor_state(name='PixivSubscriptionManager', level=30),
)


@pixiv_subscription.command(
    'add-subscription',
    aliases={'pixiv用户订阅', 'Pixiv用户订阅'},
    handlers=[
        get_set_default_state_handler('ensure', value=None),
        get_command_str_single_arg_parser_handler('user_id', ensure_key=True)
    ]
).got('ensure')
async def handle_add_subscription(
        interface: Annotated[OmegaInterface, Depends(OmegaInterface())],
        ensure: Annotated[str | None, ArgStr('ensure')],
        user_id: Annotated[str | None, ArgStr('user_id')]
) -> None:
    interface.refresh_matcher_state()

    # 检查是否收到确认消息后执行新增订阅
    if ensure is None:
        pass
    elif ensure in ['是', '确认', 'Yes', 'yes', 'Y', 'y']:
        await interface.send_reply('正在更新Pixiv用户订阅信息, 若首次订阅可能需要较长时间更新用户作品信息, 请稍候')

        user = PixivUser(uid=int(user_id))
        scheduler.pause()  # 暂停计划任务避免中途检查更新
        try:
            await add_pixiv_user_sub(interface=interface, pixiv_user=user)
            await interface.entity.commit_session()
            logger.success(f"PixivAddUserSubscription | {interface.entity}订阅用户(uid={user_id})成功")
            msg = f'订阅Pixiv用户{user_id}成功'
        except Exception as e:
            logger.error(f"PixivAddUserSubscription | {interface.entity}订阅用户(uid={user_id})失败, {e!r}")
            msg = f'订阅Pixiv用户{user_id}失败, 可能是网络异常或发生了意外的错误, 请稍后重试或联系管理员处理'
        scheduler.resume()
        await interface.send_reply(msg)
        return
    else:
        await interface.send_reply('已取消操作')
        return

    # 未收到确认消息后则为首次触发命令执行获取用户信息
    if user_id is None:
        await interface.send_reply('未提供用户UID参数, 已取消操作')
        return
    uid = user_id.strip()
    if not uid.isdigit():
        await interface.send_reply('非有效的用户UID, 用户UID应当为纯数字, 已取消操作')
        return

    try:
        user = PixivUser(uid=int(user_id))
        user_data = await user.query_user_data()
    except Exception as e:
        logger.error(f'PixivAddUserSubscription | 获取用户(uid={user_id})数据失败, {e}')
        await interface.send_reply('获取用户信息失败了QAQ, 可能是网络原因或没有这个用户, 请稍后再试')
        return

    ensure_msg = f'即将订阅Pixiv用户【{user_data.name}】的作品\n\n确认吗?\n【是/否】'
    await interface.reject_arg_reply('ensure', ensure_msg)


@pixiv_subscription.command(
    'del-subscription',
    aliases={'pixiv取消用户订阅', 'Pixiv取消用户订阅'},
    handlers=[
        get_set_default_state_handler('ensure', value=None),
        get_command_str_single_arg_parser_handler('user_id', ensure_key=True)
    ]
).got('ensure')
async def handle_del_subscription(
        interface: Annotated[OmegaInterface, Depends(OmegaInterface())],
        ensure: Annotated[str | None, ArgStr('ensure')],
        user_id: Annotated[str | None, ArgStr('user_id')]
) -> None:
    interface.refresh_matcher_state()

    # 检查是否收到确认消息后执行删除订阅
    if ensure is None:
        pass
    elif ensure in ['是', '确认', 'Yes', 'yes', 'Y', 'y']:
        try:
            await delete_pixiv_user_sub(interface=interface, uid=int(user_id))
            await interface.entity.commit_session()
            logger.success(f'PixivDeleteUserSubscription | {interface.entity}取消订阅用户(uid={user_id})成功')
            msg = f'取消订阅Pixiv用户{user_id}成功!'
        except Exception as e:
            logger.error(f'PixivDeleteUserSubscription | {interface.entity}取消订阅用户(uid={user_id})失败, {e!r}')
            msg = f'取消订阅Pixiv用户{user_id}失败, 请稍后再试或联系管理员处理'
        await interface.send_reply(msg)
        return
    else:
        await interface.send_reply('已取消操作')
        return

    # 未收到确认消息后则为首次触发命令执行获取用户信息
    if user_id is None:
        await interface.send_reply('未提供用户UID参数, 已取消操作')
        return
    user_id = user_id.strip()
    if not user_id.isdigit():
        await interface.send_reply('非有效的用户UID, 用户UID应当为纯数字, 已取消操作')
        return

    try:
        exist_sub = await query_entity_subscribed_user_sub_source(interface=interface)
        if user_id in exist_sub.keys():
            ensure_msg = f'取消订阅Pixiv用户【{exist_sub.get(user_id)}】的作品\n\n确认吗?\n【是/否】'
            reject_key = 'ensure'
        else:
            exist_text = '\n'.join(f'{sub_id}: {user_nickname}' for sub_id, user_nickname in exist_sub.items())
            ensure_msg = f'未订阅用户{user_id}, 请确认已订阅的用户动态列表:\n\n{exist_text if exist_text else "无"}'
            reject_key = None
    except Exception as e:
        logger.error(f'PixivDeleteUserSubscription | 获取{interface}已订阅用户失败, {e!r}')
        await interface.send_reply('获取已订阅Pixiv用户列表失败, 请稍后再试或联系管理员处理')
        return

    await interface.send_reply(ensure_msg)
    if reject_key is not None:
        await interface.matcher.reject_arg(reject_key)
    else:
        await interface.matcher.finish()


@pixiv_subscription.command(
    'list-subscription',
    aliases={'pixiv用户订阅列表', 'Pixiv用户订阅列表'},
    permission=None,
    priority=10
).handle()
async def handle_list_subscription(interface: Annotated[OmegaInterface, Depends(OmegaInterface())]) -> None:
    interface.refresh_matcher_state()

    try:
        exist_sub = await query_entity_subscribed_user_sub_source(interface=interface)
        exist_text = '\n'.join(f'{sub_id}: {user_nickname}' for sub_id, user_nickname in exist_sub.items())
        await interface.send_reply(f'当前已订阅的Pixiv用户列表:\n\n{exist_text if exist_text else "无"}')
    except Exception as e:
        logger.error(f'PixivListUserSubscription | 获取{interface.entity}已订阅的Pixiv用户列表, {e!r}')
        await interface.send_reply('获取已订阅的Pixiv用户列表失败, 请稍后再试或联系管理员处理')


__all__ = []
