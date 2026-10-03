"""
@Author         : Ailitonia
@Date           : 2024/9/9 00:58
@FileName       : downloader
@Project        : ailitonia-toolkit
@Description    :
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import asyncio
import sys
from asyncio import sleep as async_sleep
from collections.abc import Sequence
from copy import deepcopy
from datetime import datetime
from typing import TYPE_CHECKING, Literal

from nonebot.log import logger
from pathvalidate import sanitize_filename

from src.exception import WebSourceException
from src.resource import BaseResource, TemporaryResource
from src.service.artwork_proxy import PixivArtworkProxy
from src.utils.pixiv_api import PixivUser
from src.utils.process_utils import semaphore_gather
from .config import downloader_config
from .consts import DOWNLOADER_SETTING_NAME
from .utils import get_last_follow_illust_pid, set_last_follow_illust_pid

if TYPE_CHECKING:
    from src.service.artwork_proxy.models import ArtworkProxyData

_DATABASE_WRITE_LOCK: asyncio.Lock = asyncio.Lock()
"""数据库写入锁, 减少数据库并发写入时的冲突"""
_DOWNLOAD_URL_TMP_DIR: TemporaryResource = TemporaryResource(DOWNLOADER_SETTING_NAME)
"""下载链接缓存目录"""


class PixivArtworkDownloader:
    __slots__ = ('__fast_mode', '__use_cache', '__output_file',)

    def __init__(self, fast_mode: bool = False, use_cache: bool = True):
        self.__fast_mode = fast_mode
        self.__use_cache = use_cache or fast_mode  # use cache when enable fast mode
        self.__output_file: TemporaryResource | None = None

    @property
    def output_file(self) -> TemporaryResource:
        if self.__output_file is None:
            raise ValueError('output_file has not been set')
        return self.__output_file

    def set_output_file(self, category: str, filename: str) -> None:
        self.__output_file: TemporaryResource = _DOWNLOAD_URL_TMP_DIR(category, filename)

    @staticmethod
    async def download_any_url[T: BaseResource](
            url: str,
            save_folder: T,
            *,
            subdir: str | None = None,
            ignore_exist_file: bool = True,
    ) -> T:
        """下载任意资源到任意位置"""
        return await PixivUser._download_resource(
            url=url,
            save_folder=save_folder,
            subdir=subdir,
            ignore_exist_file=ignore_exist_file,
        )

    async def _handle_query_artwork_data(self, pid: int) -> 'ArtworkProxyData':
        """获取作品信息并写入数据库"""
        artwork = PixivArtworkProxy(artwork_id=pid)
        try:
            artwork_data = await artwork.query(use_cache=self.__use_cache)
        except WebSourceException as e:
            if e.status_code == 404:
                raise e

            # 请求过快可能暂时被流控, 暂停一下重试一次
            logger.opt(colors=True).warning(f'Query {artwork} failed and will retry again <c>></c> <r>{e!r}</r>')
            if self.__fast_mode:
                await async_sleep(30)
            else:
                await async_sleep(120)
            artwork_data = await artwork.query(use_cache=self.__use_cache)

        # 作品信息写入数据库
        async with _DATABASE_WRITE_LOCK:
            await artwork.add_artwork_into_database_ignore_exists()
        return artwork_data

    async def _handle_append_write_artworks_download_urls_into_output_file(
            self,
            artwork_data: 'ArtworkProxyData',
            output_all_urls: bool = False,
    ) -> None:
        """向输出文件追加写入作品原图下载链接"""
        async with self.output_file.async_open('a', encoding='utf8') as af:
            if output_all_urls:
                await af.write('\n'.join(x.original_file.url for x in artwork_data.pages))
                await af.write('\n')
            else:
                await af.write(artwork_data.cover_page_url)
                await af.write('\n')

            # 写入动图原始资源下载链接
            if artwork_data.extra_resource:
                await af.write('\n'.join(x for x in artwork_data.extra_resource))
                await af.write('\n')

    async def _handle_query_artworks_and_write_download_urls_into_output_file(
            self,
            pids: Sequence[int],
            *,
            enable_filter: bool = True,
    ) -> None:
        """批量获取作品信息, 并向输出文件批量写入作品原图下载链接; 为应对 pixiv 流控, 对获取作品信息进行分段处理"""
        prepare_pids = list(deepcopy(pids))
        handle_pids: list[int] = []
        while prepare_pids:
            while len(handle_pids) < 20:
                try:
                    handle_pids.append(prepare_pids.pop())
                except IndexError:
                    break

            tasks = [self._handle_query_artwork_data(pid=pid) for pid in handle_pids]
            handle_pids.clear()

            artworks_result = await semaphore_gather(tasks=tasks, semaphore_num=16, filter_exception=True)

            for artwork_data in artworks_result:
                # 根据筛选条件写入图片 url
                if not enable_filter:
                    await self._handle_append_write_artworks_download_urls_into_output_file(
                        artwork_data, output_all_urls=True,
                    )
                elif (
                        artwork_data.rating == 3
                        and artwork_data.like_count is not None
                        and artwork_data.like_count > 1666
                ):
                    await self._handle_append_write_artworks_download_urls_into_output_file(
                        artwork_data, output_all_urls=True
                    )
                elif artwork_data.rating == 3:
                    await self._handle_append_write_artworks_download_urls_into_output_file(
                        artwork_data, output_all_urls=False
                    )
                elif artwork_data.like_count is not None and artwork_data.like_count >= 666:
                    await self._handle_append_write_artworks_download_urls_into_output_file(
                        artwork_data, output_all_urls=True
                    )
                else:
                    await self._handle_append_write_artworks_download_urls_into_output_file(
                        artwork_data, output_all_urls=False
                    )

            if prepare_pids:
                logger.info(
                    f'获取作品下载链接中, 剩余: {len(prepare_pids)}, 预计时间: {int(len(prepare_pids) * 2)} 秒')
                if self.__fast_mode:
                    await async_sleep(int((len(prepare_pids) if len(prepare_pids) < 20 else 20) * 0.1))
                else:
                    await async_sleep(int((len(prepare_pids) if len(prepare_pids) < 20 else 20) * 1.5))

    @staticmethod
    async def _query_following_user_latest_illust(up_pid: int | None = None) -> list[int]:
        """获取已关注用户的最新作品 ID (转换为 int 便于排序)"""
        ids: set[int] = set()

        for page in range(1, 85):  # 只能获取到前 5000 张更新作品, 已关注作品页一页 60 个作品, 最多到 84 页, 后面全是重复的
            try:
                logger.info(f'Querying follow artwork page: {page}')
                illust_result = await PixivUser.query_following_user_latest_illust(page=page)
                ids.update(int(x) for x in illust_result.illust_ids)

                if up_pid and ((up_pid in ids) or up_pid > min(ids)):
                    logger.info(f'Found end artwork: {up_pid} in page: {page}, oldest artwork: {min(ids)}')
                    break
            except Exception as e:
                logger.error(f'Get follow latest artwork failed in page {page}, error: {e}')
                sys.exit(str(e))

        return sorted(ids)

    @staticmethod
    async def _query_all_bookmark_illust(
            uid: int | None = None,
            *,
            rest: Literal['show', 'hide'] = 'show',
            before: int | None = None,
            limit: int = 100,
    ) -> list[int]:
        """获取用户收藏的所有作品 ID (转换为 int 便于排序)"""
        ids: set[int] = set()

        bookmark_data = await PixivUser.query_bookmarks(uid=uid, rest=rest)
        before = min(bookmark_data.total, before) if before is not None else bookmark_data.total
        for index in range(0, before // limit + 1):
            offset = index * limit
            logger.info(f'Querying {rest} bookmark illust from {offset} to {offset + limit}')
            bookmark_data = await PixivUser.query_bookmarks(uid=uid, offset=offset, limit=limit, rest=rest)
            ids.update(int(x) for x in bookmark_data.illust_ids)

        return sorted(ids)

    async def _download_follow_artworks(self) -> None:
        """下载已已关注用户新作品"""
        # 获取现在最新的一个已关注用户作品, 稍后将写入数据库作为下一次获取的分界线
        illust_result = await PixivUser.query_following_user_latest_illust(page=1)
        now_up_pid = int(illust_result.illust_ids[0])

        # 读取上次截止的最后一个已关注用户作品, 以此为界开始获取本次更新的作品
        last_up_pid = await get_last_follow_illust_pid()
        logger.info(f'Last follow artwork up pid: {last_up_pid}, starting get new follow artwork')

        pids = await self._query_following_user_latest_illust(up_pid=last_up_pid)
        logger.info('Querying new follow artwork completed, waiting for rate limiting cooldown...')
        await async_sleep(60)

        output_file_name = f'download_url_{datetime.now().strftime("%Y%m%d-%H%M%S")}.txt'
        self.set_output_file(category='following', filename=output_file_name)
        await self._handle_query_artworks_and_write_download_urls_into_output_file(pids=pids, enable_filter=True)

        await set_last_follow_illust_pid(pid=now_up_pid)
        logger.success(f'Follow artwork update is all got completed, this time up pid: {now_up_pid}')

        # 执行下载
        async with self.output_file.async_open('r', encoding='utf-8') as af:
            tasks = [
                self.download_any_url(
                    url=url,
                    save_folder=downloader_config.save_dir,
                    ignore_exist_file=True,
                )
                for url in await af.readlines()
            ]

        logger.info(f'Querying latest following artworks data completed, start downloading...')
        await semaphore_gather(tasks=tasks, semaphore_num=8)
        logger.success(f'Downloading latest following artworks completed')

    async def download_follow_artworks_main(self) -> None:
        try:
            await self._download_follow_artworks()
        except Exception as e:
            logger.error(f'Downloading latest following artworks failed, error: {e}')

    async def _download_user_artworks(self, user_id: int) -> None:
        """下载用户作品"""

        # 获取用户信息及用户作品列表
        user_data = await PixivUser(uid=user_id).query_user()
        logger.info(
            f'Querying user(uid={user_id}, {user_data.name}) artworks list completed, '
            f'total: {len(user_data.manga_illusts)}, start query artwork data...'
        )
        await async_sleep(30)

        output_file_name = f'user_{user_id}_artworks_{datetime.now().strftime("%Y%m%d-%H%M%S")}.txt'
        meta_file_name = f'user_{user_id}_meta_{datetime.now().strftime("%Y%m%d-%H%M%S")}.json'
        user_friendly_name_file_name = sanitize_filename(f'{user_data.name}.NAME')
        self.set_output_file(category='user', filename=output_file_name)

        # 获取用户所有作品信息
        await self._handle_query_artworks_and_write_download_urls_into_output_file(
            pids=[int(x) for x in user_data.manga_illusts],
            enable_filter=False,
        )

        # 指定下载路径
        download_folder = downloader_config.artists_dir(f'user_{user_id}')

        # 保存用户 meta 信息
        async with download_folder(meta_file_name).async_open('w', encoding='utf-8') as maf:
            await maf.write(user_data.model_dump_json())
        async with download_folder(user_friendly_name_file_name).async_open('w', encoding='utf-8') as naf:
            await naf.write(f'{user_data.name} @ {datetime.now().strftime("%Y-%m-%d")}')

        # 执行下载
        async with self.output_file.async_open('r', encoding='utf-8') as af:
            tasks = [
                self.download_any_url(url=url, save_folder=download_folder, ignore_exist_file=True)
                for url in await af.readlines()
            ]

        logger.info(f'Querying user(uid={user_id}, {user_data.name}) artworks data completed, start downloading...')
        await semaphore_gather(tasks=tasks, semaphore_num=8)
        logger.success(f'Downloading user(uid={user_id}, {user_data.name}) artworks completed')

    async def download_users_artworks_main(self, user_ids: Sequence[int]) -> None:
        for i, user_id in enumerate(user_ids):
            try:
                logger.info(f'Querying user(uid={user_id}) artworks, now: {i + 1}/{len(user_ids)}')
                await self._download_user_artworks(user_id=user_id)
                logger.success(f'Downloading user(uid={user_id}) artworks completed')
            except Exception as e:
                logger.error(f'Downloading user(uid={user_id}) artworks failed, error: {e}')
                continue
        logger.success('Downloaded all users artworks completed')

    async def _download_bookmark_artworks(
            self,
            uid: int | None = None,
            *,
            rest: Literal['show', 'hide'] = 'show',
            before: int | None = None,
    ) -> None:
        """下载收藏的全部作品"""
        pids = await self._query_all_bookmark_illust(uid=uid, rest=rest, before=before)

        logger.info(f'Querying {rest} bookmark {uid} completed, waiting for rate limiting cooldown...')
        await async_sleep(30)

        output_file_name = f'download_url_{uid}_{rest}_bookmark_{datetime.now().strftime("%Y%m%d-%H%M%S")}.txt'
        self.set_output_file(category='bookmark', filename=output_file_name)

        # 获取所有作品信息
        await self._handle_query_artworks_and_write_download_urls_into_output_file(pids=pids, enable_filter=False)

        # 执行下载
        async with self.output_file.async_open('r', encoding='utf-8') as af:
            tasks = [
                self.download_any_url(
                    url=url,
                    save_folder=downloader_config.favorites_dir,
                    ignore_exist_file=True,
                )
                for url in await af.readlines()
            ]

        logger.info(f'Querying user(uid={uid}) {rest} bookmark data completed, start downloading...')
        await semaphore_gather(tasks=tasks, semaphore_num=8)
        logger.success(f'Downloading user(uid={uid}) {rest} bookmark artworks completed')

    async def download_bookmark_artworks_main(
            self,
            uid: int | None = None,
            *,
            before: int | None = None,
    ) -> None:
        try:
            await self._download_bookmark_artworks(uid=uid, rest='show', before=before)
        except Exception as e:
            logger.error(f'Downloading user(uid={uid}) show bookmark illust failed, error: {e}')

        try:
            await self._download_bookmark_artworks(uid=uid, rest='hide', before=before)
        except Exception as e:
            logger.error(f'Downloading user(uid={uid}) hide bookmark illust failed, error: {e}')


__all__ = [
    'PixivArtworkDownloader',
]
