"""
@Author         : Ailitonia
@Date           : 2024/9/9 00:58
@FileName       : downloader
@Project        : ailitonia-toolkit
@Description    : 下载工具类
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from asyncio import sleep as async_sleep
from collections.abc import Sequence
from datetime import datetime
from itertools import count
from typing import TYPE_CHECKING, Literal

from nonebot.log import logger
from pathvalidate import sanitize_filename

from src.exception import WebSourceException
from src.resource import BaseResource, TemporaryResource
from src.service.artwork_proxy import PixivArtworkProxy
from src.utils.pixiv_api import PixivUser
from src.utils.process_utils import semaphore_gather
from .config import downloader_config
from .consts import (
    DOWNLOAD_SEMAPHORE_NUM,
    FILTER_ALL_PAGES_LIKE_COUNT,
    FILTER_R18_ALL_PAGES_LIKE_COUNT,
    FOLLOWING_QUERY_MAX_PAGE,
    LIST_PAGE_QUERY_INTERVAL,
    QUERY_BATCH_SIZE,
    TAG_USER_QUERY_LIMIT,
)
from .utils import get_last_follow_illust_pid, set_last_follow_illust_pid

if TYPE_CHECKING:
    from src.service.artwork_proxy.models import ArtworkProxyData


class CustomUserDownloader(PixivUser):

    @classmethod
    async def download_any_url[T: BaseResource](
            cls,
            url: str,
            save_folder: T,
            *,
            ignore_exist_file: bool = True,
            retry_num: int = 3,
    ) -> T:
        """下载任意资源到任意位置, 失败时自动重试"""
        retried = 0
        while True:
            try:
                return await cls._download_resource(
                    url=url,
                    save_folder=save_folder,
                    ignore_exist_file=ignore_exist_file,
                    stream_download=True,
                )
            except Exception as e:
                # 4xx 为确定性错误(资源不存在/无权限等), 重试无意义, 直接抛出(429 流控除外)
                if isinstance(e, WebSourceException) and 400 <= e.status_code < 500 and e.status_code != 429:
                    raise
                if retried >= retry_num:
                    raise
                delay = min(5 * 2 ** retried, 30)
                retried += 1
                logger.warning(f'Download {url} failed, will retry ({retried}/{retry_num}) after {delay}s, {e!r}')
                await async_sleep(delay)

    async def _query_tag_user_id(self, tag: str) -> list[int]:
        ids: list[int] = []
        for page in count(0, 1):
            try:
                page_ids = [
                    int(u.userId)
                    for u in (await self.query_user_following_users(
                        tag=tag,
                        offset=page * TAG_USER_QUERY_LIMIT,
                        limit=TAG_USER_QUERY_LIMIT,
                    )).body.users
                ]

                if not page_ids:
                    logger.info(f'There are not users in {tag} page {page}, stop querying')
                    break

                ids.extend(page_ids)
                logger.info(f'Queried {tag} user in page {page}: {page_ids}')
            except WebSourceException as e:
                if e.status_code == 404:
                    logger.info(f'End of {tag} user page {page}, stop querying')
                else:
                    # 持续性错误(凭证失效/流控等)时中止该标签的查询, 避免无限翻页持续请求
                    logger.error(f'Query {tag} user error: {e}, stop querying at page {page}')
                break
            await async_sleep(LIST_PAGE_QUERY_INTERVAL)
        logger.info(f'Query {tag} user completed')
        return ids

    @classmethod
    async def query_default_user_tag_user_id(cls, tag: str) -> list[int]:
        return await cls.init_default_user()._query_tag_user_id(tag=tag)


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
        self.__output_file = downloader_config.url_output_dir(category, filename)

    async def _load_output_file_download_urls(self) -> list[str]:
        """读取输出文件中的下载链接, 剥离行首尾空白并跳过空行"""
        async with self.output_file.async_open('r', encoding='utf-8') as af:
            return [stripped for line in await af.readlines() if (stripped := line.strip())]

    async def _handle_download_artworks_from_output_file(self, save_folder: BaseResource) -> None:
        """从输出文件读取下载链接并批量下载, 任一链接下载失败时抛出异常"""
        urls = await self._load_output_file_download_urls()
        if not urls:
            logger.warning(f'No download urls found in {self.output_file}, skip downloading')
            return

        tasks = [
            CustomUserDownloader.download_any_url(url=url, save_folder=save_folder, ignore_exist_file=True)
            for url in urls
        ]
        results = await semaphore_gather(tasks=tasks, semaphore_num=DOWNLOAD_SEMAPHORE_NUM)

        failed = [(url, result) for url, result in zip(urls, results) if isinstance(result, Exception)]
        for url, result in failed:
            logger.error(f'Download {url} failed, error: {result!r}')
        if failed:
            raise WebSourceException(
                500,
                f'Download artworks failed, {len(failed)} of {len(urls)} urls failed',
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
        await artwork.add_artwork_into_database_ignore_exists()
        return artwork_data

    async def _handle_append_write_artworks_download_urls_into_output_file(
            self,
            artwork_data: 'ArtworkProxyData',
            output_all_urls: bool = False,
    ) -> None:
        """向输出文件追加写入作品原图下载链接"""
        if not artwork_data.pages:
            logger.warning(f'Artwork {artwork_data.aid} has no pages, skip writing download urls')
            return

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

    @staticmethod
    def _resolve_output_all_urls(artwork_data: 'ArtworkProxyData', enable_filter: bool) -> bool:
        """根据筛选条件决定是否写入作品全部页面的下载链接, 否则仅写入封面链接"""
        if not enable_filter:
            return True
        if artwork_data.rating >= 2:
            return artwork_data.like_count is not None and artwork_data.like_count > FILTER_R18_ALL_PAGES_LIKE_COUNT
        return artwork_data.like_count is not None and artwork_data.like_count >= FILTER_ALL_PAGES_LIKE_COUNT

    async def _handle_query_artworks_and_write_download_urls_into_output_file(
            self,
            pids: Sequence[int],
            *,
            enable_filter: bool = True,
    ) -> None:
        """批量获取作品信息, 并向输出文件批量写入作品原图下载链接; 为应对 pixiv 流控, 对获取作品信息进行分段处理

        单个作品查询为 404 (作品已删除/私密) 时跳过, 其余原因查询失败的作品在全部批次处理完后统一抛出异常
        """
        prepare_pids = list(pids)
        failed_pids: list[int] = []

        for offset in range(0, len(prepare_pids), QUERY_BATCH_SIZE):
            handle_pids = prepare_pids[offset:offset + QUERY_BATCH_SIZE]
            tasks = [self._handle_query_artwork_data(pid=pid) for pid in handle_pids]
            artworks_result = await semaphore_gather(tasks=tasks, semaphore_num=16)

            for pid, result in zip(handle_pids, artworks_result):
                if isinstance(result, WebSourceException) and result.status_code == 404:
                    logger.info(f'Artwork {pid} is unavailable (404), skipped')
                    continue
                if isinstance(result, Exception):
                    logger.error(f'Query artwork {pid} failed, error: {result!r}')
                    failed_pids.append(pid)
                    continue
                await self._handle_append_write_artworks_download_urls_into_output_file(
                    result,
                    output_all_urls=self._resolve_output_all_urls(result, enable_filter=enable_filter),
                )

            remaining = len(prepare_pids) - offset - len(handle_pids)
            if remaining > 0:
                logger.info(f'获取作品下载链接中, 剩余: {remaining}, 预计时间: {remaining * 2} 秒')
                next_batch_size = min(remaining, QUERY_BATCH_SIZE)
                if self.__fast_mode:
                    await async_sleep(int(next_batch_size * 0.1))
                else:
                    await async_sleep(int(next_batch_size * 1.5))

        if failed_pids:
            raise WebSourceException(
                500,
                f'Query artworks failed, {len(failed_pids)} of {len(prepare_pids)} pids failed: {failed_pids}',
            )

    @staticmethod
    async def _query_following_user_latest_illust(up_pid: int | None = None) -> list[int]:
        """获取已关注用户的最新作品 ID (转换为 int 便于排序)"""
        ids: set[int] = set()

        for page in range(1, FOLLOWING_QUERY_MAX_PAGE):
            try:
                logger.info(f'Querying follow artwork page: {page}')
                illust_result = await CustomUserDownloader.query_following_user_latest_illust(page=page)

                if not illust_result.illust_ids:
                    logger.info(f'No more artworks in page {page}, stop querying')
                    break

                ids.update(int(x) for x in illust_result.illust_ids)

                if up_pid and ((up_pid in ids) or up_pid > min(ids)):
                    logger.info(f'Found end artwork: {up_pid} in page: {page}, oldest artwork: {min(ids)}')
                    break
            except Exception as e:
                logger.error(f'Get follow latest artwork failed in page {page}, error: {e}')
                raise WebSourceException(500, f'Query following user latest illust failed in page {page}') from e
            await async_sleep(LIST_PAGE_QUERY_INTERVAL)

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

        bookmark_data = await CustomUserDownloader.query_bookmarks(uid=uid, limit=limit, rest=rest)
        total = bookmark_data.total
        before = min(total, before) if before is not None else total
        ids.update(int(x) for x in bookmark_data.illust_ids)

        for offset in range(limit, before, limit):
            logger.info(f'Querying {rest} bookmark illust from {offset} to {min(offset + limit, before)}')
            bookmark_data = await CustomUserDownloader.query_bookmarks(uid=uid, offset=offset, limit=limit, rest=rest)
            ids.update(int(x) for x in bookmark_data.illust_ids)
            await async_sleep(LIST_PAGE_QUERY_INTERVAL)

        return sorted(ids)

    async def _download_follow_artworks(self) -> None:
        """下载已已关注用户新作品"""
        # 获取现在最新的一个已关注用户作品, 稍后将写入数据库作为下一次获取的分界线
        illust_result = await CustomUserDownloader.query_following_user_latest_illust(page=1)
        if not illust_result.illust_ids:
            logger.info('No following artworks found, skip this update')
            return
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

        # 执行下载
        logger.info('Querying latest following artworks data completed, start downloading...')
        await self._handle_download_artworks_from_output_file(save_folder=downloader_config.save_dir)

        # 下载全部成功后再写入本次更新的分界线, 保证失败后重新运行可以补档
        await set_last_follow_illust_pid(pid=now_up_pid)
        logger.success(f'Follow artwork update is all got completed, this time up pid: {now_up_pid}')

    async def download_follow_artworks_main(self) -> None:
        try:
            await self._download_follow_artworks()
        except Exception as e:
            logger.error(f'Downloading latest following artworks failed, error: {e}')

    async def _download_user_artworks(self, user_id: int) -> None:
        """下载用户作品"""

        # 获取用户信息及用户作品列表
        user_data = await CustomUserDownloader(uid=user_id).query_user()
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
        logger.info(f'Querying user(uid={user_id}, {user_data.name}) artworks data completed, start downloading...')
        await self._handle_download_artworks_from_output_file(save_folder=download_folder)
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
        logger.info(f'Querying user(uid={uid}) {rest} bookmark data completed, start downloading...')
        await self._handle_download_artworks_from_output_file(save_folder=downloader_config.favorites_dir)
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
    'CustomUserDownloader',
    'PixivArtworkDownloader',
]
