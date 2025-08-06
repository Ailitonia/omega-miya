"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : utils.py
@Project        : nonebot2_miya
@Description    : Pixiv 用户作品助手
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Annotated, Any

from nonebot.log import logger
from nonebot.params import ArgStr, Depends
from nonebot.plugin import CommandGroup
from nonebot.typing import T_State

from src.params.handler import (
    get_command_str_multi_args_parser_handler,
    get_command_str_single_arg_parser_handler,
)
from src.service import OmegaMatcherInterface as OmMI
from src.service import OmegaMessageSegment, OmegaSubscriptionHandlerManager, enable_processor_state
from src.service.omega_message_context.custom_depends import (
    ARTIST_CONTEXT_MANAGER,
    OPTIONAL_REPLY_ARTIST_OR_ARTWORK_ARTIST,
)
from src.utils.pixiv_api import PixivUser
from .subscription_source import PixivUserSubscriptionManager

if TYPE_CHECKING:
    from src.resource import TemporaryResource

_pixiv_artist_subscription_manager = OmegaSubscriptionHandlerManager(
    subscription_manager=PixivUserSubscriptionManager,
    command_prefix='pixiv用户',
    aliases_command_prefix={
        'Pixiv用户',
        'pixiv用户作品',
        'Pixiv用户作品',
    },
)

_pixiv_artist_subscription = _pixiv_artist_subscription_manager.register_handlers(permission_level=30)
"""注册 Pixiv 用户作品订阅流程 Handlers"""


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
        ranking_preview_factory=PixivUserSubscriptionManager.get_ranking_preview_factory(mode='daily')
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
        ranking_preview_factory=PixivUserSubscriptionManager.get_ranking_preview_factory(mode='weekly')
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
        ranking_preview_factory=PixivUserSubscriptionManager.get_ranking_preview_factory(mode='monthly')
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
            f'UID: {x.user_id} | {x.user_name}\n{"用户无自我介绍" if x.user_desc is None else x.user_desc}'
            for x in searching_result.users
        )
        await interface.send_reply(f'{message_prefix}\n\n{result_message}')
    except Exception as e:
        logger.error(f'PixivUserSearching | 获取用户(nick={user_nick})搜索结果失败, {e}')
        await interface.send_reply('搜索用户失败, 请稍后再试或联系管理员处理')


pixiv_artist_artworks = pixiv_artist.command(
    'user-artworks',
    aliases={'pixiv用户作品', 'Pixiv用户作品', 'pixiv画师作品', 'Pixiv画师作品'},
    handlers=[get_command_str_multi_args_parser_handler('user_id_page')],
)


@pixiv_artist_artworks.handle()
async def handle_preview_reply_artist_artworks(
        artist_data: OPTIONAL_REPLY_ARTIST_OR_ARTWORK_ARTIST,
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        state: T_State,
) -> None:
    if artist_data is None:
        return

    if artist_data.origin.lower() != 'pixiv':
        await interface.finish_reply('非 Pixiv 用户来源, 无法获取用户作品信息')

    state['user_id_page_0'] = artist_data.uid


@pixiv_artist_artworks.got('user_id_page_0', prompt='请输入用户的UID:')
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
        preview_image = await PixivUserSubscriptionManager.generate_artworks_preview(
            title=title,
            pids=user_data.manga_illusts[p_start:p_end],
        )

        response = await interface.send_reply(OmegaMessageSegment.image(await preview_image.get_hosting_path()))
        await ARTIST_CONTEXT_MANAGER.set_message_context(response=response, origin='pixiv', uid=uid)
    except Exception as e:
        logger.error(f'PixivUserArtworks | 获取用户(uid={user_id})作品失败, {e}')
        await interface.send_reply('获取用户作品失败了QAQ, 请稍后再试')


pixiv_artist_bookmark = pixiv_artist.command(
    'user-bookmark',
    aliases={'pixiv用户收藏', 'Pixiv用户收藏'},
    handlers=[get_command_str_multi_args_parser_handler('user_id_page', ensure_keys_num=2)],
)


@pixiv_artist_bookmark.handle()
async def handle_preview_reply_user_bookmark(
        artist_data: OPTIONAL_REPLY_ARTIST_OR_ARTWORK_ARTIST,
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        state: T_State,
) -> None:
    if artist_data is None:
        return

    if artist_data.origin.lower() != 'pixiv':
        await interface.finish_reply('非 Pixiv 用户来源, 无法获取用户作品信息')

    state['user_id_page_0'] = artist_data.uid


@pixiv_artist_bookmark.handle()
async def handle_preview_user_bookmark(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        state: T_State,
) -> None:
    user_id = state.get('user_id_page_0', None)

    if user_id is not None and not str(user_id).isdigit():
        await interface.finish('用户UID应当为纯数字, 请确认后再重试吧')

    page_str = state.get('user_id_page_1')
    page_str = '1' if page_str is None else str(page_str)
    if not page_str.isdigit():
        await interface.finish('页码应当为纯数字, 请确认后再重试吧')
    page = int(page_str)

    await interface.send_reply('稍等, 正在获取用户收藏~')

    try:
        # 为空则获取当前登录账号的收藏
        pixiv_user = PixivUser(uid=str(user_id)) if user_id is not None else PixivUser.init_default_user()
        user_bookmark_data = await pixiv_user.query_user_bookmarks(page=page)

        title = f'Pixiv User Bookmark - {pixiv_user.uid}'
        preview_image = await PixivUserSubscriptionManager.generate_artworks_preview(
            title=title,
            pids=user_bookmark_data.illust_ids,
        )

        response = await interface.send_reply(OmegaMessageSegment.image(await preview_image.get_hosting_path()))
        await ARTIST_CONTEXT_MANAGER.set_message_context(response=response, origin='pixiv', uid=user_id)
    except Exception as e:
        logger.error(f'PixivUserBookmark | 获取用户(uid={user_id})收藏失败, {e}')
        await interface.send_reply('获取用户收藏失败了QAQ, 请稍后再试')


async def handle_ranking_preview(
        interface: 'OmMI',
        page: str,
        ranking_preview_factory: Callable[[int], Coroutine[Any, Any, 'TemporaryResource']]
) -> None:
    """生成并发送榜单预览图"""
    page = page.strip()
    if not page.isdigit():
        await interface.finish_reply('榜单页码应当为纯数字, 请确认后再重试吧')

    await interface.send_reply('稍等, 正在获取榜单作品~')

    try:
        ranking_img = await ranking_preview_factory(int(page))
        await interface.send_reply(OmegaMessageSegment.image(await ranking_img.get_hosting_path()))
    except Exception as e:
        logger.error(f'PixivRanking | 获取榜单内容(page={ranking_preview_factory!r})失败, {e}')
        await interface.send_reply('获取榜单内容失败了QAQ, 请稍后再试')


__all__ = []
