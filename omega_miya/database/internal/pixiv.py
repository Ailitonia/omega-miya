"""
@Author         : Ailitonia
@Date           : 2022/04/05 1:21
@FileName       : pixiv.py
@Project        : nonebot2_miya 
@Description    : Internal Pixiv Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pydantic import BaseModel
from typing import List, Union, Literal, Optional

from omega_miya.result import BoolResult
from omega_miya.web_resource.pixiv.model import PixivArtworkCompleteDataModel
from omega_miya.utils.process_utils import semaphore_gather

from ..schemas.pixiv_artwork import PixivArtwork, PixivArtworkModel
from ..schemas.pixiv_artwork_page import PixivArtworkPage, PixivArtworkPageModel


class PixivStatistics(BaseModel):
    """统计信息"""
    total: int
    moe: int
    setu: int
    r18: int


class InternalPixiv(object):
    """封装后用于插件调用的数据库 Pixiv 基类"""

    def __init__(self, pid: int):
        self.pid = PixivArtwork.unique_model(pid=pid).pid
        self.artwork_model: Optional[PixivArtworkModel] = None

    def __repr__(self):
        return f'<InternalPixiv|PixivArtwork(pid={self.pid})>'

    @classmethod
    async def query_by_condition(
            cls,
            keywords: Optional[Union[str, List[str]]],
            num: Optional[int] = 3,
            nsfw_tag: int = 0,
            *,
            classified: int = 1,
            acc_mode: bool = False,
            ratio: Optional[int] = None,
            order_mode: Literal['random', 'pid', 'pid_desc', 'create_time', 'create_time_desc'] = 'random'
    ) -> List[PixivArtworkModel]:
        """按条件搜索 Pixiv 作品

        :param keywords: 关键词列表
        :param num: 数量
        :param nsfw_tag: nsfw 标签值, 0=sfw, 1=nsfw, 2=r18, -1=(sfw+nsfw), -2=(sfw+nsfw+r18), -3=(nsfw+r18)
        :param classified: 已标记标签项, 0=未标记, 1=已标记, 其他=all
        :param acc_mode: 是否启用精确搜索模式
        :param ratio: 图片长宽, 1: 横图, -1: 纵图, 0: 正方形图
        :param order_mode: 排序模式, random: 随机, pid: 按 pid 顺序, pid_desc: 按 pid 逆序,
            create_time: 按收录时间顺序, create_time_desc: 按收录时间逆序
        """
        if isinstance(keywords, str):
            keywords = [keywords]

        return (await PixivArtwork.query_by_condition(
            keywords=keywords,
            num=num,
            nsfw_tag=nsfw_tag,
            classified=classified,
            acc_mode=acc_mode,
            ratio=ratio,
            order_mode=order_mode
        )).result

    @classmethod
    async def random(
            cls,
            num: Optional[int] = 3,
            nsfw_tag: int = 0,
            *,
            ratio: Optional[int] = None) -> List[PixivArtworkModel]:
        """随机抽取图库中已标记的的作品

        :param num: 抽取数量
        :param nsfw_tag: nsfw 标签值, 0=sfw, 1=nsfw, 2=r18, -1=(sfw+nsfw), -2=(sfw+nsfw+r18), -3=(nsfw+r18)
        :param ratio: 图片长宽, 1: 横图, -1: 纵图, 0: 正方形图
        """
        return await cls.query_by_condition(keywords=None, num=num, nsfw_tag=nsfw_tag, ratio=ratio)

    @classmethod
    async def query_statistics(cls, *, keywords: Optional[Union[str, List[str]]] = None) -> PixivStatistics:
        """获取数据库统计信息"""
        if isinstance(keywords, str):
            keywords = [keywords]
        return PixivStatistics.parse_obj((await PixivArtwork.count_all(keywords=keywords)).dict())

    @classmethod
    async def query_all_by_user_id(cls, uid: int) -> List[PixivArtworkModel]:
        """查询用户的全部作品"""
        return (await PixivArtwork.query_all_by_uid(uid=uid)).result

    @classmethod
    async def query_all_pid_by_user_id(cls, uid: int) -> List[int]:
        """查询用户的全部作品 pid"""
        return (await PixivArtwork.query_all_pid_by_uid(uid=uid)).result

    async def exist(self) -> (int, bool):
        """判断该作品是否在数据库中已存在

        :return: pid, 是否存在
        """
        exist = await PixivArtwork(pid=self.pid).exist()
        return self.pid, exist

    async def get_artwork_model(self) -> PixivArtworkModel:
        """获取并初始化作品对应 PixivArtworkModel"""
        if not isinstance(self.artwork_model, PixivArtworkModel):
            artwork = PixivArtwork(pid=self.pid)
            self.artwork_model = (await artwork.query()).result

        assert isinstance(self.artwork_model, PixivArtworkModel), 'Query artwork model failed'
        return self.artwork_model

    async def query_page(self, page: int) -> PixivArtworkPageModel:
        """获取作品指定 page 对应 PixivArtworkPageModel"""
        artwork = await self.get_artwork_model()
        return (await PixivArtworkPage(artwork_id=artwork.id, page=page).query()).result

    async def _query_all_pages_(self) -> List[PixivArtworkPageModel]:
        """[DEPRECATED]获取作品所有 page 的 PixivArtworkPageModel"""
        artwork = await self.get_artwork_model()
        return (await PixivArtworkPage.query_all_pages_by_artwork_index_id(id_=artwork.id)).result

    async def query_all_pages(self) -> List[PixivArtworkPageModel]:
        """获取作品所有 page 的 PixivArtworkPageModel"""
        return (await PixivArtworkPage.query_all_pages_by_pid(pid=self.pid)).result

    async def add_upgrade_page(self, page: int, original: str, regular: str, small: str, thumb_mini: str) -> BoolResult:
        """新增或更新作品 page"""
        artwork = await self.get_artwork_model()
        return await PixivArtworkPage(artwork_id=artwork.id, page=page).add_upgrade_unique_self(
            original=original, regular=regular, small=small, thumb_mini=thumb_mini)

    async def add_upgrade(
            self,
            artwork_data: PixivArtworkCompleteDataModel,
            *,
            classified: int = 0,
            nsfw_tag: int = -1,
            upgrade_pages: bool = True
    ) -> BoolResult:
        """新增或更新"""
        add_artwork_result = await PixivArtwork(pid=self.pid).add_upgrade_unique_self(
            uid=artwork_data.uid, title=artwork_data.title, uname=artwork_data.uname, tags=','.join(artwork_data.tags),
            url=artwork_data.url, width=artwork_data.width, height=artwork_data.height,
            classified=classified, nsfw_tag=nsfw_tag
        )
        if add_artwork_result.error:
            return add_artwork_result

        if upgrade_pages:
            tasks = [self.add_upgrade_page(page=page, original=page_url.original, regular=page_url.regular,
                                           small=page_url.small, thumb_mini=page_url.thumb_mini)
                     for page, page_url in artwork_data.all_page.items()]
            upgrade_pages_result = await semaphore_gather(tasks=tasks, semaphore_num=10)
            if error := [x for x in upgrade_pages_result if isinstance(x, Exception)]:
                raise RuntimeError(*error)
        return BoolResult(error=False, info='Success', result=True)

    async def add_only(
            self,
            artwork_data: PixivArtworkCompleteDataModel,
            *,
            classified: int = 0,
            nsfw_tag: int = -1,
            upgrade_pages: bool = True
    ) -> BoolResult:
        """仅新增, 若已存在则不更新"""
        add_artwork_result = await PixivArtwork(pid=self.pid).add_only(
            uid=artwork_data.uid, title=artwork_data.title, uname=artwork_data.uname, tags=','.join(artwork_data.tags),
            url=artwork_data.url, width=artwork_data.width, height=artwork_data.height,
            classified=classified, nsfw_tag=nsfw_tag
        )
        if add_artwork_result.error:
            return add_artwork_result

        if upgrade_pages:
            tasks = [self.add_upgrade_page(page=page, original=page_url.original, regular=page_url.regular,
                                           small=page_url.small, thumb_mini=page_url.thumb_mini)
                     for page, page_url in artwork_data.all_page.items()]
            upgrade_pages_result = await semaphore_gather(tasks=tasks, semaphore_num=10)
            if error := [x for x in upgrade_pages_result if isinstance(x, Exception)]:
                raise RuntimeError(*error)
        return BoolResult(error=False, info='Success', result=True)

    async def delete(self) -> BoolResult:
        """删除"""
        return await PixivArtwork(pid=self.pid).query_and_delete_unique_self()


__all__ = [
    'InternalPixiv'
]
