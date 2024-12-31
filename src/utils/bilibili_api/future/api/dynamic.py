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
from ..models import Dynamics, DynDetail


class BilibiliDynamic(BilibiliCommon):
    """Bilibili 动态 API"""

    @classmethod
    async def query_my_following_dynamics(
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

    @classmethod
    async def query_user_space_dynamics(
            cls,
            host_mid: int | str,
            *,
            offset: int | None = None,
            timezone_offset: int | None = None,
            features: str | None = None,
    ) -> Dynamics:
        """获取用户空间动态"""
        url = 'https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space'
        params: dict[str, str] = {'host_mid': str(host_mid)}
        if offset is not None:
            params.update({'offset': str(offset)})
        if timezone_offset is not None:
            params.update({'timezone_offset': str(timezone_offset)})
        if features is not None:
            params.update({'features': features})

        data = await cls._get_json(url=url, params=params)
        return Dynamics.model_validate(data)

    @classmethod
    async def query_dynamic_detail(
            cls,
            id_: int | str,
            *,
            timezone_offset: int | None = None,
    ) -> DynDetail:
        """获取动态详细信息"""
        url = 'https://api.bilibili.com/x/polymer/web-dynamic/v1/detail'
        params: dict[str, str] = {'id': str(id_)}
        if timezone_offset is not None:
            params.update({'timezone_offset': str(timezone_offset)})

        data = await cls._get_json(url=url, params=params)
        return DynDetail.model_validate(data)


__all__ = [
    'BilibiliDynamic',
]
