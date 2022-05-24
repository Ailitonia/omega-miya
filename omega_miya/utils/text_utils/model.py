"""
@Author         : Ailitonia
@Date           : 2022/05/24 21:30
@FileName       : model.py
@Project        : nonebot2_miya 
@Description    : Text utils model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal
from pydantic import BaseModel, root_validator, AnyUrl


class TextUtilsBaseModel(BaseModel):
    class Config:
        extra = 'ignore'
        allow_mutation = False


class TextSegment(TextUtilsBaseModel):
    """文字段"""
    class _Data(TextUtilsBaseModel):
        def get_content(self) -> str:
            raise NotImplementedError

    class _TextData(_Data):
        text: str

        def get_content(self) -> str:
            return self.text

    class _EmojiData(_Data):
        emoji: str

        def get_content(self) -> str:
            return self.emoji

    class _ImageData(_Data):
        image: AnyUrl

        def get_content(self) -> str:
            return str(self.image)

    type: Literal['text', 'emoji', 'image']
    data: _TextData | _EmojiData | _ImageData

    @root_validator(pre=False)
    def check_data_type_match(cls, values):
        segment_type = values.get('type')
        data = values.get('data')
        if not data or segment_type not in data.dict().keys():
            raise ValueError('Segment data type not match')
        return values

    def get_content(self) -> str:
        return self.data.get_content()

    @classmethod
    def new(cls, type_: str, data: str) -> 'TextSegment':
        return cls.parse_obj({'type': type_, 'data': {type_: data}})

    @classmethod
    def text(cls, text: str) -> 'TextSegment':
        return cls.new(type_='text', data=text)

    @classmethod
    def emoji(cls, emoji: str) -> 'TextSegment':
        return cls.new(type_='emoji', data=emoji)

    @classmethod
    def image(cls, image: str) -> 'TextSegment':
        return cls.new(type_='image', data=image)


class TextContent(TextUtilsBaseModel):
    """绘制文字内容"""
    content: list[TextSegment]

    def get_text(self) -> str:
        return ''.join(x.get_content() for x in self.content)


__all__ = [
    'TextSegment',
    'TextContent'
]
