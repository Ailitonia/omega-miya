"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : utils.py
@Project        : nonebot2_miya
@Description    : Pixiv 用户作品助手
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Annotated

from nonebot.log import logger
from nonebot.params import ArgStr, Depends
from nonebot.plugin import CommandGroup
from nonebot.typing import T_State

from src.params.handler import (
    get_command_str_single_arg_parser_handler,
    get_command_str_multi_args_parser_handler,
    get_set_default_state_handler,
)
from src.params.permission import IS_ADMIN
from src.service import OmegaMatcherInterface as OmMI, OmegaMessageSegment, enable_processor_state
from src.utils.pixiv_api import PixivUser
from .helpers import (
    add_pixiv_user_sub,
    delete_pixiv_user_sub,
    query_entity_subscribed_pixiv_user_sub_source,
    generate_artworks_preview,
    get_ranking_preview_factory,
    handle_ranking_preview,
)
from .monitor import scheduler

pixiv_artist = CommandGroup(
    'pixiv-artist',
    priority=10,
    block=True,
    state=enable_processor_state(
        name='PixivArtist',
        level=30,
        auth_node='pixiv_artist',
        cooldown=60
    ),
)


@pixiv_artist.command(
    'daily-ranking',
    aliases={'pixiv用户日榜', 'Pixiv用户日榜'},
    handlers=[get_command_str_single_arg_parser_handler('page', default='1')],
).got('page', prompt='想看榜单的哪一页呢? 请输入页码:')
async def handle_daily_ranking(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        page: Annotated[str, ArgStr('page')],
) -> None:
    await handle_ranking_preview(
        interface=interface,
        page=page,
        ranking_preview_factory=get_ranking_preview_factory(mode='daily')
    )


@pixiv_artist.command(
    'weekly-ranking',
    aliases={'pixiv用户周榜', 'Pixiv用户周榜'},
    handlers=[get_command_str_single_arg_parser_handler('page', default='1')],
).got('page', prompt='想看榜单的哪一页呢? 请输入页码:')
async def handle_weekly_ranking(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        page: Annotated[str, ArgStr('page')],
) -> None:
    await handle_ranking_preview(
        interface=interface,
        page=page,
        ranking_preview_factory=get_ranking_preview_factory(mode='weekly')
    )


@pixiv_artist.command(
    'monthly-ranking',
    aliases={'pixiv用户月榜', 'Pixiv用户月榜'},
    handlers=[get_command_str_single_arg_parser_handler('page', default='1')],
).got('page', prompt='想看榜单的哪一页呢? 请输入页码:')
async def handle_monthly_ranking(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        page: Annotated[str, ArgStr('page')],
) -> None:
    await handle_ranking_preview(
        interface=interface,
        page=page,
        ranking_preview_factory=get_ranking_preview_factory(mode='monthly')
    )


@pixiv_artist.command(
    'searching',
    aliases={'pixiv用户搜索', 'Pixiv用户搜索', 'pixiv画师搜索', 'Pixiv画师搜索'},
    handlers=[get_command_str_single_arg_parser_handler('user_nick')],
).got('user_nick', prompt='请输入想要搜索的Pixiv用户名:')
async def handle_searching_user(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        user_nick: Annotated[str, ArgStr('user_nick')],
) -> None:
    user_nick = user_nick.strip()
    try:
        searching_result = await PixivUser.search_user(nick=user_nick)

        message_prefix = f'【Pixiv用户搜索结果: {user_nick}】'
        result_message = f'\n{"-" * 6 + "+" + "-" * 6 + "+" + "-" * 6}\n'.join(
            f'UID: {x.user_id} | {x.user_name}\n{'用户无自我介绍' if x.user_desc is None else x.user_desc}'
            for x in searching_result.users
        )
        await interface.send_reply(f'{message_prefix}\n\n{result_message}')
    except Exception as e:
        logger.error(f'PixivUserSearching | 获取用户(nick={user_nick})搜索结果失败, {e}')
        await interface.send_reply('搜索用户失败, 请稍后再试或联系管理员处理')


@pixiv_artist.command(
    'user-artworks',
    aliases={'pixiv用户作品', 'Pixiv用户作品', 'pixiv画师作品', 'Pixiv画师作品'},
    handlers=[get_command_str_multi_args_parser_handler('user_id_page')],
).got('user_id_page_0', prompt='请输入用户的UID:')
async def handle_preview_user_artworks(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        user_id: Annotated[str, ArgStr('user_id_page_0')],
        state: T_State,
) -> None:
    user_id = user_id.strip()
    if not user_id.isdigit():
        await interface.finish_reply('用户UID应当为纯数字, 请确认后再重试吧')
    uid = int(user_id)

    page_str = str(state.get('user_id_page_1', 1))
    if not page_str.isdigit():
        await interface.finish_reply('页码应当为纯数字, 请确认后再重试吧')
    page = int(page_str)

    await interface.send_reply('稍等, 正在获取用户作品~')

    try:
        user_data = await PixivUser(uid=uid).query_user_data()
        p_start = 48 * (page - 1)
        p_end = 48 * page

        title = f'Pixiv User Artwork - {user_data.name}'
        preview_image = await generate_artworks_preview(title=title, pids=user_data.manga_illusts[p_start:p_end])

        await interface.send_reply(OmegaMessageSegment.image(preview_image.path))
    except Exception as e:
        logger.error(f'PixivUserArtworks | 获取用户(uid={user_id})作品失败, {e}')
        await interface.send_reply('获取用户作品失败了QAQ, 请稍后再试')


@pixiv_artist.command(
    'user-bookmark',
    aliases={'pixiv用户收藏', 'Pixiv用户收藏'},
    handlers=[get_command_str_multi_args_parser_handler('user_id_page', ensure_keys_num=2)],
).handle()
async def handle_preview_user_bookmark(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        state: T_State,
) -> None:
    user_id = state.get('user_id_page_0')

    # 为空则获取当前登录账号的收藏
    if user_id is None:
        try:
            bot_owner_user_data = await PixivUser.query_global_data()
            user_id = bot_owner_user_data.uid
        except Exception as e:
            logger.debug(f'PixivUserBookmark | 获取 Bot 所有者用户信息失败, 未配置或 cookies 失效, {e}')

    user_id = str(user_id)
    if not user_id.isdigit():
        await interface.finish('用户UID应当为纯数字, 请确认后再重试吧')
    uid = int(user_id)

    page_str = state.get('user_id_page_1')
    page_str = '1' if page_str is None else str(page_str)
    if not page_str.isdigit():
        await interface.finish('页码应当为纯数字, 请确认后再重试吧')
    page = int(page_str)

    await interface.send_reply('稍等, 正在获取用户收藏~')

    try:
        user_bookmark_data = await PixivUser(uid=uid).query_user_bookmarks(page=page)

        title = f'Pixiv User Bookmark - {uid}'
        preview_image = await generate_artworks_preview(title=title, pids=user_bookmark_data.illust_ids)

        await interface.send_reply(OmegaMessageSegment.image(preview_image.path))
    except Exception as e:
        logger.error(f'PixivUserBookmark | 获取用户(uid={user_id})收藏失败, {e}')
        await interface.send_reply('获取用户收藏失败了QAQ, 请稍后再试')


pixiv_artist_subscription = CommandGroup(
    'pixiv_artist_subscription',
    permission=IS_ADMIN,
    priority=20,
    block=True,
    state=enable_processor_state(name='PixivArtistSubscriptionManager', level=30),
)


@pixiv_artist_subscription.command(
    'add-subscription',
    aliases={'pixiv用户订阅', 'Pixiv用户订阅'},
    handlers=[
        get_set_default_state_handler('ensure', value=None),
        get_command_str_single_arg_parser_handler('user_id', ensure_key=True)
    ]
).got('ensure')
async def handle_add_subscription(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        ensure: Annotated[str | None, ArgStr('ensure')],
        user_id: Annotated[str | None, ArgStr('user_id')],
) -> None:
    # 检查是否收到确认消息后执行新增订阅
    if ensure is None or user_id is None:
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
        await interface.finish_reply(msg)
    else:
        await interface.finish_reply('已取消操作')

    # 未收到确认消息后则为首次触发命令执行获取用户信息
    if user_id is None:
        await interface.finish_reply('未提供用户UID参数, 已取消操作')
    uid = user_id.strip()
    if not uid.isdigit():
        await interface.finish_reply('非有效的用户UID, 用户UID应当为纯数字, 已取消操作')

    try:
        user = PixivUser(uid=int(user_id))
        user_data = await user.query_user_data()
    except Exception as e:
        logger.error(f'PixivAddUserSubscription | 获取用户(uid={user_id})数据失败, {e}')
        await interface.finish_reply('获取用户信息失败了QAQ, 可能是网络原因或没有这个用户, 请稍后再试')

    ensure_msg = f'即将订阅Pixiv用户【{user_data.name}】的作品\n\n确认吗?\n【是/否】'
    await interface.reject_arg_reply('ensure', ensure_msg)


@pixiv_artist_subscription.command(
    'del-subscription',
    aliases={'取消pixiv用户订阅', '取消Pixiv用户订阅'},
    handlers=[
        get_set_default_state_handler('ensure', value=None),
        get_command_str_single_arg_parser_handler('user_id', ensure_key=True)
    ]
).got('ensure')
async def handle_del_subscription(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        ensure: Annotated[str | None, ArgStr('ensure')],
        user_id: Annotated[str | None, ArgStr('user_id')]
) -> None:
    # 检查是否收到确认消息后执行删除订阅
    if ensure is None or user_id is None:
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
        await interface.finish_reply(msg)
    else:
        await interface.finish_reply('已取消操作')

    # 未收到确认消息后则为首次触发命令执行获取用户信息
    if user_id is None:
        await interface.finish_reply('未提供用户UID参数, 已取消操作')
    user_id = user_id.strip()
    if not user_id.isdigit():
        await interface.finish_reply('非有效的用户UID, 用户UID应当为纯数字, 已取消操作')

    try:
        exist_sub = await query_entity_subscribed_pixiv_user_sub_source(interface=interface)
        if user_id in exist_sub.keys():
            ensure_msg = f'取消订阅Pixiv用户【{exist_sub.get(user_id)}】的作品\n\n确认吗?\n【是/否】'
            reject_key = 'ensure'
        else:
            exist_text = '\n'.join(f'{sub_id}: {user_nickname}' for sub_id, user_nickname in exist_sub.items())
            ensure_msg = f'未订阅用户{user_id}, 请确认已订阅的用户动态列表:\n\n{exist_text if exist_text else "无"}'
            reject_key = None
    except Exception as e:
        logger.error(f'PixivDeleteUserSubscription | 获取{interface}已订阅用户失败, {e!r}')
        await interface.finish_reply('获取已订阅Pixiv用户列表失败, 请稍后再试或联系管理员处理')

    await interface.send_reply(ensure_msg)
    if reject_key is not None:
        await interface.matcher.reject_arg(reject_key)
    else:
        await interface.matcher.finish()


@pixiv_artist_subscription.command(
    'list-subscription',
    aliases={'pixiv用户订阅列表', 'Pixiv用户订阅列表'},
    permission=None,
    priority=10
).handle()
async def handle_list_subscription(interface: Annotated[OmMI, Depends(OmMI.depend())]) -> None:
    try:
        exist_sub = await query_entity_subscribed_pixiv_user_sub_source(interface=interface)
        exist_text = '\n'.join(f'{sub_id}: {user_nickname}' for sub_id, user_nickname in exist_sub.items())
        await interface.send_reply(f'当前已订阅的Pixiv用户列表:\n\n{exist_text if exist_text else "无"}')
    except Exception as e:
        logger.error(f'PixivListUserSubscription | 获取{interface.entity}已订阅的Pixiv用户列表, {e!r}')
        await interface.send_reply('获取已订阅的Pixiv用户列表失败, 请稍后再试或联系管理员处理')


__all__ = []
