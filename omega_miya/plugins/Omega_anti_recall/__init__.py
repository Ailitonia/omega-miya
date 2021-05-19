from nonebot import on_command, on_notice, export, logger
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.adapters.cqhttp import Message
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent, GroupRecallNoticeEvent
from nonebot.adapters.cqhttp.permission import GROUP_ADMIN, GROUP_OWNER
from omega_miya.utils.Omega_Base import DBGroup, DBAuth, DBHistory, Result
from omega_miya.utils.Omega_plugin_utils import init_export, init_permission_state, has_auth_node


# Custom plugin usage text
__plugin_raw_name__ = __name__.split('.')[-1]
__plugin_name__ = 'AntiRecall'
__plugin_usage__ = r'''【AntiRecall 反撤回】
检测消息撤回并提取原消息

**Permission**
Group only with
AuthNode

**AuthNode**
basic

**Usage**
**GroupAdmin and SuperUser Only**
/AntiRecall <ON|OFF>'''

# 声明本插件可配置的权限节点
__plugin_auth_node__ = [
    'basic'
]

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__, __plugin_auth_node__)


# 注册事件响应器
anti_recall_admin = on_command(
    'AntiRecall',
    aliases={'antirecall', '反撤回'},
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_permission_state(
        name='anti_recall',
        command=True,
        level=10),
    permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER,
    priority=10,
    block=True)


# 修改默认参数处理
@anti_recall_admin.args_parser
async def parse(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await anti_recall_admin.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await anti_recall_admin.finish('操作已取消')


@anti_recall_admin.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        pass
    elif args and len(args) == 1:
        state['sub_command'] = args[0]
    else:
        await anti_recall_admin.finish('参数错误QAQ')


@anti_recall_admin.got('sub_command', prompt='执行操作?\n【ON/OFF】')
async def handle_sub_command_args(bot: Bot, event: GroupMessageEvent, state: T_State):
    sub_command = state['sub_command']
    if sub_command not in ['on', 'off']:
        await anti_recall_admin.reject('没有这个选项哦, 请在【ON/OFF】中选择并重新发送, 取消命令请发送【取消】:')

    if sub_command == 'on':
        _res = await anti_recall_on(bot=bot, event=event, state=state)
    elif sub_command == 'off':
        _res = await anti_recall_off(bot=bot, event=event, state=state)
    else:
        _res = Result.IntResult(error=True, info='Unknown error, except sub_command', result=-1)

    if _res.success():
        logger.info(f"设置 AntiRecall 状态为 {sub_command} 成功, group_id: {event.group_id}, {_res.info}")
        await anti_recall_admin.finish(f'已设置 AntiRecall 状态为 {sub_command}!')
    else:
        logger.error(f"设置 AntiRecall 状态为 {sub_command} 失败, group_id: {event.group_id}, {_res.info}")
        await anti_recall_admin.finish(f'设置 AntiRecall 状态失败了QAQ, 请稍后再试~')


async def anti_recall_on(bot: Bot, event: GroupMessageEvent, state: T_State) -> Result.IntResult:
    group_id = event.group_id
    group = DBGroup(group_id=group_id)
    group_exist = await group.exist()
    if not group_exist:
        return Result.IntResult(error=False, info='Group not exist', result=-1)

    auth_node = DBAuth(auth_id=group_id, auth_type='group', auth_node=f'{__plugin_raw_name__}.basic')
    result = await auth_node.set(allow_tag=1, deny_tag=0, auth_info='启用反撤回')
    return result


async def anti_recall_off(bot: Bot, event: GroupMessageEvent, state: T_State) -> Result.IntResult:
    group_id = event.group_id
    group = DBGroup(group_id=group_id)
    group_exist = await group.exist()
    if not group_exist:
        return Result.IntResult(error=False, info='Group not exist', result=-1)

    auth_node = DBAuth(auth_id=group_id, auth_type='group', auth_node=f'{__plugin_raw_name__}.basic')
    result = await auth_node.set(allow_tag=0, deny_tag=1, auth_info='禁用反撤回')
    return result


anti_recall_handler = on_notice(rule=has_auth_node(__plugin_raw_name__, 'basic'), priority=100, block=False)


@anti_recall_handler.handle()
async def check_recall_notice(bot: Bot, event: GroupRecallNoticeEvent, state: T_State):
    self_id = event.self_id
    group_id = event.group_id
    user_id = event.user_id
    message_id = event.message_id
    history_result = await DBHistory.search_unique_msg(
        self_id=self_id, post_type='message', detail_type='group', sub_type='normal',
        event_id=message_id, group_id=group_id, user_id=user_id)
    if history_result.error:
        logger.error(f'AntiRecall 查询历史消息失败, message_id: {message_id}, error: {history_result.info}')
        return
    else:
        history = history_result.result
        user_name = history.user_name
        time = history.created_at
        msg = history.msg_data
        send_msg = Message(f"AntiRecall 已检测到撤回消息:\n{time}@{user_name}:\n").append(msg)
        logger.info(f'AntiRecall 已处理撤回消息, message_id: {message_id}')
        await anti_recall_handler.finish(send_msg)
