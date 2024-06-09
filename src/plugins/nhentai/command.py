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
from src.service import OmegaInterface, OmegaMessageSegment, enable_processor_state
from src.utils.nhentai import NhentaiGallery

from .helper import get_searching_argument_parser, parse_from_searching_parser, format_gallery_desc_msg


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
    tuple(),
    aliases={'nh', 'NH'},
    handlers=[get_command_str_single_arg_parser_handler('gid')],
).got('gid', prompt='想要查看哪个作品呢? 请输入作品ID:')
async def handle_preview_gallery(
        interface: Annotated[OmegaInterface, Depends(OmegaInterface())],
        gid: Annotated[str, ArgStr('gid')]
) -> None:
    interface.refresh_matcher_state()

    gid = gid.strip()
    if not gid.isdigit():
        await interface.finish('作品ID应当为纯数字, 请确认后再重试吧')

    await interface.send_reply('稍等, 正在获取作品信息~')

    try:
        send_msg = await format_gallery_desc_msg(gallery=NhentaiGallery(gallery_id=int(gid)))
        await interface.send_msg_auto_revoke(message=send_msg)
    except Exception as e:
        logger.error(f'Nhentai | 获取作品(gallery_id={gid})信息失败, {e}')
        await interface.send_reply(message='获取作品失败了QAQ, 可能是网络原因或者作品已经被删除, 请稍后再试')


@nhentai.command(
    'preview',
    aliases={'nh_preview'},
    handlers=[get_command_str_single_arg_parser_handler('gid')],
).got('gid', prompt='想要查看哪个作品呢? 请输入作品ID:')
async def handle_preview_gallery(
        interface: Annotated[OmegaInterface, Depends(OmegaInterface())],
        gid: Annotated[str, ArgStr('gid')]
) -> None:
    interface.refresh_matcher_state()

    gid = gid.strip()
    if not gid.isdigit():
        await interface.finish('作品ID应当为纯数字, 请确认后再重试吧')

    await interface.send_reply('稍等, 正在下载图片~')

    try:
        gallery_preview = await NhentaiGallery(gallery_id=int(gid)).query_gallery_with_preview()
        await interface.send_msg_auto_revoke(message=OmegaMessageSegment.image(gallery_preview.path))
    except Exception as e:
        logger.error(f'Nhentai | 获取作品(gallery_id={gid})预览失败, {e}')
        await interface.send_reply(message='获取作品失败了QAQ, 可能是网络原因或者作品已经被删除, 请稍后再试')


@nhentai.shell_command(
    'search',
    aliases={'nh_search'},
    parser=get_searching_argument_parser(),
    handlers=[get_shell_command_parse_failed_handler()],
).handle()
async def handle_nhentai_searching(
        interface: Annotated[OmegaInterface, Depends(OmegaInterface())],
        args: Annotated[Namespace, ShellCommandArgs()]
) -> None:
    searching_args = parse_from_searching_parser(args=args)
    interface.refresh_matcher_state()

    keyword = ' '.join(searching_args.keyword)
    await interface.send_reply('获取搜索结果中, 请稍候')

    try:
        search_results = await NhentaiGallery.search_gallery_with_preview(
            keyword=keyword, page=searching_args.page, sort=searching_args.sort
        )
        await interface.send_msg_auto_revoke(OmegaMessageSegment.image(search_results.path))
    except Exception as e:
        logger.error(f'NhentaiSearching | 获取搜索内容({searching_args})失败, {e}')
        await interface.send_reply('获取搜索内容失败了QAQ, 请稍后再试')


__all__ = []
