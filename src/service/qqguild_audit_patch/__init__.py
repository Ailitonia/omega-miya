"""
@Author         : Ailitonia
@Date           : 2023/9/24 16:16
@FileName       : qqguild_audit_patch
@Project        : nonebot2_miya
@Description    : qqguild 消息审核处理
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Any, Dict, Optional

from nonebot.log import logger
from nonebot.exception import MockApiException

from nonebot.adapters.qqguild.bot import Bot as QQGuildBot
from nonebot.adapters.qqguild.exception import AuditException
from nonebot.adapters.qqguild.event import MessageAuditPassEvent


@QQGuildBot.on_called_api
async def handle_api_result(
        bot: QQGuildBot,
        exception: Optional[Exception],
        api: str,
        data: Dict[str, Any],
        result: Any
):
    """获取消息发送后审核状态并自动处理 AuditException 事件"""
    if not isinstance(bot, QQGuildBot):
        return

    if exception is None:
        return

    if isinstance(exception, AuditException) and api == 'post_messages':
        logger.debug(f'QQGuild message send failed with AuditException, querying audit(id={exception.audit_id}) result')
        audit_result = await exception.get_audit_result(timeout=30)

        if isinstance(audit_result, MessageAuditPassEvent):
            message_get = await bot.get_message_of_id(channel_id=audit_result.channel_id,
                                                      message_id=audit_result.message_id)
            return_message = message_get.message
            return_message.id = audit_result.message_id
            raise MockApiException(result=return_message)


logger.opt(colors=True).info(f'<lc>QQGuild audit patch</lc> loaded')


__all__ = []
