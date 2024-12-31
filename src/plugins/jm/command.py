"""
@Author         : Ailitonia
@Date           : 2024/6/26 上午3:26
@FileName       : command
@Project        : nonebot2_miya
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Annotated

from nonebot.log import logger
from nonebot.params import ArgStr, Depends, ShellCommandArgs
from nonebot.plugin import CommandGroup
from nonebot.rule import Namespace

from src.params.handler import get_command_str_single_arg_parser_handler, get_shell_command_parse_failed_handler
from src.service import OmegaMatcherInterface as OmMI
from src.service import OmegaMessageSegment, enable_processor_state
from src.utils.comic18 import Comic18
from .helper import format_album_desc_msg, get_searching_argument_parser, parse_from_searching_parser

jm = CommandGroup(
    'jm',
    priority=10,
    block=True,
    state=enable_processor_state(
        name='JM',
        auth_node='allow_view',
        cooldown=60
    ),
)


@jm.command(
    tuple(),
    aliases={'JM', '18comic'},
    handlers=[get_command_str_single_arg_parser_handler('aid')],
).got('aid', prompt='想要查看哪个作品呢? 请输入作品ID:')
async def handle_preview_album_info(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        aid: Annotated[str, ArgStr('aid')],
) -> None:
    aid = aid.lower().strip().removeprefix('jm')
    if not aid.isdigit():
        await interface.finish_reply('作品ID应当为纯数字, 请确认后再重试吧')

    await interface.send_reply('稍等, 正在获取作品信息~')

    try:
        send_msg = await format_album_desc_msg(album=Comic18(album_id=int(aid)))
        await interface.send_auto_revoke(message=send_msg)
    except Exception as e:
        logger.error(f'JM | 获取作品(album_id={aid})信息失败, {e}')
        await interface.finish_reply(message='获取作品失败了QAQ, 可能是网络原因或者作品已经被删除, 请稍后再试')


@jm.command(
    'preview',
    aliases={'jm_preview'},
    handlers=[get_command_str_single_arg_parser_handler('aid')],
).got('aid', prompt='想要查看哪个作品呢? 请输入作品ID:')
async def handle_preview_gallery(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        aid: Annotated[str, ArgStr('aid')],
) -> None:
    aid = aid.lower().strip().removeprefix('jm')
    if not aid.isdigit():
        await interface.finish_reply('作品ID应当为纯数字, 请确认后再重试吧')

    await interface.send_reply('稍等, 正在下载图片~')

    try:
        gallery_preview = await Comic18(album_id=int(aid)).query_album_with_preview()
        await interface.send_auto_revoke(message=OmegaMessageSegment.image_file(gallery_preview.path))
    except Exception as e:
        logger.error(f'JM | 获取作品(album_id={aid})信息失败, {e}')
        await interface.finish_reply(message='获取作品失败了QAQ, 可能是网络原因或者作品已经被删除, 请稍后再试')


@jm.shell_command(
    'search',
    aliases={'jm_search'},
    parser=get_searching_argument_parser(),
    handlers=[get_shell_command_parse_failed_handler()],
).handle()
async def handle_jm_searching(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        args: Annotated[Namespace, ShellCommandArgs()],
) -> None:
    searching_args = parse_from_searching_parser(args=args)

    await interface.send_reply('获取搜索结果中, 请稍候')

    try:
        if ('分类' in searching_args.keyword) or ('排行' in searching_args.keyword):
            search_results = await Comic18.query_albums_list_with_preview(
                page=searching_args.page,
                type_=searching_args.type,
                time=searching_args.time,
                order=searching_args.order,
            )
        else:
            keyword = ' '.join(searching_args.keyword)
            search_results = await Comic18.search_photos_with_preview(
                search_query=keyword,
                page=searching_args.page,
                type_=searching_args.type,
                time=searching_args.time,
                order=searching_args.order,  # type: ignore
                main_tag=searching_args.tag,
            )

        await interface.send_auto_revoke(OmegaMessageSegment.image(search_results.path))
    except Exception as e:
        logger.error(f'JM | 获取搜索内容({searching_args})失败, {e}')
        await interface.finish_reply('获取搜索内容失败了QAQ, 请稍后再试')


__all__ = []
