"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : moe.py
@Project        : nonebot2_miya
@Description    : 来点萌图
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import re
from copy import deepcopy
from typing import Annotated

from nonebot.log import logger
from nonebot.params import Depends, ShellCommandArgs
from nonebot.plugin import on_shell_command
from nonebot.rule import Namespace

from src.params.handler import get_shell_command_parse_failed_handler
from src.service import OmegaMatcherInterface as OmMI
from src.service import enable_processor_state
from src.utils import semaphore_gather
from .config import moe_plugin_config
from .consts import ALLOW_R18_NODE
from .helpers import (
    get_query_argument_parser,
    has_allow_r18_node,
    parse_from_query_parser,
    prepare_send_image,
    query_artworks_from_database,
)


@on_shell_command(
    '来点涩图',
    aliases={'涩图', 'setu'},
    parser=get_query_argument_parser(),
    handlers=[get_shell_command_parse_failed_handler()],
    priority=10,
    block=True,
    state=enable_processor_state(
        name='Setu',
        level=60,
        auth_node='setu',
        extra_auth_node={ALLOW_R18_NODE},
        cooldown=60
    ),
).handle()
async def handle_setu(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        args: Annotated[Namespace, ShellCommandArgs()],
) -> None:
    """解析命令成功"""
    try:
        parsed_args = parse_from_query_parser(args=args)
        keywords = parsed_args.keywords
    except Exception as e:
        logger.warning(f'Setu | 命令参数解析错误, {e}')
        await interface.finish_reply('命令参数解析错误, 请确认后重试')

    # 根据搜索关键词再判断一次 allow_rating_range
    allow_rating_range = (3, 3) if parsed_args.r18 else (1, 2)
    for word in deepcopy(keywords):
        if re.match(r'^[Rr]-?18[Gg]?$', word):
            keywords.remove(word)
            allow_rating_range = (3, 3)

    # 对于 rate:E 以上的作品就需要检查权限
    if max(allow_rating_range) >= 3:
        allow_r18 = await has_allow_r18_node(interface=interface)
        if not allow_r18:
            await interface.finish_reply('没有涩涩的权限, 禁止开车车!')

    artworks = await query_artworks_from_database(
        keywords=keywords,
        origin=parsed_args.origin,
        all_origin=parsed_args.all_origin,
        allow_rating_range=allow_rating_range,
        latest=parsed_args.latest,
        ratio=parsed_args.ratio,
        num=parsed_args.num,
    )

    if not artworks:
        await interface.finish_reply('找不到涩图QAQ')

    await interface.send_reply('稍等, 正在下载图片~')

    send_messages = await semaphore_gather(
        tasks=[prepare_send_image(x) for x in artworks],
        semaphore_num=4,
        filter_exception=True
    )

    if not send_messages:
        await interface.finish_reply('所有图片都获取失败了QAQ, 可能是网络原因或作品被删除, 请稍后再试')

    await semaphore_gather(
        tasks=[
            interface.send_auto_revoke(
                message=message,
                revoke_interval=moe_plugin_config.moe_plugin_setu_auto_recall_time
            )
            for message in send_messages
        ],
        semaphore_num=3,
        filter_exception=True
    )


@on_shell_command(
    '来点萌图',
    aliases={'萌图', 'moe'},
    parser=get_query_argument_parser(),
    handlers=[get_shell_command_parse_failed_handler()],
    priority=10,
    block=True,
    state=enable_processor_state(
        name='Moe',
        level=30,
        auth_node='moe',
        cooldown=60
    ),
).handle()
async def handle_moe(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        args: Annotated[Namespace, ShellCommandArgs()]
) -> None:
    """解析命令成功"""
    try:
        parsed_args = parse_from_query_parser(args=args)
        keywords = parsed_args.keywords
    except Exception as e:
        logger.warning(f'Moe | 命令参数解析错误, {e}')
        await interface.finish_reply('命令参数解析错误, 请确认后重试')

    # 移除无用的 r-18 关键词
    for word in deepcopy(keywords):
        if re.match(r'^[Rr]-?18[Gg]?$', word):
            keywords.remove(word)

    artworks = await query_artworks_from_database(
        keywords=keywords,
        origin=parsed_args.origin,
        all_origin=parsed_args.all_origin,
        allow_rating_range=(0, 0),
        latest=parsed_args.latest,
        ratio=parsed_args.ratio,
        num=parsed_args.num,
    )

    if not artworks:
        await interface.finish_reply('找不到萌图QAQ')

    await interface.send_reply('稍等, 正在下载图片~')

    send_messages = await semaphore_gather(
        tasks=[prepare_send_image(x) for x in artworks],
        semaphore_num=4,
        filter_exception=True
    )

    if not send_messages:
        await interface.finish_reply('所有图片都获取失败了QAQ, 可能是网络原因或作品被删除, 请稍后再试')

    await semaphore_gather(
        tasks=[
            interface.send_auto_revoke(
                message=message,
                revoke_interval=moe_plugin_config.moe_plugin_moe_auto_recall_time
            )
            for message in send_messages
        ],
        semaphore_num=3,
        filter_exception=True
    )


__all__ = []
