"""
@Author         : Ailitonia
@Date           : 2024/9/9 00:52
@FileName       : pixiv_artwork_downloader
@Project        : ailitonia-toolkit
@Description    : pixiv 作品批量下载工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.log import logger

from .downloader import CustomUserDownloader, PixivArtworkDownloader


async def download_bookmark_artworks(*args: str):
    """下载所有已收藏作品"""
    before = int(x) if (args and (x := args[0]).isdecimal()) else 480
    await PixivArtworkDownloader(fast_mode=True).download_bookmark_artworks_main(before=before)


async def download_follow_artworks():
    await PixivArtworkDownloader(fast_mode=False, use_cache=False).download_follow_artworks_main()


async def download_users_artworks(*args: str):
    """下载所有指定用户作品"""
    invalid_args = [x for x in args if not x.isdecimal()]
    if invalid_args:
        logger.error(f'Invalid user id args: {invalid_args}, ignored')
    user_ids = [int(x) for x in args if x.isdecimal()]
    if not user_ids:
        logger.error('No valid user id provided, abort')
        return
    await PixivArtworkDownloader(fast_mode=False, use_cache=False).download_users_artworks_main(user_ids)


async def download_tag_users_artworks(*args: str):
    """按关注标签下载所有该标签下用户的作品"""

    if not args:
        logger.error('No tag provided, abort')
        return

    user_ids = list(dict.fromkeys([
        user_id
        for tag in args
        for user_id in await CustomUserDownloader.query_default_user_tag_user_id(tag=tag)
    ]))
    if not user_ids:
        logger.error('No valid user id queried from provided tags, abort')
        return
    await PixivArtworkDownloader(fast_mode=False, use_cache=False).download_users_artworks_main(user_ids)


__all__ = [
    'download_bookmark_artworks',
    'download_follow_artworks',
    'download_tag_users_artworks',
    'download_users_artworks',
]
