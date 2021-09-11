from nonebot import MatcherGroup, logger
from nonebot.plugin.export import export
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.adapters.cqhttp import Message
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP, GROUP_ADMIN, GROUP_OWNER
from omega_miya.database import DBBot, DBBotGroup, DBAuth, Result
from omega_miya.utils.omega_plugin_utils import init_export, init_processor_state, OmegaRules


# Custom plugin usage text
__plugin_raw_name__ = __name__.split('.')[-1]
__plugin_custom_name__ = 'AntiFlash'
__plugin_usage__ = r'''【AntiFlash 反闪照】
检测闪照并提取原图

**Permission**
Group only with
AuthNode

**AuthNode**
basic

**Usage**
**GroupAdmin and SuperUser Only**
/AntiFlash <ON|OFF>'''

# 声明本插件可配置的权限节点
__plugin_auth_node__ = [
    'basic'
]

# Init plugin export
init_export(export(), __plugin_custom_name__, __plugin_usage__, __plugin_auth_node__)


# 注册事件响应器
AntiFlash = MatcherGroup(type='message', permission=GROUP, priority=100, block=False)

anti_flash_admin = AntiFlash.on_command(
    'AntiFlash',
    aliases={'antiflash', '反闪照'},
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='anti_flash',
        command=True,
        level=10),
    permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER,
    priority=10,
    block=True)


# 修改默认参数处理
@anti_flash_admin.args_parser
async def parse(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await anti_flash_admin.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await anti_flash_admin.finish('操作已取消')


@anti_flash_admin.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        pass
    elif args and len(args) == 1:
        state['sub_command'] = args[0]
    else:
        await anti_flash_admin.finish('参数错误QAQ')


@anti_flash_admin.got('sub_command', prompt='执行操作?\n【ON/OFF】')
async def handle_sub_command_args(bot: Bot, event: GroupMessageEvent, state: T_State):
    sub_command = state['sub_command']
    if sub_command not in ['on', 'off']:
        await anti_flash_admin.reject('没有这个选项哦, 请在【ON/OFF】中选择并重新发送, 取消命令请发送【取消】:')

    if sub_command == 'on':
        _res = await anti_flash_on(bot=bot, event=event, state=state)
    elif sub_command == 'off':
        _res = await anti_flash_off(bot=bot, event=event, state=state)
    else:
        _res = Result.IntResult(error=True, info='Unknown error, except sub_command', result=-1)

    if _res.success():
        logger.info(f"设置 AntiFlash 状态为 {sub_command} 成功, group_id: {event.group_id}, {_res.info}")
        await anti_flash_admin.finish(f'已设置 AntiFlash 状态为 {sub_command}!')
    else:
        logger.error(f"设置 AntiFlash 状态为 {sub_command} 失败, group_id: {event.group_id}, {_res.info}")
        await anti_flash_admin.finish(f'设置 AntiFlash 状态失败了QAQ, 请稍后再试~')


async def anti_flash_on(bot: Bot, event: GroupMessageEvent, state: T_State) -> Result.IntResult:
    group_id = event.group_id
    self_bot = DBBot(self_qq=int(bot.self_id))
    group = DBBotGroup(group_id=group_id, self_bot=self_bot)
    group_exist = await group.exist()
    if not group_exist:
        return Result.IntResult(error=False, info='Group not exist', result=-1)

    auth_node = DBAuth(self_bot=self_bot, auth_id=group_id, auth_type='group', auth_node=f'{__plugin_raw_name__}.basic')
    result = await auth_node.set(allow_tag=1, deny_tag=0, auth_info='启用反闪照')
    return result


async def anti_flash_off(bot: Bot, event: GroupMessageEvent, state: T_State) -> Result.IntResult:
    group_id = event.group_id
    self_bot = DBBot(self_qq=int(bot.self_id))
    group = DBBotGroup(group_id=group_id, self_bot=self_bot)
    group_exist = await group.exist()
    if not group_exist:
        return Result.IntResult(error=False, info='Group not exist', result=-1)

    auth_node = DBAuth(self_bot=self_bot, auth_id=group_id, auth_type='group', auth_node=f'{__plugin_raw_name__}.basic')
    result = await auth_node.set(allow_tag=0, deny_tag=1, auth_info='禁用反闪照')
    return result


anti_flash_handler = AntiFlash.on_message(rule=OmegaRules.has_auth_node(__plugin_raw_name__, 'basic'))


@anti_flash_handler.handle()
async def check_flash_img(bot: Bot, event: GroupMessageEvent, state: T_State):
    for msg_seg in event.message:
        if msg_seg.type == 'image':
            if msg_seg.data.get('type') == 'flash':
                msg = Message('AntiFlash 已检测到闪照:\n').append(str(msg_seg).replace(',type=flash', ''))
                logger.info(f'AntiFlash 已处理闪照, message_id: {event.message_id}')
                await anti_flash_handler.finish(msg)
