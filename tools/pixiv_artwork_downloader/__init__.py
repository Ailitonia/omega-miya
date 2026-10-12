"""
@Author         : Ailitonia
@Date           : 2024/9/9 00:52
@FileName       : pixiv_artwork_downloader
@Project        : ailitonia-toolkit
@Description    : pixiv 作品批量下载工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm

用法:
    python bot.py --tool-execute pixiv_artwork_downloader:download_bookmark_artworks [before]
    python bot.py --tool-execute pixiv_artwork_downloader:download_follow_artworks
    python bot.py --tool-execute pixiv_artwork_downloader:download_users_artworks <uid> [uid ...]
    python bot.py --tool-execute pixiv_artwork_downloader:download_tag_users_artworks <tag> [tag ...]

说明:
    - download_bookmark_artworks 下载默认账号全部收藏 (公开与私密各一轮), before 为从最新
      往前获取的收藏数量 (缺省 480), 全页下载无筛选, 保存到 favorites/ 目录
    - download_follow_artworks 增量下载已关注用户新作品, 以数据库记录的上次最新作品 pid 为
      分界线, 下载全部成功后才更新分界线 (失败后重新执行可补档); 按点赞数筛选, R18 作品
      点赞数 > 1666、非 R18 作品点赞数 >= 666 才下载全部页, 否则仅下载封面; 保存到 download/ 目录
    - download_users_artworks 下载指定用户全部作品 (全页无筛选), 每个用户保存到
      artists/user_<uid>/ 目录并附带用户 meta JSON 与 .NAME 文件; 非数字参数被忽略,
      无有效 uid 时中止
    - download_tag_users_artworks 查询默认账号 pixiv 关注标签下的用户 (多标签去重合并),
      再按 download_users_artworks 方式下载其全部作品
    - 下载流程为先查询作品信息 (写入图库数据库), 原图链接暂存到临时资源目录
      omega_tool_pixiv_artwork_downloader/output_urls/ 下, 再 8 并发批量下载, 已存在文件自动跳过
    - 输出根目录由 OMEGA_TOOL_PIXIV_DOWNLOAD_ROOT_FOLDER 指定 (完整路径,
      缺省为临时资源目录 omega_tool_pixiv_artwork_downloader/),
      download / artists / favorites 子目录名可由对应的
      OMEGA_TOOL_PIXIV_DOWNLOAD_*_FOLDER_NAME 环境变量调整
    - 需在环境变量中配置 PIXIV_PHPSESSID 提供登录态 (默认账号 uid 从中解析),
      工具同时依赖 bot 数据库 (写入作品信息与关注分界线记录)
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
