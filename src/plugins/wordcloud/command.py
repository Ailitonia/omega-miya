"""
@Author         : Ailitonia
@Date           : 2024/11/17 22:43
@FileName       : command
@Project        : omega-miya
@Description    : 词云插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import datetime, timedelta
from typing import Annotated

from nonebot.log import logger
from nonebot.params import ArgStr
from nonebot.permission import SUPERUSER
from nonebot.plugin import CommandGroup

from src.params.depends import (
    EVENT_ENTITY_PARAMS,
    EVENT_ENTITY_PROFILE_IMAGE_URL,
    EVENT_MATCHER_INTERFACE,
    USER_ENTITY_PARAMS,
    USER_ENTITY_PROFILE_IMAGE_URL,
    USER_MATCHER_INTERFACE,
)
from src.params.handler import get_command_str_single_arg_parser_handler
from src.service import OmegaMessageSegment, enable_processor_state
from .data_source import add_user_dict, query_entity_message_history, query_profile_image
from .helpers import draw_message_history_wordcloud

# 注册事件响应器
wordcloud = CommandGroup(
    'wordcloud',
    priority=10,
    block=True,
    state=enable_processor_state(name='WordCloud', level=10, cooldown=15)
)


@wordcloud.command(
    'add-user-dict',
    aliases={'词云添加自定义词典', '词云添加用户词典'},
    handlers=[get_command_str_single_arg_parser_handler('content')],
    permission=SUPERUSER
).got('content', prompt='请输入需要添加的词语或短语:')
async def handle_add_user_dict(
        interface: EVENT_MATCHER_INTERFACE,
        content: Annotated[str, ArgStr('content')],
) -> None:
    content = content.strip()
    try:
        await add_user_dict(content=content)
        await interface.send_reply(f'已添加自定义词典: {content}')
    except Exception as e:
        logger.error(f'WordCloud | 添加自定义词典失败, {e}')
        await interface.send_reply('添加自定义词典失败')


@wordcloud.command('daily', aliases={'词云', '今日词云', '今天聊了啥'}).handle()
async def handle_daily_wordcloud(
        interface: EVENT_MATCHER_INTERFACE,
        profile_image_url: EVENT_ENTITY_PROFILE_IMAGE_URL,
        event_entity_params: EVENT_ENTITY_PARAMS,
) -> None:
    start_time = datetime.now() - timedelta(days=1)
    desc_text = '自一天前以来的消息词云'
    await wordcloud_generate_handler(
        interface=interface,
        start_time=start_time,
        desc_text=desc_text,
        profile_image_url=profile_image_url,
        event_entity_params=event_entity_params,
    )


@wordcloud.command('weekly', aliases={'本周词云', '这周聊了啥'}).handle()
async def handle_weekly_wordcloud(
        interface: EVENT_MATCHER_INTERFACE,
        profile_image_url: EVENT_ENTITY_PROFILE_IMAGE_URL,
        event_entity_params: EVENT_ENTITY_PARAMS,
) -> None:
    start_time = datetime.now() - timedelta(days=7)
    desc_text = '自一周前以来的消息词云'
    await wordcloud_generate_handler(
        interface=interface,
        start_time=start_time,
        desc_text=desc_text,
        profile_image_url=profile_image_url,
        event_entity_params=event_entity_params,
    )


@wordcloud.command('monthly', aliases={'本月词云'}).handle()
async def handle_monthly_wordcloud(
        interface: EVENT_MATCHER_INTERFACE,
        profile_image_url: EVENT_ENTITY_PROFILE_IMAGE_URL,
        event_entity_params: EVENT_ENTITY_PARAMS,
) -> None:
    start_time = datetime.now() - timedelta(days=30)
    desc_text = '自一个月前以来的消息词云'
    await wordcloud_generate_handler(
        interface=interface,
        start_time=start_time,
        desc_text=desc_text,
        profile_image_url=profile_image_url,
        event_entity_params=event_entity_params,
    )


@wordcloud.command('my-daily', aliases={'我的词云', '我的今日词云', '我今天聊了啥'}).handle()
async def handle_my_daily_wordcloud(
        interface: USER_MATCHER_INTERFACE,
        profile_image_url: USER_ENTITY_PROFILE_IMAGE_URL,
        event_entity_params: EVENT_ENTITY_PARAMS,
        user_entity_params: USER_ENTITY_PARAMS,
) -> None:
    start_time = datetime.now() - timedelta(days=1)
    desc_text = f'{interface.get_event_user_nickname()}的今日词云'
    await wordcloud_generate_handler(
        interface=interface,
        start_time=start_time,
        desc_text=desc_text,
        profile_image_url=profile_image_url,
        event_entity_params=event_entity_params,
        user_entity_params=user_entity_params,
    )


@wordcloud.command('my-weekly', aliases={'我的本周词云', '我这周聊了啥'}).handle()
async def handle_my_weekly_wordcloud(
        interface: USER_MATCHER_INTERFACE,
        profile_image_url: USER_ENTITY_PROFILE_IMAGE_URL,
        event_entity_params: EVENT_ENTITY_PARAMS,
        user_entity_params: USER_ENTITY_PARAMS,
) -> None:
    start_time = datetime.now() - timedelta(days=7)
    desc_text = f'{interface.get_event_user_nickname()}的本周词云'
    await wordcloud_generate_handler(
        interface=interface,
        start_time=start_time,
        desc_text=desc_text,
        profile_image_url=profile_image_url,
        event_entity_params=event_entity_params,
        user_entity_params=user_entity_params,
    )


@wordcloud.command('my-monthly', aliases={'我的本月词云'}).handle()
async def handle_my_monthly_wordcloud(
        interface: USER_MATCHER_INTERFACE,
        profile_image_url: USER_ENTITY_PROFILE_IMAGE_URL,
        event_entity_params: EVENT_ENTITY_PARAMS,
        user_entity_params: USER_ENTITY_PARAMS,
) -> None:
    start_time = datetime.now() - timedelta(days=30)
    desc_text = f'{interface.get_event_user_nickname()}的本月词云'
    await wordcloud_generate_handler(
        interface=interface,
        start_time=start_time,
        desc_text=desc_text,
        profile_image_url=profile_image_url,
        event_entity_params=event_entity_params,
        user_entity_params=user_entity_params,
    )


async def wordcloud_generate_handler(
        interface: EVENT_MATCHER_INTERFACE | USER_MATCHER_INTERFACE,
        start_time: datetime,
        desc_text: str,
        profile_image_url: EVENT_ENTITY_PROFILE_IMAGE_URL | USER_ENTITY_PROFILE_IMAGE_URL,
        event_entity_params: EVENT_ENTITY_PARAMS,
        user_entity_params: USER_ENTITY_PARAMS | None = None,
) -> None:
    """词云处理流程 Handler"""
    try:
        message_history_list = await query_entity_message_history(
            event_entity_params=event_entity_params,
            user_entity_params=user_entity_params,
            start_time=start_time,
        )
        if len(message_history_list) < 100 and len([x for x in message_history_list if x.message_text.strip()]) < 10:
            logger.info(f'WordCloud | {interface.entity} 没有足够的历史消息记录用于生成词云')
            await interface.send_reply('没有足够的历史消息记录用于生成词云, 请稍后再试')
            return

        profile_image = await query_profile_image(profile_image_url=profile_image_url)

        desc_text += f'\n已统计 {len(message_history_list)} 条消息\n生成于: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'

        wordcloud_image = await draw_message_history_wordcloud(
            messages=message_history_list, profile_image_file=profile_image, desc_text=desc_text
        )

        logger.success(f'WordCloud | 生成 {interface.entity} 自 {start_time} 以来的词云成功')
        await interface.send_reply(OmegaMessageSegment.image(await wordcloud_image.get_hosting_path()))
    except Exception as e:
        logger.error(f'WordCloud | 生成 {interface.entity} 自 {start_time} 以来的词云失败, {e!r}')
        await interface.send_reply('生成词云失败, 请稍后再试或联系管理员处理')


__all__ = []
