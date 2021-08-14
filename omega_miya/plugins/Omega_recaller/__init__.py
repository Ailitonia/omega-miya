"""
@Author         : Ailitonia
@Date           : 2021/07/17 22:36
@FileName       : omega_recaller.py
@Project        : nonebot2_miya 
@Description    : 自助撤回群内消息 需bot为管理员
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Dict
from datetime import datetime
from nonebot import logger
from nonebot.plugin.export import export
from nonebot.plugin import CommandGroup
from nonebot.typing import T_State
from nonebot.exception import FinishedException
from nonebot.permission import SUPERUSER
from nonebot.adapters.cqhttp.permission import GROUP, GROUP_OWNER, GROUP_ADMIN
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.adapters.cqhttp.message import Message, MessageSegment
from omega_miya.database import DBBot, DBBotGroup, DBAuth, DBHistory
from omega_miya.utils.omega_plugin_utils import init_export, init_permission_state, PermissionChecker


# Custom plugin usage text
__plugin_raw_name__ = __name__.split('.')[-1]
__plugin_name__ = '自助撤回'
__plugin_usage__ = r'''【自助撤回】
让非管理员自助撤回群消息
Bot得是管理员才行

**Permission**
AuthNode

**AuthNode**
basic

**Usage**
回复需撤回的消息
/撤回

**GroupAdmin and SuperUser Only**
/启用撤回 [@用户]
/禁用撤回 [@用户]
'''

# 声明本插件可配置的权限节点
__plugin_auth_node__ = [
    'basic'
]

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__, __plugin_auth_node__)

# 存放bot在群组的身份
BOT_ROLE: Dict[int, str] = {}

# 存放bot群组信息过期时间
BOT_ROLE_EXPIRED: Dict[int, datetime] = {}


# 注册事件响应器
SelfHelpRecall = CommandGroup(
    'SelfHelpRecall',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_permission_state(
        name='search_anime',
        command=True,
        level=10,
        auth_node='basic'),
    permission=SUPERUSER | GROUP,
    priority=10,
    block=True
)


recall = SelfHelpRecall.command('recall', aliases={'撤回'})


@recall.handle()
async def handle_super_recall_self_msg(bot: Bot, event: GroupMessageEvent, state: T_State):
    # 特别处理管理员撤回bot发送的消息
    if event.reply and str(event.user_id) in bot.config.superusers:
        if event.reply.sender.user_id == event.self_id:
            recall_msg_id = event.reply.message_id
            try:
                await bot.delete_msg(message_id=recall_msg_id)
                logger.info(f'Self-help Recall | 管理员 {event.group_id}/{event.user_id} '
                            f'撤回了Bot消息: {recall_msg_id}, "{event.reply.message}"')
                await recall.finish()
            except FinishedException:
                raise FinishedException
            except Exception as e:
                logger.error(f'Self-help Recall | 管理员 {event.group_id}/{event.user_id} '
                             f'撤回Bot消息失败, error: {repr(e)}')
                msg = f'{MessageSegment.at(user_id=event.user_id)}撤回消息部分或全部失败了QAQ'
                await recall.finish(Message(msg))


@recall.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    if event.sender.role in ['owner', 'admin']:
        await recall.finish('您已经是群管理了, 请您自行去撤回消息OvO')

    # 用户权限检查
    auth_check_result = await PermissionChecker(self_bot=DBBot(self_qq=event.self_id)).check_auth_node(
        auth_id=event.group_id, auth_type='group', auth_node=f'{__plugin_raw_name__}.basic.{event.user_id}')
    if auth_check_result != 1:
        await recall.finish(Message(f'{MessageSegment.at(user_id=event.user_id)}你没有撤回消息的权限QAQ'))

    global BOT_ROLE
    global BOT_ROLE_EXPIRED
    # 判断bot身份和过期时间
    bot_role = BOT_ROLE.get(event.group_id)
    bot_role_expired = BOT_ROLE_EXPIRED.get(event.group_id)
    if not bot_role_expired:
        bot_role_expired = datetime.now()
        BOT_ROLE_EXPIRED.update({event.group_id: bot_role_expired})
    # 默认过期时间为 21600 秒 (6 小时)
    is_role_expired = (datetime.now() - bot_role_expired).total_seconds() > 21600
    if is_role_expired or not bot_role:
        bot_role = (await bot.get_group_member_info(group_id=event.group_id, user_id=event.self_id)).get('role')
        BOT_ROLE.update({event.group_id: bot_role})

    if bot_role not in ['owner', 'admin']:
        await recall.finish('Bot非群管理员, 无法执行撤回操作QAQ')

    error_tag: bool = False
    # 提取引用消息
    if event.reply:
        # 同时撤回被引用的消息
        recall_msg_id = event.reply.message_id
        try:
            await bot.delete_msg(message_id=recall_msg_id)
            logger.info(
                f'Self-help Recall | {event.group_id}/{event.user_id} 撤回消息: {recall_msg_id}, "{event.reply.message}"')
        except Exception as e:
            error_tag = True
            logger.error(f'Self-help Recall | {event.group_id}/{event.user_id} 撤回引用消息失败, error: {repr(e)}')

        # 同时撤回和当前执行撤回人的消息
        command_msg_id = event.message_id
        try:
            await bot.delete_msg(message_id=command_msg_id)
            logger.debug(f'Self-help Recall | {event.group_id}/{event.user_id} 撤回执行消息: {command_msg_id}')
        except Exception as e:
            error_tag = True
            logger.error(f'Self-help Recall | {event.group_id}/{event.user_id} 撤回当前执行消息失败, error: {repr(e)}')

        history_result = await DBHistory(
            time=event.time, self_id=event.self_id, post_type='Self-help Recall', detail_type='member-recall').add(
            sub_type=f'error:{error_tag}', event_id=event.message_id, group_id=event.group_id, user_id=event.user_id,
            user_name=event.sender.nickname,
            raw_data=f'Operator: {event.group_id}/{event.user_id}; RecalledMsg, user_id: {event.reply.sender.user_id}, '
                     f'msg_id: {recall_msg_id}, {event.reply.message}',
            msg_data=f'群: {event.group_id}, 用户: {event.user_id}/{event.sender.card}/{event.sender.nickname}, '
                     f'撤回了用户 {event.reply.sender.user_id}/{event.reply.sender.nickname} 的一条消息: {recall_msg_id}, '
                     f'被撤回消息内容: {event.reply.message}'
        )
        if history_result.error:
            logger.error(f'Self-help Recall | 记录撤回历史失败, error: {history_result.info}')

        if error_tag:
            msg = f'{MessageSegment.at(user_id=event.user_id)}撤回消息部分或全部失败了QAQ'
            await recall.finish(Message(msg))
        else:
            msg = f'{MessageSegment.at(user_id=event.user_id)}你撤回了' \
                  f'{MessageSegment.at(user_id=event.reply.sender.user_id)}的一条消息'
            await recall.finish(Message(msg))
    else:
        await recall.finish('没有引用需要撤回的消息! 请回复需要撤回的消息后发送“/撤回”')


recall_allow = SelfHelpRecall.command(
    'recall_allow', aliases={'启用撤回'}, permission=SUPERUSER | GROUP_OWNER | GROUP_ADMIN)


@recall_allow.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().split()
    if not args:
        pass
    else:
        await recall_allow.finish('参数错误QAQ, 请在 “/启用撤回” 命令后直接@对应用户')

    # 处理@人 qq在at别人时后面会自动加空格
    if len(event.message) in [1, 2]:
        if event.message[0].type == 'at':
            at_qq = event.message[0].data.get('qq')
            if at_qq:
                self_bot = DBBot(self_qq=event.self_id)
                group = DBBotGroup(group_id=event.group_id, self_bot=self_bot)
                group_exist = await group.exist()
                if not group_exist:
                    logger.error(f'Self-help Recall | 启用用户撤回失败, 数据库没有对应群组: {event.group_id}')
                    await recall_allow.finish('发生了意外的错误QAQ, 请联系管理员处理')

                auth_node = DBAuth(self_bot=self_bot, auth_id=event.group_id, auth_type='group',
                                   auth_node=f'{__plugin_raw_name__}.basic.{at_qq}')
                result = await auth_node.set(allow_tag=1, deny_tag=0, auth_info='启用自助撤回')
                if result.success():
                    logger.info(f'Self-help Recall | {event.group_id}/{event.user_id} 已启用用户 {at_qq} 撤回权限')
                    await recall_allow.finish(f'已启用用户{at_qq}撤回权限')
                else:
                    logger.error(f'Self-help Recall | {event.group_id}/{event.user_id} 启用用户 {at_qq} 撤回权限失败, '
                                 f'error: {result.info}')
                    await recall_allow.finish(f'启用用户撤回权限失败QAQ, 请联系管理员处理')

    await recall_allow.finish('没有指定用户QAQ, 请在 “/启用撤回” 命令后直接@对应用户')


recall_deny = SelfHelpRecall.command(
    'recall_deny', aliases={'禁用撤回'}, permission=SUPERUSER | GROUP_OWNER | GROUP_ADMIN)


@recall_deny.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().split()
    if not args:
        pass
    else:
        await recall_deny.finish('参数错误QAQ, 请在 “/禁用撤回” 命令后直接@对应用户')

    # 处理@人 qq在at别人时后面会自动加空格
    if len(event.message) in [1, 2]:
        if event.message[0].type == 'at':
            at_qq = event.message[0].data.get('qq')
            if at_qq:
                self_bot = DBBot(self_qq=event.self_id)
                group = DBBotGroup(group_id=event.group_id, self_bot=self_bot)
                group_exist = await group.exist()
                if not group_exist:
                    logger.error(f'Self-help Recall | 禁用用户撤回失败, 数据库没有对应群组: {event.group_id}')
                    await recall_deny.finish('发生了意外的错误QAQ, 请联系管理员处理')

                auth_node = DBAuth(self_bot=self_bot, auth_id=event.group_id, auth_type='group',
                                   auth_node=f'{__plugin_raw_name__}.basic.{at_qq}')
                result = await auth_node.set(allow_tag=0, deny_tag=1, auth_info='禁用自助撤回')
                if result.success():
                    logger.info(f'Self-help Recall | {event.group_id}/{event.user_id} 已禁用用户 {at_qq} 撤回权限')
                    await recall_deny.finish(f'已禁用用户{at_qq}撤回权限')
                else:
                    logger.error(f'Self-help Recall | {event.group_id}/{event.user_id} 禁用用户 {at_qq} 撤回权限失败, '
                                 f'error: {result.info}')
                    await recall_deny.finish(f'禁用用户撤回权限失败QAQ, 请联系管理员处理')

    await recall_deny.finish('没有指定用户QAQ, 请在 “/禁用撤回” 命令后直接@对应用户')
