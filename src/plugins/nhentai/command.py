"""
@Author         : Ailitonia
@Date           : 2024/6/8 下午11:10
@FileName       : command
@Project        : nonebot2_miya
@Description    : Nhentai
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
from src.utils.nhentai import NhentaiGallery
from .helper import format_gallery_desc_msg, get_searching_argument_parser, parse_from_searching_parser

nhentai = CommandGroup(
    'nhentai',
    priority=10,
    block=True,
    state=enable_processor_state(
        name='nhentai',
        auth_node='allow_view',
        cooldown=60
    ),
)


@nhentai.command(
    (),
    aliases={'nh', 'NH'},
    handlers=[get_command_str_single_arg_parser_handler('gid')],
).got('gid', prompt='想要查看哪个作品呢? 请输入作品ID:')
async def handle_get_nhentai_gallery(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        gid: Annotated[str, ArgStr('gid')],
) -> None:
    gid = gid.strip()
    if not gid.isdigit():
        await interface.finish_reply('作品ID应当为纯数字, 请确认后再重试吧')

    await interface.send_reply('稍等, 正在获取作品信息~')

    try:
        send_msg = await format_gallery_desc_msg(gallery=NhentaiGallery(gallery_id=int(gid)))
        await interface.send_auto_revoke(send_msg)
    except Exception as e:
        logger.error(f'Nhentai | 获取作品(gallery_id={gid})信息失败, {e}')
        await interface.finish_reply('获取作品失败了QAQ, 可能是网络原因或者作品已经被删除, 请稍后再试')


@nhentai.command(
    'preview',
    aliases={'nh_preview'},
    handlers=[get_command_str_single_arg_parser_handler('gid')],
).got('gid', prompt='想要查看哪个作品呢? 请输入作品ID:')
async def handle_preview_hentai_gallery(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        gid: Annotated[str, ArgStr('gid')],
) -> None:
    gid = gid.strip()
    if not gid.isdigit():
        await interface.finish_reply('作品ID应当为纯数字, 请确认后再重试吧')

    await interface.send_reply('稍等, 正在下载图片~')

    try:
        gallery_preview = await NhentaiGallery(gallery_id=int(gid)).query_gallery_with_preview()
        await interface.send_auto_revoke(OmegaMessageSegment.image(await gallery_preview.get_hosting_path()))
    except Exception as e:
        logger.error(f'Nhentai | 获取作品(gallery_id={gid})预览失败, {e}')
        await interface.finish_reply('获取作品失败了QAQ, 可能是网络原因或者作品已经被删除, 请稍后再试')


@nhentai.shell_command(
    'search',
    aliases={'nh_search'},
    parser=get_searching_argument_parser(),
    handlers=[get_shell_command_parse_failed_handler()],
).handle()
async def handle_nhentai_searching(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        args: Annotated[Namespace, ShellCommandArgs()]
) -> None:
    searching_args = parse_from_searching_parser(args=args)
    keyword = ' '.join(searching_args.keyword)

    await interface.send_reply('获取搜索结果中, 请稍候')

    try:
        search_results = await NhentaiGallery.search_gallery_with_preview(
            keyword=keyword, page=searching_args.page, sort=searching_args.sort
        )
        await interface.send_auto_revoke(OmegaMessageSegment.image(await search_results.get_hosting_path()))
    except Exception as e:
        logger.error(f'NhentaiSearching | 获取搜索内容({searching_args})失败, {e}')
        await interface.finish_reply('获取搜索内容失败了QAQ, 请稍后再试')


__all__ = []
