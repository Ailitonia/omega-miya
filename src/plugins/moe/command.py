"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : moe.py
@Project        : nonebot2_miya
@Description    : 来点萌图
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import asyncio
import re
from copy import deepcopy
from typing import Annotated

from nonebot.adapters import Message
from nonebot.exception import ParserExit
from nonebot.matcher import Matcher
from nonebot.log import logger
from nonebot.params import ArgStr, CommandArg, Depends, ShellCommandArgs
from nonebot.permission import SUPERUSER
from nonebot.plugin import on_command, on_shell_command
from nonebot.rule import Namespace, to_me
from nonebot.typing import T_State

from src.database import begin_db_session
from src.params.handler import get_command_str_single_arg_parser_handler
from src.service import EntityInterface, MatcherInterface, enable_processor_state
from src.service.omega_base.internal import OmegaPixivArtwork
from src.utils.pixiv_api import PixivArtwork
from src.utils.process_utils import semaphore_gather

from .config import moe_plugin_config
from .consts import ALLOW_R18_NODE
from .helpers import (
    has_allow_r18_node,
    get_query_argument_parser,
    parse_from_query_parser,
    prepare_send_image,
    get_database_import_pids,
    add_artwork_into_database
)


setu = on_shell_command(
    '来点涩图',
    aliases={'涩图', 'setu'},
    parser=get_query_argument_parser(),
    priority=10,
    block=True,
    state=enable_processor_state(
        name='Setu',
        level=60,
        auth_node='setu',
        extra_auth_node={ALLOW_R18_NODE},
        cooldown=60
    ),
)


@setu.handle()
async def handle_parsed_failed(matcher: Matcher, args: Annotated[ParserExit, ShellCommandArgs()]):
    """解析命令失败"""
    await matcher.finish('命令参数错误\n' + args.message)


@setu.handle()
async def handle_parsed_success(
        matcher: Matcher,
        entity_interface: Annotated[EntityInterface, Depends(EntityInterface())],
        args: Annotated[Namespace, ShellCommandArgs()]
) -> None:
    """解析命令成功"""
    matcher_interface = MatcherInterface()

    args = parse_from_query_parser(args=args)
    keywords = args.word

    nsfw_tag = 1 if args.nsfw_tag == 0 else args.nsfw_tag
    for word in deepcopy(keywords):
        if re.match(r'^[Rr]-?18[Gg]?$', word):
            keywords.remove(word)
            nsfw_tag = 2

    allow_r18 = await has_allow_r18_node(matcher=matcher, entity_interface=entity_interface)
    if not allow_r18 and nsfw_tag != 1:
        await matcher.finish('没有涩涩的权限, 禁止开车车!')
    if not allow_r18:
        nsfw_tag = 1

    num_limit = moe_plugin_config.moe_plugin_query_image_limit
    num = args.num if args.num <= num_limit else num_limit

    async with begin_db_session() as session:
        artworks = await OmegaPixivArtwork.query_by_condition(
            session=session,
            keywords=keywords,
            num=num,
            nsfw_tag=nsfw_tag,
            classified=args.classified,
            acc_mode=args.acc_mode,
            order_mode=args.order
        )

    if not artworks:
        await matcher_interface.send_reply('找不到涩图QAQ')
        return

    await matcher_interface.send_reply('稍等, 正在下载图片~')

    message_result = await semaphore_gather(
        tasks=[prepare_send_image(pid=x.pid) for x in artworks],
        semaphore_num=5,
        filter_exception=True
    )
    send_messages = list(message_result)
    if not send_messages:
        await matcher_interface.send_reply('所有图片都获取失败了QAQ, 可能是网络原因或作品被删除, 请稍后再试')
        return

    await semaphore_gather(
        tasks=[
            entity_interface.send_msg_auto_revoke(
                message=message,
                revoke_interval=moe_plugin_config.moe_plugin_setu_auto_recall_time
            )
            for message in send_messages
        ],
        semaphore_num=3,
        filter_exception=True
    )


moe = on_shell_command(
    '来点萌图',
    aliases={'萌图', 'moe'},
    parser=get_query_argument_parser(),
    priority=10,
    block=True,
    state=enable_processor_state(
        name='Moe',
        level=30,
        auth_node='moe',
        cooldown=60
    ),
)


@moe.handle()
async def handle_parsed_failed(matcher: Matcher, args: Annotated[ParserExit, ShellCommandArgs()]):
    """解析命令失败"""
    await matcher.finish('命令参数错误\n' + args.message)


@moe.handle()
async def handle_parsed_success(
        entity_interface: Annotated[EntityInterface, Depends(EntityInterface())],
        args: Annotated[Namespace, ShellCommandArgs()]
) -> None:
    """解析命令成功"""
    matcher_interface = MatcherInterface()

    args = parse_from_query_parser(args=args)
    keywords = args.word

    for word in deepcopy(keywords):
        if re.match(r'^[Rr]-?18[Gg]?$', word):
            keywords.remove(word)

    num_limit = moe_plugin_config.moe_plugin_query_image_limit
    num = args.num if args.num <= num_limit else num_limit

    async with begin_db_session() as session:
        artworks = await OmegaPixivArtwork.query_by_condition(
            session=session,
            keywords=keywords,
            num=num,
            nsfw_tag=0,
            classified=args.classified,
            acc_mode=args.acc_mode,
            order_mode=args.order
        )

    if not artworks:
        await matcher_interface.send_reply('找不到萌图QAQ')
        return

    await matcher_interface.send_reply('稍等, 正在下载图片~')

    message_result = await semaphore_gather(
        tasks=[prepare_send_image(pid=x.pid) for x in artworks],
        semaphore_num=5,
        filter_exception=True
    )
    send_messages = list(message_result)
    if not send_messages:
        await matcher_interface.send_reply('所有图片都获取失败了QAQ, 可能是网络原因或作品被删除, 请稍后再试')
        return

    await semaphore_gather(
        tasks=[
            entity_interface.send_msg_auto_revoke(
                message=message,
                revoke_interval=moe_plugin_config.moe_plugin_moe_auto_recall_time
            )
            for message in send_messages
        ],
        semaphore_num=3,
        filter_exception=True
    )


@on_command(
    '图库统计',
    rule=to_me(),
    aliases={'图库查询', '查询图库'},
    priority=20,
    block=True,
    permission=SUPERUSER,
    handlers=[
        get_command_str_single_arg_parser_handler('keyword', ensure_key=True)
    ],
    state=enable_processor_state(name='MoeStatistics', enable_processor=False),
).got('keyword')
async def handle_keyword_statistics(keyword: Annotated[str | None, ArgStr('keyword')]):
    matcher_interface = MatcherInterface()

    if not keyword:
        keywords = []
    else:
        keywords = keyword.strip().split()

    try:
        async with begin_db_session() as session:
            statistics_data = await OmegaPixivArtwork.query_statistics(
                session=session,
                keywords=keywords
            )
        msg_prefix = f'本地数据库[{",".join(keywords) if keywords else "total"}]统计:'
    except Exception as e:
        logger.error(f'MoeStatistics | 查询图库统计(keyword={keywords})失败, {e!r}')
        await matcher_interface.send_reply('查询统计信息失败, 详情请查看日志')
        return

    msg = f'{msg_prefix}\n\n' \
          f'Total: {statistics_data.total}\n' \
          f'Moe: {statistics_data.moe}\n' \
          f'Setu: {statistics_data.setu}\n' \
          f'R18: {statistics_data.r18}'
    await matcher_interface.send_reply(msg)


async def handle_parse_database_import_pid(state: T_State, cmd_arg: Annotated[Message, CommandArg()]):
    """首次运行时解析命令参数"""
    cmd_args = cmd_arg.extract_plain_text().strip().split()
    arg_num = len(cmd_args)
    if arg_num == 1:
        state.update({'mode': cmd_args[0], 'pids': []})
    elif arg_num > 1:
        state.update({'mode': cmd_args[0], 'pids': [pid for pid in cmd_args[1:] if pid.isdigit()]})
    else:
        state.update({'pids': []})


@on_command(
    '导入图库',
    aliases={'图库导入'},
    priority=20,
    block=True,
    rule=to_me(),
    permission=SUPERUSER,
    handlers=[handle_parse_database_import_pid],
    state=enable_processor_state(name='MoeDatabaseImport', enable_processor=False),
).got('mode', prompt='请输入导入模式:\n【setu/moe】')
async def handle_database_import(
        mode: Annotated[str, ArgStr('mode')],
        state: T_State
) -> None:
    matcher_interface = MatcherInterface()

    mode = mode.strip()
    match mode:
        case 'moe':
            nsfw_tag = 0
        case 'setu':
            nsfw_tag = 1
        case _:
            await matcher_interface.send_at_sender('不支持的导入模式参数, 请在【setu/moe】中选择, 已取消操作')
            return

    pids: list[int] = [int(x) for x in state.get('pids', [])]
    if not pids:
        await matcher_interface.send_at_sender('尝试从文件中读取导入文件列表')
        pids = await get_database_import_pids()
    if not pids:
        await matcher_interface.send_at_sender('导入列表不存在, 已取消操作, 详情请查看日志')
        return

    pids = sorted(list(set(pids)), reverse=True)
    all_count = len(pids)
    await matcher_interface.send_at_sender(f'已获取导入列表, 总计: {all_count}, 开始获取作品信息')

    # 应对 pixiv 流控, 对获取作品信息进行分段处理
    pids = deepcopy(pids)
    handle_pids: list[int] = []
    failed_count = 0
    while pids:
        while len(handle_pids) < 20:
            try:
                handle_pids.append(pids.pop())
            except IndexError:
                break

        tasks = [
            add_artwork_into_database(
                PixivArtwork(pid),
                nsfw_tag=nsfw_tag,
                add_ignored_exists=False,
                ignore_mark=True
            )
            for pid in handle_pids
        ]
        handle_pids.clear()
        import_result = await semaphore_gather(tasks=tasks, semaphore_num=20)
        failed_count += len([x for x in import_result if isinstance(x, Exception)])

        if pids:
            logger.info(f'MoeDatabaseImport | 导入操作中, 剩余: {len(pids)}, 预计时间: {int(len(pids) * 1.52)} 秒')
            await asyncio.sleep(int((len(pids) if len(pids) < 20 else 20) * 1.5))

    logger.success(f'MoeDatabaseImport | 导入操作已完成, 成功: {all_count - failed_count}, 总计: {all_count}')
    await matcher_interface.send_reply(f'导入操作已完成, 成功: {all_count - failed_count}, 总计: {all_count}')
