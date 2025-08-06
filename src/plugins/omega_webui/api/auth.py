"""
@Author         : Ailitonia
@Date           : 2025/5/8 19:56:48
@FileName       : auth.py
@Project        : omega-miya
@Description    : 校验 API
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from src.service.omega_api import return_standard_api_result

from .base import omega_webui_api


@omega_webui_api.register_post_route('/auth/nav')
@return_standard_api_result
async def auth_validate() -> None:
    return None


__all__ = []
