"""
@Author         : Ailitonia
@Date           : 2022/05/08 15:50
@FileName       : model.py
@Project        : nonebot2_miya 
@Description    : Image Searcher Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import abc
from typing import Optional
from pydantic import AnyUrl, BaseModel


class ImageSearchingResult(BaseModel):
    """识图结果"""
    source: str  # 来源说明
    source_urls: Optional[list[AnyUrl]] = None  # 来源地址
    similarity: Optional[str] = None  # 相似度
    thumbnail: Optional[AnyUrl] = None  # 缩略图地址

    # async def get_output_message(self) -> Message:
    #     """将识别结果转换为消息"""
    #     url = '\n'.join(self.source_urls) if self.source_urls else '无可用来源'
    #     message = f'来源: {self.source}\n相似度: {self.similarity if self.similarity else "未知"}\n来源地址:\n{url}'
    #
    #     if self.thumbnail:
    #         thumbnail_file = _TMP_FOLDER(HttpFetcher.hash_url_file_name('ImageSearcher', url=self.thumbnail))
    #         download_result = await run_async_catching_exception(HttpFetcher().download_file)(url=self.thumbnail,
    #                                                                                           file=thumbnail_file)
    #         if not isinstance(download_result, Exception):
    #             message = message + '\n' + MessageSegment.image(thumbnail_file.file_uri)
    #     return Message(message)


class ImageSearcher(abc.ABC):
    """识图引擎基类"""
    _searcher_name: str = 'abc_searcher'

    def __init__(self, image_url: str):
        """仅支持传入图片 url

        :param image_url: 待识别的图片 url
        """
        self.image_url = image_url

    def __repr__(self) -> str:
        return f'ImageSearcher(name={self._searcher_name.upper()}, image_url={self.image_url})'

    @abc.abstractmethod
    async def search(self) -> list[ImageSearchingResult]:
        """获取搜索结果"""
        raise NotImplementedError

    # async def searching_result(self) -> list[Message]:
    #     """获取搜索结果并转换为消息"""
    #     searching_result = await self.search()
    #     tasks = [x.get_output_message() for x in searching_result]
    #     message_result = await semaphore_gather(tasks=tasks, semaphore_num=10, filter_exception=True)
    #     searcher_text = f'识图引擎: {self._searcher_name}\n'
    #     return [searcher_text + x for x in message_result]


__all__ = [
    'ImageSearchingResult',
    'ImageSearcher'
]
