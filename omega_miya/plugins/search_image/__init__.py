from nonebot import on_command, export, logger
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent, GroupMessageEvent, PrivateMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP, PRIVATE_FRIEND
from nonebot.adapters.cqhttp import MessageSegment, Message
from omega_miya.utils.Omega_plugin_utils import init_export, init_permission_state
from .utils import pic_2_base64, get_saucenao_identify_result, get_ascii2d_identify_result

# Custom plugin usage text
__plugin_name__ = '识图'
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
/识图'''

# 声明本插件可配置的权限节点
__plugin_auth_node__ = [
    'basic'
]

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__, __plugin_auth_node__)


# 注册事件响应器
search_image = on_command(
    '识图',
    aliases={'搜图'},
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_permission_state(
        name='search_image',
        command=True,
        level=50,
        auth_node='basic'),
    permission=GROUP | PRIVATE_FRIEND,
    priority=20,
    block=True)


# 修改默认参数处理
@search_image.args_parser
async def parse(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_message()).strip().split()
    if not args:
        await search_image.reject('你似乎没有发送有效的消息呢QAQ, 请重新发送:')

    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await search_image.finish('操作已取消')

    for msg_seg in event.message:
        if msg_seg.type == 'image':
            state[state["_current_key"]] = msg_seg.data.get('url')
            return


@search_image.handle()
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
        await search_image.finish('你发送的好像不是图片呢QAQ')


@search_image.got('image_url', prompt='请发送你想要识别的图片:')
async def handle_draw(bot: Bot, event: MessageEvent, state: T_State):
    if isinstance(event, GroupMessageEvent):
        group_id = event.group_id
    else:
        group_id = 'Private event'

    image_url = state['image_url']
    try:
        has_error = False
        await search_image.send('获取识别结果中, 请稍后~')
        identify_result = []
        identify_saucenao_result = await get_saucenao_identify_result(url=image_url)
        if identify_saucenao_result.success():
            identify_result.extend(identify_saucenao_result.result)
        else:
            has_error = True

        # saucenao 没有结果时再使用 ascii2d 进行搜索
        if not identify_result:
            identify_ascii2d_result = await get_ascii2d_identify_result(url=image_url)
            # 合并搜索结果
            if identify_ascii2d_result.success():
                identify_result.extend(identify_ascii2d_result.result)
            else:
                has_error = True
        if identify_result:
            for item in identify_result:
                try:
                    if type(item['ext_urls']) == list:
                        ext_urls = ''
                        for urls in item['ext_urls']:
                            ext_urls += f'{urls}\n'
                        ext_urls = ext_urls.strip()
                    else:
                        ext_urls = item['ext_urls']
                        ext_urls = ext_urls.strip()
                    img_b64 = await pic_2_base64(item['thumbnail'])
                    if not img_b64.success():
                        msg = f"识别结果: {item['index_name']}\n\n相似度: {item['similarity']}\n资源链接: {ext_urls}"
                        await search_image.send(msg)
                    else:
                        img_seg = MessageSegment.image(img_b64.result)
                        msg = f"识别结果: {item['index_name']}\n\n相似度: {item['similarity']}\n资源链接: {ext_urls}\n{img_seg}"
                        await search_image.send(Message(msg))
                except Exception as e:
                    logger.warning(f'处理和发送识别结果时发生了错误: {repr(e)}')
                    continue
            logger.info(f"{group_id} / {event.user_id} 使用searchimage成功搜索了一张图片")
            return
        elif not identify_result and has_error:
            await search_image.send('识图过程中获取信息失败QAQ, 可能被流量限制, 或图片大小超过5Mb限制, 请重试一下吧')
            logger.info(f"{group_id} / {event.user_id} 使用了searchimage, 但在识图过程中获取信息失败")
            return
        else:
            await search_image.send('没有找到相似度足够高的图片QAQ')
            logger.info(f"{group_id} / {event.user_id} 使用了searchimage, 但没有找到相似的图片")
            return
    except Exception as e:
        await search_image.send('识图失败, 发生了意外的错误QAQ, 请稍后重试')
        logger.error(f"{group_id} / {event.user_id} 使用命令searchimage时发生了错误: {repr(e)}")
        return
