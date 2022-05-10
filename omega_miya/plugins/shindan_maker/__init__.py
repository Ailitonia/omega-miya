"""
@Author         : Ailitonia
@Date           : 2021/06/28 21:41
@FileName       : shindan_maker.py
@Project        : nonebot2_miya
@Description    : shindan_maker 占卜插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import re
import datetime
from nonebot import on_command, on_regex, logger
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import GroupMessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.params import Depends, CommandArg, ArgStr, EventMessage

from omega_miya.service import init_processor_state
from omega_miya.onebot_api import GoCqhttpBot
from omega_miya.utils.message_tools import MessageTools
from omega_miya.utils.process_utils import run_async_catching_exception, semaphore_gather

from .data_source import ShindanMaker


# Custom plugin usage text
__plugin_custom_name__ = 'ShindanMaker'
__plugin_usage__ = r'''【ShindanMaker 占卜】
使用ShindanMaker进行各种奇怪的占卜
只能在群里使用
就是要公开处刑！

用法:
/ShindanMaker [占卜名称] [占卜对象名称]'''


shindan_maker = on_command(
    'ShindanMaker',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='shindan_maker', level=50, auth_node='shindan_maker'),
    aliases={'shindanmaker', 'SHINDANMAKER', 'Shindan', 'shindan', 'SHINDAN'},
    permission=GROUP,
    priority=20,
    block=True
)


@Depends
async def parse_at(bot: Bot, event: GroupMessageEvent, state: T_State, cmd_message: Message = CommandArg()):
    """解析命令消息中 @ 人的信息并保存到 state 中"""
    at_list = MessageTools(message=cmd_message).get_all_at_qq()
    if at_list:
        gocq_bot = GoCqhttpBot(bot=bot)
        at_user_data = await run_async_catching_exception(gocq_bot.get_group_member_info)(group_id=event.group_id,
                                                                                          user_id=at_list[0])
        if not isinstance(at_user_data, Exception):
            state.update({'input_name': at_user_data.card if at_user_data.card else at_user_data.nickname})


@shindan_maker.handle(parameterless=[parse_at])
async def handle_parser(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    cmd_args = cmd_arg.extract_plain_text().strip().rsplit(maxsplit=1)
    arg_num = len(cmd_args)
    match arg_num:
        case 1:
            state.update({'shindan': cmd_args[0]})
        case 2:
            state.update({'shindan': cmd_args[0], 'input_name': cmd_args[1]})


@shindan_maker.got('shindan', prompt='你想做什么占卜呢?\n不知道的话可以输入关键词进行搜索哦~')
@shindan_maker.got('input_name', prompt='请输入您想要进行占卜的昵称:')
async def handle_shindanmaker(matcher: Matcher, shindan: str = ArgStr('shindan'),
                              input_name: str = ArgStr('input_name')):
    shindan = shindan.strip()
    input_name = input_name.strip()

    if shindan.isdigit():
        # 如果输入的时数字则直接作为 shindan_id 处理
        shindan_id = int(shindan)

    else:
        # 若是文本作为占卜名处理, 进行缓存查找和搜索
        logger.debug('ShindanMaker | 尝试载入名称缓存文件')
        cache = await ShindanMaker.read_shindan_cache()
        cache_id = cache.get(shindan)
        if not cache_id:
            # 执行搜索
            logger.debug(f'ShindanMaker | 未在缓存中找到占卜名: {shindan} 对应 id, 执行搜索')
            search_result = await ShindanMaker.search(keyword=shindan)
            if isinstance(search_result, Exception):
                logger.error(f'ShindanMaker | 搜索占卜名: {shindan} 失败, {search_result}')
                await matcher.finish('获取ShindanMaker占卜信息失败了QAQ, 请稍后再试')
                return
            else:
                search_data = {x.name: x.id for x in search_result}
                # 更新缓存
                await ShindanMaker.upgrade_shindan_cache(data=search_data)
                if id_from_search := search_data.get(shindan):
                    shindan_id = int(id_from_search)
                else:
                    search_text = '\n'.join(f'{x.id}: {x.name}' for x in search_result)
                    msg = f'搜索到了以下占卜\n\n{search_text}\n\n请输入你想要进行占卜的ID:'
                    await matcher.reject_arg('shindan', msg)
                    return
        else:
            logger.debug(f'ShindanMaker | 已在缓存中找到占卜名: {shindan} id: {cache_id}')
            shindan_id = int(cache_id)

    # 加入日期使每天的结果不一样
    today = f"@{datetime.date.today().strftime('%Y%m%d')}@"
    today_input_name = f'{input_name}{today}'
    shindan_result = await ShindanMaker(shindan_id=shindan_id).query_result(input_name=today_input_name)
    if isinstance(shindan_result, Exception):
        logger.error(f'ShindanMaker | 搜索结果: {shindan}/{input_name} 失败, {shindan_result}')
        await matcher.finish('获取ShindanMaker占卜结果失败了QAQ, 请稍后再试')

    # 删除之前加入的日期字符
    result_text = shindan_result.text.replace(today, '')

    # 结果有图片就处理图片
    if shindan_result.image_url:
        image_download_tasks = [ShindanMaker.download_image(url=x) for x in shindan_result.image_url]
        image_result = await semaphore_gather(tasks=image_download_tasks, semaphore_num=10)
        image_message = Message(MessageSegment.image(x.file_uri) for x in image_result if not isinstance(x, Exception))
        result_text = result_text + image_message

    await matcher.finish(result_text)


# 固定的shindan_id
_CUSTOM_SHINDAN_ID: dict[str, int] = {
    '什么少女': 162207,
    '什么魔法少女': 828741,
    '什么偶像': 828727,
    '什么做的': 761425,
    '什么干员': 959146,
    '什么小动物': 828905,
    '什么猫': 28998,
    '什么主角': 828977,
    '什么宝石': 890951,
    '什么花': 829525,
    '二次元での嫁ヒロイン': 1075116,
    '二次元老婆': 1075116,
    '老婆是谁': 1075116,
    '异世界角色': 637918
}
shindan_pattern = r'^今天的?(.+)(的|是)(.+?)[?？]?$'
shindan_maker_today = on_regex(
    shindan_pattern,
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='shindan_maker', level=30, echo_processor_result=False),
    permission=GROUP,
    priority=20,
    block=True
)


@shindan_maker_today.handle()
async def handle_shindanmaker_today(matcher: Matcher, message: Message = EventMessage()):
    message = message.extract_plain_text().strip()
    search_result = re.search(shindan_pattern, message)
    input_name, shindan_name = search_result.group(1), search_result.group(3)
    shindan_id = _CUSTOM_SHINDAN_ID.get(shindan_name, None)
    if not shindan_id:
        await matcher.finish()

    # 加入日期使每天的结果不一样
    today = f"@{datetime.date.today().strftime('%Y%m%d')}@"
    today_input_name = f'{input_name}{today}'
    shindan_result = await ShindanMaker(shindan_id=shindan_id).query_result(input_name=today_input_name)
    if isinstance(shindan_result, Exception):
        logger.error(f'ShindanMakerToday | 搜索结果: {shindan_id}/{input_name} 失败, {shindan_result}')
        await matcher.finish()

    # 删除之前加入的日期字符
    result_text = shindan_result.text.replace(today, '')

    # 结果有图片就处理图片
    if shindan_result.image_url:
        image_download_tasks = [ShindanMaker.download_image(url=x) for x in shindan_result.image_url]
        image_result = await semaphore_gather(tasks=image_download_tasks, semaphore_num=10)
        image_message = Message(MessageSegment.image(x.file_uri) for x in image_result if not isinstance(x, Exception))
        result_text = result_text + image_message

    await matcher.finish(result_text)
