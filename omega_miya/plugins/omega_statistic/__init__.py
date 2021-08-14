"""
@Author         : Ailitonia
@Date           : 2021/08/15 1:19
@FileName       : __init__.py.py
@Project        : nonebot2_miya 
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime
from nonebot import on_command, logger
from nonebot.plugin.export import export
from nonebot.typing import T_State
from nonebot.rule import to_me
from nonebot.permission import SUPERUSER
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent, GroupMessageEvent, PrivateMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP, PRIVATE_FRIEND
from nonebot.adapters.cqhttp.message import MessageSegment
from omega_miya.utils.omega_plugin_utils import init_export, init_permission_state, PicEncoder
from omega_miya.database import DBStatistic
from .utils import draw_statistics


# Custom plugin usage text
__plugin_name__ = '统计信息'
__plugin_usage__ = r'''【Omega 插件使用统计】
查询插件使用统计信息

**Permission**
Friend Private
Command & Lv.10
or AuthNode

**AuthNode**
basic

**Usage**
/统计信息 [条件]'''


# 声明本插件可配置的权限节点
__plugin_auth_node__ = [
    'basic'
]

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__, __plugin_auth_node__)


# 注册事件响应器
statistic = on_command(
    '统计信息',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_permission_state(
        name='statistic',
        command=True,
        level=10,
        auth_node='basic'),
    aliases={'插件统计', 'statistic'},
    permission=GROUP | PRIVATE_FRIEND,
    priority=10,
    block=True)


# 修改默认参数处理
@statistic.args_parser
async def parse(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await statistic.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await statistic.finish('操作已取消')


@statistic.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        state['condition'] = '本月'
    elif args and len(args) == 1:
        state['condition'] = args[0]
    else:
        await statistic.finish('参数错误QAQ')


@statistic.got('condition', prompt='请输入查询条件:\n【全部/本月/本年】')
async def handle_statistic(bot: Bot, event: MessageEvent, state: T_State):
    condition = state['condition']
    self_id = event.self_id
    now = datetime.now()
    if condition == '本月':
        start_time = datetime(year=now.year, month=now.month, day=1)
    elif condition == '本年':
        start_time = datetime(year=now.year, month=1, day=1)
    else:
        condition = '全部'
        start_time = None

    if isinstance(event, GroupMessageEvent):
        title = f'本群{condition}插件使用统计'
        group_id = event.group_id
        statistic_result = await DBStatistic(
            self_bot_id=self_id).get_group_statistic(group_id=group_id, start_time=start_time)
    elif isinstance(event, PrivateMessageEvent):
        title = f'用户{condition}插件使用统计'
        user_id = event.user_id
        statistic_result = await DBStatistic(
            self_bot_id=self_id).get_user_statistic(user_id=user_id, start_time=start_time)
    else:
        return

    if statistic_result.error:
        logger.error(f'查询统计信息失败, error: {statistic_result.info}')
        await statistic.finish('查询统计信息失败QAQ')

    draw_bytes = await draw_statistics(data=statistic_result.result, title=title)
    img_result = await PicEncoder.bytes_to_file(image=draw_bytes, folder_flag='statistic')
    if img_result.error:
        logger.error(f'生成统计图表失败, error: {img_result.info}')
        await statistic.finish('生成统计图表失败QAQ')

    await statistic.finish(MessageSegment.image(img_result.result))


admin_statistic = on_command(
    '全局统计信息',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    rule=to_me(),
    state=init_permission_state(
        name='admin_statistic',
        command=True,
        level=10,
        auth_node='basic'),
    aliases={'全局插件统计', 'total_stat'},
    permission=SUPERUSER,
    priority=10,
    block=True)


@admin_statistic.handle()
async def handle_admin_statistic(bot: Bot, event: MessageEvent, state: T_State):
    self_id = event.self_id
    statistic_result = await DBStatistic(self_bot_id=self_id).get_bot_statistic()
    if statistic_result.error:
        logger.error(f'查询全局统计信息失败, error: {statistic_result.info}')
        await statistic.finish('查询全局统计信息失败QAQ')

    title = f'Bot:{self_id} 全局插件使用统计'
    draw_bytes = await draw_statistics(data=statistic_result.result, title=title)
    img_result = await PicEncoder.bytes_to_file(image=draw_bytes, folder_flag='statistic')
    if img_result.error:
        logger.error(f'生成全局统计图表失败, error: {img_result.info}')
        await statistic.finish('生成全局统计图表失败QAQ')

    await statistic.finish(MessageSegment.image(img_result.result))
