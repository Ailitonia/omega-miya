"""
@Author         : Ailitonia
@Date           : 2025/7/16 17:46:09
@FileName       : api.py
@Project        : omega-miya
@Description    : 短链接服务 API
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from fastapi import HTTPException
from fastapi.responses import RedirectResponse
from nonebot.log import logger

from .config import short_link_config
from .utils import query_short_link_url, query_url_short_link_uuid
from ..omega_api import OmegaAPI

_SHORT_LINK_API = OmegaAPI(
    app_name='omega_short_link',
    access_domain=short_link_config.omega_short_link_access_domain,
    use_https=short_link_config.omega_short_link_use_https,
)
"""短链接服务 API"""

if short_link_config.omega_short_link_enable_http_forward_service:

    # 注册文件托管服务 API
    @_SHORT_LINK_API.register_get_route('/go/{uuid}')
    async def _download_file(uuid: str) -> RedirectResponse:
        url = await query_short_link_url(uuid)

        if not url:
            raise HTTPException(status_code=404, detail='Short link expired or deleted')

        return RedirectResponse(url=url, status_code=307)

    logger.opt(colors=True).success('<lc>OmegaShortLink</lc> | <lg>短链接服务已启用</lg>')

__all__ = [
    'query_short_link_url',
    'query_url_short_link_uuid',
]
