"""
@Author         : Ailitonia
@Date           : 2024/8/17 下午7:56
@FileName       : statistics_command.py
@Project        : nonebot2_miya
@Description    : 数据库统计信息查询命令
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import Sequence

from arclet.alconna import Alconna, Args, CommandMeta, MultiVar, Option
from nonebot.log import logger
from nonebot.permission import SUPERUSER
from nonebot.rule import to_me
from nonebot_plugin_alconna import Match, on_alconna

from src.database import ArtworkCollectionDAL
from src.params.depends import EVENT_M_IFACE
from src.service import enable_processor_state


@on_alconna(
    Alconna(
        'artwork-collection-statistics',
        Option('--origin|-o', Args['origin?#图库来源', str], help_text='指定统计作品的来源'),
        Option('--keywords|-k', Args['keywords?#搜索关键词', MultiVar(str)], help_text='指定统计作品关键词'),
        meta=CommandMeta(
            description='图库作品统计信息查询',
            usage='图库统计 [-o <origin>] [-k <keywords...>]',
            example='图库统计 -o pixiv -k 原创 风景',
            compact=True,
        ),
    ),
    rule=to_me(),
    use_cmd_start=True,
    aliases={'图库统计', '图库查询', '查询图库'},
    permission=SUPERUSER,
    priority=10,
    block=True,
    default_state=enable_processor_state(
        name='ArtworkCollectionStatistics',
        enable_processor=False
    ),
).handle()
async def handle_artwork_collection_statistics(
        interface: EVENT_M_IFACE,
        origin: Match[str],
        keywords: Match[Sequence[str]],
) -> None:
    target_origin = origin.result.strip() if origin.available and origin.result.strip() else None
    keywords_text = (
        [k for k in (keyword.strip() for keyword in keywords.result) if k] if keywords.available else None
    )

    try:
        async with ArtworkCollectionDAL.create() as dal:
            classification_statistic = await dal.query_classification_statistic(target_origin, keywords_text)
            rating_statistic = await dal.query_rating_statistic(target_origin, keywords_text)
    except Exception as e:
        logger.error(
            f'ArtworkCollectionStatistics | 查询数据库作品{target_origin!r} {keywords_text!r}统计信息失败, {e}'
        )
        await interface.finish_reply(f'查询数据库作品{target_origin!r} {keywords_text!r}统计信息失败, 详情请查看日志')

    prefix_text = f'本地数据库{target_origin if target_origin is not None else "全量"!r}统计信息:'
    classification_text = (
        f'-- Classification --\n'
        f'Unused: {classification_statistic.unused}\n'
        f'Uncategorized: {classification_statistic.uncategorized}\n'
        f'AIGenerated: {classification_statistic.ai_generated}\n'
        f'Confirmed: {classification_statistic.external_confirmed + classification_statistic.human_confirmed}\n'
        f'Featured: {classification_statistic.featured}'
    )
    rating_text = (
        f'-- Rating --\n'
        f'Unknown: {rating_statistic.unknown}\n'
        f'General: {rating_statistic.general}\n'
        f'Sensitive: {rating_statistic.sensitive}\n'
        f'Questionable: {rating_statistic.questionable}\n'
        f'Explicit: {rating_statistic.explicit}'
    )
    send_message = f'{prefix_text}\n\n{classification_text}\n\n{rating_text}'

    await interface.finish_reply(send_message)


__all__ = []
