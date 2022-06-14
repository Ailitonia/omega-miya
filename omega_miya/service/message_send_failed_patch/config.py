"""
@Author         : Ailitonia
@Date           : 2022/06/14 20:28
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : message send failed patch config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_driver, logger
from pydantic import BaseModel, ValidationError


class MessageSendFailedPatchConfig(BaseModel):
    """MessageSendFailed Patch 配置"""
    message_send_failed_info: str = '消息发送失败了, 可能被风控QAQ'

    class Config:
        extra = "ignore"


try:
    message_send_failed_patch_config = MessageSendFailedPatchConfig.parse_obj(get_driver().config)
except ValidationError as e:
    import sys
    logger.opt(colors=True).critical(f'<r>MessageSendFailed Patch 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'MessageSendFailed Patch 配置格式验证失败, {e}')


__all__ = [
    'message_send_failed_patch_config'
]
