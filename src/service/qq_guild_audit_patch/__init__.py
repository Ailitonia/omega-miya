"""
@Author         : Ailitonia
@Date           : 2023/9/24 16:16
@FileName       : qq_guild_audit_patch
@Project        : nonebot2_miya
@Description    : QQ 适配器频道消息审核处理
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Any

from nonebot.adapters.qq import AuditException as QQAuditException
from nonebot.adapters.qq import Bot as QQBot
from nonebot.adapters.qq import Message as QQMessage
from nonebot.adapters.qq import MessageAuditPassEvent as QQMessageAuditPassEvent
from nonebot.exception import MockApiException
from nonebot.log import logger


@QQBot.on_called_api
async def handle_api_result(
        bot: QQBot,
        exception: Exception | None,
        api: str,
        data: dict[str, Any],
        result: Any
):
    """获取消息发送后审核状态并自动处理 AuditException 事件"""
    if not isinstance(bot, QQBot):
        return

    if exception is None:
        return

    if isinstance(exception, QQAuditException) and api == 'post_messages':
        logger.debug(f'Sending QQ guild message failed by auditing, querying auditing(id={exception.audit_id}) result')
        audit_result = await exception.get_audit_result(timeout=30)

        if isinstance(audit_result, QQMessageAuditPassEvent):
            message_get = await bot.get_message_of_id(
                channel_id=audit_result.channel_id,
                message_id=audit_result.message_id,
            )
            return_message = QQMessage.from_guild_message(message_get)
            raise MockApiException(result=return_message)


logger.opt(colors=True).info('<lc>QQ GuildAudit patch</lc> loaded')


__all__ = []
