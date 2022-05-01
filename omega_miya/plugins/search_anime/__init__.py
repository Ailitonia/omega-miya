from nonebot import on_command, get_driver, logger
from nonebot.plugin.export import export
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent, GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP, PRIVATE_FRIEND
from nonebot.adapters.cqhttp import MessageSegment
from omega_miya.utils.omega_plugin_utils import init_export, init_processor_state, PicEncoder, MsgSender
from .config import Config
from .utils import get_identify_result


__global_config = get_driver().config
plugin_config = Config(**__global_config.dict())
ENABLE_NODE_CUSTOM = plugin_config.enable_node_custom


# Custom plugin usage text
__plugin_custom_name__ = '识番'
__plugin_usage__ = r'''【识番助手】
使用 trace.moe API 识别番剧
群组/私聊可用

**Permission**
Friend Private
Command & Lv.50
or AuthNode

**AuthNode**
basic

**Usage**
/识番'''


# Init plugin export
init_export(export(), __plugin_custom_name__, __plugin_usage__)


# 注册事件响应器
search_anime = on_command(
    '识番',
    aliases={'搜番', '番剧识别'},
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='search_anime',
        command=True,
        level=50),
    permission=GROUP | PRIVATE_FRIEND,
    priority=20,
    block=True)


# 修改默认参数处理
@search_anime.args_parser
async def parse(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_message()).strip().split()
    if not args:
        await search_anime.reject('你似乎没有发送有效的消息呢QAQ, 请重新发送:')

    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await search_anime.finish('操作已取消')

    for msg_seg in event.message:
        if msg_seg.type == 'image':
            state[state["_current_key"]] = msg_seg.data.get('url')
            return


@search_anime.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
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
        await search_anime.finish('你发送的好像不是图片呢QAQ')


@search_anime.got('image_url', prompt='请发送你想要识别的番剧截图:')
async def handle_draw(bot: Bot, event: MessageEvent, state: T_State):
    if isinstance(event, GroupMessageEvent):
        group_id = event.group_id
    else:
        group_id = 'Private event'

    image_url = state['image_url']

    await search_anime.send('获取识别结果中, 请稍候~')
    res = await get_identify_result(img_url=image_url)
    if not res.success():
        logger.warning(f"{group_id} / {event.user_id} search_anime failed: {res.info}")
        await search_anime.finish('发生了意外的错误QAQ, 请稍后再试')

    if not res.result:
        logger.warning(f"{group_id} / {event.user_id} 使用了search_anime, 但没有找到相似的番剧")
        await search_anime.finish('没有找到与截图相似度足够高的番剧QAQ')

    msg_list = []
    for index, item in enumerate(res.result):
        try:
            filename = item.get('filename')
            episode = item.get('episode')
            from_ = item.get('from')
            to = item.get('to')
            similarity = item.get('similarity')
            image = item.get('image')
            title_native = item.get('title_native')
            title_chinese = item.get('title_chinese')
            is_adult = item.get('is_adult')

            img_result = await PicEncoder(pic_url=image).get_file(folder_flag='search_anime')

            if img_result.error:
                msg = f"识别结果:\n\n原始名称:【{title_native}】\n中文名称:【{title_chinese}】\n" \
                      f"相似度: {int(similarity*100)}\n\n来源文件: {filename}\n集数: 【{episode}】\n" \
                      f"预览图时间位置: {from_} - {to}\n绅士: {is_adult}"
                msg_list.append(msg)
            else:
                msg = f"识别结果:\n\n原始名称:【{title_native}】\n中文名称:【{title_chinese}】\n" \
                      f"相似度: {int(similarity*100)}\n\n来源文件: {filename}\n集数: 【{episode}】\n" \
                      f"预览图时间位置: {from_} - {to}\n绅士: {is_adult}\n" + MessageSegment.image(img_result.result)
                msg_list.append(msg)
        except Exception as e:
            logger.error(f"SearchAnime | 处理识别结果({index})时发生了错误: {repr(e)}, 已跳过")
            continue

    msg_sender = MsgSender(bot=bot, log_flag='SearchAnime')
    if isinstance(event, GroupMessageEvent) and ENABLE_NODE_CUSTOM:
        await msg_sender.safe_send_group_node_custom(group_id=event.group_id, message_list=msg_list)
    else:
        await msg_sender.safe_send_msgs(event=event, message_list=msg_list)
    logger.info(f"SearchAnime | {group_id} / {event.user_id} 进行了一次搜索")
