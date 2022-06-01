from nonebot import on_command, logger
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent, GroupMessageEvent
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.adapters.onebot.v11.permission import GROUP, PRIVATE_FRIEND
from nonebot.params import Depends, CommandArg, Arg, ArgStr

from omega_miya.service import init_processor_state
from omega_miya.service.gocqhttp_guild_patch import GuildMessageEvent, GUILD
from omega_miya.onebot_api import GoCqhttpBot
from omega_miya.utils.process_utils import run_async_catching_exception
from omega_miya.utils.message_tools import MessageTools
from omega_miya.utils.qq_tools import get_user_head_img_url

from .render import get_render, get_all_render_name, download_source_image


# Custom plugin usage text
__plugin_custom_name__ = '表情包'
__plugin_usage__ = rf'''【表情包助手】
使用模板快速制作表情包

/表情包 [模板名] [表情包文本] [表情包图片]'''


sticker = on_command(
    'Sticker',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='sticker', level=10),
    aliases={'sticker', '表情包'},
    permission=GROUP | GUILD | PRIVATE_FRIEND,
    priority=10,
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
            await matcher.reject_arg(key, '你发送的好像不是图片呢, 请重新发送你想要制作的表情包的图片:')

    return _key_parser


@Depends
async def parse_at_head_image(bot: Bot, event: MessageEvent, state: T_State, cmd_message: Message = CommandArg()):
    """解析命令消息中 @ 人的信息, 并将最后被 @ 人的信息作为素材保存到 state 中"""
    at_list = MessageTools(message=cmd_message).get_all_at_qq()
    if at_list:
        gocq_bot = GoCqhttpBot(bot=bot)
        if isinstance(event, GuildMessageEvent):
            profile = await run_async_catching_exception(gocq_bot.get_guild_member_profile)(
                guild_id=event.guild_id, user_id=at_list[-1])
            if not isinstance(profile, Exception):
                state.update({'source_image': profile.avatar_url, 'text': profile.nickname})
        elif isinstance(event, GroupMessageEvent):
            avatar_url = get_user_head_img_url(user_id=at_list[-1])
            nickname = ''
            profile = await run_async_catching_exception(gocq_bot.get_group_member_info)(
                group_id=event.group_id, user_id=at_list[-1])
            if not isinstance(profile, Exception):
                nickname = profile.card if profile.card else profile.nickname
            state.update({'source_image': avatar_url, 'text': nickname})
        else:
            avatar_url = get_user_head_img_url(user_id=at_list[-1])
            state.update({'source_image': avatar_url})


@sticker.handle(parameterless=[parse_at_head_image])
async def handle_parser(matcher: Matcher, state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    # 解析消息中是否有图片
    images = MessageTools(message=cmd_arg).get_all_img_url()
    if images:
        state.update({'source_image': images[0]})

    if not state.get('source_image'):
        state.update({'source_image': ''})
    if not state.get('text'):
        state.update({'text': ''})

    # 处理消息中其他参数
    cmd_args = cmd_arg.extract_plain_text().strip().split(maxsplit=1)
    arg_num = len(cmd_args)
    match arg_num:
        case 1:
            state.update({'render_name': cmd_args[0]})
        case 2:
            state.update({'render_name': cmd_args[0], 'text': cmd_args[1]})
        case _:
            render_name_text = '当前可用表情包模板有:\n\n' + '\n'.join(x for x in get_all_render_name())
            await matcher.send(render_name_text)


@sticker.got('render_name', prompt='请输入你想要制作的表情包模板:')
@sticker.got('text', prompt='请输入你想要制作的表情包的文字:')
@sticker.got('source_image', prompt='请发送你想要制作的表情包的图片:', parameterless=[Depends(parse_image('source_image'))])
async def handle_sticker(
        matcher: Matcher,
        render_name: str = ArgStr('render_name'),
        text: str = ArgStr('text'),
        source_image: str = ArgStr('source_image')
):
    render_name = render_name.strip()
    text = text.strip()
    source_image = source_image.strip()

    # 首先判断用户输入的表情包模板是否可用
    render_names = get_all_render_name()
    render_name_text = '\n'.join(x for x in render_names)
    if render_name not in render_names:
        await matcher.reject_arg('render_name',
                                 f'”{render_name}“不是可用的表情包模板, 请在以下模板中选择并重新输入:\n\n{render_name_text}',
                                 at_sender=True)

    # 获取表情包模板并检查是否需要文字或图片作为素材
    sticker_render = get_render(render_name)
    if sticker_render.need_text and not text:
        await matcher.reject_arg('text', f'请输入你想要制作的表情包的文字:', at_sender=True)
    if sticker_render.need_image and not source_image:
        await matcher.reject_arg('source_image', f'请发送你想要制作的表情包的图片:', at_sender=True)

    # 若需要外部图片素材则首先尝试下载图片资源
    if sticker_render.need_image:
        source_image = await download_source_image(url=source_image)
        if isinstance(source_image, Exception):
            logger.error(f'StickerMaker | 下载表情包素材图片失败, {source_image}')
            await matcher.finish('表情包制作失败了QAQ, 发生了意外的错误, 请稍后再试', at_sender=True)

    # 制作表情包并输出
    sticker_result = await run_async_catching_exception(sticker_render(text=text, source_image=source_image).make)()
    if isinstance(sticker_result, Exception):
        logger.error(f'StickerMaker | 制作表情包失败, {sticker_result}')
        await matcher.finish('表情包制作失败了QAQ, 发生了意外的错误, 请稍后再试', at_sender=True)
    else:
        await matcher.finish(MessageSegment.image(sticker_result.file_uri), at_sender=True)
