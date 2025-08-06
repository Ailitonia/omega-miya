"""
@Author         : Ailitonia
@Date           : 2025/7/16 17:06:51
@FileName       : omega_short_link.py
@Project        : omega-miya
@Description    : 短链接服务
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from .api import query_short_link_url, query_url_short_link_uuid

__all__ = [
    'query_short_link_url',
    'query_url_short_link_uuid',
]
