"""
@Author         : Ailitonia
@Date           : 2022/05/08 1:35
@FileName       : model.py
@Project        : nonebot2_miya 
@Description    : DeepL Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pydantic import BaseModel


class BaseDeepLModel(BaseModel):
    class Config:
        extra = 'ignore'
        allow_mutation = False


class TranslateSeq(BaseDeepLModel):
    """翻译结果内容序列"""
    detected_source_language: str
    text: str


class TranslateResult(BaseDeepLModel):
    """翻译结果 Model"""
    translations: list[TranslateSeq]

    @property
    def translate_text(self) -> str:
        result_text = ''.join(x.text for x in self.translations)
        return result_text


__all__ = [
    'TranslateResult'
]

