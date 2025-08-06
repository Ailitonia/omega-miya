"""
@Author         : Ailitonia
@Date           : 2022/04/30 18:11
@FileName       : pixivision.py
@Project        : nonebot2_miya
@Description    : Pixivision 助手
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Annotated

from nonebot.log import logger
from nonebot.params import ArgStr, Depends

from src.params.handler import get_command_str_single_arg_parser_handler
from src.service import OmegaMatcherInterface as OmMI
from src.service import OmegaMessageSegment, OmegaSubscriptionHandlerManager
from .subscription_source import PixivisionSubscriptionManager

_pixivision_handler_manager = OmegaSubscriptionHandlerManager(
    subscription_manager=PixivisionSubscriptionManager,
    command_prefix='Pixivision',
    aliases_command_prefix={'pixivision'},
    default_sub_id='pixivision',
)

_pixivision = _pixivision_handler_manager.register_handlers()
"""注册 Pixivision 订阅流程 Handlers"""


@_pixivision.command(
    'query-articles-list',
    aliases={'Pixivision列表', 'pixivision列表'},
    permission=None,
    handlers=[get_command_str_single_arg_parser_handler('page', default='1')],
    priority=10,
).got('page')
async def handle_query_articles_list(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        page: Annotated[str, ArgStr('page')],
) -> None:
    page = page.strip()
    if not page.isdigit():
        await interface.finish_reply('页码应当为纯数字, 请确认后再重试吧')

    await interface.send_reply('稍等, 正在获取 Pixivision 特辑列表~')

    try:
        page_preview = await PixivisionSubscriptionManager.generate_pixivision_illustration_list_preview(int(page))
        await interface.send_reply(OmegaMessageSegment.image(await page_preview.get_hosting_path()))
    except Exception as e:
        logger.error(f'获取 Pixivision 特辑页面(page={page})失败, {e!r}')
        await interface.send_reply('获取 Pixivision 特辑列表失败, 可能是网络原因异常, 请稍后再试')


@_pixivision.command(
    'query-article',
    aliases={'Pixivision特辑', 'pixivision特辑'},
    permission=None,
    handlers=[get_command_str_single_arg_parser_handler('aid')],
    priority=10,
).got('aid', prompt='想要查看哪个 Pixivision 特辑呢? 请输入特辑 ID:')
async def handle_query_article(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        aid: Annotated[str, ArgStr('aid')],
) -> None:
    aid = aid.strip()
    if not aid.isdigit():
        await interface.finish_reply('特辑 ID 应当为纯数字, 请确认后再重试吧')

    await interface.send_reply('稍等, 正在获取 Pixivision 特辑作品内容~')

    try:
        article_preview = await PixivisionSubscriptionManager.format_pixivision_article_message(int(aid))
        await interface.send_reply(article_preview)
    except Exception as e:
        logger.error(f'获取特辑(aid={aid})预览内容失败, {e!r}')
        await interface.send_reply('获取 Pixivision 特辑预览失败, 可能是网络原因异常, 请稍后再试')


__all__ = []
