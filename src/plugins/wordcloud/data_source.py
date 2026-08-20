"""
@Author         : Ailitonia
@Date           : 2024/10/27 00:19
@FileName       : data_source
@Project        : omega-miya
@Description    : 词云内容生成模块
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from os import SEEK_END, SEEK_SET
from typing import TYPE_CHECKING, Optional

from src.database import HistoryDAL, begin_db_session
from src.utils import OmegaRequests
from .config import wordcloud_plugin_config

if TYPE_CHECKING:
    from datetime import datetime

    from src.database.internal.history import History
    from src.params.depends import EVENT_ENTITY_PARAMS, USER_ENTITY_PARAMS
    from src.resource import TemporaryResource


async def query_entity_message_history(
        event_entity_params: 'EVENT_ENTITY_PARAMS',
        user_entity_params: Optional['USER_ENTITY_PARAMS'] = None,
        *,
        start_time: Optional['datetime'] = None,
        end_time: Optional['datetime'] = None,
) -> list['History']:
    """查询当前事件的消息历史记录"""
    async with begin_db_session() as session:
        histories_list = await HistoryDAL(session).query_entity_records(
            bot_self_id=event_entity_params.bot_id,
            event_entity_id=event_entity_params.entity_id,
            user_entity_id=user_entity_params.entity_id if user_entity_params is not None else None,
            start_time=start_time,
            end_time=end_time,
            limit=wordcloud_plugin_config.wordcloud_plugin_query_history_limit,
            exclude_bot_self_message=wordcloud_plugin_config.wordcloud_plugin_exclude_bot_self_message,
        )
    return histories_list


async def query_profile_image(profile_image_url: str) -> 'TemporaryResource':
    """获取头像"""
    image_name = OmegaRequests.hash_url_file_name('wordcloud-head-image', url=profile_image_url)
    image_file = wordcloud_plugin_config.profile_image_folder(image_name)
    return await OmegaRequests().download(url=profile_image_url, file=image_file)


async def add_user_dict(content: str) -> None:
    """新增用户词典内容"""
    async with wordcloud_plugin_config.user_dict_file.async_open('a+', encoding='utf-8') as af:
        await af.seek(0, SEEK_SET)
        exists_user_dicts = {x.strip() for x in await af.readlines()}
        if content not in exists_user_dicts:
            await af.seek(0, SEEK_END)
            await af.write(f'{content.strip()}\n')


__all__ = [
    'query_entity_message_history',
    'query_profile_image',
    'add_user_dict',
]
