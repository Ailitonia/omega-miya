"""
@Author         : Ailitonia
@Date           : 2025/2/12 17:13:10
@FileName       : file.py
@Project        : omega-miya
@Description    : openai file model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from .base import BaseOpenAIModel


class File(BaseOpenAIModel):
    id: str
    object: str
    bytes: int
    created_at: int
    filename: str
    purpose: str


class FileContent(BaseOpenAIModel):
    content: str
    file_type: str
    filename: str
    title: str
    type: str


class FileDeleted(BaseOpenAIModel):
    id: str
    object: str
    deleted: bool


class FileList(BaseOpenAIModel):
    object: str
    data: list[File]


__all__ = [
    'File',
    'FileContent',
    'FileDeleted',
    'FileList',
]
