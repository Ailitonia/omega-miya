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
                '主要是用来收验证码的\n\n'
                '【警告】在会话中添加邮箱可能导致账号信息泄露, 强烈建议使用内置工具在命令行导入',
    usage='/邮箱 <添加|绑定|解绑|收件> [选项]\n\n'
          '超级用户命令:\n'
          '/邮箱 添加\n'
          '管理员命令:\n'
          '/邮箱 绑定\n'
          '/邮箱 解绑\n\n'
          '所有命令可带 --address 等选项直接传参, 缺省时按提示交互输入',
    extra={'author': 'Ailitonia'},
)


from . import command as command

__all__ = []
