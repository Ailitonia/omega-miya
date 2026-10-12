"""
@Author         : Ailitonia
@Date           : 2026/10/12
@FileName       : helpers
@Project        : omega-miya
@Description    : omega_core_manager 插件单元测试共用 helper 函数

    本模块仅放置共用 helper (纯函数/上下文管理器), fixture 统一定义在 conftest.py;
    事件/Bot 构造与数据库播种 helper 位于 tests/utils.py
    遵守项目约定: `src.*` 导入必须留在函数体内 (测试模块在 nonebot 初始化前被收集导入)

@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nonebot.adapters import Event as BaseEvent
    from nonebot.adapters.onebot.v11 import Message

    from src.database.internal.bot import BotSelf
    from src.service.omega_base import OmegaEntity


def expected_reply(event: 'BaseEvent', text: str) -> 'Message':
    """构造 finish_reply/send_reply 回复的预期消息: 头部 reply 段 + 文本段"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    message_id = getattr(event, 'message_id')
    return Message([MessageSegment.reply(message_id), MessageSegment.text(text)])


@asynccontextmanager
async def obv11_user_entity(bot: 'BotSelf', entity_id: str) -> AsyncGenerator['OmegaEntity', None]:
    """在独立会话中构造指定用户的 OneBot V11 实体 (会话退出即提交), 用于操作后的数据库状态验证/播种"""
    from src.database.helpers import database_session
    from src.database.internal.entity import EntityType
    from src.service.omega_base import OmegaEntity

    async with database_session() as session:
        yield OmegaEntity(
            session=session,
            bot_type=bot.bot_type,
            bot_id=bot.self_id,
            entity_type=EntityType.ONEBOT_V11_USER,
            entity_id=entity_id,
        )
