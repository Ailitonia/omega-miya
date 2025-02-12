"""
@Author         : Ailitonia
@Date           : 2025/2/13 11:18:42
@FileName       : session.py
@Project        : omega-miya
@Description    : 基于 openai API 的服务
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING, Self

from .api import BaseOpenAIClient
from .models import Message, MessageContent

if TYPE_CHECKING:
    from pydantic import BaseModel


class ChatSession:
    """对话会话基类"""

    def __init__(
            self,
            service_name: str,
            model_name: str,
            *,
            default_user_name: str | None = None,
            init_system_message: str | None = None,
            init_assistant_message: str | None = None,
            use_developer_message: bool = False,
    ) -> None:
        self.client = BaseOpenAIClient.init_from_config(service_name=service_name, model_name=model_name)
        self.default_user_name = default_user_name
        self.model = model_name
        self.message = Message()
        if init_system_message is not None:
            self.message.set_prefix_content(
                system_text=init_system_message,
                assistant_text=init_assistant_message,
                use_developer=use_developer_message,
            )

    @classmethod
    def init_default_from_config(
            cls,
            *,
            default_user_name: str | None = None,
            init_system_message: str | None = None,
            init_assistant_message: str | None = None,
            use_developer_message: bool = False,
    ) -> Self:
        """从配置文件中初始化, 使用第一个可用配置项"""
        if not (available_services := BaseOpenAIClient.get_available_services()):
            raise RuntimeError('no openai service has been config')
        return cls(
            *available_services[0],
            default_user_name=default_user_name,
            init_system_message=init_system_message,
            init_assistant_message=init_assistant_message,
            use_developer_message=use_developer_message,
        )

    async def chat(
            self,
            text: str,
            *,
            user_name: str | None = None,
            **kwargs,
    ) -> str:
        """用户发起对话, 返回响应对话内容"""
        user_name = user_name if user_name is not None else self.default_user_name
        self.message.add_content(MessageContent.user(name=user_name).set_plain_text(text))

        result = await self.client.create_chat_completion(
            model=self.model,
            message=self.message,
            **kwargs,
        )

        reply_message = result.choices[0].message
        self.message.add_content(reply_message)
        return reply_message.plain_text

    async def chat_query_schema[T: 'BaseModel'](
            self,
            text: str,
            model_type: type[T],
            *,
            user_name: str | None = None,
            **kwargs,
    ) -> T:
        """用户发起对话, 指定结构化响应, 并解析响应返回值"""
        user_name = user_name if user_name is not None else self.default_user_name
        self.message.add_content(MessageContent.user(name=user_name).set_plain_text(text))

        result = await self.client.create_chat_completion(
            model=self.model,
            message=self.message,
            response_format={
                'type': 'json_schema',
                'json_schema': {
                    'name': 'DatetimeInfo',
                    'schema': model_type.model_json_schema(mode='serialization'),
                    'strict': True,
                }
            },
            **kwargs,
        )

        reply_message = result.choices[0].message
        self.message.add_content(reply_message)
        return model_type.model_validate_json(reply_message.plain_text)


__all__ = [
    'ChatSession',
]
