from nonebot import on_command, export, logger
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP_ADMIN, GROUP_OWNER
from omega_miya.utils.Omega_Base import DBBot, DBBotGroup, DBSubscription, Result
from omega_miya.utils.Omega_plugin_utils import init_export, init_permission_state
from .monitor import scheduler


# Custom plugin usage text
__plugin_name__ = 'Pixivision'
__plugin_usage__ = r'''【Pixivision订阅】
推送最新的Pixivision特辑
仅限群聊使用

**Permission**
Command & Lv.30

**Usage**
**GroupAdmin and SuperUser Only**
/Pixivision 订阅
/Pixivision 取消订阅'''

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__)

# 注册事件响应器
pixivision = on_command(
    'pixivision',
    aliases={'Pixivision'},
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_permission_state(
        name='pixivision',
        command=True,
        level=30),
    permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER,
    priority=20,
    block=True)


# 修改默认参数处理
@pixivision.args_parser
async def parse(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await pixivision.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await pixivision.finish('操作已取消')


@pixivision.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        pass
    elif args and len(args) == 1:
        state['sub_command'] = args[0]
    else:
        await pixivision.finish('参数错误QAQ')


@pixivision.got('sub_command', prompt='执行操作?\n【订阅/取消订阅】')
async def handle_sub_command_args(bot: Bot, event: GroupMessageEvent, state: T_State):
    sub_command = state['sub_command']
    if sub_command not in ['订阅', '取消订阅']:
        await pixivision.reject('没有这个命令哦, 请在【订阅/取消订阅】中选择并重新发送, 取消命令请发送【取消】:')

    if sub_command == '订阅':
        _res = await sub_add(bot=bot, event=event, state=state)
    elif sub_command == '取消订阅':
        _res = await sub_del(bot=bot, event=event, state=state)
    else:
        _res = Result.IntResult(error=True, info='Unknown error, except sub_command', result=-1)
    if _res.success():
        logger.info(f"{sub_command}Pixivision成功, group_id: {event.group_id}, {_res.info}")
        await pixivision.finish(f'{sub_command}成功!')
    else:
        logger.error(f"{sub_command}Pixivision失败, group_id: {event.group_id}, {_res.info}")
        await pixivision.finish(f'{sub_command}失败了QAQ, 可能并未订阅Pixivision, 或请稍后再试~')


async def sub_add(bot: Bot, event: GroupMessageEvent, state: T_State) -> Result.IntResult:
    group_id = event.group_id
    self_bot = DBBot(self_qq=int(bot.self_id))
    group = DBBotGroup(group_id=group_id, self_bot=self_bot)
    sub_id = -1
    sub = DBSubscription(sub_type=8, sub_id=sub_id)
    _res = await sub.add(up_name='Pixivision', live_info='Pixivision订阅')
    if not _res.success():
        return _res
    _res = await group.subscription_add(sub=sub, group_sub_info='Pixivision订阅')
    if not _res.success():
        return _res
    result = Result.IntResult(error=False, info='Success', result=0)
    return result


async def sub_del(bot: Bot, event: GroupMessageEvent, state: T_State) -> Result.IntResult:
    group_id = event.group_id
    self_bot = DBBot(self_qq=int(bot.self_id))
    group = DBBotGroup(group_id=group_id, self_bot=self_bot)
    sub_id = -1
    _res = await group.subscription_del(sub=DBSubscription(sub_type=8, sub_id=sub_id))
    if not _res.success():
        return _res
    result = Result.IntResult(error=False, info='Success', result=0)
    return result
