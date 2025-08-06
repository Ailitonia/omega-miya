"""
@Author         : Ailitonia
@Date           : 2025/2/16 20:55
@FileName       : session
@Project        : omega-miya
@Description    : 会话管理
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from asyncio import Lock as AsyncLock
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.utils.openai_api import ChatSession
from .config import roguelike_story_plugin_config
from .consts import (
    CONTINUE_PROMPT,
    FAST_STORY_CONTINUE_PROMPT,
    SAFE_ROLL_PROMPT,
    STORY_CREATE_PROMPT,
    UNLIMITED_ROLL_PROMPT,
)
from .models import (
    CurrentSituation,
    FastCurrentSituation,
    NextSituation,
    RollCondition,
    RollResults,
    Story,
)

if TYPE_CHECKING:
    from src.service import OmegaMatcherInterface as OmMI

_SESSIONS: dict[str, 'StorySession'] = {}
"""全局缓存的所有故事会话, KEY 为各个事件主体 Entity ID"""


@dataclass
class StorySession:
    """故事会话, 每个事件主体 Entity 唯一"""
    current_situation: str = field(default_factory=str)
    _continued_session: ChatSession | None = field(default=None)
    _roll_session: ChatSession | None = field(default=None)
    _is_inited: bool = field(default=False)
    _lock: AsyncLock = field(default_factory=AsyncLock)

    @property
    def is_processing(self) -> bool:
        return self._lock.locked()

    @property
    def is_inited(self) -> bool:
        return self._is_inited

    @property
    def continued_session(self) -> ChatSession:
        if self._continued_session is None:
            raise RuntimeError('StorySession has not been initialized')
        return self._continued_session

    @property
    def roll_session(self) -> ChatSession:
        if self._roll_session is None:
            raise RuntimeError('StorySession has not been initialized')
        return self._roll_session

    async def init(self, description: str) -> Story:
        """根据提供的描述生成故事框架, 并初始化故事会话"""
        if self._is_inited:
            raise RuntimeError('StorySession has already been initialized')

        if self.is_processing:
            raise RuntimeError('StorySession is processing')

        async with self._lock:
            # 生成故事框架
            story = await ChatSession.create(
                service_name=roguelike_story_plugin_config.roguelike_story_plugin_ai_service_name,
                model_name=roguelike_story_plugin_config.roguelike_story_plugin_ai_model_name,
                init_system_message=STORY_CREATE_PROMPT,
            ).advance_chat(
                description,
                response_format=roguelike_story_plugin_config.roguelike_story_plugin_ai_json_output,
                model_type=Story,
                temperature=roguelike_story_plugin_config.roguelike_story_plugin_ai_temperature,
                max_tokens=roguelike_story_plugin_config.roguelike_story_plugin_ai_max_tokens,
                timeout=roguelike_story_plugin_config.roguelike_story_plugin_ai_timeout,
            )

        # 初始化续写 Session
        current_continue_prompt = f'{CONTINUE_PROMPT}\n\n{story.overview}'
        self._continued_session = ChatSession.create(
            service_name=roguelike_story_plugin_config.roguelike_story_plugin_ai_service_name,
            model_name=roguelike_story_plugin_config.roguelike_story_plugin_ai_model_name,
            init_system_message=current_continue_prompt,
        )

        # 初始化掷骰 Session
        if roguelike_story_plugin_config.roguelike_story_plugin_ai_safe_roll:
            current_roll_prompt = f'{SAFE_ROLL_PROMPT}\n\n{story.overview}'
        else:
            current_roll_prompt = f'{UNLIMITED_ROLL_PROMPT}\n\n{story.overview}'
        self._roll_session = ChatSession.create(
            service_name=roguelike_story_plugin_config.roguelike_story_plugin_ai_service_name,
            model_name=roguelike_story_plugin_config.roguelike_story_plugin_ai_model_name,
            init_system_message=current_roll_prompt,
        )

        self.current_situation = story.prologue
        self._is_inited = True
        return story

    async def fast_story_continue(self, action: str) -> FastCurrentSituation:
        """"快速故事续写, 无需前文预设"""
        if self.is_processing:
            raise RuntimeError('StorySession is processing')

        async with self._lock:
            continue_result = await ChatSession.create(
                service_name=roguelike_story_plugin_config.roguelike_story_plugin_ai_service_name,
                model_name=roguelike_story_plugin_config.roguelike_story_plugin_ai_model_name,
                init_system_message=FAST_STORY_CONTINUE_PROMPT,
            ).advance_chat(
                action,
                response_format=roguelike_story_plugin_config.roguelike_story_plugin_ai_json_output,
                model_type=FastCurrentSituation,
                temperature=roguelike_story_plugin_config.roguelike_story_plugin_ai_temperature,
                max_tokens=roguelike_story_plugin_config.roguelike_story_plugin_ai_max_tokens,
                timeout=roguelike_story_plugin_config.roguelike_story_plugin_ai_timeout,
            )

        return continue_result

    async def fast_roll(self, action: str, *, current_situation: str = '') -> RollResults:
        """快速掷骰, 无需前文预设"""
        if self.is_processing:
            raise RuntimeError('StorySession is processing')

        if roguelike_story_plugin_config.roguelike_story_plugin_ai_safe_roll:
            roll_prompt = SAFE_ROLL_PROMPT
        else:
            roll_prompt = UNLIMITED_ROLL_PROMPT

        async with self._lock:
            roll_result = await ChatSession.create(
                service_name=roguelike_story_plugin_config.roguelike_story_plugin_ai_service_name,
                model_name=roguelike_story_plugin_config.roguelike_story_plugin_ai_model_name,
                init_system_message=roll_prompt,
            ).advance_chat(
                RollCondition(current_situation=current_situation, action=action).model_dump_json(),
                response_format=roguelike_story_plugin_config.roguelike_story_plugin_ai_json_output,
                model_type=RollResults,
                temperature=roguelike_story_plugin_config.roguelike_story_plugin_ai_temperature,
                max_tokens=roguelike_story_plugin_config.roguelike_story_plugin_ai_max_tokens,
                timeout=roguelike_story_plugin_config.roguelike_story_plugin_ai_timeout,
            )

        return roll_result

    async def roll(self, action: str) -> RollResults:
        """根据提供的玩家行动描述, 对行动结果进行掷骰, 返回可能的不同结果的事件描述"""
        if not self._is_inited:
            raise RuntimeError('StorySession has not been initialized')

        if self.is_processing:
            raise RuntimeError('StorySession is processing')

        async with self._lock:
            roll_result = await self.roll_session.advance_chat(
                RollCondition(current_situation=self.current_situation, action=action).model_dump_json(),
                response_format=roguelike_story_plugin_config.roguelike_story_plugin_ai_json_output,
                model_type=RollResults,
                temperature=roguelike_story_plugin_config.roguelike_story_plugin_ai_temperature,
                max_tokens=roguelike_story_plugin_config.roguelike_story_plugin_ai_max_tokens,
                timeout=roguelike_story_plugin_config.roguelike_story_plugin_ai_timeout,
            )

        return roll_result

    async def continue_story(self, player_action: str, roll_result: str) -> NextSituation:
        """根据当前故事进度、玩家行为及掷骰结果, 生成后续故事"""
        if not self._is_inited:
            raise RuntimeError('StorySession has not been initialized')

        if self.is_processing:
            raise RuntimeError('StorySession is processing')

        async with self._lock:
            continued_result = await self.continued_session.advance_chat(
                CurrentSituation(
                    current_situation=self.current_situation,
                    player_action=player_action,
                    roll_result=roll_result,
                ).model_dump_json(),
                response_format=roguelike_story_plugin_config.roguelike_story_plugin_ai_json_output,
                model_type=NextSituation,
                temperature=roguelike_story_plugin_config.roguelike_story_plugin_ai_temperature,
                max_tokens=roguelike_story_plugin_config.roguelike_story_plugin_ai_max_tokens,
                timeout=roguelike_story_plugin_config.roguelike_story_plugin_ai_timeout,
            )

        self.current_situation = continued_result.next_situation
        return continued_result

    def delete(self) -> None:
        del self._continued_session
        del self._roll_session
        del self._lock


def get_story_session(interface: 'OmMI') -> StorySession:
    """获取事件主体 Entity 对应的故事会话, 如果会话不存在则新建"""
    if interface.entity.tid in _SESSIONS:
        return _SESSIONS[interface.entity.tid]
    else:
        _SESSIONS[interface.entity.tid] = StorySession()
        return _SESSIONS[interface.entity.tid]


def remove_story_session(interface: 'OmMI') -> None:
    """移除事件主体 Entity 对应的故事会话"""
    if interface.entity.tid in _SESSIONS:
        _SESSIONS[interface.entity.tid].delete()
        _SESSIONS.pop(interface.entity.tid)


__all__ = [
    'StorySession',
    'get_story_session',
    'remove_story_session',
]
