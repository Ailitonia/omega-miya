"""
@Author         : Ailitonia
@Date           : 2021/06/28 21:41
@FileName       : shindan_maker
@Project        : nonebot2_miya
@Description    : shindan_maker 占卜插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import datetime
from typing import Annotated

from nonebot.log import logger
from nonebot.params import ArgStr, Depends
from nonebot.plugin import CommandGroup

from src.params.handler import get_command_str_single_arg_parser_handler, get_command_str_multi_args_parser_handler
from src.service import OmegaInterface, OmegaMessageSegment, enable_processor_state
from src.utils.process_utils import semaphore_gather

from .data_source import ShindanMaker


shindan_maker = CommandGroup(
    'shindan_maker',
    priority=10,
    block=True,
    state=enable_processor_state(
        name='ShindanMaker',
        level=50,
        auth_node='shindan_maker'
    ),
)


make_shindan = shindan_maker.command(
    tuple(),
    aliases={'shindan', 'Shindan', 'ShindanMaker'},
    handlers=[
        get_command_str_multi_args_parser_handler('shindan_arg')
    ]
)


@make_shindan.got('shindan_arg_0', prompt='你想做什么占卜呢?\n请输入想要做的占卜名称或ID:')
@make_shindan.got('shindan_arg_1', prompt='请输入您想要进行占卜对象的昵称:')
async def handle_shindan_make(
        interface: Annotated[OmegaInterface, Depends(OmegaInterface())],
        shindan_arg_0: Annotated[str, ArgStr('shindan_arg_0')],
        shindan_arg_1: Annotated[str, ArgStr('shindan_arg_1')],
) -> None:
    interface.refresh_matcher_state()

    shindan_title = shindan_arg_0.strip()
    input_name = shindan_arg_1.strip()

    # 加入日期使每天的结果不一样
    today = f"@{datetime.today().strftime('%Y%m%d')}@"
    input_name = f'{input_name}{today}'

    try:
        # 如果输入的时数字则直接作为 shindan_id 处理
        if shindan_title.isdigit():
            result = await ShindanMaker(shindan_id=int(shindan_title)).query_shindan_result(input_name=input_name)
        else:
            result = await ShindanMaker.fuzzy_shindan(shindan=shindan_title, input_name=input_name)
    except Exception as e:
        logger.error(f'ShindanMaker | 获取占卜结果 {shindan_title!r}-{input_name!r} 失败, {e}')
        await interface.send_reply('获取结果失败了, 请稍后再试或联系管理员处理')
        return

    if result is None:
        logger.warning(f'ShindanMaker | 未找到占卜 {shindan_title!r}')
        await interface.send_reply(f'没有找到{shindan_title!r}, 请确认占卜名或使用占卜ID重试')
        return

    # 删除之前加入的日期字符
    result_text = result.text.replace(today, '')
    send_msg = OmegaMessageSegment.text(result_text)

    # 结果有图片就处理图片
    if result.image_url:
        image_download_tasks = [ShindanMaker.download_image(url=x) for x in result.image_url]
        image_result = await semaphore_gather(tasks=image_download_tasks, semaphore_num=10, filter_exception=True)
        for img in image_result:
            send_msg += OmegaMessageSegment.image(img.path)

    await interface.send_reply(send_msg)


@shindan_maker.command(
    'search',
    aliases={'shindan-search', 'ShindanSearch'},
    handlers=[get_command_str_single_arg_parser_handler('keyword')]
).got('keyword', prompt='请输入搜索关键词:')
async def handle_shindan_searching(
        interface: Annotated[OmegaInterface, Depends(OmegaInterface())],
        keyword: Annotated[str, ArgStr('keyword')],
) -> None:
    interface.refresh_matcher_state()
    keyword = keyword.strip()

    try:
        searching_result = await ShindanMaker.complex_search(keyword=keyword)
        search_text = '\n'.join(f'{x.id}: {x.name}' for x in searching_result)
        await interface.send_reply(f'搜索到了以下占卜\n\n{search_text}')
    except Exception as e:
        logger.error(f'ShindanMaker | 搜索占卜名 {keyword!r} 失败, {e}')
        await interface.send_reply(f'搜索{keyword!r}失败了, 请稍后再试或联系管理员处理')


@shindan_maker.command(
    'ranking',
    aliases={'shindan-ranking', 'ShindanRanking'},
).handle()
async def handle_shindan_ranking(interface: Annotated[OmegaInterface, Depends(OmegaInterface())]) -> None:
    interface.refresh_matcher_state()

    try:
        ranking_result = await ShindanMaker.complex_ranking()
        ranking_text = '\n'.join(f'{x.id}: {x.name}' for x in ranking_result)
        await interface.send_reply(f'根据热度及排行榜获取到了以下占卜\n\n{ranking_text}')
    except Exception as e:
        logger.error(f'ShindanMaker | 获取占卜排行榜失败, {e}')
        await interface.send_reply(f'获取排行榜失败了, 请稍后再试或联系管理员处理')


__all__ = []
