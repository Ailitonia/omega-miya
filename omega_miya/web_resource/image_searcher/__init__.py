"""
@Author         : Ailitonia
@Date           : 2022/05/08 15:49
@FileName       : image_searcher.py
@Project        : nonebot2_miya 
@Description    : 图片搜索引擎
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Type
from nonebot.log import logger
from nonebot.adapters.onebot.v11.message import Message

from omega_miya.utils.process_utils import semaphore_gather

from .ascii2d import Ascii2d
from .iqdb import Iqdb
from .saucenao import Saucenao
from .trace_moe import TraceMoe

from .config import image_searcher_config
from .model import ImageSearcher, ImageSearchingResult


class ComplexImageSearcher(object):
    """综合图片搜索"""

    _searcher: list[Type[ImageSearcher]] = []

    if image_searcher_config.image_searcher_enable_saucenao:
        _searcher.append(Saucenao)

    if image_searcher_config.image_searcher_enable_iqdb:
        _searcher.append(Iqdb)

    if image_searcher_config.image_searcher_enable_ascii2d:
        _searcher.append(Ascii2d)

    def __init__(self, image_url: str):
        """仅支持传入图片 url

        :param image_url: 待识别的图片 url
        """
        self.image_url = image_url

    async def search(self) -> list[ImageSearchingResult]:
        searching_tasks = [searcher(image_url=self.image_url).search() for searcher in self._searcher]
        searching_result = await semaphore_gather(tasks=searching_tasks, semaphore_num=5)
        if error := [x for x in searching_result if isinstance(x, Exception)]:
            logger.error(f'ImageSearcher | ComplexImageSearcherError, {", ".join(repr(e) for e in error)}')
        return [x for result_list in searching_result if not isinstance(result_list, Exception) for x in result_list]

    async def searching_result(self) -> list[Message]:
        searching_tasks = [searcher(image_url=self.image_url).searching_result() for searcher in self._searcher]
        searching_result = await semaphore_gather(tasks=searching_tasks, semaphore_num=5)
        if error := [x for x in searching_result if isinstance(x, Exception)]:
            logger.error(f'ImageSearcher | ComplexImageSearcherError, {", ".join(repr(e) for e in error)}')
        return [msg for msg_list in searching_result if not isinstance(msg_list, Exception) for msg in msg_list]


__all__ = [
    'ComplexImageSearcher',
    'Ascii2d',
    'Iqdb',
    'Saucenao',
    'TraceMoe'
]
