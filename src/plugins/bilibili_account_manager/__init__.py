"""
@Author         : Ailitonia
@Date           : 2024/6/3 上午2:11
@FileName       : bilibili_account_manager
@Project        : nonebot2_miya
@Description    : bilibili 账户及凭据管理工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.plugin import PluginMetadata


__plugin_meta__ = PluginMetadata(
    name='bilibiliAccountManager',
    description='【B站账户管理插件】\n'
                '配置登录账户',
    usage='仅限超级管理员使用:\n'
          '/bilibili扫码登录',
    extra={'author': 'Ailitonia'},
)


from . import command as command


__all__ = []
