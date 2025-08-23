"""
@Author         : Ailitonia
@Date           : 2025/8/23 13:50:19
@FileName       : base.py
@Project        : omega-miya
@Description    : 场景应用基类
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import abc

from ..session import ChatSession


class BaseAIScenarioApp(abc.ABC):

    def __init__(
            self,
            service_name: str | None = None,
            model_name: str | None = None,
            *,
            default_user_name: str | None = None,
            init_system_message: str | None = None,
            init_assistant_message: str | None = None,
            use_developer_message: bool | None = None,
            max_messages: int | None = None,
    ) -> None:
        self.chat_session = ChatSession.create(
            service_name=service_name or self._set_default_service_name(),
            model_name=model_name or self._set_default_model_name(),
            default_user_name=default_user_name or self._set_default_user_name(),
            init_system_message=init_system_message or self._set_init_system_message(),
            init_assistant_message=init_assistant_message or self._set_init_assistant_message(),
            use_developer_message=use_developer_message or self._set_use_developer_message(),
            max_messages=max_messages or self._set_max_messages(),
        )

    @classmethod
    def _set_default_service_name(cls) -> str | None:
        return None

    @classmethod
    def _set_default_model_name(cls) -> str | None:
        return None

    @classmethod
    def _set_default_user_name(cls) -> str | None:
        return None

    @classmethod
    def _set_init_system_message(cls) -> str | None:
        return None

    @classmethod
    def _set_init_assistant_message(cls) -> str | None:
        return None

    @classmethod
    def _set_use_developer_message(cls) -> bool:
        return False

    @classmethod
    def _set_max_messages(cls) -> int:
        return 20


__all__ = [
    'BaseAIScenarioApp',
]
