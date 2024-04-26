"""
@Author         : Ailitonia
@Date           : 2024/4/26 上午1:18
@FileName       : shindan_maker
@Project        : nonebot2_miya
@Description    : shindan_maker 占卜插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.plugin import PluginMetadata


__plugin_meta__ = PluginMetadata(
    name='ShindanMaker',
    description='【ShindanMaker 占卜插件】\n'
                '使用ShindanMaker进行各种奇怪的占卜\n'
                '禁止涩涩！',
    usage='/shindan [占卜名称|占卜ID] [对象名称]\n'
          '/shindan_search [占卜名称]\n'
          '/shindan_ranking',
    extra={'author': 'Ailitonia'},
)


from . import command as command


__all__ = []
