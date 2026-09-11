"""
@Author         : Ailitonia
@Date           : 2023/3/19 16:48
@FileName       : universal
@Project        : nonebot2_miya
@Description    : 通用 processor
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.adapters import Bot as BaseBot
from nonebot.adapters import Event as BaseEvent
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.message import event_postprocessor, event_preprocessor, run_postprocessor, run_preprocessor

from src.database import DATABASE_SESSION
from .cancellation import preprocessor_cancellation
from .cooldown import preprocessor_cooldown
from .cost import preprocessor_plugin_cost
from .friendship import postprocessor_friendship
from .history import postprocessor_history
from .permission import preprocessor_permission
from .plugin import preprocessor_plugin_manager
from .processor_utils import enable_processor_state
from .rate_limiting import preprocessor_rate_limiting
from .statistic import postprocessor_statistic


@event_preprocessor
async def handle_universal_event_preprocessor(
        bot: BaseBot,
        event: BaseEvent,
) -> None:
    """事件预处理"""
    # 处理速率控制
    await preprocessor_rate_limiting(bot=bot, event=event)


@run_preprocessor
async def handle_universal_run_preprocessor(
        bot: BaseBot,
        event: BaseEvent,
        matcher: Matcher,
        db_session: DATABASE_SESSION,
) -> None:
    """运行预处理"""
    # 处理插件管理
    await preprocessor_plugin_manager(bot=bot, event=event, matcher=matcher, db_session=db_session)

    try:
        # 处理消息事件
        message = event.get_message()
        # 处理用户取消
        await preprocessor_cancellation(matcher=matcher, message=message)
        # 处理权限
        await preprocessor_permission(bot=bot, event=event, matcher=matcher, db_session=db_session)
        # 处理冷却
        await preprocessor_cooldown(bot=bot, event=event, matcher=matcher, db_session=db_session)
        # 处理消耗
        await preprocessor_plugin_cost(bot=bot, event=event, matcher=matcher, db_session=db_session)
    except (NotImplementedError, ValueError) as e:
        logger.debug(f'UniversalRunPreprocessor ignored {event} without message, {e}')
    except Exception as e:
        logger.error(f'UniversalRunPreprocessor handle {event} message failed, {e}')
        raise e


@run_postprocessor
async def handle_universal_run_postprocessor(
        bot: BaseBot,
        event: BaseEvent,
        matcher: Matcher,
        db_session: DATABASE_SESSION,
) -> None:
    """运行后处理"""
    # 处理插件统计
    await postprocessor_statistic(bot=bot, event=event, matcher=matcher, db_session=db_session)


@event_postprocessor
async def handle_universal_event_postprocessor(
        bot: BaseBot,
        event: BaseEvent,
        db_session: DATABASE_SESSION,
) -> None:
    """运行消息事件后处理"""
    # 处理消息事件
    try:
        message = event.get_message()
        # 处理好感度
        await postprocessor_friendship(bot=bot, event=event, db_session=db_session)
        # 处理历史记录
        await postprocessor_history(bot=bot, event=event, message=message, db_session=db_session)
    except (NotImplementedError, ValueError) as e:
        logger.debug(f'UniversalEventPostprocessor ignored {event} without message, {e}')
    except Exception as e:
        logger.error(f'UniversalEventPostprocessor handle {event} message failed, {e}')
        raise e


__all__ = [
    'enable_processor_state',
]
