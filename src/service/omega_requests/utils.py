"""
@Author         : Ailitonia
@Date           : 2022/12/10 20:30
@FileName       : utils.py
@Project        : nonebot2_miya 
@Description    : Omega requests handler utils
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import aiohttp
from typing import Iterable, Any


class FormData(aiohttp.FormData):
    """Patched aiohttp FormData"""

    def __init__(
            self,
            fields: Iterable[Any] = (),
            *,
            is_multipart: bool = False,
            is_processed: bool = False,
            quote_fields: bool = True,
            charset: str | None = None,
            boundary: str | None = None
    ) -> None:
        self._writer = aiohttp.multipart.MultipartWriter("form-data", boundary=boundary)
        self._fields: list = []
        self._is_multipart = is_multipart
        self._is_processed = is_processed
        self._quote_fields = quote_fields
        self._charset = charset

        if isinstance(fields, dict):
            fields = list(fields.items())
        elif not isinstance(fields, (list, tuple)):
            fields = (fields,)
        self.add_fields(*fields)


__all__ = [
    'FormData'
]
