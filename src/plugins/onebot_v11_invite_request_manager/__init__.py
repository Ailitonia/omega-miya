"""
@Author         : Ailitonia
@Date           : 2023/7/16 3:12
@FileName       : onebot_v11_invite_request_manager
@Project        : nonebot2_miya
@Description    : 好友与群组邀请管理
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.plugin import PluginMetadata


__plugin_meta__ = PluginMetadata(
    name='好友和群组请求管理',
    description='【QQ 好友和群组请求管理插件】\n'
                "处理加好友请求和加群、退群请求",
    usage='/好友验证码 [用户qq] \n\n'
          '说明:\n'
          '以上命令只允许管理员使用\n'
          '"好友验证码"命令会为指定用户生成一段验证码, 该用户在验证消息中输入该验证码可让 Bot 通过好友验证\n'
          '只有成为 Bot 好友的用户方能邀请 Bot 进群, Bot 会自动同意好友用户的邀请进群请求, 否则 Bot 会自动退群',
    supported_adapters={'OneBot V11'},
    extra={'author': 'Ailitonia'},
)


from . import command as command


__all__ = []
