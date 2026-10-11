"""
@Author         : Ailitonia
@Date           : 2023/7/3 2:42
@FileName       : omega_core_manager
@Project        : nonebot2_miya
@Description    : Omega 核心管理插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name='OmegaCoreManager',
    description='【Omega 机器人核心管理插件】\n'
                '机器人开关、维护、功能及权限管理',
    usage='/omega start  启用/初始化\n'
          '/omega disable  禁用\n'
          '/omega help [插件名]  帮助\n\n'
          '管理员命令:\n'
          '/omega status  查看状态\n'
          '/omega set-level [等级]\n'
          '/omega list-commands\n'
          '/omega list-plugins\n'
          '/omega enable-plugin [插件名]\n'
          '/omega disable-plugin [插件名]\n'
          '/omega show-plugin-nodes [插件名]\n'
          '/omega allow-plugin-node [插件名] [权限节点]\n'
          '/omega deny-plugin-node [插件名] [权限节点]\n'
          '/omega list-configured-auth',
    config=None,
    extra={'author': 'Ailitonia'},
)


from . import command as command

__all__ = []
