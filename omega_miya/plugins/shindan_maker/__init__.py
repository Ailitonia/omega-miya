"""
@Author         : Ailitonia
@Date           : 2021/06/28 21:41
@FileName       : __init__.py.py
@Project        : nonebot2_miya 
@Description    : shindan_maker 无聊的占卜插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import os
import re
import datetime
from typing import Dict
from nonebot import MatcherGroup, logger
from nonebot.plugin.export import export
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP
from nonebot.adapters.cqhttp.message import MessageSegment
from omega_miya.utils.omega_plugin_utils import (init_export, init_processor_state, OmegaRules,
                                                 MessageDecoder, PicEncoder, ProcessUtils, BotTools)
from .data_source import ShindanMaker


# Custom plugin usage text
__plugin_custom_name__ = 'ShindanMaker'
__plugin_usage__ = r'''【ShindanMaker 占卜】
使用ShindanMaker进行各种奇怪的占卜
只能在群里使用
就是要公开处刑！

**Permission**
Command & Lv.50
or AuthNode

**AuthNode**
basic

**Usage**
/ShindanMaker [占卜名称] [占卜对象名称]'''

# 声明本插件额外可配置的权限节点
__plugin_auth_node__ = [
    'pattern_match'
]

# Init plugin export
init_export(export(), __plugin_custom_name__, __plugin_usage__, __plugin_auth_node__)


# 缓存占卜名称与对应id
SHINDANMAKER_CACHE: Dict[str, int] = {}


# 注册事件响应器
shindan_maker = MatcherGroup(
    type='message',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='shindan_maker',
        command=True,
        level=50),
    permission=GROUP,
    priority=20,
    block=True)


shindan_maker_default = shindan_maker.on_command(
    'ShindanMaker', aliases={'占卜', 'shindanmaker', 'SHINDANMAKER', 'Shindan', 'shindan', 'SHINDAN'})


# 修改默认参数处理
@shindan_maker_default.args_parser
async def parse(bot: Bot, event: GroupMessageEvent, state: T_State):
    if state["_current_key"] == 'input_name':
        at_qq = MessageDecoder(message=event.get_message()).get_all_at_qq()
        if at_qq:
            card = await BotTools(bot=bot).get_user_group_card(user_id=at_qq[0], group_id=event.group_id)
            if card:
                state['input_name'] = card
                return

    args = str(event.get_plaintext()).strip().split()
    if not args:
        await shindan_maker_default.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await shindan_maker_default.finish('操作已取消')


@shindan_maker_default.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().split()
    state['id'] = 0
    if not args:
        pass
    elif args and len(args) == 1:
        state['shindan_name'] = args[0]
    elif args and len(args) == 2:
        state['shindan_name'] = args[0]
        state['input_name'] = args[1]
    else:
        await shindan_maker_default.finish('参数错误QAQ')

    # 特殊处理@人
    if len(event.message) >= 2:
        if event.message[1].type == 'at':
            at_qq = event.message[1].data.get('qq')
            card = await BotTools(bot=bot).get_user_group_card(user_id=int(at_qq), group_id=event.group_id)
            if card:
                state['input_name'] = card


@shindan_maker_default.got('shindan_name', prompt='你想做什么占卜呢?\n不知道的话可以输入关键词进行搜索哦~')
async def handle_shindan_name(bot: Bot, event: GroupMessageEvent, state: T_State):
    global SHINDANMAKER_CACHE
    # 尝试从文件中载入缓存
    if not SHINDANMAKER_CACHE:
        logger.debug('ShindanMaker | 尝试载入名称缓存文件...')
        shindan_file_cache = await ShindanMaker.read_shindan_cache_from_file()
        if shindan_file_cache.success():
            SHINDANMAKER_CACHE.update(shindan_file_cache.result)
        else:
            logger.warning(f'ShindanMaker | 载入缓存时读取名称缓存文件失败, error: {shindan_file_cache.info}')

    shindan_name = state['shindan_name']
    # 允许直接通过id进行
    if re.match(r'^\d+$', shindan_name):
        shindan_id = int(shindan_name)
    else:
        shindan_id = SHINDANMAKER_CACHE.get(shindan_name, 0)
    if shindan_id == 0:
        shindan_name_result = await ShindanMaker.search(keyword=shindan_name)
        if shindan_name_result.error:
            logger.error(f'ShindanMaker | User: {event.user_id} 获取 ShindanMaker 占卜名失败, {shindan_name_result.info}')
            await shindan_maker_default.finish('获取ShindanMaker占卜信息失败了QAQ, 请稍后再试')
        else:
            for item in shindan_name_result.result:
                if item.get('name'):
                    SHINDANMAKER_CACHE.update({
                        re.sub(r'\s', '', item.get('name')): item.get('id', 0)
                    })

            # 触发搜索后更新文件缓存
            logger.debug('ShindanMaker | 更新名称缓存文件...')
            file_cache_result = await ShindanMaker.read_shindan_cache_from_file()
            if file_cache_result.success():
                new_file_cache = file_cache_result.result
                new_file_cache.update(SHINDANMAKER_CACHE)
                write_result = await ShindanMaker.write_shindan_cache_from_file(data=new_file_cache)
                if write_result.error:
                    logger.error(f'ShindanMaker | 更新缓存时写入名称缓存文件失败, error: {write_result.info}')
            else:
                logger.warning(f'ShindanMaker | 更新缓存时读取名称缓存文件失败, error: {file_cache_result.info}')

            shindan_id = SHINDANMAKER_CACHE.get(shindan_name, 0)
            if shindan_id == 0:
                shindan_list = '】\n【'.join(
                    [re.sub(r'\s', '', x.get('name')) for x in shindan_name_result.result if x.get('name')])
                msg = f'搜索到了以下占卜\n{"="*12}\n【{shindan_list}】\n{"="*12}\n' \
                      f'请使用占卜名称(方括号里面的完整名称)重新开始!'
                await shindan_maker_default.finish(msg)

    state['id'] = shindan_id


@shindan_maker_default.got('input_name', prompt='请输入您想要进行占卜的人名:')
async def handle_input_name(bot: Bot, event: GroupMessageEvent, state: T_State):
    input_name = state['input_name']
    shindan_id = state['id']
    today = f"@{datetime.date.today().strftime('%Y%m%d')}@"
    # 加入日期使每天的结果不一样
    _input_name = f'{input_name}{today}'
    result = await ShindanMaker(maker_id=shindan_id).get_result(input_name=_input_name)
    if result.error:
        logger.error(f'ShindanMaker | User: {event.user_id} 获取 ShindanMaker 占卜结果失败, {result.info}')
        await shindan_maker_default.finish('获取ShindanMaker占卜结果失败了QAQ, 请稍后再试')

    result_text, result_img_list = result.result

    # 删除之前加入的日期字符
    result_msg = result_text.replace(today, '')

    # 结果有图片就处理图片
    if result_img_list:
        tasks = [PicEncoder(pic_url=img_url).get_file(
            folder_flag='shindan_maker_img_temp',
            format_=os.path.splitext(img_url)[-1][1:]
        ) for img_url in result_img_list]
        img_result = await ProcessUtils.fragment_process(tasks=tasks, log_flag='get_shindan_maker_result_img')
        for _result in img_result:
            if _result.success():
                result_msg += MessageSegment.image(file=_result.result)

    await shindan_maker_default.finish(result_msg)


shindan_pattern = r'^今天的?(.+?)(的|是)(.+?)[?？]?$'
shindan_maker_today_custom = shindan_maker.on_regex(
    shindan_pattern,
    rule=OmegaRules.has_group_command_permission() & OmegaRules.has_level_or_node(30, 'shindan_maker.pattern_match')
)


@shindan_maker_today_custom.handle()
async def handle_shojo(bot: Bot, event: GroupMessageEvent, state: T_State):
    # 固定的id
    shindan_custon_id: Dict[str, int] = {
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

    args = str(event.get_plaintext()).strip()
    input_name, shindan_name = re.findall(shindan_pattern, args)[0][0], re.findall(shindan_pattern, args)[0][2]
    shindan_id = shindan_custon_id.get(shindan_name, None)
    if not shindan_id:
        logger.debug(f'ShindanMaker | User: {event.user_id} 获取 ShindanMaker 占卜结果被中止, '
                     f'没有对应的预置占卜, {shindan_name} not found')
        await shindan_maker_today_custom.finish(
            f'没有你想问的东西哦, 或者你是想知道, 今天的XX是什么{"/".join(shindan_custon_id.keys())}吗?')

    today = f"@{datetime.date.today().strftime('%Y%m%d')}@"
    # 加入日期使每天的结果不一样
    _input_name = f'{input_name}{today}'
    result = await ShindanMaker(maker_id=shindan_id).get_result(input_name=_input_name)
    if result.error:
        logger.error(f'ShindanMaker | User: {event.user_id} 获取 ShindanMaker 占卜结果失败, {result.info}')
        await shindan_maker_today_custom.finish('获取ShindanMaker占卜结果失败了QAQ, 请稍后再试')

    result_text, result_img_list = result.result

    # 删除之前加入的日期字符
    result_msg = result_text.replace(today, '')

    # 结果有图片就处理图片
    if result_img_list:
        tasks = [PicEncoder(pic_url=img_url).get_file(
            folder_flag='shindan_maker_img_temp',
            format_=os.path.splitext(img_url)[-1][1:]
        ) for img_url in result_img_list]
        img_result = await ProcessUtils.fragment_process(tasks=tasks, log_flag='get_shindan_maker_result_img')
        for _result in img_result:
            if _result.success():
                result_msg += MessageSegment.image(file=_result.result)

    await shindan_maker_today_custom.finish(result_msg)
