"""
@Author         : Ailitonia
@Date           : 2024/3/26 22:57
@FileName       : pixiv
@Project        : nonebot2_miya
@Description    : Pixiv 助手
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.plugin import PluginMetadata


__plugin_meta__ = PluginMetadata(
    name='Pixiv',
    description='【Pixiv助手插件】\n'
                '查看Pixiv插画、发现与推荐、日榜、周榜、月榜以及搜索作品\n'
                '订阅并跟踪画师作品更新',
    usage='/pixiv <PID>\n'
          '/pixiv随机 [关键词]\n'
          '/pixiv推荐 [PID or ArtworkUrl]\n'
          '/pixiv发现\n'
          '/pixiv日榜 [页码]\n'
          '/pixiv周榜 [页码]\n'
          '/pixiv月榜 [页码]\n'
          '/pixiv搜索 [参数] <关键词>\n'
          '/pixiv用户搜索 [用户昵称]\n'
          '/pixiv用户作品 <UID> [page]\n'
          '/pixiv用户收藏 <UID> [page]\n'
          '/pixiv用户订阅列表\n\n'
          '仅限私聊或群聊中群管理员使用:\n'
          '/pixiv用户订阅 [UID]\n'
          '/pixiv取消用户订阅 [UID]\n\n'
          '搜索命令参数:\n'
          '"-c", "--custom": 启用自定义参数\n'
          '"-a", "---ai-type": 是否排除 ai 生成作品, 0: 不排除, 1: 排除\n'
          '"-p", "--page": 搜索结果页码\n'
          '"-o", "--order": 排序方式, 可选: "date_d", "popular_d"\n'
          '"-l", "--like": 筛选最低收藏数\n'
          '"-d", "--from-days-ago": 筛选作品发布日期, 从几天前起始发布的作品\n'
          '"-s", "--safe-mode": NSFW 模式, 可选: "safe", "all", "r18"',
    extra={'author': 'Ailitonia'},
)


from . import command as command
from . import monitor as monitor


__all__ = []
