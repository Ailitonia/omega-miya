"""
@Author         : Ailitonia
@Date           : 2025/8/23 13:49:59
@FileName       : translate.py
@Project        : omega-miya
@Description    : 翻译应用
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from .base import BaseAIScenarioApp

_SYSTEM_INIT_PROMPT: str = """# Profile

你是一位经验丰富的翻译专家，精通多种语言，对语言的语法、词汇和文化背景有深入的理解，能够准确地将一种语言的文本转换为另一种语言，同时保留原文的意图和风格。你具备精准的语言转换能力，能够理解并运用不同语言的表达习惯和文化差异，确保翻译的准确性和流畅性。

# Goals

将用户的文本准确、流畅地翻译成指定的语言，确保翻译后的文本在语义、语法和文化背景上与原文相符。

# Constrains

1. 精确理解用户提供的原文内容，包括其语义、语境和文化背景。
2. 根据目标语言的要求，进行语言转换，确保翻译的准确性和流畅性。
3. 审核翻译内容，确保没有语法错误、文化误解或语义偏差。
4. 翻译应保持原文的意图和风格，避免文化误解，确保语言的准确性和自然性。
5. 翻译后的文本应以清晰、准确的格式呈现，适合目标语言的阅读习惯。"""


class TranslateApp(BaseAIScenarioApp):
    """翻译应用"""

    @classmethod
    def _set_init_system_message(cls) -> str | None:
        return _SYSTEM_INIT_PROMPT

    @classmethod
    def _set_max_messages(cls) -> int:
        return 2

    @staticmethod
    def _format_input_prompt(text: str, target_language: str = '简体中文') -> str:
        return f'本次翻译的目标语言是: ```{target_language}```, 以下内容为待翻译文本: \n\n```{text}```'

    async def translate(self, text: str, *, target_language: str = '简体中文') -> str:
        return await self.chat_session.chat(text=self._format_input_prompt(text, target_language=target_language))


__all__ = [
    'TranslateApp',
]
