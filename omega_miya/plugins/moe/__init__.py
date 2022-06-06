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
from nonebot import on_shell_command, on_command, logger
from nonebot.rule import to_me
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.rule import Namespace
from nonebot.exception import ParserExit
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP, PRIVATE_FRIEND
from nonebot.adapters.onebot.v11.message import Message
from nonebot.params import CommandArg, ArgStr, ShellCommandArgs

from omega_miya.service import init_processor_state
from omega_miya.service.gocqhttp_guild_patch.permission import GUILD, GUILD_SUPERUSER
from omega_miya.database import InternalPixiv
from omega_miya.web_resource.pixiv import PixivArtwork
from omega_miya.utils.process_utils import run_async_catching_exception, semaphore_gather
from omega_miya.utils.message_tools import MessageSender

from .config import moe_plugin_config
from .utils import (has_allow_r18_node, prepare_send_image, get_database_import_pids, add_artwork_into_database,
                    get_query_argument_parser, parse_from_query_parser)


# Custom plugin usage text
__plugin_custom_name__ = '来点萌图'
__plugin_usage__ = r'''【来点萌图】
随机萌图和随机涩图
不可以随意涩涩!

用法:
/来点萌图 [关键词, ...]
/来点涩图 [关键词, ...]

可用参数:
'-s', '--nsfw-tag': 指定nsfw_tag
'-n', '--num': 指定获取的图片数量
'-nf', '--no-flash': 强制不使用闪照发送图片

仅限管理员使用:
/图库统计
/图库查询 [关键词, ...]
/导入图库'''


_ALLOW_R18_NODE = moe_plugin_config.moe_plugin_allow_r18_node
"""允许预览 r18 作品的权限节点"""


setu = on_shell_command(
    '来点涩图',
    parser=get_query_argument_parser(),
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='Setu',
        level=60,
        auth_node='setu',
        extra_auth_node={_ALLOW_R18_NODE},
        cool_down=60,
        user_cool_down_override=2
    ),
    aliases={'涩图'},
    permission=GROUP | GUILD | PRIVATE_FRIEND,
    priority=20,
    block=True
)


@setu.handle()
async def handle_parse_failed(matcher: Matcher, args: ParserExit = ShellCommandArgs()):
    """解析命令失败"""
    await matcher.finish('命令格式错误QAQ\n' + args.message)


@setu.handle()
async def handle_parse_success(bot: Bot, event: MessageEvent, matcher: Matcher, args: Namespace = ShellCommandArgs()):
    """解析命令成功"""
    args = parse_from_query_parser(args=args)
    keywords = args.word

    nsfw_tag = 1 if args.nsfw_tag == 0 else args.nsfw_tag
    for word in deepcopy(keywords):
        if re.match(r'^[Rr]-?18[Gg]?$', word):
            keywords.remove(word)
            nsfw_tag = 2

    allow_r18 = await has_allow_r18_node(bot=bot, event=event, matcher=matcher)
    if not allow_r18 and nsfw_tag != 1:
        await matcher.finish('没有涩涩的权限, 禁止开车车!')
    if not allow_r18:
        nsfw_tag = 1

    num_limit = moe_plugin_config.moe_plugin_query_image_limit
    num = args.num if args.num <= num_limit else num_limit

    artworks = await InternalPixiv.query_by_condition(
        keywords=keywords,
        num=num,
        nsfw_tag=nsfw_tag,
        classified=args.classified,
        acc_mode=args.acc_mode,
        order_mode=args.order
    )
    if not artworks:
        await matcher.finish('找不到涩图QAQ')

    await matcher.send('稍等, 正在下载图片~')
    image_message_tasks = [prepare_send_image(pid=x.pid, enable_flash_mode=(not args.no_flash)) for x in artworks]
    message_result = await semaphore_gather(tasks=image_message_tasks, semaphore_num=5, filter_exception=True)
    send_messages = list(message_result)
    if not send_messages:
        await matcher.finish('所有图片都获取失败了QAQ, 可能是网络原因或作品被删除, 请稍后再试')
    await MessageSender(bot=bot).send_msgs_and_recall(event=event, message_list=send_messages,
                                                      recall_time=moe_plugin_config.moe_plugin_auto_recall_time)


moe = on_shell_command(
    '来点萌图',
    parser=get_query_argument_parser(),
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='Moe',
        level=30,
        auth_node='moe',
        cool_down=60,
        user_cool_down_override=2
    ),
    aliases={'萌图'},
    permission=GROUP | GUILD | PRIVATE_FRIEND,
    priority=20,
    block=True
)


@moe.handle()
async def handle_parse_failed(matcher: Matcher, args: ParserExit = ShellCommandArgs()):
    """解析命令失败"""
    await matcher.finish('命令格式错误QAQ\n' + args.message)


@moe.handle()
async def handle_parse_success(bot: Bot, event: MessageEvent, matcher: Matcher, args: Namespace = ShellCommandArgs()):
    """解析命令成功"""
    args = parse_from_query_parser(args=args)
    keywords = args.word

    for word in deepcopy(keywords):
        if re.match(r'^[Rr]-?18[Gg]?$', word):
            keywords.remove(word)

    num_limit = moe_plugin_config.moe_plugin_query_image_limit
    num = args.num if args.num <= num_limit else num_limit

    artworks = await InternalPixiv.query_by_condition(
        keywords=keywords,
        num=num,
        nsfw_tag=0,
        classified=args.classified,
        acc_mode=args.acc_mode,
        order_mode=args.order
    )
    if not artworks:
        await matcher.finish('找不到萌图QAQ')

    await matcher.send('稍等, 正在下载图片~')
    image_message_tasks = [prepare_send_image(pid=x.pid, enable_flash_mode=(not args.no_flash)) for x in artworks]
    message_result = await semaphore_gather(tasks=image_message_tasks, semaphore_num=5, filter_exception=True)
    send_messages = list(message_result)
    if not send_messages:
        await matcher.finish('所有图片都获取失败了QAQ, 可能是网络原因或作品被删除, 请稍后再试')
    await MessageSender(bot=bot).send_msgs_and_recall(event=event, message_list=send_messages,
                                                      recall_time=moe_plugin_config.moe_plugin_auto_recall_time)


statistics = on_command(
    '图库统计',
    rule=to_me(),
    state=init_processor_state(name='MoeStatistics', enable_processor=False),
    permission=SUPERUSER | GUILD_SUPERUSER,
    aliases={'图库查询', '查询图库'},
    priority=20,
    block=True
)


@statistics.handle()
async def handle_parse_keywords(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    keyword = cmd_arg.extract_plain_text().strip()
    if keyword:
        state.update({'keyword': keyword})
    else:
        state.update({'keyword': ''})


@statistics.got('keyword', prompt='请输入要查询统计的关键词:')
async def handle_keyword_statistics(matcher: Matcher, keyword: str = ArgStr('keyword')):
    keywords = keyword.strip().split()
    if not keywords:
        statistics_data = await run_async_catching_exception(InternalPixiv.query_statistics)()
        msg_prefix = '本地数据库统计:'
    else:
        statistics_data = await run_async_catching_exception(InternalPixiv.query_statistics)(keywords=keywords)
        msg_prefix = f'本地数据库[{",".join(keywords)}]统计:'

    if isinstance(statistics_data, Exception):
        logger.error(f'MoeStatistics | 查询图库统计(keyword={keywords})失败, {statistics_data}')
        await matcher.finish('查询统计信息失败了QAQ, 详情请查看日志')

    msg = f'{msg_prefix}\n\n' \
          f'Total: {statistics_data.total}\n' \
          f'Moe: {statistics_data.moe}\n' \
          f'Setu: {statistics_data.setu}\n' \
          f'R18: {statistics_data.r18}'
    await matcher.finish(msg)


database_import = on_command(
    '导入图库',
    rule=to_me(),
    state=init_processor_state(name='MoeDatabaseImport', enable_processor=False),
    permission=SUPERUSER,
    aliases={'图库导入', 'imp'},
    priority=20,
    block=True
)


@database_import.handle()
async def handle_parse_import(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    cmd_args = cmd_arg.extract_plain_text().strip().split()
    arg_num = len(cmd_args)
    if arg_num == 1:
        state.update({'mode': cmd_args[0], 'pids': []})
    elif arg_num > 1:
        state.update({'mode': cmd_args[0], 'pids': [pid for pid in cmd_args[1:] if pid.isdigit()]})
    else:
        state.update({'pids': []})


@database_import.got('mode', prompt='请输入导入模式:\n【setu/moe】')
async def handle_database_import(state: T_State, matcher: Matcher, mode: str = ArgStr('mode')):
    mode = mode.strip()
    pids: list[int] = [int(x) for x in state.get('pids', [])]
    if not pids:
        await matcher.send('尝试从文件中读取导入文件列表')
        pids = await get_database_import_pids()
    if not pids:
        await matcher.finish('导入列表不存在, 详情请查看日志')

    match mode:
        case 'moe':
            tasks = [add_artwork_into_database(PixivArtwork(pid=pid), nsfw_tag=0, add_only=False) for pid in pids]
        case 'setu':
            tasks = [add_artwork_into_database(PixivArtwork(pid=pid), nsfw_tag=1, add_only=False) for pid in pids]
        case _:
            await matcher.reject('不支持的导入模式参数, 请在【setu/moe】中选择并重新输入:')
            return

    all_count = len(pids)
    await matcher.send(f'已获取导入列表, 总计: {all_count}, 开始获取作品信息~')
    import_result = await semaphore_gather(tasks=tasks, semaphore_num=25)
    fail_count = len([x for x in import_result if isinstance(x, Exception)])
    logger.success(f'MoeDatabaseImport | 导入操作已完成, 成功: {all_count - fail_count}, 总计: {all_count}')
    await matcher.finish(f'导入操作已完成, 成功: {all_count - fail_count}, 总计: {all_count}')
