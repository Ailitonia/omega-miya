"""
@Author         : Ailitonia
@Date           : 2025/2/16 21:39
@FileName       : command
@Project        : omega-miya
@Description    : 故事肉鸽插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Annotated

from nonebot.exception import MatcherException
from nonebot.log import logger
from nonebot.params import ArgStr, Depends
from nonebot.plugin import CommandGroup

from src.params.handler import get_command_str_single_arg_parser_handler
from src.service import OmegaMatcherInterface as OmMI
from src.service import enable_processor_state
from .helpers import handle_fast_roll_action, handle_story_continue, handle_story_init
from .session import get_story_session, remove_story_session

roguelike_story = CommandGroup(
    'roguelike-story',
    block=True,
    state=enable_processor_state(
        name='RoguelikeStory',
        level=30,
        cooldown=60,
    ),
)


@roguelike_story.command(
    'start',
    aliases={'故事肉鸽启动', '肉鸽故事启动', '继续故事肉鸽', '继续肉鸽故事'},
    handlers=[get_command_str_single_arg_parser_handler('description', ensure_key=True)],
).got('description')
async def handle_story_start(
        interface: Annotated[OmMI, Depends(OmMI.depend('event'))],
        description: Annotated[str | None, ArgStr('description')],
) -> None:
    try:
        story_session = get_story_session(interface=interface)
    except Exception as e:
        logger.warning(f'Roguelike Story | {interface.entity}获取故事会话失败, {e}')
        await interface.finish_reply('获取故事会话失败, 请稍后再试或联系管理员处理')

    try:
        if not story_session.is_inited:
            await handle_story_init(story_session=story_session, interface=interface, description=description)
        else:
            await handle_story_continue(story_session=story_session, interface=interface, description=description)
    except MatcherException as e:
        raise e
    except Exception as e:
        logger.warning(f'Roguelike Story | 生成失败, {e}')
        await interface.finish_reply('肉鸽姬还没有想好接下来会发生什么, 请稍后再试QAQ')


@roguelike_story.command(
    'remove',
    aliases={'结束故事肉鸽', '结束肉鸽故事', '移除故事肉鸽', '移除肉鸽故事', '故事肉鸽重开', '肉鸽故事重开'},
    handlers=[get_command_str_single_arg_parser_handler('ensure', ensure_key=True)],
).got('ensure')
async def handle_story_remove(
        interface: Annotated[OmMI, Depends(OmMI.depend('event'))],
        ensure: Annotated[str | None, ArgStr('ensure')],
) -> None:
    try:
        if ensure is None:
            await interface.reject_arg_reply('ensure', '你确认要终结这个肉鸽故事吗？\n【是/否】')
        elif ensure in ['是', '确认', 'Yes', 'yes', 'Y', 'y']:
            remove_story_session(interface=interface)
            await interface.finish_reply('目前的肉鸽故事已移除，你可以重新开始新的冒险了~')
        else:
            await interface.finish_reply('已取消操作')
    except MatcherException as e:
        raise e
    except Exception as e:
        logger.warning(f'Roguelike Story | {interface.entity}获取故事会话失败, {e}')
        await interface.finish_reply('获取故事会话失败, 请稍后再试或联系管理员处理')


@roguelike_story.command(
    'action',
    aliases={'行动检定'},
    handlers=[get_command_str_single_arg_parser_handler('description')],
).got('description', prompt='请输入需要检定的行动或任务描述')
async def handle_action_checking(
        interface: Annotated[OmMI, Depends(OmMI.depend('user'))],
        description: Annotated[str, ArgStr('description')],
) -> None:
    try:
        story_session = get_story_session(interface=interface)
    except Exception as e:
        logger.warning(f'Roguelike Story | {interface.entity}获取故事会话失败, {e}')
        await interface.finish_reply('获取故事会话失败, 请稍后再试或联系管理员处理')

    try:
        await handle_fast_roll_action(
            story_session=story_session,
            interface=interface,
            description=description,
            fast_generate_story_continue=True,
        )
    except MatcherException as e:
        raise e
    except Exception as e:
        logger.warning(f'Roguelike Story | 生成失败, {e}')
        await interface.finish_reply('肉鸽姬还没有想好接下来会发生什么, 请稍后再试QAQ')


@roguelike_story.command(
    'fast-action',
    aliases={'快速行动检定'},
    handlers=[get_command_str_single_arg_parser_handler('description')],
).got('description', prompt='请输入需要检定的行动或任务描述')
async def handle_fast_action_checking(
        interface: Annotated[OmMI, Depends(OmMI.depend('user'))],
        description: Annotated[str, ArgStr('description')],
) -> None:
    try:
        story_session = get_story_session(interface=interface)
    except Exception as e:
        logger.warning(f'Roguelike Story | {interface.entity}获取故事会话失败, {e}')
        await interface.finish_reply('获取故事会话失败, 请稍后再试或联系管理员处理')

    try:
        await handle_fast_roll_action(story_session=story_session, interface=interface, description=description)
    except MatcherException as e:
        raise e
    except Exception as e:
        logger.warning(f'Roguelike Story | 生成失败, {e}')
        await interface.finish_reply('肉鸽姬还没有想好接下来会发生什么, 请稍后再试QAQ')


__all__ = []
