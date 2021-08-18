"""
@Author         : Ailitonia
@Date           : 2021/06/28 21:41
@FileName       : __init__.py.py
@Project        : nonebot2_miya 
@Description    : shindan_maker 无聊的占卜插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import re
import datetime
from typing import Dict
from nonebot import MatcherGroup, logger
from nonebot.plugin.export import export
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent, GroupMessageEvent, PrivateMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP
from omega_miya.utils.omega_plugin_utils import init_export, init_permission_state, PluginCoolDown, OmegaRules
from .data_source import ShindanMaker


# Custom plugin usage text
__plugin_custom_name__ = 'ShindanMaker'
__plugin_usage__ = r'''【ShindanMaker 占卜】
使用ShindanMaker进行各种奇怪的占卜
只能在群里使用
就是要公开处刑！

**Permission**
Command & Lv.30
or AuthNode

**AuthNode**
basic

**Usage**
/ShindanMaker [占卜名称] [占卜对象名称]'''

# 声明本插件可配置的权限节点
__plugin_auth_node__ = [
    PluginCoolDown.skip_auth_node,
    'basic'
]

# # 声明本插件的冷却时间配置
# __plugin_cool_down__ = [
#     PluginCoolDown(PluginCoolDown.user_type, 1),
#     PluginCoolDown(PluginCoolDown.group_type, 1)
# ]

# Init plugin export
init_export(export(), __plugin_custom_name__, __plugin_usage__, __plugin_auth_node__)


# 缓存占卜名称与对应id
SHINDANMAKER_CACHE: Dict[str, int] = {}


# 注册事件响应器
shindan_maker = MatcherGroup(
    type='message',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_permission_state(
        name='shindan_maker',
        command=True,
        level=30,
        auth_node='basic'),
    permission=GROUP,
    priority=20,
    block=True)


shindan_maker_default = shindan_maker.on_command(
    'ShindanMaker', aliases={'占卜', 'shindanmaker', 'SHINDANMAKER', 'Shindan', 'shindan', 'SHINDAN'})


# 修改默认参数处理
@shindan_maker_default.args_parser
async def parse(bot: Bot, event: GroupMessageEvent, state: T_State):
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
            group_member_list = await bot.get_group_member_list(group_id=event.group_id)
            nickname = [x for x in group_member_list if x.get('user_id') == int(at_qq)]
            if nickname:
                input_name = nickname[0].get('card') if nickname[0].get('card') else nickname[0].get('nickname')
                if input_name:
                    state['input_name'] = input_name


@shindan_maker_default.got('shindan_name', prompt='你想做什么占卜呢?\n不知道的话可以输入关键词进行搜索哦~')
async def handle_shindan_name(bot: Bot, event: GroupMessageEvent, state: T_State):
    global SHINDANMAKER_CACHE

    shindan_name = state['shindan_name']
    shindan_id = SHINDANMAKER_CACHE.get(shindan_name, 0)
    if shindan_id == 0:
        shindan_name_result = await ShindanMaker.search(keyword=shindan_name)
        if shindan_name_result.error:
            logger.error(f'User: {event.user_id} 获取 ShindanMaker 占卜信息失败, {shindan_name_result.info}')
            await shindan_maker_default.finish('获取ShindanMaker占卜信息失败了QAQ, 请稍后再试')
        else:
            for item in shindan_name_result.result:
                if item.get('name'):
                    SHINDANMAKER_CACHE.update({
                        re.sub(r'\s', '', item.get('name')): item.get('id', 0)
                    })
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
    shindan_name = state['shindan_name']
    input_name = state['input_name']
    shindan_id = state['id']
    today = f"@{datetime.date.today().strftime('%Y%m%d')}@"
    # 加入日期使每天的结果不一样
    _input_name = f'{input_name}{today}'
    result = await ShindanMaker(maker_id=shindan_id).get_result(input_name=_input_name)
    if result.error:
        logger.error(f'User: {event.user_id} 获取 ShindanMaker 占卜结果失败, {result.info}')
        await shindan_maker_default.finish('获取ShindanMaker占卜结果失败了QAQ, 请稍后再试')

    result_text = result.result.replace(today, '')
    msg = f'{shindan_name}@{input_name}\n{"="*16}\n{result_text}'
    await shindan_maker_default.finish(msg)


shindan_pattern = r'^今天的?(.+?)是什么(样的)?(.+?)[?？]?$'
shindan_maker_today_custom = shindan_maker.on_regex(
    shindan_pattern,
    rule=OmegaRules.has_group_command_permission() & OmegaRules.has_level_or_node(30, 'shindan_maker.basic')
)


@shindan_maker_today_custom.handle()
async def handle_shojo(bot: Bot, event: GroupMessageEvent, state: T_State):
    # 固定的id
    shindan_custon_id: Dict[str, int] = {
        '少女': 162207,
        '魔法少女': 828741,
        '偶像': 828727,
        '做的': 761425,
        '干员': 959146,
        '小动物': 828905,
        '猫': 28998,
        '主角': 828977,
        '宝石': 890951,
        '花': 829525
    }

    args = str(event.get_plaintext()).strip()
    input_name, shindan_name = re.findall(shindan_pattern, args)[0][0], re.findall(shindan_pattern, args)[0][2]
    shindan_id = shindan_custon_id.get(shindan_name, None)
    if not shindan_id:
        logger.info(f'User: {event.user_id} 获取 ShindanMaker 占卜结果被中止, 没有对应的预置占卜, {shindan_name} not found')
        await shindan_maker_today_custom.finish(
            f'没有你想问的东西哦, 或者你是想知道, 今天的XX是什么{"/".join(shindan_custon_id.keys())}吗?')

    today = f"@{datetime.date.today().strftime('%Y%m%d')}@"
    # 加入日期使每天的结果不一样
    _input_name = f'{input_name}{today}'
    result = await ShindanMaker(maker_id=shindan_id).get_result(input_name=_input_name)
    if result.error:
        logger.error(f'User: {event.user_id} 获取 ShindanMaker 占卜结果失败, {result.info}')
        await shindan_maker_today_custom.finish('获取ShindanMaker占卜结果失败了QAQ, 请稍后再试')

    result_text = result.result.replace(today, '')
    await shindan_maker_today_custom.finish(result_text)
