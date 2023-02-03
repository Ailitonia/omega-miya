"""
@Author         : Ailitonia
@Date           : 2023/2/3 23:55
@FileName       : config
@Project        : nonebot2_miya
@Description    : Weibo config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from dataclasses import dataclass

from src.resource import TemporaryResource


@dataclass
class WeiboLocalResourceConfig:
    # 默认的缓存资源保存路径
    default_tmp_folder: TemporaryResource = TemporaryResource('weibo')
    default_download_folder: TemporaryResource = default_tmp_folder('download')


weibo_resource_config = WeiboLocalResourceConfig()


__all__ = [
    'weibo_resource_config'
]
