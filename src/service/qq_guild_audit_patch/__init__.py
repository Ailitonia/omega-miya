"""
@Author         : Ailitonia
@Date           : 2023/9/24 16:16
@FileName       : qq_guild_audit_patch
@Project        : nonebot2_miya
@Description    : QQ 适配器频道消息审核处理
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Any, Dict, Optional

from nonebot.log import logger
from nonebot.exception import MockApiException

from nonebot.adapters.qq.bot import Bot as QQBot
from nonebot.adapters.qq.exception import AuditException
from nonebot.adapters.qq.event import MessageAuditPassEvent


@QQBot.on_called_api
async def handle_api_result(
        bot: QQBot,
        exception: Optional[Exception],
        api: str,
        data: Dict[str, Any],
        result: Any
):
    """获取消息发送后审核状态并自动处理 AuditException 事件"""
    if not isinstance(bot, QQBot):
        return

    if exception is None:
        return

    if isinstance(exception, AuditException) and api == 'post_messages':
        logger.debug(f'Sending QQ guild message failed by auditing, querying auditing(id={exception.audit_id}) result')
        audit_result = await exception.get_audit_result(timeout=30)

        if isinstance(audit_result, MessageAuditPassEvent):
            message_get = await bot.get_message_of_id(channel_id=audit_result.channel_id,
                                                      message_id=audit_result.message_id)
            return_message = message_get.message
            return_message.id = audit_result.message_id
            raise MockApiException(result=return_message)


logger.opt(colors=True).info(f'<lc>QQ GuildAudit patch</lc> loaded')


__all__ = []
