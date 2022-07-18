"""
@Author         : Ailitonia
@Date           : 2021/08/15 1:19
@FileName       : omega_statistic.py
@Project        : nonebot2_miya 
@Description    : 统计插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime
from nonebot.log import logger
from nonebot.plugin import on_command, PluginMetadata
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.adapters.onebot.v11.event import MessageEvent, GroupMessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP, PRIVATE_FRIEND
from nonebot.params import CommandArg, ArgStr

from omega_miya.service import init_processor_state
from omega_miya.service.gocqhttp_guild_patch import GuildMessageEvent, GUILD

from .utils import draw_statistics


__plugin_meta__ = PluginMetadata(
    name="统计信息",
    description="【OmegaStatistic 插件使用统计】\n"
                "查询插件使用统计信息",
    usage="/统计信息 [条件]\n\n"
          "条件:\n"
          "- 本月\n"
          "- 本年\n"
          "- 全部\n"
          "- 所有",
    extra={"author": "Ailitonia"},
)


# 注册事件响应器
statistic = on_command(
    'statistic',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='statistic', level=10),
    aliases={'统计信息', '使用统计', '插件统计'},
    permission=SUPERUSER | GROUP | GUILD | PRIVATE_FRIEND,
    priority=10,
    block=True
)


@statistic.handle()
async def handle_parse_condition(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    condition = cmd_arg.extract_plain_text().strip()
    if condition:
        state.update({'condition': condition})
    else:
        state.update({'condition': '本月'})


@statistic.got('condition', prompt='请输入查询条件:')
async def handle_help_message(bot: Bot, matcher: Matcher, event: MessageEvent, condition: str = ArgStr('condition')):
    condition = condition.strip()

    if isinstance(event, GroupMessageEvent):
        call_id = f'group_{event.group_id}'
        title_prefix = f'本群({event.group_id})'
    elif isinstance(event, GuildMessageEvent):
        call_id = f'guild_channel_{event.guild_id}_{event.channel_id}'
        title_prefix = f'频道({event.channel_id})'
    elif isinstance(event, MessageEvent):
        call_id = f'user_{event.user_id}'
        title_prefix = f'用户({event.user_id})'
    else:
        call_id = f'bot_{event.self_id}'
        title_prefix = f'Bot({event.self_id})'

    now = datetime.now()
    match condition:
        case '本月':
            start_time = datetime(year=now.year, month=now.month, day=1)
        case '本年':
            start_time = datetime(year=now.year, month=1, day=1)
        case '全部':
            start_time = None
        case '所有':
            if not await SUPERUSER(bot=bot, event=event):
                await matcher.finish('只有管理员才可以查看所有的统计信息哦')
            start_time = None
            call_id = None
            title_prefix = f'Bot({event.self_id})'
        case _:
            start_time = None

    statistic_image = await draw_statistics(
        self_id=bot.self_id, start_time=start_time, title=f'{title_prefix}{condition}插件使用统计', call_id=call_id)

    if isinstance(statistic_image, Exception):
        logger.error(f'生成统计图表失败, error: {statistic_image}')
        await matcher.finish('生成统计图表失败QAQ')

    await matcher.finish(MessageSegment.image(statistic_image.file_uri))
