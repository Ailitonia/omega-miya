"""
@Author         : Ailitonia
@Date           : 2022/12/09 18:53
@FileName       : pixiv_artwork.py
@Project        : nonebot2_miya 
@Description    : 数据库 Pixiv 作品常用方法
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from sqlalchemy.exc import NoResultFound
from typing import Literal, Optional

from src.database import begin_db_session
from src.database.internal.pixiv_artwork import PixivArtwork, PixivArtworkDAL, PixivArtworkStatistic
from src.database.internal.pixiv_artwork_page import PixivArtworkPage, PixivArtworkPageDAL

from .models import CollectedArtwork, BaseArtworkCollection


class CollectedPixivArtwork(CollectedArtwork):
    classified: int
    nsfw_tag: int
    width: int
    height: int

    @property
    def pid(self) -> int:
        return int(self.aid)


class PixivArtworkCollection(BaseArtworkCollection):
    """Pixiv 作品合集"""

    @property
    def pid(self) -> int:
        return int(self.artwork_id)

    @staticmethod
    def covert_collected_pixiv_artwork_model(data: PixivArtwork) -> CollectedPixivArtwork:
        aid = str(data.pid)
        tags = [x.strip() for x in data.tags.split(',')]
        return CollectedPixivArtwork(
            aid=aid, title=data.title, uname=data.uname, tags=tags, url=data.url,
            classified=data.classified, nsfw_tag=data.nsfw_tag, width=data.width, height=data.height
        )

    @classmethod
    async def query_by_condition(
            cls,
            keywords: Optional[str | list[str]],
            num: Optional[int] = 3,
            nsfw_tag: int = 0,
            *,
            classified: int = 1,
            acc_mode: bool = False,
            ratio: Optional[int] = None,
            order_mode: Literal['random', 'pid', 'pid_desc', 'create_time', 'create_time_desc'] = 'random'
    ) -> list[CollectedPixivArtwork]:
        """按条件搜索 Pixiv 作品

        :param keywords: 关键词列表
        :param num: 数量
        :param nsfw_tag: nsfw 标签值, 0=sfw, 1=nsfw, 2=r18, -1=(sfw+nsfw), -2=(sfw+nsfw+r18), -3=(nsfw+r18)
        :param classified: 已标记标签项, 0=未标记, 1=已标记, 2=AI生成作品
        :param acc_mode: 是否启用精确搜索模式
        :param ratio: 图片长宽, 1: 横图, -1: 纵图, 0: 正方形图
        :param order_mode: 排序模式, random: 随机, pid: 按 pid 顺序, pid_desc: 按 pid 逆序,
            create_time: 按收录时间顺序, create_time_desc: 按收录时间逆序
        """
        if isinstance(keywords, str):
            keywords = [keywords]

        async with begin_db_session() as session:
            result = await PixivArtworkDAL(session=session).query_by_condition(
                keywords=keywords, num=num, nsfw_tag=nsfw_tag, classified=classified,
                acc_mode=acc_mode, ratio=ratio, order_mode=order_mode
            )
        return [cls.covert_collected_pixiv_artwork_model(x) for x in result]

    @classmethod
    async def random(
            cls,
            num: Optional[int] = 3,
            nsfw_tag: int = 0,
            *,
            ratio: Optional[int] = None
    ) -> list[CollectedPixivArtwork]:
        """随机抽取图库中已标记的的作品

        :param num: 抽取数量
        :param nsfw_tag: nsfw 标签值, 0=sfw, 1=nsfw, 2=r18, -1=(sfw+nsfw), -2=(sfw+nsfw+r18), -3=(nsfw+r18)
        :param ratio: 图片长宽, 1: 横图, -1: 纵图, 0: 正方形图
        """
        return await cls.query_by_condition(keywords=None, num=num, nsfw_tag=nsfw_tag, ratio=ratio)

    @classmethod
    async def query_statistics(
            cls,
            *,
            keywords: Optional[str | list[str]] = None,
            ignore_classified: bool = False
    ) -> PixivArtworkStatistic:
        """获取数据库统计信息"""
        if isinstance(keywords, str):
            keywords = [keywords]
        classified = None if ignore_classified else 1

        async with begin_db_session() as session:
            result = await PixivArtworkDAL(session=session).query_statistic(keywords=keywords, classified=classified)
        return result

    @classmethod
    async def query_user_all(cls, uid: int) -> list[PixivArtwork]:
        """查询用户的全部作品"""
        async with begin_db_session() as session:
            result = await PixivArtworkDAL(session=session).query_user_all(uid=uid)
        return result

    @classmethod
    async def query_user_all_pids(cls, uid: int) -> list[int]:
        """查询用户的全部作品 pid"""
        async with begin_db_session() as session:
            result = await PixivArtworkDAL(session=session).query_user_all_pids(uid=uid)
        return result

    async def query_artwork(self) -> CollectedPixivArtwork:
        return self.covert_collected_pixiv_artwork_model(await self.query_pixiv_artwork())

    async def query_pixiv_artwork(self) -> PixivArtwork:
        """查询数据库作品信息"""
        async with begin_db_session() as session:
            artwork = await PixivArtworkDAL(session=session).query_unique(pid=self.pid)
        return artwork

    async def query_page(self, page: int) -> PixivArtworkPage:
        """获取作品指定 page 链接"""
        async with begin_db_session() as session:
            artwork = await PixivArtworkDAL(session=session).query_unique(pid=self.pid)
            page = await PixivArtworkPageDAL(session=session).query_unique(artwork_index_id=artwork.id, page=page)
        return page

    async def query_all_pages(self) -> list[PixivArtworkPage]:
        """获取作品所有 page 链接"""
        async with begin_db_session() as session:
            artwork = await PixivArtworkDAL(session=session).query_unique(pid=self.pid)
            pages = await PixivArtworkPageDAL(session=session).query_artwork_all(artwork_index_id=artwork.id)
        return pages

    async def add_page_ignore_exists(self, page: int, original: str, regular: str, small: str, thumb_mini: str) -> None:
        """新增作品 page 链接, 若已存在则忽略"""
        async with begin_db_session() as session:
            artwork = await PixivArtworkDAL(session=session).query_unique(pid=self.pid)
            page_dal = PixivArtworkPageDAL(session=session)
            try:
                await page_dal.query_unique(artwork_index_id=artwork.id, page=page)
            except NoResultFound:
                await page_dal.add(
                    artwork_index_id=artwork.id, page=page,
                    original=original, regular=regular, small=small, thumb_mini=thumb_mini
                )

    async def add_upgrade_page(self, page: int, original: str, regular: str, small: str, thumb_mini: str) -> None:
        """新增作品 page 链接, 若已存在则更新"""
        async with begin_db_session() as session:
            artwork = await PixivArtworkDAL(session=session).query_unique(pid=self.pid)
            page_dal = PixivArtworkPageDAL(session=session)
            try:
                exist_page = await page_dal.query_unique(artwork_index_id=artwork.id, page=page)
                await page_dal.update(
                    id_=exist_page.id,
                    original=original, regular=regular, small=small, thumb_mini=thumb_mini
                )
            except NoResultFound:
                await page_dal.add(
                    artwork_index_id=artwork.id, page=page,
                    original=original, regular=regular, small=small, thumb_mini=thumb_mini
                )

    async def add_ignore_exists(
            self,
            uid: int,
            title: str,
            uname: str,
            classified: int,
            nsfw_tag: int,
            width: int,
            height: int,
            tags: str,
            url: str,
    ) -> None:
        """新增作品信息, 若已存在忽略"""
        async with begin_db_session() as session:
            artwork_dal = PixivArtworkDAL(session=session)
            try:
                await artwork_dal.query_unique(pid=self.pid)
            except NoResultFound:
                await artwork_dal.add(
                    pid=self.pid, uid=uid, title=title, uname=uname, classified=classified, nsfw_tag=nsfw_tag,
                    width=width, height=height, tags=tags, url=url
                )

    async def add_upgrade(
            self,
            uid: int,
            title: str,
            uname: str,
            classified: int,
            nsfw_tag: int,
            width: int,
            height: int,
            tags: str,
            url: str,
            *,
            ignore_mark: bool = False,
    ) -> None:
        """新增作品信息, 若已存在则更新

        :param uid: 作者 uid
        :param title: 作品标题
        :param uname: 作者名
        :param classified: 标记标签
        :param nsfw_tag: nsfw标签
        :param width: 原始图片宽度
        :param height: 原始图片高度
        :param tags: 作品标签
        :param url: 作品页面链接
        :param ignore_mark: 更新时是否忽略数据库中存在的 classified 及 nsfw_tag标签, Ture: 强制更新, False: 仅大于已有值时更新
        """
        async with begin_db_session() as session:
            artwork_dal = PixivArtworkDAL(session=session)
            try:
                artwork = await artwork_dal.query_unique(pid=self.pid)

                if not ignore_mark:
                    classified = artwork.classified if artwork.classified >= classified else classified
                    nsfw_tag = artwork.nsfw_tag if artwork.nsfw_tag >= nsfw_tag else nsfw_tag

                await artwork_dal.update(
                    id_=artwork.id, uid=uid, title=title, uname=uname, classified=classified, nsfw_tag=nsfw_tag,
                    width=width, height=height, tags=tags, url=url
                )
            except NoResultFound:
                await artwork_dal.add(
                    pid=self.pid, uid=uid, title=title, uname=uname, classified=classified, nsfw_tag=nsfw_tag,
                    width=width, height=height, tags=tags, url=url
                )

    async def delete(self) -> None:
        """删除作品信息"""
        async with begin_db_session() as session:
            artwork_dal = PixivArtworkDAL(session=session)
            artwork = await artwork_dal.query_unique(pid=self.pid)
            await artwork_dal.delete(id_=artwork.id)


__all__ = [
    'CollectedPixivArtwork',
    'PixivArtworkCollection'
]
