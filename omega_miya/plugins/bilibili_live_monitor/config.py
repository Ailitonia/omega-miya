"""
@Author         : Ailitonia
@Date           : 2022/07/30 21:31
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : Bilibili 直播间订阅插件配置
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_driver, logger
from pydantic import BaseModel, ValidationError


class BilibiliLiveMonitorPluginConfig(BaseModel):
    """BilibiliLiveMonitor 插件配置"""

    # 发送消息通知时尝试@全体
    bilibili_live_monitor_enable_group_at_all_notice: bool = False

    class Config:
        extra = "ignore"


try:
    bilibili_live_monitor_plugin_config = BilibiliLiveMonitorPluginConfig.parse_obj(get_driver().config)
except ValidationError as e:
    import sys
    logger.opt(colors=True).critical(f'<r>Bilibili 直播间订阅插件配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Bilibili 直播间订阅插件配置格式验证失败, {e}')


__all__ = [
    'bilibili_live_monitor_plugin_config'
]
