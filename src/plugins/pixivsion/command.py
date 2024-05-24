"""
@Author         : Ailitonia
@Date           : 2022/04/30 18:11
@FileName       : pixivision.py
@Project        : nonebot2_miya
@Description    : Pixiv 助手
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Annotated

from nonebot.log import logger
from nonebot.params import ArgStr, Depends
from nonebot.plugin import CommandGroup

from src.params.handler import get_command_str_single_arg_parser_handler
from src.params.permission import IS_ADMIN
from src.service import OmegaInterface, OmegaMessageSegment, enable_processor_state
from src.utils.pixiv_api import Pixivision

from .monitor import scheduler
from .helpers import add_pixivision_sub, delete_pixivision_sub, format_pixivision_update_message


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
    handlers=[
        get_command_str_single_arg_parser_handler('page', default='1')
    ],
    priority=10,
).got('page')
async def handle_query_articles_list(page: Annotated[str, ArgStr('page')]) -> None:
    interface = OmegaInterface()

    page = page.strip()
    if not page.isdigit():
        await interface.send_at_sender('非有效的页码, 页码应当为纯数字, 已取消操作')
        return

    try:
        page_preview = await Pixivision.query_illustration_list_with_preview(page=int(page))
    except Exception as e:
        logger.error(f'获取 Pixivision 特辑页面(page={page})失败, {e!r}')
        await interface.send_at_sender('获取 Pixivision 特辑列表失败, 可能是网络原因异常, 请稍后再试')
        return

    await interface.send(OmegaMessageSegment.image(url=page_preview.path))


@pixivision.command(
    'query-article',
    aliases={'Pixivision特辑', 'pixivision特辑'},
    permission=None,
    handlers=[
        get_command_str_single_arg_parser_handler('aid')
    ],
    priority=10,
).got('aid', prompt='想要查看哪个 Pixivision 特辑呢? 请输入特辑文章 ID:')
async def handle_query_article(aid: Annotated[str, ArgStr('aid')]) -> None:
    interface = OmegaInterface()

    aid = aid.strip()
    if not aid.isdigit():
        await interface.send_at_sender('非有效的特辑文章 ID, 特辑文章 ID 应当为纯数字, 已取消操作')
        return

    try:
        article_preview = await format_pixivision_update_message(article=Pixivision(aid=(int(aid))))
    except Exception as e:
        logger.error(f'获取特辑(aid={aid})预览内容失败, {e!r}')
        await interface.send_at_sender('获取 Pixivision 特辑预览失败, 可能是网络原因异常, 请稍后再试')
        return

    await interface.send(article_preview)


@pixivision.command(
    'add-subscription',
    aliases={'pixivision订阅', 'Pixivision订阅'},
).handle()
async def handle_add_subscription(
        interface: Annotated[OmegaInterface, Depends(OmegaInterface())]
) -> None:
    interface.refresh_matcher_state()

    scheduler.pause()  # 暂停计划任务避免中途检查更新
    try:
        await add_pixivision_sub(interface=interface)
        await interface.entity.commit_session()
        logger.success(f'{interface.entity}订阅 Pixivision 成功')
        msg = f'订阅 Pixivision 成功'
    except Exception as e:
        logger.error(f'{interface.entity}订阅 Pixivision 失败, {e!r}')
        msg = f'订阅 Pixivision 失败, 可能是网络异常或发生了意外的错误, 请稍后再试或联系管理员处理'
    scheduler.resume()

    await interface.send_at_sender(msg)


@pixivision.command(
    'del-subscription',
    aliases={'取消pixivision订阅', '取消Pixivision订阅'},
).handle()
async def handle_del_subscription(
        interface: Annotated[OmegaInterface, Depends(OmegaInterface())]
) -> None:
    interface.refresh_matcher_state()

    try:
        await delete_pixivision_sub(interface=interface)
        await interface.entity.commit_session()
        logger.success(f'{interface.entity}取消订阅 Pixivision 成功')
        msg = f'已取消 Pixivision 订阅'
    except Exception as e:
        logger.error(f'{interface.entity}取消订阅 Pixivision 失败, {e!r}')
        msg = f'取消 Pixivision 订阅失败, 请稍后再试或联系管理员处理'
    await interface.send_at_sender(msg)


__all__ = []
