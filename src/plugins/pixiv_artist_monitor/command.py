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
from nonebot.params import ArgStr
from nonebot.typing import T_State

from src.params.depends import EVENT_MATCHER_INTERFACE
from src.params.handler import get_command_str_single_arg_parser_handler
from src.params.template import OmegaSubscriptionHandlerManager
from src.service.omega_message_context.custom_depends import OPTIONAL_REPLY_ARTIST_OR_ARTWORK_ARTIST
from src.utils.pixiv_api import PixivUser
from .subscription_source import PixivUserSubscriptionManager


async def handle_set_artist_sub_id(
        artist_data: OPTIONAL_REPLY_ARTIST_OR_ARTWORK_ARTIST,
        state: T_State,
) -> None:
    """获取回复消息中用户 ID 并在上下文中设置为订阅 ID, 仅供 SubscriptionHandlerManager 使用"""
    if (artist_data is None) or (artist_data.origin.lower() != 'pixiv'):
        return

    state['sub_id'] = artist_data.uid


_pixiv_artist_subscription_manager = OmegaSubscriptionHandlerManager(
    subscription_manager=PixivUserSubscriptionManager,
    command_prefix='pixiv用户',
    aliases_command_prefix={
        'Pixiv用户',
        'pixiv用户作品',
        'Pixiv用户作品',
    },
)

_pixiv_artist_subscription = _pixiv_artist_subscription_manager.register_handlers(
    extra_sub_handlers=[handle_set_artist_sub_id],
    permission_level=30,
)
"""注册 Pixiv 用户作品订阅流程 Handlers"""


# 附加用户查找功能命令处理
@_pixiv_artist_subscription.command(
    'searching',
    aliases={'pixiv用户搜索', 'Pixiv用户搜索', 'pixiv画师搜索', 'Pixiv画师搜索'},
    permission=None,
    handlers=[get_command_str_single_arg_parser_handler('user_nick')],
).got('user_nick', prompt='请输入想要搜索的Pixiv用户名:')
async def handle_searching_user(
        interface: EVENT_MATCHER_INTERFACE,
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


__all__ = []
