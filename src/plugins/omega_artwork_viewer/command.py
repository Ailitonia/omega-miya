"""
@Author         : Ailitonia
@Date           : 2024/8/31 上午3:23
@FileName       : command
@Project        : omega-miya
@Description    : 注册图站相关命令
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import TYPE_CHECKING

from arclet.alconna import Alconna, CommandMeta, Option, store_true
from nonebot_plugin_alconna import on_alconna

from src.params.depends import EVENT_M_IFACE
from src.params.template.artwork_viewer import ALLOW_R18_NODE, ArtworkViewerHandlerFactory
from src.service import enable_processor_state
from src.service.artwork_proxy import (
    DanbooruArtworkProxy,
    GelbooruArtworkProxy,
    KonachanSafeArtworkProxy,
    PixivArtworkProxy,
    YandereArtworkProxy,
    get_artwork_proxy,
)
from src.service.omega_message_context.custom_depends import (
    OPTIONAL_REPLY_ARTIST_OR_ARTWORK_ARTIST,
    OPTIONAL_REPLY_ARTWORK,
)

if TYPE_CHECKING:
    from src.service.artwork_proxy.internal import BaseArtworkProxy

# ------------------------------------------------------------------ #
# 批量为可用的图站注册模板命令
# ------------------------------------------------------------------ #

_ARTWORK_VIEWER_PROXY_LIST: list[type['BaseArtworkProxy']] = [
    DanbooruArtworkProxy,
    GelbooruArtworkProxy,
    KonachanSafeArtworkProxy,
    YandereArtworkProxy,
    PixivArtworkProxy,
]
"""可用的 ArtworkProxy 列表"""

_ALLOWED_ORIGIN_NAMES: set[str] = {x.get_origin_name() for x in _ARTWORK_VIEWER_PROXY_LIST}
"""允许通过回复消息浏览作品的图站来源名称"""

for artwork_proxy in _ARTWORK_VIEWER_PROXY_LIST:
    ArtworkViewerHandlerFactory(
        artwork_proxy=artwork_proxy,
        need_decimal_artwork_id=True,
        need_decimal_user_id=True,
    ).register_handlers(
        priority=10,
        block=True,
        permission_level=50,
        extra_auth_node={ALLOW_R18_NODE},
        cooldown=60,
    )

# ------------------------------------------------------------------ #
# 回复消息响应命令, 自动匹配图站
# ------------------------------------------------------------------ #

reply_artwork_viewer = on_alconna(
    Alconna(
        'show-reply-artwork',
        Option('--user|-u', action=store_true, help_text='是否查看对应用户作品'),
        meta=CommandMeta(
            description='回复消息中的作品查询与浏览',
            usage='[回复消息] show-reply-artwork [选项]',
            example='[回复消息] 看看图 --user',
            compact=True,
        ),
    ),
    use_cmd_start=True,
    aliases={'看图', '看看图'},
    priority=10,
    block=True,
    default_state=enable_processor_state(
        name='ShowReplyArtwork',
        level=50,
        auth_node='show_reply_artwork',
        extra_auth_node={ALLOW_R18_NODE},
        cooldown=60,
    ),
)


@reply_artwork_viewer.assign('$main')
async def handle_show_reply_artwork(
        artwork_data: OPTIONAL_REPLY_ARTWORK,
        interface: EVENT_M_IFACE,
) -> None:
    if artwork_data is None:
        await interface.finish_reply('回复或引用消息中没有作品信息')

    if artwork_data.origin not in _ALLOWED_ORIGIN_NAMES:
        await interface.finish_reply('回复或引用消息中的作品无可用来源')

    handler_factory = ArtworkViewerHandlerFactory(artwork_proxy=get_artwork_proxy(artwork_data.origin))

    allow_r18 = await handler_factory.check_allow_r18(interface=interface)
    await interface.send_reply('稍等, 正在获取作品信息~')
    await handler_factory.execute_query_and_send_result(
        interface=interface,
        query_handler=handler_factory.query_artwork(artwork_id=artwork_data.aid),
        allow_r18=allow_r18,
    )


@reply_artwork_viewer.assign('options.user')
async def handle_show_reply_user_artworks(
        user_data: OPTIONAL_REPLY_ARTIST_OR_ARTWORK_ARTIST,
        interface: EVENT_M_IFACE,
) -> None:
    if user_data is None:
        await interface.finish_reply('回复或引用消息中没有作品或用户信息')

    if user_data.origin not in _ALLOWED_ORIGIN_NAMES:
        await interface.finish_reply('回复或引用消息中的作品无可用来源')

    handler_factory = ArtworkViewerHandlerFactory(artwork_proxy=get_artwork_proxy(user_data.origin))

    allow_r18 = await handler_factory.check_allow_r18(interface=interface)
    await interface.send_reply('稍等, 正在获取作品信息~')
    await handler_factory.execute_query_and_send_result(
        interface=interface,
        query_handler=handler_factory.query_user(uid=user_data.uid, page=1),
        allow_r18=allow_r18,
    )


__all__ = []
