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

from nonebot.internal.adapter import Bot as BaseBot
from nonebot.internal.adapter import Event as BaseEvent
from nonebot.log import logger
from nonebot.params import ArgStr, Depends
from nonebot.permission import SUPERUSER
from nonebot.plugin import CommandGroup

from src.params.handler import get_command_str_single_arg_parser_handler
from src.service import OmegaMatcherInterface as OmMI
from src.service import OmegaMessageSegment, enable_processor_state
from .data_source import add_user_dict, query_entity_message_history, query_profile_image
from .helpers import draw_message_history_wordcloud

# 注册事件响应器
wordcloud = CommandGroup(
    'wordcloud',
    priority=10,
    block=True,
    state=enable_processor_state(name='WordCloud', level=10, cooldown=120)
)


@wordcloud.command(
    'add-user-dict',
    aliases={'词云添加自定义词典', '词云添加用户词典'},
    handlers=[get_command_str_single_arg_parser_handler('content')],
    permission=SUPERUSER
).got('content', prompt='请输入需要添加的词语或短语:')
async def handle_add_user_dict(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        content: Annotated[str, ArgStr('content')],
) -> None:
    content = content.strip()
    try:
        await add_user_dict(content=content)
        await interface.send_reply(f'已添加自定义词典: {content}')
    except Exception as e:
        logger.error(f'WordCloud | 添加自定义词典失败, {e}')
        await interface.send_reply('添加自定义词典失败')


@wordcloud.command('daily', aliases={'词云', '今日词云'}).handle()
async def handle_daily_wordcloud(
        bot: BaseBot,
        event: BaseEvent,
        interface: Annotated[OmMI, Depends(OmMI.depend())],
) -> None:
    start_time = datetime.now() - timedelta(days=1)
    desc_text = '自一天前以来的消息词云'
    await wordcloud_generate_handler(
        bot=bot, event=event, interface=interface, start_time=start_time, desc_text=desc_text
    )


@wordcloud.command('weekly', aliases={'本周词云'}).handle()
async def handle_weekly_wordcloud(
        bot: BaseBot,
        event: BaseEvent,
        interface: Annotated[OmMI, Depends(OmMI.depend())],
) -> None:
    start_time = datetime.now() - timedelta(days=7)
    desc_text = '自一周前以来的消息词云'
    await wordcloud_generate_handler(
        bot=bot, event=event, interface=interface, start_time=start_time, desc_text=desc_text
    )


@wordcloud.command('monthly', aliases={'本月词云'}).handle()
async def handle_monthly_wordcloud(
        bot: BaseBot,
        event: BaseEvent,
        interface: Annotated[OmMI, Depends(OmMI.depend())],
) -> None:
    start_time = datetime.now() - timedelta(days=30)
    desc_text = '自一个月前以来的消息词云'
    await wordcloud_generate_handler(
        bot=bot, event=event, interface=interface, start_time=start_time, desc_text=desc_text
    )


@wordcloud.command('my-daily', aliases={'我的词云', '我的今日词云'}).handle()
async def handle_my_daily_wordcloud(
        bot: BaseBot,
        event: BaseEvent,
        interface: Annotated[OmMI, Depends(OmMI.depend())],
) -> None:
    start_time = datetime.now() - timedelta(days=1)
    desc_text = f'{interface.get_event_user_nickname()}的今日词云'
    await wordcloud_generate_handler(
        bot=bot, event=event, interface=interface, start_time=start_time, desc_text=desc_text, match_user=True
    )


@wordcloud.command('my-weekly', aliases={'我的本周词云'}).handle()
async def handle_my_weekly_wordcloud(
        bot: BaseBot,
        event: BaseEvent,
        interface: Annotated[OmMI, Depends(OmMI.depend())],
) -> None:
    start_time = datetime.now() - timedelta(days=7)
    desc_text = f'{interface.get_event_user_nickname()}的本周词云'
    await wordcloud_generate_handler(
        bot=bot, event=event, interface=interface, start_time=start_time, desc_text=desc_text, match_user=True
    )


@wordcloud.command('my-monthly', aliases={'我的本月词云'}).handle()
async def handle_my_monthly_wordcloud(
        bot: BaseBot,
        event: BaseEvent,
        interface: Annotated[OmMI, Depends(OmMI.depend())],
) -> None:
    start_time = datetime.now() - timedelta(days=30)
    desc_text = f'{interface.get_event_user_nickname()}的本月词云'
    await wordcloud_generate_handler(
        bot=bot, event=event, interface=interface, start_time=start_time, desc_text=desc_text, match_user=True
    )


async def wordcloud_generate_handler(
        bot: BaseBot,
        event: BaseEvent,
        interface: OmMI,
        start_time: datetime,
        desc_text: str,
        *,
        match_event: bool = True,
        match_user: bool = False,
) -> None:
    await interface.send_reply('正在处理历史消息, 请稍候')
    try:
        message_history_list = await query_entity_message_history(
            bot=bot, event=event, start_time=start_time, match_event=match_event, match_user=match_user
        )
        profile_image = await query_profile_image(bot, event, match_user=match_user)

        desc_text += f'\n已统计 {len(message_history_list)} 条消息\n生成于: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'

        wordcloud_image = await draw_message_history_wordcloud(
            messages=message_history_list, profile_image_file=profile_image, desc_text=desc_text
        )

        logger.success(f'WordCloud | 生成 {interface.entity} 自 {start_time} 以来的词云成功')
        await interface.send_reply(OmegaMessageSegment.image(wordcloud_image.path))
    except Exception as e:
        logger.error(f'WordCloud | 生成 {interface.entity} 自 {start_time} 以来的词云失败, {e!r}')
        await interface.send_reply('生成词云失败, 请稍后再试或联系管理员处理')


__all__ = []
