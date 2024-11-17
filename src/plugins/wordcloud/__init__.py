"""
@Author         : Ailitonia
@Date           : 2024/10/27 00:19
@FileName       : wordcloud
@Project        : omega-miya
@Description    : 词云插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name='词云',
    description='【WordCloud 词云插件】\n'
                '根据历史聊天记录生成词云图片',
    usage='/词云\n'
          '/本周词云\n'
          '/本月词云\n'
          '/我的词云\n'
          '/我的本周词云\n'
          '/我的本月词云\n\n'
          '管理员命令:\n'
          '/添加自定义词典',
    config=None,
    extra={'author': 'Ailitonia'},
)

from . import command as command

__all__ = []
