"""
@Author         : Ailitonia
@Date           : 2025/2/16 20:49
@FileName       : helpers
@Project        : omega-miya
@Description    : 工具类函数
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from random import randint
from typing import TYPE_CHECKING

from .consts import INTRO_TEXT

if TYPE_CHECKING:
    from src.service import OmegaMatcherInterface as OmMI

    from .models import RollResults
    from .session import StorySession


async def handle_story_init(story_session: 'StorySession', interface: 'OmMI', description: str | None) -> None:
    """处理首次交互, 初始化故事会话"""
    if story_session.is_processing:
        await interface.finish_reply('肉鸽娘正在努力工作中_<, 请稍后再试')

    if description is None:
        await interface.reject_arg_reply('description', INTRO_TEXT)

    await interface.send_reply('肉鸽娘正在编写剧本中_<, 请稍候')

    story = await story_session.init(description=description)
    await interface.send_reply(f'{story.background}\n\n{story.story_summary}')
    await interface.send_reply(story.characters_overview)
    await interface.send_reply(story.prologue)

    await interface.reject_arg_reply('description', '你的下一步行动是？')


async def handle_story_continue(story_session: 'StorySession', interface: 'OmMI', description: str | None) -> None:
    """处理后续交互，继续后续故事"""
    if story_session.is_processing:
        await interface.finish_reply('肉鸽娘正在努力工作中_<, 请稍后再试')

    if description is None:
        await interface.send_reply(story_session.current_situation)
        await interface.reject_arg_reply('description', '你的下一步行动是？')

    await interface.send_reply('肉鸽娘正在编写剧本中_<, 请稍候')
    roll_result = await story_session.roll(action=description)

    # 尝试获取用户属性值, 若不存在对应属性值时尝试随机获取
    attr_value = await interface.entity.query_character_attribute(
        attr_name=roll_result.characteristics,
        default_factory=lambda: randint(1, 100),
    )
    await interface.entity.commit_session()

    # 判定用户属性, 决定骰子事件后续发展
    checking_value = randint(1, 100)
    result_msg = _format_roll_result_text(
        roll_result=roll_result,
        attr_value=attr_value,
        checking_value=checking_value,
    )

    # 编写下一步剧情故事
    continue_story = await story_session.continue_story(player_action=description, roll_result=result_msg)

    await interface.send_reply(
        f'你进行了【{roll_result.characteristics}({attr_value})】检定\n1D100=>{checking_value}=>{result_msg}'
    )
    await interface.send_reply(continue_story.next_situation)
    await interface.send_reply(continue_story.player_options)

    await interface.reject_arg_reply('description', '你的下一步行动是？')


async def handle_fast_roll_action(
        story_session: 'StorySession',
        interface: 'OmMI',
        description: str,
        fast_generate_story_continue: bool = False,
) -> None:
    """处理快速行动检定"""
    if story_session.is_processing:
        await interface.finish_reply('骰子姬正在努力工作中_<, 请稍后再试')

    await interface.send_reply('骰子姬正在编写剧本中_<, 请稍候')

    current_situation = ''
    if fast_generate_story_continue:
        story_continue = await story_session.fast_story_continue(action=description)
        current_situation = f'{story_continue.background}\n\n{story_continue.current_situation}'

    roll_result = await story_session.fast_roll(action=description, current_situation=current_situation)

    # 尝试获取用户属性值, 若不存在对应属性值时尝试随机获取
    attr_value = await interface.entity.query_character_attribute(
        attr_name=roll_result.characteristics,
        default_factory=lambda: randint(1, 100),
    )
    await interface.entity.commit_session()

    # 判定用户属性, 决定骰子事件后续发展
    checking_value = randint(1, 100)
    result_msg = _format_roll_result_text(
        roll_result=roll_result,
        attr_value=attr_value,
        checking_value=checking_value,
    )

    sent_msg = (
        f'{current_situation}\n\n'
        f'你进行了【{roll_result.characteristics}({attr_value})】检定\n'
        f'1D100=>{checking_value}=>{result_msg}'
    ).strip()
    await interface.send_reply(sent_msg)


def _format_roll_result_text(roll_result: 'RollResults', attr_value: int, checking_value: int) -> str:
    """进行掷骰判定并格式化结果文本"""
    if attr_value > checking_value:
        if checking_value < attr_value * 0.1:
            result_msg = f'大成功！！\n{roll_result.completed_success}'
        else:
            result_msg = f'成功！\n{roll_result.success}'
    else:
        if checking_value > 95:
            result_msg = f'大失败~\n{roll_result.critical_failure}'
        else:
            result_msg = f'失败~\n{roll_result.failure}'

    return result_msg


__all__ = [
    'handle_story_init',
    'handle_story_continue',
    'handle_fast_roll_action',
]
