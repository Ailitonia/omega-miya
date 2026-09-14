"""
@Author         : Ailitonia
@Date           : 2024/12/17 19:38:14
@FileName       : dynamic.py
@Project        : omega-miya
@Description    : bilibili 动态相关 API
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm

部分动态相关接口请求存在 features 参数, 主要用于控制返回结果中的 modules 中的内容, 主要参数含义如下:
- htmlNewStyle      是否显示专栏正文, 对于纯动态类型接口无效
- itemOpusStyle     是否以图文风格显示动态, 部分动态强制需要, 对于图文类型接口无效
- listOnlyfans
- opusBigCover      是否在返回结果中区分大封面与九宫格, 对于图文接口似乎无效, 前置条件 itemOpusStyle
- onlyfansVote      是否在投票信息中增加参与按钮等
- onlyfansAssetsV2
- forwardListHidden
- ugcDelete
- onlyfansQaCard    是否展示更详细的展示充电专属问答
- commentsNewVersion
- decorationCard    是否以卡片形式显示装扮
- editable          是否在右上角三点菜单中显示编辑, 必须是自己发送的动态才有效果
- opusPrivateVisible
- tribeeEdit
- avatarAutoTheme   头像颜色使用 CSS 变量, 对于纯动态类型接口无效
- avatarTypeOpus
"""

from typing import Literal

from .base import BilibiliCommon
from ..models import DynamicDetail, DynamicOpusDetail, Dynamics


class BilibiliDynamic(BilibiliCommon):
    """Bilibili 动态 API"""

    @classmethod
    async def query_my_following_dynamics(
            cls,
            *,
            type_: Literal['all', 'video', 'pgc', 'article'] | None = None,
            host_mid: str | None = None,
            offset: int | str | None = None,
            update_baseline: int | str | None = None,
    ) -> Dynamics:
        """获取我关注的动态列表更新"""
        url = 'https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/all'

        _spm_prefix = await cls._init_spm_prefix()
        params: dict[str, str] = {
            'platform': 'web',
            'features': 'itemOpusStyle,listOnlyfans,opusBigCover,onlyfansVote,'
                        'decorationCard,onlyfansAssetsV2,ugcDelete',
            'web_location': _spm_prefix,
        }
        if type_ is not None:
            params.update({'type': type_})
        if host_mid is not None:
            params.update({'host_mid': host_mid})
        if offset is not None:
            params.update({'offset': str(offset)})
        if update_baseline is not None:
            params.update({'update_baseline': str(update_baseline)})

        data = await cls._get_resource_as_json(url=url, params=params)
        return Dynamics.model_validate(data)

    @classmethod
    async def query_user_space_dynamics(
            cls,
            host_mid: int | str,
            *,
            offset: int | str | None = None,
            timezone_offset: int | None = None,
    ) -> Dynamics:
        """获取用户空间动态"""
        url = 'https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space'
        # alternative_url: `https://api.bilibili.com/x/polymer/web-dynamic/desktop/v1/feed/space`

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
            timezone_offset: int | None = None,
    ) -> DynamicDetail:
        """获取动态详细信息"""
        url = 'https://api.bilibili.com/x/polymer/web-dynamic/v1/detail'
        # alternative_url: `https://api.bilibili.com/x/polymer/web-dynamic/desktop/v1/detail`

        _spm_prefix = await cls._init_spm_prefix()
        params: dict[str, str] = {
            'id': str(id_),
            'platform': 'web',
            'gaia_source': 'main_web',
            'features': 'itemOpusStyle,opusBigCover,onlyfansVote,endFooterHidden,decorationCard,'
                        'onlyfansAssetsV2,ugcDelete,onlyfansQaCard,editable,opusPrivateVisible,'
                        'avatarAutoTheme,commentsNewVersion',
            'web_location': _spm_prefix,
            # 'x-bili-device-req-json': '{"platform":"web","device":"pc"}',
            # 'x-bili-web-req-json': '{"spm_id":"333.1368"}',
        }
        if timezone_offset is not None:
            params.update({'timezone_offset': str(timezone_offset)})

        # Wbi 签名 (非必要)
        # params = await cls.sign_wbi_params(params=params)

        data = await cls._get_resource_as_json(url=url, params=params)
        return DynamicDetail.model_validate(data)

    @classmethod
    async def query_dynamic_opus_detail(
            cls,
            id_: int | str,
            *,
            timezone_offset: int | None = None,
    ) -> DynamicOpusDetail:
        """获取图文详细信息"""
        url = 'https://api.bilibili.com/x/polymer/web-dynamic/v1/opus/detail'

        params: dict[str, str] = {
            'id': str(id_),
            'features': 'onlyfansVote,onlyfansAssetsV2,decorationCard,htmlNewStyle,ugcDelete,'
                        'editable,opusPrivateVisible,tribeeEdit,avatarAutoTheme,avatarTypeOpus',
        }
        if timezone_offset is not None:
            params.update({'timezone_offset': str(timezone_offset)})

        data = await cls._get_resource_as_json(url=url, params=params)
        return DynamicOpusDetail.model_validate(data)


__all__ = [
    'BilibiliDynamic',
]
