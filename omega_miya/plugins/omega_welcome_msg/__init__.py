"""
@Author         : Ailitonia
@Date           : 2021/08/14 19:09
@FileName       : __init__.py.py
@Project        : nonebot2_miya 
@Description    : 群自定义欢迎信息
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""


from nonebot import logger
from nonebot.plugin.export import export
from nonebot.plugin import on_notice, CommandGroup
from nonebot.typing import T_State
from nonebot.rule import to_me
from nonebot.permission import SUPERUSER
from nonebot.adapters.cqhttp.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.message import Message, MessageSegment
from nonebot.adapters.cqhttp.event import GroupMessageEvent, GroupIncreaseNoticeEvent
from omega_miya.database import DBBot, DBBotGroup
from omega_miya.utils.omega_plugin_utils import init_export, OmegaRules


SETTING_NAME: str = 'group_welcome_message'
DEFAULT_WELCOME_MSG: str = '欢迎新朋友～\n进群请先看群公告～\n一起愉快地聊天吧!'


# Custom plugin usage text
__plugin_name__ = '群欢迎消息'
__plugin_usage__ = r'''【群自定义欢迎信息插件】
向新入群的成员发送欢迎消息

以下命令均需要@机器人
**Usage**
**GroupAdmin and SuperUser Only**
/设置欢迎消息
/清空欢迎消息
'''

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__)


# 注册事件响应器
WelcomeMsg = CommandGroup(
    'WelcomeMsg',
    rule=to_me(),
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER,
    priority=10,
    block=True
)

welcome_msg_set = WelcomeMsg.command('set', aliases={'设置欢迎消息'})
welcome_msg_clear = WelcomeMsg.command('clear', aliases={'清空欢迎消息'})


# 修改默认参数处理
@welcome_msg_set.args_parser
async def parse(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_message()).strip()
    if not args:
        await welcome_msg_set.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args
    if state[state["_current_key"]] == '取消':
        await welcome_msg_set.finish('操作已取消')


@welcome_msg_set.got('welcome_msg', prompt='请发送你要设置的欢迎消息:')
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    welcome_msg = state['welcome_msg']
    group_id = event.group_id
    self_bot = DBBot(self_qq=int(bot.self_id))
    group = DBBotGroup(group_id=group_id, self_bot=self_bot)
    msg_set_result = await group.setting_set(setting_name=SETTING_NAME, main_config='Custom',
                                             extra_config=welcome_msg, setting_info='自定义群组欢迎信息')
    if msg_set_result.success():
        logger.info(f'已为群组: {group_id} 设置自定义欢迎信息: {welcome_msg}')
        await welcome_msg_set.finish(f'已为本群组设定了自定义欢迎信息!')
    else:
        logger.error(f'为群组: {group_id} 设置自定义欢迎信息失败, error info: {msg_set_result.info}')
        await welcome_msg_set.finish(f'为本群组设定自定义欢迎信息失败了QAQ, 请稍后再试或联系管理员处理')


@welcome_msg_clear.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    group_id = event.group_id
    self_bot = DBBot(self_qq=int(bot.self_id))
    group = DBBotGroup(group_id=group_id, self_bot=self_bot)
    msg_set_result = await group.setting_del(setting_name=SETTING_NAME)
    if msg_set_result.success():
        logger.info(f'已为群组: {group_id} 清除自定义欢迎信息')
        await welcome_msg_clear.finish(f'已清除了本群组设定的自定义欢迎信息!')
    else:
        logger.error(f'为群组: {group_id} 清除自定义欢迎信息失败, error info: {msg_set_result.info}')
        await welcome_msg_clear.finish(f'为本群组清除自定义欢迎信息失败了QAQ, 请稍后再试或联系管理员处理')


# 注册事件响应器, 新增群成员
group_increase = on_notice(priority=100, rule=OmegaRules.has_group_command_permission())


@group_increase.handle()
async def handle_group_increase(bot: Bot, event: GroupIncreaseNoticeEvent, state: T_State):
    user_id = event.user_id
    group_id = event.group_id
    self_bot = DBBot(self_qq=int(bot.self_id))
    group = DBBotGroup(group_id=group_id, self_bot=self_bot)
    # 获取自定义欢迎信息
    welcome_msg_result = await group.setting_get(setting_name=SETTING_NAME)
    if welcome_msg_result.success():
        main, second, extra = welcome_msg_result.result
        if extra:
            msg = extra
        else:
            msg = DEFAULT_WELCOME_MSG
    else:
        msg = DEFAULT_WELCOME_MSG

    # 发送欢迎消息
    at_seg = MessageSegment.at(user_id=user_id)
    await bot.send(event=event, message=Message(at_seg).append(msg))
    logger.info(f'群组: {group_id}, 有新用户: {user_id} 进群')
