"""
@Author         : Ailitonia
@Date           : 2024/4/24 下午7:45
@FileName       : mirage_tank
@Project        : nonebot2_miya
@Description    : 幻影坦克图片生成器
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.plugin import PluginMetadata


__plugin_meta__ = PluginMetadata(
    name='幻影坦克',
    description='【幻影坦克图片生成工具】\n'
                '制作幻影坦克图片',
    usage='/幻影坦克 [模式] [图片]\n\n'
          '合成模式可选: "白底", "黑底", "噪点", "彩色噪点", "灰度混合", "彩色混合", "差分"',
    extra={'author': 'Ailitonia'},
)


from . import command as command


__all__ = []
