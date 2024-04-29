"""
@Author         : Ailitonia
@Date           : 2024/4/30 上午12:01
@FileName       : onebot_v11_zhoushen_hime
@Project        : nonebot2_miya
@Description    : 自动审轴姬
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.plugin import PluginMetadata


__plugin_meta__ = PluginMetadata(
    name='自动审轴姬',
    description='【自动审轴姬插件】\n'
                '检测群内上传文件并自动锤轴\n'
                '仅限 QQ 群聊使用',
    usage='仅限群管理员使用:\n'
          '/审轴姬 <ON|OFF>',
    supported_adapters={'OneBot V11'},
    extra={'author': 'Ailitonia'},
)


from . import command as command


__all__ = []
