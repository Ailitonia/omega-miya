"""
@Author         : Ailitonia
@Date           : 2021/06/16 22:53
@FileName       : image_searcher.py
@Project        : nonebot2_miya
@Description    : 识图搜番
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot import on_command, logger
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent, GroupMessageEvent
from nonebot.adapters.onebot.v11.message import Message
from nonebot.adapters.onebot.v11.permission import GROUP, PRIVATE_FRIEND
from nonebot.params import Depends, RawCommand, CommandArg, Arg, ArgStr

from omega_miya.service import init_processor_state
from omega_miya.service.gocqhttp_guild_patch.permission import GUILD
from omega_miya.utils.process_utils import run_async_catching_exception
from omega_miya.utils.message_tools import MessageSender, MessageTools
from omega_miya.web_resource.image_searcher import ComplexImageSearcher, TraceMoe
from omega_miya.onebot_api import GoCqhttpBot


# Custom plugin usage text
__plugin_custom_name__ = '识图搜番'
__plugin_usage__ = r'''【识图搜番助手】
使用 SauceNAO/iqdb/ascii2d/trace.moe 识别各类图片、插画、番剧

用法:
/识图
/搜番'''


# 注册事件响应器
image_searcher = on_command(
    'ImageSearcher',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='search_image', level=50),
    aliases={'识图', '搜图', '识番', '搜番'},
    permission=GROUP | GUILD | PRIVATE_FRIEND,
    priority=20,
    block=True
)


def parse_image(key: str):
    """解析消息中的第一张图片(若有), 并将结果存入 state 中"""

    async def _key_parser(matcher: Matcher, state: T_State, message: Message | str = Arg(key)):
        if isinstance(message, str):
            return

        images = MessageTools(message=message).get_all_img_url()
        if images:
            state.update({key: images[0]})
        else:
            await matcher.reject_arg(key, '你发送的好像不是图片呢, 请重新发送你想要识别的图片:')

    return _key_parser


@image_searcher.handle()
async def handle_parser(bot: Bot, event: MessageEvent, state: T_State,
                        cmd: str = RawCommand(), cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    # 尝试解析消息中回复引用的图片
    if event.reply:
        gocq_bot = GoCqhttpBot(bot=bot)
        message = await run_async_catching_exception(gocq_bot.get_msg)(message_id=event.reply.message_id)
        if not isinstance(message, Exception):
            images = MessageTools(message=message.message).get_all_img_url()
            state.update({'image': images[0]})

    # 解析消息中是否有图片(优先级更高)
    images = MessageTools(message=cmd_arg).get_all_img_url()
    if images:
        state.update({'image': images[0]})

    cmd = cmd.lstrip(''.join(bot.config.command_start))
    match cmd:
        case '识番' | '搜番':
            state.update({'anime_mode': True})
        case _:
            state.update({'anime_mode': False})


@image_searcher.got('image', prompt='请发送你想要识别的图片:', parameterless=[Depends(parse_image('image'))])
async def handle_sticker(bot: Bot, matcher: Matcher, event: MessageEvent, state: T_State, image: str = ArgStr('image')):
    anime_mode: bool = state.get('anime_mode', False)
    url = image.strip()

    await matcher.send('获取识别结果中, 请稍候~')
    if anime_mode:
        searching_result = await run_async_catching_exception(TraceMoe(image_url=url).searching_result)()
    else:
        searching_result = await run_async_catching_exception(ComplexImageSearcher(image_url=url).searching_result)()

    if isinstance(searching_result, Exception):
        logger.error(f'ImageSearcher | 获取搜索结果失败, {searching_result}')
        await matcher.finish('获取识别结果失败了QAQ, 发生了意外的错误, 请稍后再试', at_sender=True)
    elif not searching_result:
        await matcher.finish('没有找到相似度足够高的图片QAQ')
    else:
        await MessageSender(bot=bot).send_node_custom_and_recall(
            event=event, recall_time=90, message_list=searching_result
        )
