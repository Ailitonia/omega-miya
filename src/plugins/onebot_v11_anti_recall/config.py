"""
@Author         : Ailitonia
@Date           : 2024/10/23 17:04:59
@FileName       : config.py
@Project        : omega-miya
@Description    : OneBot V11 反撤回插件配置
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, ValidationError


class OnebotV11AntiRecallConfig(BaseModel):
    """OneBot V11 反撤回插件配置"""

    # 是否使用内部数据库的消息记录作为查询已撤回消息的来源
    onebot_v11_anti_recall_plugin_enable_internal_database: bool = False

    model_config = ConfigDict(extra='ignore')


try:
    onebot_v11_anti_recall_config = get_plugin_config(OnebotV11AntiRecallConfig)
except ValidationError as e:
    import sys

    logger.opt(colors=True).critical(f'<r>OneBot V11 反撤回插件配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'OneBot V11 反撤回插件配置格式验证失败, {e}')

__all__ = [
    'onebot_v11_anti_recall_config',
]
