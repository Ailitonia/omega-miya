"""
@Author         : Ailitonia
@Date           : 2024/8/31 上午3:23
@FileName       : command
@Project        : omega-miya
@Description    : 注册图站相关命令
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import TYPE_CHECKING, Annotated

from nonebot.log import logger
from nonebot.params import Depends
from nonebot.plugin import on_command

from src.service import OmegaMatcherInterface as OmMI
from src.service import enable_processor_state
from src.service.artwork_proxy import (
    DanbooruArtworkProxy,
    GelbooruArtworkProxy,
    KonachanSafeArtworkProxy,
    PixivArtworkProxy,
    YandereArtworkProxy,
)
from src.service.omega_message_context.custom_depends import OPTIONAL_REPLY_ARTWORK
from .consts import ALLOW_R18_NODE
from .handlers import ArtworkHandlerManager

if TYPE_CHECKING:
    from src.service.artwork_proxy.add_ons.image_ops import ImageOpsMixin

__ARTWORK_PROXY_LIST: list[type['ImageOpsMixin']] = [
    DanbooruArtworkProxy,
    GelbooruArtworkProxy,
    KonachanSafeArtworkProxy,
    YandereArtworkProxy,
    PixivArtworkProxy,
]
"""可用的 ArtworkProxy 列表"""
__ARTWORK_PROXY_MAP: dict[str, type['ImageOpsMixin']] = {
    ap.get_base_origin_name().lower(): ap for ap in __ARTWORK_PROXY_LIST
}
"""可用的作品源与 ArtworkProxy 字典"""

for artwork_proxy_type in __ARTWORK_PROXY_LIST:
    ArtworkHandlerManager(artwork_class=artwork_proxy_type).register_handler()


@on_command(
    'show-artwork',
    aliases={'看图', '看看图'},
    priority=10,
    block=True,
    state=enable_processor_state(
        name='OmegaAnyArtworks',
        level=50,
        auth_node='show_artwork',
        extra_auth_node={ALLOW_R18_NODE},
        cooldown=60,
    )
).handle()
async def handle_show_artwork(
        artwork_data: OPTIONAL_REPLY_ARTWORK,
        interface: Annotated[OmMI, Depends(OmMI.depend())],
) -> None:
    if artwork_data is None:
        await interface.finish_reply('回复或引用消息中没有作品信息')

    if (origin := artwork_data.origin.lower()) not in __ARTWORK_PROXY_MAP:
        await interface.finish_reply('回复或引用消息中的作品无可用来源')

    # 检查权限确定图片处理模式
    allow_r18 = await ArtworkHandlerManager.has_allow_r18_node(interface=interface)
    no_blur_rating = 3 if allow_r18 else 1

    await interface.send_reply('稍等, 正在获取作品信息~')

    try:
        await ArtworkHandlerManager.send_artwork_message(
            interface=interface,
            artwork=__ARTWORK_PROXY_MAP[origin](artwork_id=artwork_data.aid),
            no_blur_rating=no_blur_rating,
        )
    except Exception as e:
        logger.error(f'OmegaAnyArtwork | 获取作品预览失败, {artwork_data}, {e}')
        await interface.finish_reply(message='获取作品失败了QAQ, 可能是网络原因或者作品已经被删除, 请稍后再试')


__all__ = []
