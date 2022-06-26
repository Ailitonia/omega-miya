"""
@Author         : Ailitonia
@Date           : 2022/04/05 19:49
@FileName       : model.py
@Project        : nonebot2_miya 
@Description    : HttpFetcher Result Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Optional
from pydantic import BaseModel, Json
from http.cookies import SimpleCookie as _SimpleCookie


class BaseHttpFetcherResult(BaseModel):
    status: int
    headers: dict
    cookies: Optional[_SimpleCookie]


class HttpFetcherJsonResult(BaseHttpFetcherResult):
    result: Json


class HttpFetcherDictResult(BaseHttpFetcherResult):
    result: dict


class HttpFetcherTextResult(BaseHttpFetcherResult):
    result: str


class HttpFetcherBytesResult(BaseHttpFetcherResult):
    result: bytes


__all__ = [
    'HttpFetcherJsonResult',
    'HttpFetcherDictResult',
    'HttpFetcherTextResult',
    'HttpFetcherBytesResult'
]
