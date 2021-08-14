import re
import asyncio
from typing import Optional
from nonebot import on_command, logger, get_driver
from nonebot.plugin.export import export
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent, GroupMessageEvent, PrivateMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP, PRIVATE_FRIEND
from nonebot.adapters.cqhttp import MessageSegment, Message
from omega_miya.database import DBBot
from omega_miya.utils.omega_plugin_utils import \
    init_export, init_permission_state, PluginCoolDown, PermissionChecker, MsgSender
from omega_miya.utils.pixiv_utils import PixivIllust
from .config import Config


__global_config = get_driver().config
plugin_config = Config(**__global_config.dict())
ENABLE_NODE_CUSTOM = plugin_config.enable_node_custom


# Custom plugin usage text
__plugin_name__ = 'Pixiv'
__plugin_usage__ = r'''【Pixiv助手】
查看Pixiv插画, 以及日榜、周榜、月榜
仅限群聊使用

**Permission**
Command & Lv.50
or AuthNode

**AuthNode**
basic
download

**CoolDown**
群组共享冷却时间
1 Minutes
用户冷却时间
1 Minutes

**Usage**
/pixiv <PID>
/pixiv 日榜
/pixiv 周榜
/pixiv 月榜
**Need AuthNode**
/pixivdl <PID> [页码]'''

# 声明本插件可配置的权限节点
__plugin_auth_node__ = [
    PluginCoolDown.skip_auth_node,
    'basic',
    'allow_r18',
    'download'
]

# 声明本插件的冷却时间配置
__plugin_cool_down__ = [
    PluginCoolDown(PluginCoolDown.user_type, 1),
    PluginCoolDown(PluginCoolDown.group_type, 1)
]

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__, __plugin_auth_node__, __plugin_cool_down__)


# 注册事件响应器
pixiv = on_command(
    'pixiv',
    aliases={'Pixiv'},
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_permission_state(
        name='pixiv',
        command=True,
        level=50,
        auth_node='basic'),
    permission=GROUP | PRIVATE_FRIEND,
    priority=20,
    block=True)


# 修改默认参数处理
@pixiv.args_parser
async def parse(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await pixiv.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await pixiv.finish('操作已取消')


@pixiv.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        pass
    elif args and len(args) == 1:
        state['mode'] = args[0]
    else:
        await pixiv.finish('参数错误QAQ')


@pixiv.got('mode', prompt='你是想看日榜, 周榜, 月榜, 还是作品呢? 想看特定作品的话请输入PixivID~')
async def handle_pixiv(bot: Bot, event: MessageEvent, state: T_State):
    mode = state['mode']
    if mode == '日榜':
        await pixiv.send('稍等, 正在下载图片~')
        rank_result = await PixivIllust.get_ranking(mode='daily')
        if rank_result.error:
            logger.warning(f"User: {event.user_id} 获取Pixiv Rank失败, {rank_result.info}")
            await pixiv.finish('加载失败, 网络超时QAQ')

        tasks = []
        for rank, illust_data in dict(rank_result.result).items():
            if rank >= 10:
                break
            tasks.append(__handle_ranking_msg(rank=rank, illust_data=illust_data))
        ranking_msg_result = list(await asyncio.gather(*tasks))

        # 根据ENABLE_NODE_CUSTOM处理消息发送
        if ENABLE_NODE_CUSTOM and isinstance(event, GroupMessageEvent):
            msg_sender = MsgSender(bot=bot, log_flag='PixivDailyRanking')
            await msg_sender.safe_send_group_node_custom(group_id=event.group_id, message_list=ranking_msg_result)
        else:
            for msg_seg in ranking_msg_result:
                try:
                    await pixiv.send(msg_seg)
                except Exception as e:
                    logger.warning(f'图片发送失败, user: {event.user_id}. error: {repr(e)}')
    elif mode == '周榜':
        await pixiv.send('稍等, 正在下载图片~')
        rank_result = await PixivIllust.get_ranking(mode='weekly')
        if rank_result.error:
            logger.warning(f"User: {event.user_id} 获取Pixiv Rank失败, {rank_result.info}")
            await pixiv.finish('加载失败, 网络超时QAQ')

        tasks = []
        for rank, illust_data in dict(rank_result.result).items():
            if rank >= 10:
                break
            tasks.append(__handle_ranking_msg(rank=rank, illust_data=illust_data))
        ranking_msg_result = list(await asyncio.gather(*tasks))

        # 根据ENABLE_NODE_CUSTOM处理消息发送
        if ENABLE_NODE_CUSTOM and isinstance(event, GroupMessageEvent):
            msg_sender = MsgSender(bot=bot, log_flag='PixivWeeklyRanking')
            await msg_sender.safe_send_group_node_custom(group_id=event.group_id, message_list=ranking_msg_result)
        else:
            for msg_seg in ranking_msg_result:
                try:
                    await pixiv.send(msg_seg)
                except Exception as e:
                    logger.warning(f'图片发送失败, user: {event.user_id}. error: {repr(e)}')
    elif mode == '月榜':
        await pixiv.send('稍等, 正在下载图片~')
        rank_result = await PixivIllust.get_ranking(mode='monthly')
        if rank_result.error:
            logger.warning(f"User: {event.user_id} 获取Pixiv Rank失败, {rank_result.info}")
            await pixiv.finish('加载失败, 网络超时QAQ')

        tasks = []
        for rank, illust_data in dict(rank_result.result).items():
            if rank >= 10:
                break
            tasks.append(__handle_ranking_msg(rank=rank, illust_data=illust_data))
        ranking_msg_result = list(await asyncio.gather(*tasks))

        # 根据ENABLE_NODE_CUSTOM处理消息发送
        if ENABLE_NODE_CUSTOM and isinstance(event, GroupMessageEvent):
            msg_sender = MsgSender(bot=bot, log_flag='PixivMonthlyRanking')
            await msg_sender.safe_send_group_node_custom(group_id=event.group_id, message_list=ranking_msg_result)
        else:
            for msg_seg in ranking_msg_result:
                try:
                    await pixiv.send(msg_seg)
                except Exception as e:
                    logger.warning(f'图片发送失败, user: {event.user_id}. error: {repr(e)}')
    elif re.match(r'^\d+$', mode):
        pid = mode
        logger.debug(f'开始获取Pixiv资源: {pid}.')
        # 获取illust
        illust = PixivIllust(pid=pid)
        illust_data_result = await illust.get_illust_data()
        if illust_data_result.error:
            logger.warning(f"User: {event.user_id} 获取Pixiv资源失败, 网络超时或 {pid} 不存在, {illust_data_result.info}")
            await pixiv.finish('加载失败, 网络超时或没有这张图QAQ')

        # 处理r18权限
        if illust_data_result.result.get('is_r18'):
            if isinstance(event, PrivateMessageEvent):
                user_id = event.user_id
                auth_checker = await PermissionChecker(self_bot=DBBot(self_qq=int(bot.self_id))).\
                    check_auth_node(auth_id=user_id, auth_type='user', auth_node='pixiv.allow_r18')
            elif isinstance(event, GroupMessageEvent):
                group_id = event.group_id
                auth_checker = await PermissionChecker(self_bot=DBBot(self_qq=int(bot.self_id))).\
                    check_auth_node(auth_id=group_id, auth_type='group', auth_node='pixiv.allow_r18')
            else:
                auth_checker = 0

            if auth_checker != 1:
                logger.warning(f"User: {event.user_id} 获取Pixiv资源 {pid} 被拒绝, 没有 allow_r18 权限")
                await pixiv.finish('R18禁止! 不准开车车!')

        # 区分作品类型
        illust_type = illust_data_result.result.get('illust_type')
        await pixiv.send('稍等, 正在下载图片~')
        illust_info_result = await illust.get_format_info_msg()
        if illust_type == 2:
            # 动图作品生成动图后发送
            illust_result = await illust.get_ugoira_gif_filepath()
        else:
            illust_result = await illust.get_file()
        if illust_result.success() and illust_info_result.success():
            msg = illust_info_result.result
            img_seg = MessageSegment.image(illust_result.result)
            # 发送图片和图片信息
            await pixiv.send(Message(img_seg).append(msg))
        else:
            logger.warning(f"User: {event.user_id} 获取Pixiv资源失败, 网络超时或 {pid} 不存在, "
                           f"{illust_info_result.info} // {illust_result.info}")
            await pixiv.send('加载失败, 网络超时或没有这张图QAQ')
    else:
        await pixiv.reject('你输入的命令好像不对呢……请输入"月榜"、"周榜"、"日榜"或者PixivID, 取消命令请发送【取消】:')


# 注册事件响应器
pixiv_dl = on_command(
    'pixivdl',
    aliases={'Pixivdl'},
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_permission_state(
        name='pixivdl',
        command=True,
        auth_node='download'),
    permission=GROUP,
    priority=20,
    block=True)


# 修改默认参数处理
@pixiv_dl.args_parser
async def parse(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await pixiv_dl.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await pixiv_dl.finish('操作已取消')


@pixiv_dl.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        state['page'] = None
    elif args and len(args) == 1:
        state['pid'] = args[0]
        state['page'] = None
    elif args and len(args) == 2:
        state['pid'] = args[0]
        state['page'] = args[1]
    else:
        await pixiv_dl.finish('参数错误QAQ')

    if state['page']:
        try:
            state['page'] = int(state['page'])
        except ValueError:
            await pixiv_dl.finish('参数错误QAQ, 页码应为数字')


@pixiv_dl.got('pid', prompt='请输入PixivID:')
async def handle_pixiv_dl(bot: Bot, event: GroupMessageEvent, state: T_State):
    pid = state['pid']
    page = state['page']
    if re.match(r'^\d+$', pid):
        pid = int(pid)
        logger.debug(f'获取Pixiv资源: {pid}.')
        await pixiv_dl.send('稍等, 正在下载图片~')
        download_result = await PixivIllust(pid=pid).download_illust(page=page)
        if download_result.error:
            logger.warning(f"User: {event.user_id} 下载Pixiv资源失败, 网络超时或 {pid} 不存在, {download_result.info}")
            await pixiv_dl.finish('下载失败, 网络超时或没有这张图QAQ')
        else:
            file_path = download_result.result
            file_name = download_result.info
            try:
                await bot.call_api(api='upload_group_file', group_id=event.group_id, file=file_path, name=file_name)
            except Exception as e:
                logger.warning(f'User: {event.user_id} 下载Pixiv资源失败, 上传群文件失败: {repr(e)}')
                await pixiv_dl.finish('上传图片到群文件失败QAQ, 可能获取上传结果超时但上传仍在进行中, 请等待1~2分钟后再重试')

    else:
        await pixiv_dl.finish('参数错误, pid应为纯数字')


# 处理Pixiv.__ranking榜单消息
async def __handle_ranking_msg(rank: int, illust_data: dict) -> Optional[Message]:
    rank += 1

    illust_id = illust_data.get('illust_id')
    illust_title = illust_data.get('illust_title')
    illust_uname = illust_data.get('illust_uname')

    image_result = await PixivIllust(pid=illust_id).get_file()
    if image_result.success():
        msg = f'No.{rank} - ID: {illust_id}\n「{illust_title}」/「{illust_uname}」'
        img_seg = MessageSegment.image(image_result.result)
        return Message(img_seg).append(msg)
    else:
        logger.warning(f"下载图片失败, pid: {illust_id}, {image_result.info}")
        return None
