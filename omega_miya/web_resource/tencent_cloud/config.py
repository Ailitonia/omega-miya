"""
@Author         : Ailitonia
@Date           : 2022/04/10 19:03
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : Tencent Cloud Config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_driver, logger
from pydantic import BaseModel, ValidationError


class TencentCloudConfig(BaseModel):
    """Tencent Cloud 配置"""
    tencent_cloud_secret_id: str | None = None
    tencent_cloud_secret_key: str | None = None

    class Config:
        extra = "ignore"


try:
    tencent_cloud_config = TencentCloudConfig.parse_obj(get_driver().config)
except ValidationError as e:
    import sys
    logger.opt(colors=True).critical(f'<r>Tencent Cloud 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Tencent Cloud 配置格式验证失败, {e}')


__all__ = [
    'tencent_cloud_config'
]
