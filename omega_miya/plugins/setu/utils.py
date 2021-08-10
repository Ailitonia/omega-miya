from nonebot import logger
from omega_miya.utils.Omega_Base import DBPixivillust, Result
from omega_miya.utils.pixiv_utils import PixivIllust


async def add_illust(pid: int, nsfw_tag: int, *, force_tag: bool = False) -> Result.IntResult:
    illust_result = await PixivIllust(pid=pid).get_illust_data()

    if illust_result.success():
        illust_data = illust_result.result
        title = illust_data.get('title')
        uid = illust_data.get('uid')
        uname = illust_data.get('uname')
        url = illust_data.get('url')
        width = illust_data.get('width')
        height = illust_data.get('height')
        tags = illust_data.get('tags')
        is_r18 = illust_data.get('is_r18')
        illust_pages = illust_data.get('illust_pages')

        if is_r18:
            nsfw_tag = 2

        illust = DBPixivillust(pid=pid)
        illust_add_result = await illust.add(uid=uid, title=title, uname=uname, nsfw_tag=nsfw_tag,
                                             width=width, height=height, tags=tags, url=url, force_tag=force_tag)
        if illust_add_result.error:
            logger.error(f'Setu | Adding illust to database failed, pid: {pid}, error: {illust_add_result.info}')
            return illust_add_result

        for page, urls in illust_pages.items():
            original = urls.get('original')
            regular = urls.get('regular')
            small = urls.get('small')
            thumb_mini = urls.get('thumb_mini')
            page_upgrade_result = await illust.upgrade_page(
                page=page, original=original, regular=regular, small=small, thumb_mini=thumb_mini)
            if page_upgrade_result.error:
                logger.warning(f'Setu | upgrade illust page {page} failed: {page_upgrade_result.info}')
        return illust_add_result
    else:
        logger.error(f'Setu | Getting illust data failed, pid: {pid}, error: {illust_result.info}')
        return Result.IntResult(error=True, info=illust_result.info, result=-1)
