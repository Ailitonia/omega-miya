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
from ..models import DynDetail, Dynamics


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
    ) -> Dynamics:
        """获取我关注的动态列表更新"""
        url = 'https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/all'
        params: dict[str, str] = {
            'platform': 'web',
            'web_location': '333.1365',
            'features': 'itemOpusStyle,listOnlyfans,opusBigCover,onlyfansVote,'
                        'decorationCard,onlyfansAssetsV2,ugcDelete',
        }
        if type_ is not None:
            params.update({'type': type_})
        if host_mid is not None:
            params.update({'host_mid': host_mid})
        if offset is not None:
            params.update({'offset': str(offset)})
        if update_baseline is not None:
            params.update({'type': str(update_baseline)})

        data = await cls._get_resource_as_json(url=url, params=params)
        return Dynamics.model_validate(data)

    @classmethod
    async def query_user_space_dynamics(
            cls,
            host_mid: int | str,
            *,
            offset: int | None = None,
            timezone_offset: int | None = None,
    ) -> Dynamics:
        """获取用户空间动态"""
        url = 'https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space'
        params: dict[str, str] = {
            'host_mid': str(host_mid),
            'features': 'itemOpusStyle',
        }
        if offset is not None:
            params.update({'offset': str(offset)})
        if timezone_offset is not None:
            params.update({'timezone_offset': str(timezone_offset)})

        data = await cls._get_resource_as_json(url=url, params=params)
        return Dynamics.model_validate(data)

    @classmethod
    async def query_dynamic_detail(
            cls,
            id_: int | str,
            *,
            timezone_offset: int = -480,
    ) -> DynDetail:
        """获取动态详细信息"""
        url = 'https://api.bilibili.com/x/polymer/web-dynamic/v1/detail'
        params: dict[str, str] = {
            'id': str(id_),
            'platform': 'web',
            'gaia_source': 'main_web',
            'features': 'itemOpusStyle,opusBigCover,onlyfansVote,endFooterHidden,decorationCard,'
                        'onlyfansAssetsV2,ugcDelete,onlyfansQaCard,editable,opusPrivateVisible,'
                        'avatarAutoTheme,commentsNewVersion',
            'x-bili-device-req-json': '{"platform":"web","device":"pc"}',
            'x-bili-web-req-json': '{"spm_id":"333.1368"}',
        }
        if timezone_offset is not None:
            params.update({'timezone_offset': str(timezone_offset)})

        # Wbi 签名 (非必要)
        # params = await cls.sign_wbi_params(params=params)

        data = await cls._get_resource_as_json(url=url, params=params)
        return DynDetail.model_validate(data)


__all__ = [
    'BilibiliDynamic',
]
