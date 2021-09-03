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

    # plugin custom config
    # 是否启用自动下载签到头图的定时任务
    enable_pic_preparing_scheduler: bool = True

    # 相关数值显示命令
    favorability_alias: str = '好感度'
    energy_alias: str = '能量值'
    currency_alias: str = '硬币'

    # 能量值与好感度的兑换比例 公式为(能量值 * 兑换比 = 好感度)
    ef_exchange_rate: float = 0.25

    class Config:
        extra = "ignore"
