import random
import asyncio
from nonebot import on_command, logger, get_driver
from nonebot.plugin.export import export
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent, GroupMessageEvent, PrivateMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP, PRIVATE_FRIEND
from nonebot.adapters.cqhttp import MessageSegment, Message
from omega_miya.database import DBBot
from omega_miya.utils.omega_plugin_utils import (init_export, init_processor_state,
                                                 PicEncoder, PermissionChecker, PluginCoolDown)
from omega_miya.utils.pixiv_utils import PixivIllust
from .utils import SEARCH_ENGINE, HEADERS
from .config import Config

__global_config = get_driver().config
plugin_config = Config(**__global_config.dict())
ENABLE_SAUCENAO = plugin_config.enable_saucenao
ENABLE_IQDB = plugin_config.enable_iqdb
ENABLE_ASCII2D = plugin_config.enable_ascii2d
AUTO_RECALL_TIME = plugin_config.auto_recall_time
ENABLE_RECOMMEND_AUTO_RECALL = plugin_config.enable_recommend_auto_recall

# Custom plugin usage text
__plugin_custom_name__ = '识图'
__plugin_usage__ = r'''【识图助手】
使用SauceNAO/ascii2d识别各类图片、插画
群组/私聊可用

**Permission**
Friend Private
Command & Lv.50
or AuthNode

**AuthNode**
basic

**Usage**
/识图

**Hidden Command**
/再来点'''

# 声明本插件额外可配置的权限节点
__plugin_auth_node__ = [
    'recommend_image',
    'allow_recommend_r18'
]

# Init plugin export
init_export(export(), __plugin_custom_name__, __plugin_usage__, __plugin_auth_node__)


# 注册事件响应器
search_image = on_command(
    '识图',
    aliases={'搜图'},
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='search_image',
        command=True,
        level=50),
    permission=GROUP | PRIVATE_FRIEND,
    priority=20,
    block=True)


# 修改默认参数处理
@search_image.args_parser
async def parse(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_message()).strip().split()
    if not args:
        await search_image.reject('你似乎没有发送有效的消息呢QAQ, 请重新发送:')

    if state["_current_key"] == 'using_engine':
        if args[0] == '是':
            return
        else:
            await search_image.finish('操作已取消')

    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await search_image.finish('操作已取消')

    for msg_seg in event.message:
        if msg_seg.type == 'image':
            state[state["_current_key"]] = msg_seg.data.get('url')
            return


@search_image.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    # 识图引擎开关
    usable_engine = []
    if ENABLE_SAUCENAO:
        usable_engine.append('saucenao')
    if ENABLE_IQDB:
        usable_engine.append('iqdb')
    if ENABLE_ASCII2D:
        usable_engine.append('ascii2d')

    state['using_engine'] = usable_engine.pop(0) if usable_engine else None
    state['usable_engine'] = usable_engine

    # 提取图片链接, 默认只取消息中的第一张图
    img_url = None
    if event.reply:
        for msg_seg in event.reply.message:
            if msg_seg.type == 'image':
                img_url = msg_seg.data.get('url')
                break
    else:
        for msg_seg in event.message:
            if msg_seg.type == 'image':
                img_url = msg_seg.data.get('url')
                break
    if img_url:
        state['image_url'] = img_url
        return

    args = str(event.get_plaintext()).strip().lower().split()
    if args:
        await search_image.finish('你发送的好像不是图片呢QAQ')


@search_image.got('image_url', prompt='请发送你想要识别的图片:')
async def handle_got_image(bot: Bot, event: MessageEvent, state: T_State):
    image_url = state['image_url']
    if not str(image_url).startswith('http'):
        await search_image.finish('错误QAQ，你发送的不是有效的图片')
    await search_image.send('获取识别结果中, 请稍后~')


@search_image.got('using_engine', prompt='使用识图引擎识图:')
async def handle_saucenao(bot: Bot, event: MessageEvent, state: T_State):
    image_url = state['image_url']
    using_engine = state['using_engine']
    usable_engine = list(state['usable_engine'])

    # 获取识图结果
    search_engine = SEARCH_ENGINE.get(using_engine, None)
    if using_engine and search_engine:
        identify_result = await search_engine(image_url)
        if identify_result.success() and identify_result.result:
            # 有结果了, 继续执行接下来的结果解析handler
            pass
        else:
            # 没有结果
            if identify_result.error:
                logger.warning(f'{using_engine}引擎获取识别结果失败: {identify_result.info}')
            if usable_engine:
                # 还有可用的识图引擎
                next_using_engine = usable_engine.pop(0)
                msg = f'{using_engine}引擎没有找到相似度足够高的图片，是否继续使用{next_using_engine}引擎识别图片?\n\n【是/否】'
                state['using_engine'] = next_using_engine
                state['usable_engine'] = usable_engine
                await search_image.reject(msg)
            else:
                # 没有可用的识图引擎了
                logger.info(f'{event.user_id} 使用了searchimage所有的识图引擎, 但没有找到相似的图片')
                await search_image.finish('没有找到相似度足够高的图片QAQ')
    else:
        logger.error(f'获取识图引擎异常, using_engine: {using_engine}')
        await search_image.finish('发生了意外的错误QAQ, 请稍后再试或联系管理员')
        return

    state['identify_result'] = identify_result.result


@search_image.handle()
async def handle_result(bot: Bot, event: MessageEvent, state: T_State):
    if isinstance(event, GroupMessageEvent):
        group_id = event.group_id
    else:
        group_id = 'Private event'

    identify_result = state['identify_result']
    try:
        if identify_result:
            for item in identify_result:
                try:
                    if isinstance(item['ext_urls'], list):
                        ext_urls = '\n'.join(item['ext_urls'])
                    else:
                        ext_urls = item['ext_urls'].strip()
                    img_result = await PicEncoder(
                        pic_url=item['thumbnail'], headers=HEADERS).get_file(folder_flag='search_image')
                    if img_result.error:
                        msg = f"识别结果: {item['index_name']}\n\n相似度: {item['similarity']}\n资源链接: {ext_urls}"
                        await search_image.send(msg)
                    else:
                        img_seg = MessageSegment.image(img_result.result)
                        msg = f"识别结果: {item['index_name']}\n\n相似度: {item['similarity']}\n资源链接: {ext_urls}\n{img_seg}"
                        await search_image.send(Message(msg))
                except Exception as e:
                    logger.warning(f'处理和发送识别结果时发生了错误: {repr(e)}')
                    continue
            logger.info(f"{group_id} / {event.user_id} 使用searchimage成功搜索了一张图片")
            return
        else:
            await search_image.send('没有找到相似度足够高的图片QAQ')
            logger.info(f"{group_id} / {event.user_id} 使用了searchimage, 但没有找到相似的图片")
            return
    except Exception as e:
        await search_image.send('识图失败, 发生了意外的错误QAQ, 请稍后重试')
        logger.error(f"{group_id} / {event.user_id} 使用命令searchimage时发生了错误: {repr(e)}")
        return


# 注册事件响应器
recommend_image = on_command(  # 使用 pixiv api 的相关作品推荐功能查找相似作品
    '再来点',
    aliases={'多来点', '相似作品', '类似作品'},
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='search_image_recommend_image',
        command=True,
        auth_node='recommend_image',
        cool_down=[PluginCoolDown(PluginCoolDown.group_type, 90)]
    ),
    permission=GROUP | PRIVATE_FRIEND,
    priority=20,
    block=True)


@recommend_image.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    # 从回复消息中捕获待匹配的图片信息
    # 只返回匹配到的第一个符合要求的链接或图片
    if event.reply:
        # 首先筛查链接
        for msg_seg in event.reply.message:
            if msg_seg.type == 'text':
                text = msg_seg.data.get('text')
                if pid := PixivIllust.parse_pid_from_url(text=text):
                    state['pid'] = pid
                    logger.debug(f"Recommend image | 已从消息段文本匹配到 pixiv url, pid: {pid}")
                    return

        # 若消息被分片可能导致链接被拆分
        raw_text = getattr(event.reply, 'raw_message', None)
        if pid := PixivIllust.parse_pid_from_url(text=raw_text):
            state['pid'] = pid
            logger.debug(f"Recommend image | 已从消息 raw 文本匹配到 pixiv url, pid: {pid}")
            return

        # 没有发现则开始对图片进行识别, 为保证准确性只使用 saucenao api
        for msg_seg in event.reply.message:
            if msg_seg.type == 'image':
                img_url = msg_seg.data.get('url')
                saucenao_search_engine = SEARCH_ENGINE.get('saucenao')
                identify_result = await saucenao_search_engine(img_url)
                # 从识别结果中匹配图片
                for url_list in [x.get('ext_urls') for x in identify_result.result]:
                    for url in url_list:
                        if pid := PixivIllust.parse_pid_from_url(text=url):
                            state['pid'] = pid
                            logger.debug(f"Recommend image | 已从识别图片匹配到 pixiv url, pid: {pid}")
                            return
    else:
        logger.debug(f'Recommend image | 命令没有引用消息, 操作已取消')
        await recommend_image.finish('没有引用需要查找的图片QAQ, 请使用本命令时直接回复相关消息')


@recommend_image.handle()
async def handle_illust_recommend(bot: Bot, event: GroupMessageEvent, state: T_State):
    pid = state.get('pid')
    if not pid:
        logger.debug(f'Recommend image | 没有匹配到图片pid, 操作已取消')
        await recommend_image.finish('没有匹配到相关图片QAQ, 请确认搜索的图片是在 Pixiv 上的作品')

    recommend_result = await PixivIllust(pid=pid).get_recommend(init_limit=36)
    if recommend_result.error:
        logger.warning(f'Recommend image | 获取相似作品信息失败, pid: {pid}, error: {recommend_result.info}')
        await recommend_image.finish('获取相关作品信息失败QAQ, 原作品可能已经被删除')

    # 获取推荐作品的信息
    await recommend_image.send('稍等, 正在获取相似作品~')
    pid_list = [x.get('id') for x in recommend_result.result.get('illusts') if x.get('illustType') == 0]
    tasks = [PixivIllust(pid=x).get_illust_data() for x in pid_list]
    recommend_illust_data_result = await asyncio.gather(*tasks)

    # 执行 r18 权限检查
    if isinstance(event, PrivateMessageEvent):
        user_id = event.user_id
        auth_checker = await PermissionChecker(self_bot=DBBot(self_qq=int(bot.self_id))). \
            check_auth_node(auth_id=user_id, auth_type='user', auth_node='search_image.allow_recommend_r18')
    elif isinstance(event, GroupMessageEvent):
        group_id = event.group_id
        auth_checker = await PermissionChecker(self_bot=DBBot(self_qq=int(bot.self_id))). \
            check_auth_node(auth_id=group_id, auth_type='group', auth_node='search_image.allow_recommend_r18')
    else:
        auth_checker = 0

    # 筛选推荐作品 筛选条件 收藏不少于2k 点赞数不少于收藏一半 点赞率大于百分之五
    if auth_checker == 1:
        filtered_illust_data_result = [x for x in recommend_illust_data_result if (
                x.success() and
                2000 <= x.result.get('bookmark_count') <= 2 * x.result.get('like_count') and
                x.result.get('view_count') <= 20 * x.result.get('like_count')
        )]
    else:
        filtered_illust_data_result = [x for x in recommend_illust_data_result if (
                x.success() and
                not x.result.get('is_r18') and
                2000 <= x.result.get('bookmark_count') <= 2 * x.result.get('like_count') and
                x.result.get('view_count') <= 20 * x.result.get('like_count')
        )]

    # 从筛选结果里面随机挑三个
    if len(filtered_illust_data_result) > 3:
        illust_list = [PixivIllust(pid=x.result.get('pid')) for x in random.sample(filtered_illust_data_result, k=3)]
    else:
        illust_list = [PixivIllust(pid=x.result.get('pid')) for x in filtered_illust_data_result]

    if not illust_list:
        logger.info(f'Recommend image | 筛选结果为0, 没有找到符合要求的相似作品')
        await recommend_image.finish('没有找到符合要求的相似作品QAQ')

    # 直接下载图片
    tasks = [x.get_sending_msg() for x in illust_list]
    illust_download_result = await asyncio.gather(*tasks)

    sent_msg_ids = []
    for img, info in [x.result for x in illust_download_result if x.success()]:
        img_seg = MessageSegment.image(file=img)
        try:
            sent_msg_id = await recommend_image.send(Message(img_seg).append(info))
            sent_msg_ids.append(sent_msg_id.get('message_id') if isinstance(sent_msg_id, dict) else None)
        except Exception as e:
            logger.warning(f'Recommend image | 发送图片失败, error: {repr(e)}')
            continue
    logger.info(f'Recommend image | User: {event.user_id} 已获取相似图片')

    if ENABLE_RECOMMEND_AUTO_RECALL:
        logger.info(f"{event.group_id} / {event.self_id} 将于 {AUTO_RECALL_TIME} 秒后撤回已发送相似图片...")
        await asyncio.sleep(AUTO_RECALL_TIME)
        for msg_id in sent_msg_ids:
            if not msg_id:
                continue
            try:
                await bot.delete_msg(message_id=msg_id)
            except Exception as e:
                logger.warning(f'撤回图片失败, {event.group_id} / {event.user_id}, msg_id: {msg_id}. error: {repr(e)}')
                continue
