import os
import re
import asyncio
import aiofiles
from nonebot import CommandGroup, on_command, get_driver, logger
from nonebot.plugin.export import export
from nonebot.rule import to_me
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import Event, MessageEvent, GroupMessageEvent, PrivateMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP, PRIVATE_FRIEND
from nonebot.adapters.cqhttp import MessageSegment
from omega_miya.utils.omega_plugin_utils import init_export, init_permission_state, PluginCoolDown, PermissionChecker
from omega_miya.utils.omega_plugin_utils import PicEncoder, PicEffector, MsgSender, ProcessUtils
from omega_miya.database import DBBot, DBPixivillust
from omega_miya.utils.pixiv_utils import PixivIllust
from .utils import add_illust
from .config import Config


__global_config = get_driver().config
plugin_config = Config(**__global_config.dict())
ACC_MODE = plugin_config.acc_mode
IMAGE_NUM_LIMIT = plugin_config.image_num_limit
ENABLE_NODE_CUSTOM = plugin_config.enable_node_custom
ENABLE_MOE_FLASH = plugin_config.enable_moe_flash
ENABLE_SETU_FLASH = plugin_config.enable_setu_flash
ENABLE_SETU_GAUSSIAN_BLUR = plugin_config.enable_setu_gaussian_blur
ENABLE_SETU_GAUSSIAN_NOISE = plugin_config.enable_setu_gaussian_noise
AUTO_RECALL_TIME = plugin_config.auto_recall_time
ENABLE_MOE_AUTO_RECALL = plugin_config.enable_moe_auto_recall
ENABLE_SETU_AUTO_RECALL = plugin_config.enable_setu_auto_recall


# Custom plugin usage text
__plugin_custom_name__ = '来点萌图'
__plugin_usage__ = r'''【来点萌图】
测试群友LSP成分
群组/私聊可用

**Permission**
Friend Private
Command & Lv.50
or AuthNode

**AuthNode**
setu
moepic
allow_r18

**CoolDown**
群组共享冷却时间
1 Minutes
用户冷却时间
1 Minutes

**Usage**
/来点涩图 [tag]
/来点萌图 [tag]

**SuperUser Only**
/图库统计
/图库查询 [*keywords]
/导入图库'''

# 声明本插件可配置的权限节点
__plugin_auth_node__ = [
    PluginCoolDown.skip_auth_node,
    'setu',
    'allow_r18',
    'moepic'
]

# 声明本插件的冷却时间配置
__plugin_cool_down__ = [
    PluginCoolDown(PluginCoolDown.user_type, 3),
    PluginCoolDown(PluginCoolDown.group_type, 2)
]

# Init plugin export
init_export(export(), __plugin_custom_name__, __plugin_usage__, __plugin_auth_node__, __plugin_cool_down__)


# 注册事件响应器
Setu = CommandGroup('sepic', permission=GROUP | PRIVATE_FRIEND, priority=20, block=True)

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
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    args = set(str(event.get_plaintext()).strip().split())
    # 处理r18
    state['nsfw_tag'] = 1
    for tag in args.copy():
        if re.match(r'[Rr]-?18[Gg]?', tag):
            args.remove(tag)
            state['nsfw_tag'] = 2
    state['tags'] = list(args)


@setu.got('tags', prompt='tag?')
async def handle_setu(bot: Bot, event: MessageEvent, state: T_State):
    if isinstance(event, GroupMessageEvent):
        group_id = event.group_id
    else:
        group_id = 'Private event'

    nsfw_tag = state['nsfw_tag']
    tags = state['tags']

    # 处理R18权限
    if nsfw_tag > 1:
        auth_checker = await __handle_r18_perm(bot=bot, event=event)
        if auth_checker != 1:
            logger.warning(f"User: {event.user_id} 请求涩图被拒绝, 没有 allow_r18 权限")
            await setu.finish('R18禁止! 不准开车车!')

    if tags:
        pid_res = await DBPixivillust.list_illust(
            keywords=tags, num=IMAGE_NUM_LIMIT, nsfw_tag=nsfw_tag, acc_mode=ACC_MODE)
        pid_list = pid_res.result
    else:
        # 没有tag则随机获取
        pid_res = await DBPixivillust.rand_illust(num=IMAGE_NUM_LIMIT, nsfw_tag=nsfw_tag)
        pid_list = pid_res.result

    if not pid_list:
        logger.info(f"{group_id} / {event.user_id} 没有找到他/她想要的涩图")
        await setu.finish('找不到涩图QAQ')
    await setu.send('稍等, 正在下载图片~')
    # 处理article中图片内容
    tasks = []
    for pid in pid_list:
        tasks.append(PixivIllust(pid=pid).load_illust_pic())
    p_res = await asyncio.gather(*tasks)

    # 处理图片消息段, 之后再根据ENABLE_NODE_CUSTOM确定消息发送方式
    fault_count = 0
    image_seg_list = []
    for image_res in p_res:
        try:
            if image_res.error:
                fault_count += 1
                logger.warning(f'图片下载失败, error: {image_res.info}')
                continue
            if ENABLE_SETU_GAUSSIAN_NOISE:
                image_res = await PicEffector(image=image_res.result).gaussian_noise(sigma=16)
                if image_res.error:
                    fault_count += 1
                    logger.warning(f'处理图片高斯噪声处理失败, error: {image_res.info}')
                    continue
            if ENABLE_SETU_GAUSSIAN_BLUR:
                image_res = await PicEffector(image=image_res.result).gaussian_blur(radius=4)
                if image_res.error:
                    fault_count += 1
                    logger.warning(f'处理图片高斯模糊失败, error: {image_res.info}')
                    continue
            image_res = await PicEncoder.bytes_to_file(image=image_res.result, folder_flag='setu')
            if image_res.error:
                fault_count += 1
                logger.warning(f'图片转换失败, error: {image_res.info}')
                continue
            else:
                if ENABLE_SETU_FLASH:
                    image_seg_list.append(MessageSegment.image(image_res.result, type_='flash'))
                else:
                    image_seg_list.append(MessageSegment.image(image_res.result))
        except Exception as e:
            logger.warning(f'预处理图片失败: {repr(e)}')
            continue

    sent_msg_ids = []
    # 根据ENABLE_NODE_CUSTOM处理消息发送
    if ENABLE_NODE_CUSTOM and isinstance(event, GroupMessageEvent):
        msg_sender = MsgSender(bot=bot, log_flag='Setu')
        await msg_sender.safe_send_group_node_custom(group_id=event.group_id, message_list=image_seg_list)
    else:
        for msg_seg in image_seg_list:
            try:
                sent_msg_id = await setu.send(msg_seg)
                sent_msg_ids.append(sent_msg_id.get('message_id') if isinstance(sent_msg_id, dict) else None)
            except Exception as e:
                logger.warning(f'图片发送失败, {group_id} / {event.user_id}. error: {repr(e)}')

    if fault_count == len(pid_list):
        logger.info(f"{group_id} / {event.user_id} 没能看到他/她想要的涩图, 图片下载失败, {pid_list}")
        await setu.finish('似乎出现了网络问题, 所有的图片都下载失败了QAQ')
    else:
        logger.info(f"{group_id} / {event.user_id} 找到了他/她想要的涩图, {pid_list}")

    if ENABLE_SETU_AUTO_RECALL:
        logger.info(f"{group_id} / {event.user_id} 撤回已发送涩图...")
        await asyncio.sleep(AUTO_RECALL_TIME)
        for msg_id in sent_msg_ids:
            if not msg_id:
                continue
            try:
                await bot.delete_msg(message_id=msg_id)
            except Exception as e:
                logger.warning(f'撤回图片失败, {group_id} / {event.user_id}, msg_id: {msg_id}. error: {repr(e)}')
                continue


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
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    args = set(str(event.get_plaintext()).strip().split())
    # 排除r18
    for tag in args.copy():
        if re.match(r'[Rr]-?18[Gg]?', tag):
            args.remove(tag)
    state['tags'] = list(args)


@moepic.got('tags', prompt='tag?')
async def handle_moepic(bot: Bot, event: MessageEvent, state: T_State):
    if isinstance(event, GroupMessageEvent):
        group_id = event.group_id
    else:
        group_id = 'Private event'

    tags = state['tags']

    if tags:
        pid_res = await DBPixivillust.list_illust(keywords=tags, num=IMAGE_NUM_LIMIT, nsfw_tag=0, acc_mode=ACC_MODE)
        pid_list = pid_res.result
    else:
        # 没有tag则随机获取
        pid_res = await DBPixivillust.rand_illust(num=IMAGE_NUM_LIMIT, nsfw_tag=0)
        pid_list = pid_res.result

    if not pid_list:
        logger.info(f"{group_id} / {event.user_id} 没有找到他/她想要的萌图")
        await moepic.finish('找不到萌图QAQ')

    await moepic.send('稍等, 正在下载图片~')
    # 处理article中图片内容
    tasks = []
    for pid in pid_list:
        tasks.append(PixivIllust(pid=pid).load_illust_pic())
    p_res = await asyncio.gather(*tasks)

    # 处理图片消息段, 之后再根据ENABLE_NODE_CUSTOM确定消息发送方式
    fault_count = 0
    image_seg_list = []
    for image_res in p_res:
        try:
            if image_res.error:
                fault_count += 1
                logger.warning(f'图片下载失败, error: {image_res.info}')
                continue
            image_res = await PicEncoder.bytes_to_file(image=image_res.result, folder_flag='moepic')
            if image_res.error:
                fault_count += 1
                logger.warning(f'图片转换失败, error: {image_res.info}')
                continue
            else:
                if ENABLE_MOE_FLASH:
                    image_seg_list.append(MessageSegment.image(image_res.result, type_='flash'))
                else:
                    image_seg_list.append(MessageSegment.image(image_res.result))
        except Exception as e:
            logger.warning(f'预处理图片失败: {repr(e)}')
            continue

    sent_msg_ids = []
    # 根据ENABLE_NODE_CUSTOM处理消息发送
    if ENABLE_NODE_CUSTOM and isinstance(event, GroupMessageEvent):
        msg_sender = MsgSender(bot=bot, log_flag='Moepic')
        await msg_sender.safe_send_group_node_custom(group_id=event.group_id, message_list=image_seg_list)
    else:
        for msg_seg in image_seg_list:
            try:
                sent_msg_id = await moepic.send(msg_seg)
                sent_msg_ids.append(sent_msg_id.get('message_id') if isinstance(sent_msg_id, dict) else None)
            except Exception as e:
                logger.warning(f'图片发送失败, {group_id} / {event.user_id}. error: {repr(e)}')

    if fault_count == len(pid_list):
        logger.info(f"{group_id} / {event.user_id} 没能看到他/她想要的萌图, 图片下载失败, {pid_list}")
        await moepic.finish('似乎出现了网络问题, 所有的图片都下载失败了QAQ')
    else:
        logger.info(f"{group_id} / {event.user_id} 找到了他/她想要的萌图, {pid_list}")

    if ENABLE_MOE_AUTO_RECALL:
        logger.info(f"{group_id} / {event.user_id} 撤回已发送萌图...")
        await asyncio.sleep(AUTO_RECALL_TIME)
        for msg_id in sent_msg_ids:
            if not msg_id:
                continue
            try:
                await bot.delete_msg(message_id=msg_id)
            except Exception as e:
                logger.warning(f'撤回图片失败, {group_id} / {event.user_id}, msg_id: {msg_id}. error: {repr(e)}')
                continue


# 注册事件响应器
setu_stat = on_command('图库统计', rule=to_me(), permission=SUPERUSER, priority=20, block=True)


@setu_stat.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    status_res = await DBPixivillust.status()
    if status_res.error:
        logger.error(f'{event.user_id} 执行图库统计失败, {status_res.info}')
        await setu_stat.finish('查询失败了QAQ, 请稍后再试')

    msg = f"本地数据库统计:\n\n" \
          f"全部: {status_res.result.get('total')}\n" \
          f"萌图: {status_res.result.get('moe')}\n" \
          f"涩图: {status_res.result.get('setu')}\n" \
          f"R18: {status_res.result.get('r18')}"
    logger.info(f'{event.user_id} 执行图库统计成功')
    await setu_stat.finish(msg)


# 注册事件响应器
setu_count = on_command('图库查询', aliases={'查询图库'}, rule=to_me(), permission=SUPERUSER, priority=20, block=True)


@setu_count.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().split()
    if not args:
        logger.info(f'{event.user_id} 执行图库查询被取消, 未指定查询关键字')
        await setu_count.finish('无查询关键字QAQ, 查询取消')

    count_res = await DBPixivillust.count_keywords(keywords=args)
    if count_res.error:
        logger.error(f'{event.user_id} 执行图库查询失败, {count_res.info}')
        await setu_count.finish('无查询关键字QAQ, 查询取消')

    msg = f"查询关键字 {'/'.join(args)} 结果:\n\n" \
          f"全部: {count_res.result.get('total')}\n" \
          f"萌图: {count_res.result.get('moe')}\n" \
          f"涩图: {count_res.result.get('setu')}\n" \
          f"R18: {count_res.result.get('r18')}"
    await setu_count.finish(msg)


# 注册事件响应器
setu_import = on_command('导入图库', aliases={'图库导入'}, rule=to_me(), permission=SUPERUSER, priority=20, block=True)


# 修改默认参数处理
@setu_import.args_parser
async def parse(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await setu_import.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await setu_import.finish('操作已取消')


@setu_import.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        pass
    elif args and len(args) == 1:
        state['mode'] = args[0]
    else:
        await setu_import.finish('参数错误QAQ')


@setu_import.got('mode', prompt='模式: 【setu/moe】')
async def handle_setu_import(bot: Bot, event: MessageEvent, state: T_State):
    mode = state['mode']
    if mode not in ['setu', 'moe']:
        await setu_import.reject('参数错误, 重新输入: 【setu/moe】, 取消命令请发送【取消】:')

    if mode == 'moe':
        nsfw_tag = 0
        force_tag = True
    else:
        nsfw_tag = 1
        force_tag = False

    # 文件操作
    import_pid_file = os.path.join(os.path.dirname(__file__), 'import_pid.txt')
    if not os.path.exists(import_pid_file):
        logger.error(f'setu_import: 找不到导入文件: {import_pid_file}')
        await setu_import.finish('错误: 导入列表不存在QAQ')

    pid_list = []
    try:
        async with aiofiles.open(import_pid_file, 'r') as f:
            lines = await f.readlines()
            for line in lines:
                if not re.match(r'^[0-9]+$', line):
                    logger.debug(f'setu_import: 导入列表中有非数字字符: {line}')
                    continue
                pid_list.append(int(line))
    except Exception as e:
        logger.error(f'setu_import: 读取导入列表失败, error: {repr(e)}')
        await setu_import.finish('错误: 读取导入列表失败QAQ')

    # 对列表去重
    pid_list = list(set(pid_list))
    pid_list.sort()
    all_count = len(pid_list)
    await setu_import.send('已读取导入文件列表, 开始获取作品信息~')
    logger.info(f'setu_import: 读取导入文件列表完成, 总计: {all_count}, 开始导入...')
    # 开始导入操作
    # 全部一起并发网络撑不住, 做适当切分
    tasks = [add_illust(pid=pid, nsfw_tag=nsfw_tag, force_tag=force_tag) for pid in pid_list]
    _res = await ProcessUtils.fragment_process(tasks=tasks, fragment_size=50, log_flag='Setu Import')
    success_count = len([x for x in _res if x.success()])

    logger.info(f'setu_import: 导入操作已完成, 成功: {success_count}, 总计: {all_count}')
    await setu_import.send(f'导入操作已完成, 成功: {success_count}, 总计: {all_count}')


# 处理 setu 插件 r18 权限
async def __handle_r18_perm(bot: Bot, event: Event) -> int:
    if isinstance(event, PrivateMessageEvent):
        user_id = event.user_id
        auth_checker = await PermissionChecker(self_bot=DBBot(self_qq=int(bot.self_id))). \
            check_auth_node(auth_id=user_id, auth_type='user', auth_node='setu.allow_r18')
    elif isinstance(event, GroupMessageEvent):
        group_id = event.group_id
        auth_checker = await PermissionChecker(self_bot=DBBot(self_qq=int(bot.self_id))). \
            check_auth_node(auth_id=group_id, auth_type='group', auth_node='setu.allow_r18')
    else:
        auth_checker = 0
    return auth_checker
