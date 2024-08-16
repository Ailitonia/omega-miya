"""
@Author         : Ailitonia
@Date           : 2022/05/08 15:49
@FileName       : image_searcher.py
@Project        : nonebot2_miya 
@Description    : 图片搜索工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING

from src.utils.process_utils import semaphore_gather
from .config import image_searcher_config
from .model import BaseImageSearcher
from .seachers import (
    Ascii2d,
    Iqdb,
    Saucenao,
    TraceMoe,
    Yandex,
)

if TYPE_CHECKING:
    from .model import BaseImageSearcherAPI, ImageSearchingResult


class ComplexImageSearcher(BaseImageSearcher):
    """综合图片搜索"""

    _searcher: list[type["BaseImageSearcherAPI"]] = []

    if image_searcher_config.image_searcher_enable_saucenao:
        _searcher.append(Saucenao)

    if image_searcher_config.image_searcher_enable_ascii2d:
        _searcher.append(Ascii2d)

    if image_searcher_config.image_searcher_enable_iqdb:
        _searcher.append(Iqdb)

    if image_searcher_config.image_searcher_enable_yandex:
        _searcher.append(Yandex)

    async def search(self) -> list["ImageSearchingResult"]:
        searching_tasks = [
            searcher(image_url=self.image_url).search()
            for searcher in self._searcher
        ]
        all_results = await semaphore_gather(tasks=searching_tasks, semaphore_num=4, filter_exception=True)

        return [x for searcher_results in all_results for x in searcher_results]


__all__ = [
    'ComplexImageSearcher',
    'Ascii2d',
    'Iqdb',
    'Saucenao',
    'TraceMoe',
    'Yandex',
]
