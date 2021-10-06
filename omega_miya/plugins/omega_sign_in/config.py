"""
@Author         : Ailitonia
@Date           : 2021/07/17 2:04
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pydantic import BaseSettings


class Config(BaseSettings):
    # 是否启用正则匹配matcher
    # 如果 bot 配置了命令前缀, 但需要额外响应无前缀的 "签到" 等消息, 请将本选项设置为 True
    # 如果 bot 没有配置命令前缀或空白前缀, 请将本选项设置为 False, 避免重复响应
    enable_regex_matcher: bool = True

    # 是否启用自动下载签到头图的定时任务
    enable_pic_preparing_scheduler: bool = True
    # 缓存的签到头图的数量限制
    cache_pic_limit: int = 2000

    # 相关数值显示命令
    favorability_alias: str = '好感度'
    energy_alias: str = '能量值'
    currency_alias: str = '硬币'

    # 能量值与好感度的兑换比例 公式为(能量值 * 兑换比 = 好感度)
    ef_exchange_rate: float = 0.25

    class Config:
        extra = "ignore"
