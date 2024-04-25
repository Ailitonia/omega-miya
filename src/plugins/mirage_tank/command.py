"""
@Author         : Ailitonia
@Date           : 2022/06/07 20:13
@FileName       : mirage_tank
@Project        : nonebot2_miya 
@Description    : 幻影坦克图片生成器
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Annotated

from nonebot.log import logger
from nonebot.params import ArgStr, Depends
from nonebot.plugin import on_command
from nonebot.typing import T_State

from src.params.handler import get_command_str_single_arg_parser_handler
from src.service import OmegaInterface, OmegaMessageSegment, enable_processor_state

from .utils import simple_white, simple_black, complex_gray, complex_color, complex_difference


@on_command(
    'mirage-tank',
    aliases={'幻影坦克'},
    handlers=[get_command_str_single_arg_parser_handler('step_arg', default='白底')],
    priority=10,
    block=True,
    state=enable_processor_state(name='MirageTank', level=10),
).got('step_arg')
async def handle_mirage_tank(
        interface: Annotated[OmegaInterface, Depends(OmegaInterface())],
        step_arg: Annotated[str, ArgStr('step_arg')],
        state: T_State
) -> None:
    interface.refresh_interface_state()

    if not state.get('mode') and step_arg.strip():
        state.update({'mode': step_arg.strip()})
        mode = state.get('mode')
    elif state.get('mode') in ['白底', '黑底', '灰度混合', '彩色混合', '差分']:
        mode = state.get('mode')
    else:
        await interface.reject_arg('step_arg', '请输入想要制作幻影坦克的模式:\n\n"白底", "黑底", "灰度混合", "彩色混合", "差分"')
    mode = mode.strip()

    event_handler = interface.get_event_handler()
    msg_images = event_handler.get_reply_msg_image_urls() + event_handler.get_msg_image_urls()
    if (state.get('msg_images') is None) or (msg_images and not state.get('msg_images')):
        state.update({'msg_images': msg_images})
    msg_images: list[str] = state.get('msg_images')

    match mode:
        case '白底':
            if not msg_images:
                await interface.reject_arg('step_arg', f'请发送你想要制作的图片:')
            generate_coro = simple_white(image_url=msg_images[0])

        case '黑底':
            if not msg_images:
                await interface.reject_arg('step_arg', f'请发送你想要制作的图片:')
            generate_coro = simple_black(image_url=msg_images[0])

        case '灰度混合':
            white_img = state.get('complex_gray_white')
            black_img = state.get('complex_gray_black')

            if not white_img and not msg_images:
                await interface.reject_arg('step_arg', f'请发送作为白色表层的图片:')
            elif not white_img and msg_images:
                state.update({'complex_gray_white': msg_images.pop(0)})

            if not black_img and not msg_images:
                await interface.reject_arg('step_arg', f'请发送作为黑色里层的图片:')
            elif not black_img and msg_images:
                state.update({'complex_gray_black': msg_images.pop(0)})

            white_img = str(state.get('complex_gray_white')).strip()
            black_img = str(state.get('complex_gray_black')).strip()
            generate_coro = complex_gray(white_image_url=white_img, black_image_url=black_img)

        case '彩色混合':
            white_img = state.get('complex_color_white')
            black_img = state.get('complex_color_black')

            if not white_img and not msg_images:
                await interface.reject_arg('step_arg', f'请发送作为白色表层的图片:')
            elif not white_img and msg_images:
                state.update({'complex_color_white': msg_images.pop(0)})

            if not black_img and not msg_images:
                await interface.reject_arg('step_arg', f'请发送作为彩色里层的图片:')
            elif not black_img and msg_images:
                state.update({'complex_color_black': msg_images.pop(0)})

            white_img = str(state.get('complex_color_white')).strip()
            black_img = str(state.get('complex_color_black')).strip()

            generate_coro = complex_color(white_image_url=white_img, black_image_url=black_img)

        case '差分':
            base_img = state.get('complex_difference_base')
            differ_img = state.get('complex_difference_differ')

            if not base_img and not msg_images:
                await interface.reject_arg('step_arg', f'请发送作为基础层的图片:')
            elif not base_img and msg_images:
                state.update({'complex_difference_base': msg_images.pop(0)})

            if not differ_img and not msg_images:
                await interface.reject_arg('step_arg', f'请发送作为差分层的图片:')
            elif not differ_img and msg_images:
                state.update({'complex_difference_differ': msg_images.pop(0)})

            base_img = str(state.get('complex_difference_base')).strip()
            differ_img = str(state.get('complex_difference_differ')).strip()

            generate_coro = complex_difference(base_image_url=base_img, differ_image_url=differ_img)

        case _:
            await interface.finish(f'{mode!r}不是可用的模式, 仅有以下模式可选:\n\n'
                                   f'"白底", "黑底", "灰度混合", "彩色混合", "差分"')

    try:
        make_image = await generate_coro
        await interface.send_at_sender(OmegaMessageSegment.image_file(make_image.path))
    except Exception as e:
        logger.error(f'MirageTank | 制作{mode}幻影坦克图片失败, {e}')
        await interface.send_at_sender('制作幻影坦克图片失败, 请稍后再试或联系管理员处理')


__all__ = []
