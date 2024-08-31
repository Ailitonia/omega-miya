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
from nonebot.plugin import CommandGroup

from src.params.handler import get_command_str_single_arg_parser_handler
from src.params.permission import IS_ADMIN
from src.service import OmegaMatcherInterface as OmMI, OmegaMessageSegment, enable_processor_state
from src.utils.pixiv_api import Pixivision
from .helpers import (
    add_pixivision_sub,
    delete_pixivision_sub,
    format_pixivision_article_message,
    generate_pixivision_illustration_list_preview,
)
from .monitor import scheduler

pixivision = CommandGroup(
    'pixivision',
    permission=IS_ADMIN,
    priority=20,
    block=True,
    state=enable_processor_state(name='Pixivision', level=20),
)


@pixivision.command(
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
        page_preview = await generate_pixivision_illustration_list_preview(page=int(page))
        await interface.send_reply(OmegaMessageSegment.image(url=page_preview.path))
    except Exception as e:
        logger.error(f'获取 Pixivision 特辑页面(page={page})失败, {e!r}')
        await interface.send_reply('获取 Pixivision 特辑列表失败, 可能是网络原因异常, 请稍后再试')


@pixivision.command(
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
        article_preview = await format_pixivision_article_message(article=Pixivision(aid=(int(aid))))
        await interface.send_reply(article_preview)
    except Exception as e:
        logger.error(f'获取特辑(aid={aid})预览内容失败, {e!r}')
        await interface.send_reply('获取 Pixivision 特辑预览失败, 可能是网络原因异常, 请稍后再试')


@pixivision.command(
    'add-subscription',
    aliases={'pixivision订阅', 'Pixivision订阅'},
).handle()
async def handle_add_subscription(interface: Annotated[OmMI, Depends(OmMI.depend())]) -> None:
    scheduler.pause()  # 暂停计划任务避免中途检查更新
    try:
        await add_pixivision_sub(interface=interface)
        await interface.entity.commit_session()
        logger.success(f'{interface.entity}订阅 Pixivision 成功')
        msg = '订阅 Pixivision 成功'
    except Exception as e:
        logger.error(f'{interface.entity}订阅 Pixivision 失败, {e!r}')
        msg = '订阅 Pixivision 失败, 可能是网络异常或发生了意外的错误, 请稍后再试或联系管理员处理'
    scheduler.resume()

    await interface.finish_reply(msg)


@pixivision.command(
    'del-subscription',
    aliases={'取消pixivision订阅', '取消Pixivision订阅'},
).handle()
async def handle_del_subscription(interface: Annotated[OmMI, Depends(OmMI.depend())]) -> None:
    try:
        await delete_pixivision_sub(interface=interface)
        await interface.entity.commit_session()
        logger.success(f'{interface.entity}取消订阅 Pixivision 成功')
        msg = '已取消 Pixivision 订阅'
    except Exception as e:
        logger.error(f'{interface.entity}取消订阅 Pixivision 失败, {e!r}')
        msg = '取消 Pixivision 订阅失败, 请稍后再试或联系管理员处理'

    await interface.finish_reply(msg)


__all__ = []
