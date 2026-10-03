"""
@Author         : Ailitonia
@Date           : 2024/9/9 00:52
@FileName       : pixiv_artwork_downloader
@Project        : ailitonia-toolkit
@Description    : pixiv 作品批量下载工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from .downloader import PixivArtworkDownloader


async def download_follow_artworks():
    await PixivArtworkDownloader(use_cache=False).download_follow_artworks_main()


async def download_bookmark_artworks():
    await PixivArtworkDownloader(fast_mode=True).download_bookmark_artworks_main(before=480)


__all__ = [
    'download_bookmark_artworks',
    'download_follow_artworks',
]
