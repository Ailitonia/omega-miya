"""
@Author         : Ailitonia
@Date           : 2024/12/17 19:38:14
@FileName       : dynamic.py
@Project        : omega-miya
@Description    : bilibili 动态相关 API
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal

from .base import BilibiliCommon
from ..models import Dynamics


class BilibiliDynamic(BilibiliCommon):
    """Bilibili 动态 API"""

    @classmethod
    async def query_my_dynamics(
            cls,
            *,
            type_: Literal['all', 'video', 'pgc', 'article'] | None = None,
            host_mid: str | None = None,
            offset: int | None = None,
            update_baseline: int | None = None,
            platform: str = 'web',
            web_location: str = '333.1365'
    ) -> Dynamics:
        """获取我关注的动态列表更新"""
        url = 'https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/all'
        params: dict[str, str] = {'platform': platform, 'web_location': web_location}
        if type_ is not None:
            params.update({'type': type_})
        if host_mid is not None:
            params.update({'host_mid': host_mid})
        if offset is not None:
            params.update({'offset': str(offset)})
        if update_baseline is not None:
            params.update({'type': str(update_baseline)})

        data = await cls._get_json(url=url, params=params)
        return Dynamics.model_validate(data)


__all__ = [
    'BilibiliDynamic',
]
