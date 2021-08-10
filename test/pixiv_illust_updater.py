"""
@Author         : Ailitonia
@Date           : 2021/06/19 1:24
@FileName       : pixiv_illust_updater.py
@Project        : nonebot2_miya 
@Description    : 数据库pixiv illust作品图片链接信息更新工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import asyncio
import json
from nonebot import on_command, logger
from nonebot.rule import to_me
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent
from omega_miya.utils.Omega_Base import DBPixivillust, Result
from omega_miya.utils.pixiv_utils import PixivIllust


ONLY_UPDATE_NO_PAGES_ILLUST: bool = False


async def add_illust(pid: int, nsfw_tag: int) -> Result.IntResult:
    illust_result = await PixivIllust(pid=pid).get_illust_data()

    if illust_result.success():
        illust_data = illust_result.result
        title = illust_data.get('title')
        uid = illust_data.get('uid')
        uname = illust_data.get('uname')
        url = illust_data.get('url')
        tags = illust_data.get('tags')
        is_r18 = illust_data.get('is_r18')
        illust_pages = illust_data.get('illust_pages')

        if is_r18:
            nsfw_tag = 2

        illust = DBPixivillust(pid=pid)
        illust_add_result = await illust.add(uid=uid, title=title, uname=uname, nsfw_tag=nsfw_tag, tags=tags, url=url)
        if illust_add_result.error:
            logger.error(f'Add illust failed: {illust_add_result.info}')
            return Result.IntResult(error=True, info=illust_add_result.info, result=pid)

        for page, urls in illust_pages.items():
            original = urls.get('original')
            regular = urls.get('regular')
            small = urls.get('small')
            thumb_mini = urls.get('thumb_mini')
            page_upgrade_result = await illust.upgrade_page(
                page=page, original=original, regular=regular, small=small, thumb_mini=thumb_mini)
            if page_upgrade_result.error:
                logger.warning(f'Upgrade illust page {page} failed: {page_upgrade_result.info}')
        return illust_add_result
    else:
        return Result.IntResult(error=True, info=illust_result.info, result=pid)


async def output_nsfw():
    nsfw_tag = 2
    res = await DBPixivillust.list_all_illust_by_nsfw_tag(nsfw_tag=nsfw_tag)
    dict_res = {x: nsfw_tag for x in res.result}
    nsfw_json = f'C:\\nsfw_{nsfw_tag}.json'
    with open(nsfw_json, 'w+') as f:
        json.dump(dict_res, f)


async def reset_nsfw_tag():
    res = await DBPixivillust.reset_all_nsfw_tag()
    print(res)


async def set_nsfw_tag():
    nsfw_tag = 2
    nsfw_json = f'C:\\nsfw_{nsfw_tag}.json'
    with open(nsfw_json, 'r') as f:
        tags = json.load(f)
    res = await DBPixivillust.set_nsfw_tag(tags=tags)
    print(res)


# 注册事件响应器
pixiv_illust_page_updater = on_command('update_pages', rule=to_me(), permission=SUPERUSER, priority=10, block=True)


@pixiv_illust_page_updater.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    illust_list = await DBPixivillust.list_all_illust()
    if illust_list.error:
        logger.error(f'Get illust list failed: {illust_list.info}')
        await pixiv_illust_page_updater.finish('Get illust list failed.')

    all_illust = len(illust_list.result)
    pid_list = []
    if ONLY_UPDATE_NO_PAGES_ILLUST:
        for pid in illust_list.result:
            pages = await DBPixivillust(pid=pid).get_all_page()
            if pages.success() and not pages.result:
                pid_list.append(pid)
    else:
        pid_list.extend(illust_list.result)

    # 导入操作
    all_count = len(pid_list)
    success_count = 0
    failed_count = 0
    fail_list = []
    # 全部一起并发api撑不住, 做适当切分
    # 每个切片数量
    seg_n = 25
    pid_seg_list = []
    for i in range(0, all_count, seg_n):
        pid_seg_list.append(pid_list[i:i + seg_n])
    # 每个切片打包一个任务
    seg_len = len(pid_seg_list)
    process_rate = 0
    for seg_list in pid_seg_list:
        tasks = []
        for pid in seg_list:
            tasks.append(add_illust(pid=pid, nsfw_tag=0))
        # 进行异步处理
        _res = await asyncio.gather(*tasks)
        # 对结果进行计数
        for item in _res:
            if item.success():
                success_count += 1
            else:
                failed_count += 1
                fail_list.append(item.result)
                logger.error(f'upgrade illust {item.result} page failed: {item.info}')
        # 显示进度
        process_rate += 1
        if process_rate % 10 == 0:
            logger.info(f'Updater processing: {process_rate}/{seg_len}')

    logger.info(f'Updater: process complete,'
                f'All illust: {all_illust},'
                f'Total: {all_count},'
                f'Success: {success_count},'
                f'Failed: {failed_count},'
                f'Fail List: {fail_list}')
