import asyncio
import random
from nonebot import CommandGroup, on_command, export, logger
from nonebot.rule import to_me
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent, Event
from nonebot.adapters.cqhttp.permission import GROUP
from nonebot.adapters.cqhttp import MessageSegment, Message
from omega_miya.utils.Omega_plugin_utils import init_export, init_permission_state, PluginCoolDown
from omega_miya.utils.Omega_Base import DBPixivillust
from .utils import fetch_illust_b64, add_illust


# Custom plugin usage text
__plugin_name__ = '来点萌图'
__plugin_usage__ = r'''【来点萌图】
测试群友LSP成分

**Permission**
Command & Lv.50
or AuthNode

**AuthNode**
setu
moepic

**CoolDown**
群组共享冷却时间
2 Minutes
用户冷却时间
10 Minutes

**Usage**
/来点涩图 [tag]
/来点萌图 [tag]

**SuperUser Only**
/图库统计
/导入图库'''

# 声明本插件可配置的权限节点
__plugin_auth_node__ = [
    PluginCoolDown.skip_auth_node,
    'setu',
    'moepic'
]

# 声明本插件的冷却时间配置
__plugin_cool_down__ = [
    PluginCoolDown(PluginCoolDown.user_type, 10),
    PluginCoolDown(PluginCoolDown.group_type, 2)
]

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__, __plugin_auth_node__, __plugin_cool_down__)


# 注册事件响应器
Setu = CommandGroup('sepic', permission=GROUP, priority=20, block=True)

setu = Setu.command(
    'setu',
    aliases={'来点涩图'},
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_permission_state(
        name='setu',
        command=True,
        level=50,
        auth_node='setu'))


@setu.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = set(str(event.get_plaintext()).strip().split())
    # 处理r18
    state['nsfw_tag'] = 1
    for tag in args.copy():
        if tag in ['r18', 'R18', 'r-18', 'R-18']:
            args.remove(tag)
            state['nsfw_tag'] = 2
    state['tags'] = args


@setu.got('nsfw_tag', prompt='r18?')
@setu.got('tags', prompt='tag?')
async def handle_setu(bot: Bot, event: GroupMessageEvent, state: T_State):
    nsfw_tag = state['nsfw_tag']
    tags = state['tags']

    if tags:
        _res_list = list()
        for tag in tags:
            """
            _tag = DBPixivtag(tagname=tag)
            _res = _tag.list_illust(nsfw_tag=nsfw_tag)
            """
            _res = DBPixivillust.list_illust(nsfw_tag=nsfw_tag, keyword=tag)
            if _res.success():
                _pids = set(_res.result)
                _res_list.append(_pids)
        if len(_res_list) > 1:
            # 处理tag交集, 同时满足所有tag
            for item in _res_list[1:]:
                _res_list[0].intersection_update(item)
            pid_list = _res_list[0]
        elif len(_res_list) == 1:
            pid_list = _res_list[0]
        else:
            pid_list = _res_list
    else:
        # 没有tag则随机获取
        pid_list = DBPixivillust.rand_illust(num=3, nsfw_tag=nsfw_tag)

    if not pid_list:
        logger.info(f"Group: {event.group_id}, User: {event.user_id} 没有找到他/她想要的涩图")
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
            logger.warning(f"图片发送失败, group: {event.group_id}. error: {repr(e)}")
            continue

    if fault_count == len(pid_list):
        logger.info(f"Group: {event.group_id}, User: {event.user_id} 没能看到他/她想要的涩图")
        await setu.finish('似乎出现了网络问题, 所有的图片都下载失败了QAQ')
    else:
        logger.info(f"Group: {event.group_id}, User: {event.user_id} 找到了他/她想要的涩图")


# 注册事件响应器
moepic = Setu.command(
    'moepic',
    aliases={'来点萌图'},
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_permission_state(
        name='moepic',
        command=True,
        level=50,
        auth_node='moepic'))


@moepic.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = set(str(event.get_plaintext()).strip().split())
    # 排除r18
    for tag in args.copy():
        if tag in ['r18', 'R18', 'r-18', 'R-18']:
            args.remove(tag)
    state['tags'] = args


@moepic.got('tags', prompt='tag?')
async def handle_moepic(bot: Bot, event: GroupMessageEvent, state: T_State):
    tags = state['tags']
    if tags:
        _res_list = list()
        for tag in tags:
            _res = DBPixivillust.list_illust(nsfw_tag=0, keyword=tag)
            if _res.success():
                _pids = set(_res.result)
                _res_list.append(_pids)
        if len(_res_list) > 1:
            # 处理tag交集, 同时满足所有tag
            for item in _res_list[1:]:
                _res_list[0].intersection_update(item)
            pid_list = _res_list[0]
        elif len(_res_list) == 1:
            pid_list = _res_list[0]
        else:
            pid_list = _res_list
    else:
        # 没有tag则随机获取
        pid_list = DBPixivillust.rand_illust(num=3, nsfw_tag=0)

    if not pid_list:
        logger.info(f"Group: {event.group_id}, User: {event.user_id} 没有找到他/她想要的萌图")
        await moepic.finish('找不到萌图QAQ')
    elif len(pid_list) > 3:
        pid_list = random.sample(pid_list, k=3)

    await moepic.send('稍等, 正在下载图片~')
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
            await moepic.send(img_seg)
        except Exception as e:
            logger.warning(f"图片发送失败, group: {event.group_id}. error: {repr(e)}")
            continue

    if fault_count == len(pid_list):
        logger.info(f"Group: {event.group_id}, User: {event.user_id} 没能看到他/她想要的萌图")
        await moepic.finish('似乎出现了网络问题, 所有的图片都下载失败了QAQ')
    else:
        logger.info(f"Group: {event.group_id}, User: {event.user_id} 找到了他/她想要的萌图")


# 注册事件响应器
setu_stat = on_command('图库统计', rule=to_me(), permission=SUPERUSER, priority=20, block=True)


@setu_stat.handle()
async def handle_first_receive(bot: Bot, event: Event, state: T_State):
    _res = DBPixivillust.status()
    msg = f"本地数据库统计:\n\n" \
          f"全部: {_res.get('total')}\n" \
          f"萌图: {_res.get('moe')}\n" \
          f"涩图: {_res.get('setu')}\n" \
          f"R18: {_res.get('r18')}"
    await setu_stat.finish(msg)


# 注册事件响应器
setu_import = on_command('导入图库', rule=to_me(), permission=SUPERUSER, priority=20, block=True)


# 修改默认参数处理
@setu_import.args_parser
async def parse(bot: Bot, event: Event, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await setu_import.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await setu_import.finish('操作已取消')


@setu_import.handle()
async def handle_first_receive(bot: Bot, event: Event, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        pass
    elif args and len(args) == 1:
        state['mode'] = args[0]
    else:
        await setu_import.finish('参数错误QAQ')


@setu_import.got('mode', prompt='模式: 【setu/moe】')
async def handle_setu_import(bot: Bot, event: Event, state: T_State):
    mode = state['mode']
    if mode not in ['setu', 'moe']:
        await setu_import.reject('参数错误, 重新输入: 【setu/moe】, 取消命令请发送【取消】:')

    if mode == 'moe':
        nsfw_tag = 0
    else:
        nsfw_tag = 1

    import os
    import re

    # 文件操作
    import_pid_file = os.path.join(os.path.dirname(__file__), 'import_pid.txt')
    if not os.path.exists(import_pid_file):
        logger.error(f'setu_import: 找不到导入文件: {import_pid_file}')
        await setu_import.finish('错误: 导入列表不存在QAQ')

    pid_list = []
    try:
        with open(import_pid_file) as f:
            lines = f.readlines()
            for line in lines:
                if not re.match(r'^[0-9]+$', line):
                    logger.debug(f'setu_import: 导入列表中有非数字字符: {line}')
                    continue
                pid_list.append(int(line))
    except Exception as e:
        logger.error(f'setu_import: 读取导入列表失败, error: {repr(e)}')
        await setu_import.finish('错误: 读取导入列表失败QAQ')

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
            tasks.append(add_illust(pid=pid, nsfw_tag=nsfw_tag))
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
