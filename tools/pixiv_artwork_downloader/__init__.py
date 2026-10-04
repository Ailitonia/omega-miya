"""
@Author         : Ailitonia
@Date           : 2024/9/9 00:52
@FileName       : pixiv_artwork_downloader
@Project        : ailitonia-toolkit
@Description    : pixiv 作品批量下载工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from itertools import count

from nonebot.log import logger

from src.exception import WebSourceException
from .downloader import PixivArtworkDownloader


async def download_bookmark_artworks(*args: str):
    """下载所有已收藏作品"""
    before = int(x) if (args and (x := args[0]).isdecimal()) else 480
    await PixivArtworkDownloader(fast_mode=True).download_bookmark_artworks_main(before=before)


async def download_follow_artworks():
    await PixivArtworkDownloader(fast_mode=False, use_cache=False).download_follow_artworks_main()


async def download_users_artworks(*args: str):
    user_ids = [int(x) for x in args]
    await PixivArtworkDownloader(fast_mode=False, use_cache=False).download_users_artworks_main(user_ids)


async def download_tag_users_artworks(*args: str):
    from src.utils.pixiv_api import PixivUser

    limit = 48

    async def _query_tag_user_id(tag: str) -> list[int]:
        ids: list[int] = []
        for page in count(0, 1):
            try:
                page_ids = [
                    int(user.userId)
                    for user in (await PixivUser(PixivUser._get_default_user_id()).query_user_following_users(
                        tag=tag,
                        offset=page * limit,
                        limit=limit,
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
                    break
                else:
                    logger.error(f'Query {tag} user error: {e}, ignore page {page}')
                    continue
        logger.info(f'Query {tag} user completed')
        return ids

    user_ids = [user_id for tag in args for user_id in await _query_tag_user_id(tag=tag)]
    await PixivArtworkDownloader(fast_mode=False, use_cache=False).download_users_artworks_main(user_ids)


__all__ = [
    'download_bookmark_artworks',
    'download_follow_artworks',
    'download_tag_users_artworks',
    'download_users_artworks',
]
