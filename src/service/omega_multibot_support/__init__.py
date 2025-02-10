"""
@Author         : Ailitonia
@Date           : 2022/12/03 20:51
@FileName       : omega_multibot_support.py
@Project        : nonebot2_miya
@Description    : Multi-Bot 多协议端接入支持
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from . import universal as universal  # noqa: I001 通用处理模块优先导入

from . import console as console
from . import onebot_v11 as onebot_v11
from . import qq as qq
from . import telegram as telegram


get_online_bots = universal.get_online_bots


__all__ = [
    'get_online_bots'
]
