"""
@Author         : Ailitonia
@Date           : 2021/12/24 22:34
@FileName       : nhentai.py
@Project        : nonebot2_miya
@Description    : Nhentai
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm

要求go-cqhttp v0.9.40以上
"""

from nonebot import on_command, logger
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent, GroupMessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP, PRIVATE_FRIEND
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.params import CommandArg, ArgStr

from omega_miya.service import init_processor_state
from omega_miya.onebot_api import GoCqhttpBot
from omega_miya.utils.process_utils import run_async_catching_exception, semaphore_gather
from omega_miya.utils.message_tools import MessageSender
from omega_miya.web_resource.nhentai import NhentaiGallery


# Custom plugin usage text
__plugin_custom_name__ = 'NHentai'
__plugin_usage__ = r'''【NHentai】
神秘的插件

/nh search [tag]
/nh download [id]'''


# 注册事件响应器
nhentai = on_command(
    'NHentai',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='NHentai',
        auth_node='nhentai',
        cool_down=60,
        user_cool_down_override=2
    ),
    aliases={'nhentai', 'nh'},
    permission=GROUP | PRIVATE_FRIEND,
    priority=20,
    block=True
)


@nhentai.handle()
async def handle_parse_operating(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    cmd_args = cmd_arg.extract_plain_text().strip().split(maxsplit=1)
    arg_num = len(cmd_args)
    match arg_num:
        case 1:
            state.update({'operating': cmd_args[0]})
        case 2:
            state.update({'operating': cmd_args[0], 'operation_arg': cmd_args[1]})


@nhentai.got('operating', prompt='search or download?')
@nhentai.got('operation_arg', prompt='Please enter the search keywords or download gallery id')
async def handle_operating(
        bot: Bot,
        event: MessageEvent,
        matcher: Matcher,
        operating: str = ArgStr('operating'),
        operation_arg: str = ArgStr('operation_arg')
):
    operating = operating.strip()
    operation_arg = operation_arg.strip()

    match operating:
        case 'search':
            await handle_search(bot=bot, event=event, matcher=matcher, keyword=operation_arg)
        case 'download':
            if not operation_arg.isdigit():
                await matcher.reject_arg('operation_arg', 'Gallery id must be an integer')
            await handle_download(bot=bot, event=event, matcher=matcher, gallery_id=int(operation_arg))
        case _:
            await matcher.finish('Invalid operation')


async def handle_search(bot: Bot, event: MessageEvent, matcher: Matcher, keyword: str):
    await matcher.send('获取搜索结果中, 请稍候')
    search_tasks = [NhentaiGallery.search_gallery_with_preview(keyword=keyword, page=p) for p in range(1, 6)]
    search_results = await semaphore_gather(tasks=search_tasks, semaphore_num=2, filter_exception=True)
    if not search_results:
        await matcher.finish('没有搜索结果或搜索失败了QAQ, 请稍后再试')
    else:
        message_list = ['已为你找到了以下结果, 可通过id下载']
        message_list.extend([MessageSegment.image(x.file_uri) for x in search_results])
        await MessageSender(bot=bot).send_node_custom_and_recall(event=event, message_list=message_list, recall_time=60)


async def handle_download(bot: Bot, event: MessageEvent, matcher: Matcher, gallery_id: int):
    await matcher.send('下载中, 请稍候')
    download_result = await run_async_catching_exception(NhentaiGallery(gallery_id=gallery_id).download)()
    if isinstance(download_result, Exception):
        logger.error(f'NHentai | Download gallery({gallery_id}) failed, {download_result}')
        await matcher.finish('下载失败QAQ, 请稍后再试')
    else:
        await matcher.send(f'下载完成, 密码: {download_result.password},\n正在上传文件, 可能需要一段时间...')
        upload_result = await _upload_file(
            bot=bot, event=event, file=download_result.file.resolve_path, name=download_result.file.path.name
        )
        if isinstance(upload_result, Exception):
            logger.error(f'NHentai | Upload gallery({gallery_id}) to group file failed, {upload_result}')
            await matcher.finish('上传文件失败QAQ, 请稍后再试')


@run_async_catching_exception
async def _upload_file(bot: Bot, event: MessageEvent, file: str, name: str) -> None:
    gocq_bot = GoCqhttpBot(bot=bot)
    if isinstance(event, GroupMessageEvent):
        await gocq_bot.upload_group_file(group_id=event.group_id, file=file, name=name)
    else:
        await gocq_bot.upload_private_file(user_id=event.user_id, file=file, name=name)
