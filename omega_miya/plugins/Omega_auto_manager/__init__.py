"""
@Author         : Ailitonia
@Date           : 2021/06/09 19:10
@FileName       : __init__.py.py
@Project        : nonebot2_miya 
@Description    : Omega 自动化综合/群管/好友管理插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import export
from omega_miya.utils.Omega_plugin_utils import init_export
from .group_welcome_message import *
from .invite_request import *


# Custom plugin usage text
__plugin_name__ = 'OmegaAutoManager'
__plugin_usage__ = r'''【Omega 自动化综合/群管/好友管理插件】
Omega机器人自动化综合/群管/好友管理

以下命令均需要@机器人
**Usage**
**GroupAdmin and SuperUser Only**
[设置和重置群组加群欢迎信息]
/WelcomeMsg.set
/WelcomeMsg.clear
'''

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__)


__all__ = [
    'WelcomeMsg',
    'group_increase',
    'add_and_invite_request'
]
