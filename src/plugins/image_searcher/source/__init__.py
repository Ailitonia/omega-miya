"""
@Author         : Ailitonia
@Date           : 2022/05/08 15:49
@FileName       : image_searcher.py
@Project        : nonebot2_miya
@Description    : 图片搜索工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import Iterable
from typing import TYPE_CHECKING

from src.utils import semaphore_gather
from .config import image_searcher_config
from .model import SearchableImage
from .seachers import AVAILABLE_SEARCHERS

if TYPE_CHECKING:
    from .model import BaseImageSearcherAPI, ImageSearchingResult

_ENABLED_SEARCHERS: list[type['BaseImageSearcherAPI']] = [
    x for x in AVAILABLE_SEARCHERS
    if x.get_searcher_name() in image_searcher_config.image_searcher_enable_searchers
]


class ComplexImageSearcher:
    """综合图片搜索"""

    def __init__(
            self,
            image: SearchableImage,
            *,
            include_searcher: Iterable[str] | None = None,
            exclude_searcher: Iterable[str] | None = None,
    ) -> None:
        self.image = image
        self.searcher = [
            x for x in _ENABLED_SEARCHERS
            if ((include_searcher is None) or (x.get_searcher_name() in include_searcher))
               and ((exclude_searcher is None) or (x.get_searcher_name() not in exclude_searcher))
        ]

    async def search(self) -> list['ImageSearchingResult']:
        searching_tasks = [
            searcher(image=self.image).search()
            for searcher in self.searcher
        ]
        all_results = await semaphore_gather(tasks=searching_tasks, semaphore_num=4, filter_exception=True)

        return [x for searcher_results in all_results for x in searcher_results]


__all__ = [
    'ComplexImageSearcher',
]
