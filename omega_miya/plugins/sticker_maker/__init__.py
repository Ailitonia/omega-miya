import re
from nonebot import on_command, export, logger
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP
from nonebot.adapters.cqhttp import MessageSegment
from omega_miya.utils.Omega_plugin_utils import init_export
from omega_miya.utils.Omega_plugin_utils import has_command_permission, permission_level
from .utils import sticker_maker_main, pic_2_base64


# Custom plugin usage text
__plugin_name__ = '表情包'
__plugin_usage__ = r'''【表情包助手】
使用模板快速制作表情包

**Permission**
Command & Lv.10

**Usage**
/表情包 [模板名]'''

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__)


sticker = on_command('表情包', rule=has_command_permission() & permission_level(level=10), aliases={'Sticker', 'sticker'},
                     permission=GROUP, priority=10, block=True)


# 修改默认参数处理
@sticker.args_parser
async def parse(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_message()).strip()
    if not args:
        await sticker.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args
    if state[state["_current_key"]] == '取消':
        await sticker.finish('操作已取消')


@sticker.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_message()).strip().lower().split()
    if not args:
        state['temp'] = None
    elif args and len(args) == 1:
        state['temp'] = args[0]
    else:
        await sticker.finish('参数错误QAQ')


@sticker.got('temp', prompt='请输入模板名称:')
async def handle_sticker(bot: Bot, event: GroupMessageEvent, state: T_State):
    # 定义模板名称、类型, 处理模板正则
    sticker_temp = {
        '默认': {'name': 'default', 'type': 'default', 'text_part': 1, 'help_msg': '该模板不支持gif'},
        '白底': {'name': 'whitebg', 'type': 'default', 'text_part': 1, 'help_msg': '该模板不支持gif'},
        '小天使': {'name': 'littleangel', 'type': 'default', 'text_part': 1, 'help_msg': '该模板不支持gif'},
        '有内鬼': {'name': 'traitor', 'type': 'static', 'text_part': 1, 'help_msg': '该模板字数限制100（x）'},
        '记仇': {'name': 'jichou', 'type': 'static', 'text_part': 1, 'help_msg': '该模板字数限制100（x）'},
        '王境泽': {'name': 'wangjingze', 'type': 'gif', 'text_part': 4, 'help_msg': '请检查文本分段'},
        '为所欲为': {'name': 'sorry', 'type': 'gif', 'text_part': 9, 'help_msg': '请检查文本分段'}
    }

    get_sticker_temp = state['temp']
    if not get_sticker_temp or get_sticker_temp not in sticker_temp.keys():
        temp_msg = '【' + str.join('】\n【', sticker_temp.keys()) + '】'
        await sticker.reject(f'请输入你想要制作的表情包模板:\n{temp_msg}\n取消命令请发送【取消】:')

    # 获取模板名称、类型
    state['temp_name'] = sticker_temp[get_sticker_temp]['name']
    state['temp_type'] = sticker_temp[get_sticker_temp]['type']
    state['temp_text_part'] = sticker_temp[get_sticker_temp]['text_part']
    state['temp_help_msg'] = sticker_temp[get_sticker_temp]['help_msg']

    # 判断该模板表情图片来源
    if state['temp_type'] in ['static', 'gif']:
        state['image_url'] = None


@sticker.got('image_url', prompt='请发送你想要制作的表情包的图片:')
async def handle_img(bot: Bot, event: GroupMessageEvent, state: T_State):
    image_url = state['image_url']
    if state['temp_type'] not in ['static', 'gif']:
        if not re.match(r'^(\[CQ:image,file=[abcdef\d]{32}\.image,url=.+])', image_url):
            await sticker.reject('你发送的似乎不是图片呢, 请重新发送, 取消命令请发送【取消】:')

        # 提取图片url
        image_url = re.sub(r'^(\[CQ:image,file=[abcdef\d]{32}\.image,url=)', '', image_url)
        image_url = re.sub(r'(])$', '', image_url)

    state['image_url'] = image_url
    state['sticker_text'] = None


@sticker.got('sticker_text', prompt='请输入你想要制作的表情包的文字:')
async def handle_sticker_text(bot: Bot, event: GroupMessageEvent, state: T_State):
    sticker_text = state['sticker_text']
    sticker_temp_text_part = state['temp_text_part']
    # 获取制作表情包所需文字
    if sticker_temp_text_part > 1:
        text_msg = f'请输入你想要制作的表情包的文字: \n当前模板文本分段数:【{sticker_temp_text_part}】' \
                   f'\n\n注意: 请用【#】号分割文本不同段落，不同模板适用的文字字数及段落数有所区别'
    else:
        text_msg = f'请输入你想要制作的表情包的文字: \n注意: 不同模板适用的文字字数有所区别'
    if not sticker_text:
        await sticker.reject(text_msg)

    if len(sticker_text.strip().split('#')) != sticker_temp_text_part:
        eg_msg = r'我就是饿死#死外边 从这里跳下去#也不会吃你们一点东西#真香'
        await sticker.finish(f"表情制作失败QAQ, 文本分段数错误\n"
                             f"当前模板文本分段数:【{sticker_temp_text_part}】\n\n示例: \n{eg_msg}")

    sticker_image_url = state['image_url']
    sticker_temp_name = state['temp_name']
    sticker_temp_type = state['temp_type']
    sticker_temp_help_msg = state['temp_help_msg']

    try:
        sticker_path = await sticker_maker_main(url=sticker_image_url, temp=sticker_temp_name, text=sticker_text,
                                                sticker_temp_type=sticker_temp_type)

        if not sticker_path:
            raise Exception('sticker_maker_main return null')

        # 发送base64图片
        sticker_b64 = await pic_2_base64(sticker_path)
        sticker_seg = MessageSegment.image(sticker_b64)

        """
        # 直接用文件构造消息段
        sticker_seg = MessageSegment.image(f'file:///{sticker_path}')
        """

        # 发送图片
        await sticker.send(sticker_seg)
        logger.info(f"Group: {event.group_id}, 用户: {event.user_id} 成功制作了一个表情")

    except Exception as e:
        logger.error(f"Group: {event.group_id}, 用户: {event.user_id} "
                     f"制作表情时发生了错误: {repr(e)}")
        await sticker.finish(f"表情制作失败QAQ, 请稍后再试\n小提示:{sticker_temp_help_msg}")
        return
