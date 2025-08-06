"""
@Author         : Ailitonia
@Date           : 2025/5/9 16:57:21
@FileName       : bot.py
@Project        : omega-miya
@Description    : Bot 相关 API
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends

from src.database import BotSelfDAL, get_db_session
from src.service.omega_api import return_standard_api_result
from .base import omega_webui_api

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.database.internal.bot import BotSelf


@omega_webui_api.register_get_route('/bot/list')
@return_standard_api_result
async def list_bot(session: Annotated['AsyncSession', Depends(get_db_session)]) -> list['BotSelf']:
    bot_list = await BotSelfDAL(session=session).query_all()
    return bot_list


__all__ = []
