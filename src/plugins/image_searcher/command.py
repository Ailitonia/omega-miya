"""
@Author         : Ailitonia
@Date           : 2021/06/16 22:53
@FileName       : image_searcher.py
@Project        : nonebot2_miya
@Description    : 识图搜番
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Annotated

from nonebot.log import logger
from nonebot.params import ArgStr, Depends
from nonebot.plugin import on_command

from src.params.handler import get_command_str_single_arg_parser_handler
from src.resource import StaticResource, TemporaryResource
from src.service import OmegaMatcherInterface as OmMI
from src.service import OmegaMessageSegment, enable_processor_state
from src.utils import OmegaRequests, semaphore_gather
from src.utils.image_searcher import ComplexImageSearcher
from src.utils.image_utils import ImageEffectProcessor, ImageLoader
from src.utils.image_utils.template import PreviewImageModel, PreviewImageThumbs, generate_thumbs_preview_image

if TYPE_CHECKING:
    from src.utils.image_searcher.model import ImageSearchingResult


@on_command(
    'search-image',
    aliases={'识图', '搜图'},
    handlers=[get_command_str_single_arg_parser_handler('image_url', ensure_key=True)],
    priority=10,
    block=True,
    state=enable_processor_state(name='ImageSearcher', level=50)
).got('image_url')
async def handle_search_image(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        image_url: Annotated[str | None, ArgStr('image_url')],
) -> None:
    msg_images = interface.get_event_reply_msg_image_urls() + interface.get_event_msg_image_urls()

    if image_url is None and not msg_images:
        await interface.reject_arg_reply('image_url', '请发送你想要识别的图片或图片链接:')

    if msg_images:
        search_coro = ComplexImageSearcher(image=msg_images[0]).search()
    elif image_url and image_url.startswith(('http://', 'https://')):
        search_coro = ComplexImageSearcher(image=image_url).search()
    else:
        await interface.finish_reply('不是可用的图片或图片链接, 请确认后重试')

    await interface.send_reply('获取识别结果中, 请稍候~')

    try:
        searching_results = await search_coro
        if not searching_results:
            await interface.send_reply('没有找到相似度足够高的图片')
            return
        else:
            send_msg = '匹配到以下结果:\n'

            preview_img = await _generate_result_preview_image(results=searching_results)
            send_msg += OmegaMessageSegment.image(await preview_img.get_hosting_path())

            desc_img = await _generate_result_desc_image(results=searching_results)
            send_msg += OmegaMessageSegment.image(await desc_img.get_hosting_path())

            url_txt = '\n'.join(
                str(url)
                for result in searching_results if result.source_urls
                for url in result.source_urls
            )
            send_msg += url_txt

            await interface.send_reply(send_msg)
    except Exception as e:
        logger.error(f'ImageSearcher | 获取搜索结果失败, {e}')
        await interface.finish_reply('获取识别结果失败了, 发生了意外的错误, 请稍后再试')


async def _fetch_result_as_preview_body(result: 'ImageSearchingResult') -> PreviewImageThumbs:
    requests = OmegaRequests(
        timeout=15,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0'}
    )
    url = '\n'.join(result.source_urls) if result.source_urls else '无可用来源'
    desc_text = f'来源: {result.source[:16]}\n相似度: {result.similarity if result.similarity else "未知"}\n{url[:16]}...'
    thumbnail_response = await requests.get(str(result.thumbnail))
    return PreviewImageThumbs(desc_text=desc_text, preview_thumb=requests.parse_content_as_bytes(thumbnail_response))


async def _emit_preview_model_from_searching_result(results: Sequence['ImageSearchingResult']) -> PreviewImageModel:
    tasks = [_fetch_result_as_preview_body(result=result) for result in results]
    preview_data = list(await semaphore_gather(tasks=tasks, semaphore_num=6, filter_exception=True))
    return PreviewImageModel(preview_name='ImageSearcherResults', previews=preview_data)


async def _generate_result_preview_image(results: Sequence['ImageSearchingResult']) -> TemporaryResource:
    """识别图片并将结果转换为消息"""
    preview_model = await _emit_preview_model_from_searching_result(results=results)
    preview_img_file = await generate_thumbs_preview_image(
        preview=preview_model,
        preview_size=(360, 360),
        font_path=StaticResource('fonts', 'fzzxhk.ttf'),
        header_color=(250, 160, 160),
        hold_ratio=True,
        num_of_line=4,
        output_folder=TemporaryResource('image_searcher', 'preview')
    )
    return preview_img_file


async def _generate_result_desc_image(results: Sequence['ImageSearchingResult']) -> TemporaryResource:
    preview_txt = '\n\n'.join(
        f'来源: {result.source}\n相似度: {result.similarity if result.similarity else "未知"}\n来源地址:\n{url}'
        for result in results
        for url in result.source_urls
    )
    image = ImageEffectProcessor(await ImageLoader.async_init_from_text(text=preview_txt))
    save_file_name = f'{datetime.now().strftime("%Y%m%d%H%M%S")}_{hash(preview_txt)}.jpg'
    return await image.save(TemporaryResource('image_searcher', 'desc', save_file_name))


__all__ = []
