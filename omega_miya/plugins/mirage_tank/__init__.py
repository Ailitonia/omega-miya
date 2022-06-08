"""
@Author         : Ailitonia
@Date           : 2022/06/07 20:13
@FileName       : mirage_tank.py
@Project        : nonebot2_miya 
@Description    : 幻影坦克图片生成器
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import on_command
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11.event import MessageEvent
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.adapters.onebot.v11.permission import GROUP, PRIVATE_FRIEND
from nonebot.params import Depends, CommandArg, Arg, ArgStr

from omega_miya.service import init_processor_state
from omega_miya.service.gocqhttp_guild_patch import GUILD
from omega_miya.utils.message_tools import MessageTools

from .utils import simple_white, simple_black, complex_gray, complex_color, complex_difference


# Custom plugin usage text
__plugin_custom_name__ = '幻影坦克'
__plugin_usage__ = rf'''【幻影坦克图片生成工具】
制作幻影坦克图片

/幻影坦克 [模式] [图片]

合成模式可选: "白底", "黑底", "混合"
'''


mirage_tank = on_command(
    'MirageTank',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='MirageTank', level=20, cool_down=15, user_cool_down_override=2),
    aliases={'幻影坦克'},
    permission=GROUP | GUILD | PRIVATE_FRIEND,
    priority=20,
    block=True
)


@Depends
def parse_image_url(event: MessageEvent, state: T_State):
    """解析消息中的所有图片url, 并将结果存入 state 中"""
    images = MessageTools(message=event.message).get_all_img_url()
    state.update({'_command_image_list': images})


def parse_image(key: str):
    """解析消息中的第一张图片(若有), 并将结果存入 state 中"""

    async def _key_parser(matcher: Matcher, state: T_State, message: Message | str = Arg(key)):
        if isinstance(message, str):
            return

        images = MessageTools(message=message).get_all_img_url()
        if images:
            state.update({key: images[0]})
        else:
            await matcher.reject_arg(key, '你发送的好像不是图片呢, 请重新发送你想要制作的图片:')

    return _key_parser


@mirage_tank.handle(parameterless=[parse_image_url])
async def handle_parser(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    # 处理消息中其他参数
    cmd_arg = cmd_arg.extract_plain_text().strip()
    state.update({'mode': cmd_arg, 'first_image': '', 'second_image': ''})

    image_list = state.get('_command_image_list', [])
    match len(image_list):
        case 1:
            state.update({'first_image': image_list[0]})
        case 2:
            state.update({'first_image': image_list[0], 'second_image': image_list[1]})


@mirage_tank.got('mode', prompt='请选择你想要制作幻影坦克的模式:\n\n"白底", "黑底", "灰度混合", "彩色混合", "差分"')
@mirage_tank.got('first_image', prompt='第一张图片', parameterless=[Depends(parse_image('first_image'))])
@mirage_tank.got('second_image', prompt='第二张图片', parameterless=[Depends(parse_image('second_image'))])
async def handle_sticker(
        matcher: Matcher,
        mode: str = ArgStr('mode'),
        first_image: str = ArgStr('first_image'),
        second_image: str = ArgStr('second_image')
):
    mode = mode.strip()
    first_image = first_image.strip()
    second_image = second_image.strip()

    match mode:
        case '白底':
            if not first_image:
                await matcher.reject_arg('first_image', f'请发送你想要制作的图片:', at_sender=True)
            make_image = await simple_white(image_url=first_image)
            await matcher.finish(MessageSegment.image(make_image.file_uri), at_sender=True)

        case '黑底':
            if not first_image:
                await matcher.reject_arg('first_image', f'请发送你想要制作的图片:', at_sender=True)
            make_image = await simple_black(image_url=first_image)
            await matcher.finish(MessageSegment.image(make_image.file_uri), at_sender=True)

        case '灰度混合':
            if not first_image:
                await matcher.reject_arg('first_image', f'请发送作为白色表层的图片:', at_sender=True)
            if not second_image:
                await matcher.reject_arg('second_image', f'请发送作为黑色里层的图片:', at_sender=True)
            make_image = await complex_gray(white_image_url=first_image, black_image_url=second_image)
            await matcher.finish(MessageSegment.image(make_image.file_uri), at_sender=True)

        case '彩色混合':
            if not first_image:
                await matcher.reject_arg('first_image', f'请发送作为白色表层的图片:', at_sender=True)
            if not second_image:
                await matcher.reject_arg('second_image', f'请发送作为黑色里层的图片:', at_sender=True)
            make_image = await complex_color(white_image_url=first_image, black_image_url=second_image)
            await matcher.finish(MessageSegment.image(make_image.file_uri), at_sender=True)

        case '差分':
            if not first_image:
                await matcher.reject_arg('first_image', f'请发送基础图片:', at_sender=True)
            if not second_image:
                await matcher.reject_arg('second_image', f'请发送差分图片:', at_sender=True)
            make_image = await complex_difference(differ_image_url=first_image, base_image_url=second_image)
            await matcher.finish(MessageSegment.image(make_image.file_uri), at_sender=True)

        case _:
            await matcher.reject_arg('mode',
                                     f'”{mode}“不是可用的模式, 请在以下模式中选择并重新输入:\n\n'
                                     f'"白底", "黑底", "灰度混合", "彩色混合", "差分"',
                                     at_sender=True)
