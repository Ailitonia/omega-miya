"""
@Author         : Ailitonia
@Date           : 2024/11/15 16:15:55
@FileName       : user.py
@Project        : omega-miya
@Description    : bilibili 用户相关 API
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from urllib.parse import unquote

from lxml import etree
from nonebot.utils import run_sync

from src.compat import parse_json_as
from .base import BilibiliCommon
from ..models import (
    Account,
    User,
    UserSearchResult,
    UserSpaceRenderData,
    VipInfo,
)


class BilibiliUser(BilibiliCommon):
    """Bilibili 用户 API"""

    @classmethod
    async def query_my_account_info(cls) -> Account:
        """获取我的信息"""
        url = 'https://api.bilibili.com/x/member/web/account'
        data = await cls._get_json(url=url)
        return Account.model_validate(data)

    @classmethod
    async def query_my_vip_info(cls) -> VipInfo:
        """查询我的大会员状态"""
        url = 'https://api.bilibili.com/x/vip/web/user/info'
        data = await cls._get_json(url=url)
        return VipInfo.model_validate(data)

    @staticmethod
    @run_sync
    def _parse_user_space_w_webid(content: str) -> UserSpaceRenderData:
        """解析用户页面 __RENDER_DATA__ 内容"""
        html = etree.HTML(content)
        render_data = html.xpath('/html/head/script[@id="__RENDER_DATA__"]').pop(0).text
        return parse_json_as(UserSpaceRenderData, unquote(render_data))

    @classmethod
    async def _query_user_space_w_webid(cls, mid: int | str) -> UserSpaceRenderData:
        """获取并解析用户页面 __RENDER_DATA__ 内容"""
        user_space_url = f'https://space.bilibili.com/{mid}'
        user_space_page = await cls._get_resource_as_text(url=user_space_url)
        return await cls._parse_user_space_w_webid(content=user_space_page)

    @classmethod
    async def query_user_info(cls, mid: int | str) -> User:
        """获取用户基本信息"""
        url = 'https://api.bilibili.com/x/space/wbi/acc/info'
        render_data = await cls._query_user_space_w_webid(mid=mid)
        params = await cls.sign_wbi_params(params={'mid': str(mid), 'w_webid': render_data.access_id})
        data = await cls._get_json(url=url, params=params)
        return User.model_validate(data)

    @classmethod
    async def search_user(cls, keyword: str) -> list[UserSearchResult]:
        """搜索用户"""
        search_result = await cls.global_search_by_type(search_type='bili_user', keyword=keyword)
        return [x for x in search_result.all_results if isinstance(x, UserSearchResult)]


__all__ = [
    'BilibiliUser',
]
