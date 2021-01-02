import asyncio
import random
from nonebot import on_command, export, logger
from nonebot.rule import to_me
from nonebot.permission import GROUP, SUPERUSER
from nonebot.typing import Bot, Event
from nonebot.adapters.cqhttp import MessageSegment
from omega_miya.utils.Omega_plugin_utils import init_export
from omega_miya.utils.Omega_plugin_utils import has_command_permission, permission_level
from omega_miya.utils.Omega_Base import DBPixivtag, DBPixivillust
from .utils import fetch_illust_b64, add_illust


# Custom plugin usage text
__plugin_name__ = '来点涩图'
__plugin_usage__ = r'''【来点涩图】
测试群友LSP成分

**Permission**
Command & Lv.50

**Usage**
/来点涩图 [tag]

**SuperUser Only**
/涩图统计
/导入涩图'''

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__)


# 注册事件响应器
setu = on_command('来点涩图', rule=has_command_permission() & permission_level(level=50),
                  permission=GROUP, priority=20, block=True)


@setu.handle()
async def handle_first_receive(bot: Bot, event: Event, state: dict):
    args = set(str(event.plain_text).strip().split())
    # 处理r18
    state['nsfw_tag'] = 1
    for tag in args.copy():
        if tag in ['r18', 'R18', 'r-18', 'R-18']:
            args.remove(tag)
            state['nsfw_tag'] = 2
    state['tags'] = args


@setu.got('nsfw_tag', prompt='r18?')
@setu.got('tags', prompt='tag?')
async def handle_setu(bot: Bot, event: Event, state: dict):
    nsfw_tag = state['nsfw_tag']
    tags = state['tags']

    if tags:
        _res_list = list()
        for tag in tags:
            _tag = DBPixivtag(tagname=tag)
            _res = _tag.list_illust(nsfw_tag=nsfw_tag)
            if _res.success():
                _pids = set(_res.result)
                _res_list.append(_pids)
        if len(tags) > 1:
            # 处理tag交集, 同时满足所有tag
            for item in _res_list[1:]:
                _res_list[0].intersection_update(item)
            pid_list = _res_list[0]
        else:
            pid_list = _res_list[0]
    else:
        # 没有tag则随机获取
        pid_list = DBPixivillust.rand_illust(num=3, nsfw_tag=nsfw_tag)

    if not pid_list:
        logger.info(f'Group: {event.group_id}, User: {event.user_id} 没有找到他/她想要的涩图')
        await setu.finish('找不到涩图QAQ')
    elif len(pid_list) > 3:
        pid_list = random.sample(pid_list, k=3)

    await setu.send('稍等, 正在下载图片~')
    # 处理article中图片内容
    tasks = []
    for pid in pid_list:
        tasks.append(fetch_illust_b64(pid=pid))
    p_res = await asyncio.gather(*tasks)
    fault_count = 0
    for image_res in p_res:
        try:
            if not image_res.success():
                fault_count += 1
                logger.warning(f'图片下载失败, error: {image_res.info}')
                continue
            else:
                img_seg = MessageSegment.image(image_res.result)
            # 发送图片
            await setu.send(img_seg)
        except Exception as e:
            logger.warning(f'图片发送失败, group: {event.group_id}. error: {repr(e)}')
            continue

    if fault_count == len(pid_list):
        logger.info(f'Group: {event.group_id}, User: {event.user_id} 没能看到他/她想要的涩图')
        await setu.finish('似乎出现了网络问题, 所有的图片都下载失败了QAQ')
    else:
        logger.info(f'Group: {event.group_id}, User: {event.user_id} 找到了他/她想要的涩图')


# 注册事件响应器
setu_stat = on_command('涩图统计', rule=to_me(), permission=SUPERUSER, priority=20, block=True)


@setu_stat.handle()
async def handle_first_receive(bot: Bot, event: Event, state: dict):
    _res = DBPixivillust.status()
    msg = f"本地数据库统计:\n\n" \
          f"全部: {_res.get('total')}\n" \
          f"涩图: {_res.get('setu')}\n" \
          f"R18: {_res.get('r18')}"
    await setu_stat.finish(msg)


# 注册事件响应器
setu_import = on_command('导入涩图', rule=to_me(), permission=SUPERUSER, priority=20, block=True)


@setu_import.handle()
async def handle_first_receive(bot: Bot, event: Event, state: dict):
    import os
    import re

    # 文件操作
    import_pid_file = os.path.join(os.path.dirname(__file__), 'import_pid.txt')
    if not os.path.exists(import_pid_file):
        logger.error(f'setu_import: 导入列表不存在')
        await setu_import.finish('错误: 导入列表不存在QAQ')

    pid_list = []
    with open(import_pid_file) as f:
        lines = f.readlines()
        for line in lines:
            if not re.match(r'^[0-9]+$', line):
                logger.debug(f'setu_import: 导入列表中有非数字字符: {line}')
                continue
            pid_list.append(int(line))

    await setu_import.send('已读取导入文件列表, 开始获取作品信息~')

    # 对列表去重
    pid_list = list(set(pid_list))

    # 导入操作
    all_count = len(pid_list)
    success_count = 0
    # 全部一起并发api撑不住, 做适当切分
    # 每个切片数量
    seg_n = 10
    pid_seg_list = []
    for i in range(0, all_count, seg_n):
        pid_seg_list.append(pid_list[i:i + seg_n])
    # 每个切片打包一个任务
    seg_len = len(pid_seg_list)
    process_rate = 0
    for seg_list in pid_seg_list:
        tasks = []
        for pid in seg_list:
            tasks.append(add_illust(pid=pid))
        # 进行异步处理
        _res = await asyncio.gather(*tasks)
        # 对结果进行计数
        for item in _res:
            if item.success():
                success_count += 1
        # 显示进度
        process_rate += 1
        if process_rate % 10 == 0:
            await setu_import.send(f'导入操作中，已完成: {process_rate}/{seg_len}')

    logger.info(f'setu_import: 导入操作已完成, 成功: {success_count}, 总计: {all_count}')
    await setu_import.send(f'导入操作已完成, 成功: {success_count}, 总计: {all_count}')
