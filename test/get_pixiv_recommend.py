"""
@Author         : Ailitonia
@Date           : 2021/07/30 20:35
@FileName       : get_pixiv_recommend.py
@Project        : nonebot2_miya 
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import re
from typing import Optional
from nonebot import get_driver, logger
from omega_miya.database import DBPixivillust, Result
from omega_miya.utils.pixiv_utils import PixivIllust
from omega_miya.utils.omega_plugin_utils import ProcessUtils


driver = get_driver()


async def add_illust(
        pid: int, nsfw_tag: int,
        *,
        force_tag: bool = False, illust_data: Optional[Result.DictResult] = None) -> Result.IntResult:
    if not illust_data:
        illust_result = await PixivIllust(pid=pid).get_illust_data()
    else:
        illust_result = illust_data

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
            logger.error(f'Setu | add_illust failed: {illust_add_result.info}')
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
        return Result.IntResult(error=True, info=illust_result.info, result=-1)


async def test_init():
    with open(r'C:\Users\ailitonia\Desktop\pids.txt', 'r') as f:
        lines = f.readlines()
        pids = list(set([int(x.strip()) for x in lines if re.match(r'^[0-9]+$', x)]))
        pids.sort()
    tasks = [add_illust(pid, nsfw_tag=0) for pid in pids]
    await ProcessUtils.fragment_process(tasks=tasks, fragment_size=50)


async def add_recommend(pid: int):
    recommend_result = await PixivIllust(pid=pid).get_recommend(init_limit=180)
    pid_list = [x.get('id') for x in recommend_result.result.get('illusts') if x.get('illustType') == 0]
    tasks = [PixivIllust(pid=x).get_illust_data() for x in pid_list]
    recommend_illust_data_result = await ProcessUtils.fragment_process(tasks=tasks, fragment_size=50)
    filtered_illust_pids = [x for x in recommend_illust_data_result if (
            x.success() and
            6666 <= x.result.get('bookmark_count') <= 2 * x.result.get('like_count') and
            x.result.get('view_count') <= 20 * x.result.get('like_count')
    )]
    tasks = [add_illust(x.result.get('pid'), nsfw_tag=0, illust_data=x) for x in filtered_illust_pids]
    await ProcessUtils.fragment_process(tasks=tasks, fragment_size=50)


async def test():
    all_illust_result = await DBPixivillust.list_all_illust()
    tasks = [add_recommend(pid) for pid in all_illust_result.result]
    await ProcessUtils.fragment_process(tasks=tasks, fragment_size=2)


# driver.on_startup(test)
