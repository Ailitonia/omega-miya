"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : sticker_maker.py
@Project        : nonebot2_miya
@Description    : 表情包插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Annotated

from nonebot.log import logger
from nonebot.params import ArgStr, Depends
from nonebot.plugin import on_command
from nonebot.typing import T_State

from src.params.handler import get_command_str_multi_args_parser_handler, get_set_default_state_handler
from src.service import OmegaMatcherInterface as OmMI
from src.service import OmegaMessageSegment, enable_processor_state
from .render import download_source_image, get_all_render_name, get_render

sticker_maker = on_command(
    'sticker-maker',
    aliases={'sticker', '表情包'},
    handlers=[
        get_set_default_state_handler(key='source_images'),
        get_command_str_multi_args_parser_handler('sticker_arg', ensure_keys_num=2)
    ],
    priority=10,
    block=True,
    state=enable_processor_state(name='StickerMaker', level=10),
)


@sticker_maker.got('sticker_arg_0', prompt='请输入你想要制作的表情包模板:')
@sticker_maker.got('sticker_arg_1', prompt='请输入你想要制作的表情包的文字:')
@sticker_maker.got('source_images')
async def handle_make_sticker(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        render_name: Annotated[str | None, ArgStr('sticker_arg_0')],
        text: Annotated[str | None, ArgStr('sticker_arg_1')],
        state: T_State,
) -> None:
    if render_name is None:
        render_name_text = '当前可用表情包模板有:\n\n' + '\n'.join(x for x in get_all_render_name())
        await interface.reject_arg_reply('sticker_arg_0', f'{render_name_text}\n请输入你想要制作的表情包模板:')
    else:
        render_name = render_name.strip()

    if text is not None:
        text = text.strip()

    # 首先处理消息中的图片

    msg_images = interface.get_event_reply_msg_image_urls() + interface.get_event_msg_image_urls()
    if (state.get('source_images') is None) or (msg_images and not state.get('source_images')):
        state.update({'source_images': msg_images})
    source_images: list[str] = state.get('source_images', [])

    # 首先判断用户输入的表情包模板是否可用
    render_names = get_all_render_name()
    render_name_text = '\n'.join(x for x in render_names)
    if render_name not in render_names:
        await interface.reject_arg_reply(
            'sticker_arg_0',
            f'“{render_name}”不是可用的表情包模板, 请在以下模板中选择并重新输入:\n\n{render_name_text}'
        )

    # 获取表情包模板并检查是否需要文字或图片作为素材
    sticker_render = get_render(render_name)
    if sticker_render.need_external_image() and not source_images:
        await interface.reject_arg_reply('source_image', '请发送你想要制作的表情包的图片:')
    if sticker_render.need_text() and not text:
        await interface.reject_arg_reply('sticker_arg_1', '请输入你想要制作的表情包的文字:')

    source_image = None
    # 若需要外部图片素材则首先尝试下载图片资源
    if sticker_render.need_external_image():
        try:
            source_image = await download_source_image(url=source_images[0])
        except Exception as e:
            logger.error(f'StickerMaker | 下载表情包素材图片失败, {e}')
            await interface.finish_reply('表情包制作失败了QAQ, 发生了意外的错误, 请稍后再试')

    # 制作表情包并输出
    try:
        sticker_result = await sticker_render(text=text, external_image=source_image).make()
        await interface.send_reply(OmegaMessageSegment.image_file(sticker_result.path))
    except Exception as e:
        logger.error(f'StickerMaker | 制作表情包失败, {e}')
        await interface.send_reply('表情包制作失败了QAQ, 发生了意外的错误, 请稍后再试')


__all__ = []
