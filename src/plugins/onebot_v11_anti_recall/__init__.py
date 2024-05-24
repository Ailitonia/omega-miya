"""
@Author         : Ailitonia
@Date           : 2023/7/16 14:07
@FileName       : onebot_v11_anti_recall
@Project        : nonebot2_miya
@Description    : OneBot V11 反撤回插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.plugin import PluginMetadata


__plugin_meta__ = PluginMetadata(
    name='反撤回',
    description='【OneBot V11 AntiRecall 反撤回插件】\n'
                '检测消息撤回并提取原消息',
    usage='仅限群聊中群管理员进行启用或关闭:\n'
          '/AntiRecall <ON|OFF>',
    supported_adapters={'OneBot V11'},
    extra={'author': 'Ailitonia'},
)


from . import command as command


__all__ = []
