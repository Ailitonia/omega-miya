"""
@Author         : Ailitonia
@Date           : 2024/4/26 下午10:24
@FileName       : omega_email
@Project        : nonebot2_miya
@Description    : Omega 邮箱插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.plugin import PluginMetadata


__plugin_meta__ = PluginMetadata(
    name='收邮件',
    description='【OmegaEmail 邮箱插件】\n'
                '主要是用来收验证码的\n',
    usage='/收邮件\n\n'
          '管理员命令:\n'
          '/添加邮箱\n'
          '/绑定邮箱\n'
          '/解绑邮箱',
    extra={'author': 'Ailitonia'},
)


from . import command as command


__all__ = []
