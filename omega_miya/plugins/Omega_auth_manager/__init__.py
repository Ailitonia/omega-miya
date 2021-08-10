import re
from nonebot import on_command, get_plugin, get_loaded_plugins, logger
from nonebot.plugin.export import export
from nonebot.rule import to_me
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent, GroupMessageEvent, PrivateMessageEvent
from omega_miya.utils.Omega_Base import DBBot, DBFriend, DBBotGroup, DBAuth
from omega_miya.utils.Omega_plugin_utils import init_export


# Custom plugin usage text
__plugin_name__ = 'OmegaAuth'
__plugin_usage__ = r'''【OmegaAuth 授权管理插件】
插件特殊权限授权管理
仅限管理员使用

**Usage**
**SuperUser Only**
/OmegaAuth'''

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__)

# 注册事件响应器
omegaauth = on_command('OmegaAuth', rule=to_me(), aliases={'omegaauth', 'oauth'},
                       permission=SUPERUSER, priority=10, block=True)


# 修改默认参数处理
@omegaauth.args_parser
async def parse(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().split()
    if not args:
        await omegaauth.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await omegaauth.finish('操作已取消')


@omegaauth.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().split()
    if not args:
        pass
    elif args and len(args) == 1:
        state['sub_command'] = args[0]
    else:
        await omegaauth.finish('参数错误QAQ')


# 处理显示权限节点列表事件
@omegaauth.got('sub_command', prompt='执行操作?\n【allow/deny/clear/custom_*/list】')
async def handle_sub_command(bot: Bot, event: MessageEvent, state: T_State):
    sub_command = state["sub_command"]
    if sub_command not in ['allow', 'deny', 'clear', 'list', 'custom_allow', 'custom_deny', 'custom_clear']:
        await omegaauth.finish('参数错误QAQ')

    self_bot = DBBot(self_qq=int(bot.self_id))
    if sub_command == 'list':
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
            _res = await DBAuth.list(auth_type='group', auth_id=group_id, self_bot=self_bot)
            if _res.success():
                node_text = '\n'.join('/'.join(map(str, n)) for n in _res.result)
                msg = f'当前群组权限列表为:\n\n{node_text}'
                await omegaauth.finish(msg)
            else:
                await omegaauth.finish('发生了意外的错误QAQ, 请稍后再试')
        elif isinstance(event, PrivateMessageEvent):
            user_id = event.user_id
            _res = await DBAuth.list(auth_type='user', auth_id=user_id, self_bot=self_bot)
            if _res.success():
                node_text = '\n'.join('/'.join(map(str, n)) for n in _res.result)
                msg = f'当前用户权限列表为:\n\n{node_text}'
                await omegaauth.finish(msg)
            else:
                await omegaauth.finish('发生了意外的错误QAQ, 请稍后再试')
        else:
            await omegaauth.finish('非授权会话, 操作中止')
    elif sub_command in ['allow', 'deny', 'clear']:
        if isinstance(event, GroupMessageEvent):
            state["auth_type"] = 'group'
            state["auth_id"] = str(event.group_id)
        elif isinstance(event, PrivateMessageEvent):
            state["auth_type"] = 'user'
            state["auth_id"] = str(event.user_id)


@omegaauth.got('auth_type', prompt='授权类型?\n【user/group】')
async def handle_auth_type(bot: Bot, event: MessageEvent, state: T_State):
    auth_type = state["auth_type"]
    if auth_type not in ['user', 'group']:
        await omegaauth.finish('参数错误QAQ')


@omegaauth.got('auth_id', prompt='请输入授权用户qq或授权群组群号:')
async def handle_auth_id(bot: Bot, event: MessageEvent, state: T_State):
    auth_type = state["auth_type"]
    auth_id = state["auth_id"]
    self_bot = DBBot(self_qq=int(bot.self_id))
    if not re.match(r'^\d+$', auth_id):
        await omegaauth.finish('参数错误QAQ, qq或群号应为纯数字')

    if auth_type == 'user':
        user = DBFriend(user_id=auth_id, self_bot=self_bot)
        user_name_res = await user.nickname()
        if user_name_res.success():
            await omegaauth.send(f'即将对用户: 【{user_name_res.result}】执行操作')
        else:
            logger.error(f'为 {auth_type}/{auth_id} 配置权限节点失败, 数据库中不存在该用户')
            await omegaauth.finish('数据库中不存在该用户QAQ')
    elif auth_type == 'group':
        group = DBBotGroup(group_id=auth_id, self_bot=self_bot)
        group_name_res = await group.name()
        if group_name_res.success():
            await omegaauth.send(f'即将对群组: 【{group_name_res.result}】执行操作')
        else:
            logger.error(f'为 {auth_type}/{auth_id} 配置权限节点失败, 数据库中不存在该群组')
            await omegaauth.finish('数据库中不存在该群组QAQ')
    else:
        await omegaauth.finish('参数错误QAQ')

    # 处理可用权限节点列表
    plugins = get_loaded_plugins()
    auth_node_plugin = []
    for plugin in plugins:
        if plugin.export.get('auth_node'):
            auth_node_plugin.append(plugin.name)

    state["auth_node_plugin"] = auth_node_plugin
    p_list = '\n'.join(auth_node_plugin)
    await omegaauth.send(f'可配置权限节点的插件有:\n\n{p_list}')


@omegaauth.got('plugin', prompt='请输入想要配置权限节点的插件名称:')
async def handle_plugin(bot: Bot, event: MessageEvent, state: T_State):
    plugin = state["plugin"]
    auth_node_plugin = state["auth_node_plugin"]
    if plugin not in auth_node_plugin:
        await omegaauth.reject('插件名称错误, 请重新输入:')

    plugin_auth_nodes = get_plugin(plugin).export.get('auth_node')
    state["plugin_auth_nodes"] = plugin_auth_nodes
    an_list = '\n'.join(plugin_auth_nodes)
    await omegaauth.send(f'{plugin}可配置的权限节点有:\n\n{an_list}')


@omegaauth.got('auth_node', prompt='请输入想要配置的权限节点名称:')
async def handle_auth_node(bot: Bot, event: MessageEvent, state: T_State):
    auth_node = state["auth_node"]
    plugin = state["plugin"]
    plugin_auth_nodes = state["plugin_auth_nodes"]
    if auth_node not in plugin_auth_nodes:
        await omegaauth.reject('权限节点名称错误, 请重新输入:')

    r_auth_node = '.'.join([plugin, auth_node])
    auth_id = state["auth_id"]
    sub_command = re.sub(r'^custom_', '', str(state["sub_command"]))
    auth_type = state["auth_type"]
    self_bot = DBBot(self_qq=int(bot.self_id))

    auth = DBAuth(auth_id=auth_id, auth_type=auth_type, auth_node=r_auth_node, self_bot=self_bot)

    if sub_command == 'allow':
        res = await auth.set(allow_tag=1, deny_tag=0)
    elif sub_command == 'deny':
        res = await auth.set(allow_tag=0, deny_tag=1)
    elif sub_command == 'clear':
        res = await auth.delete()
    else:
        logger.error(f'handle_auth_node 执行时 sub_command 命令检验错误')
        return

    if res.success():
        logger.info(f'已成功为 {auth_type}/{auth_id} {sub_command} 了权限节点 {r_auth_node}: {res.info}')
        await omegaauth.finish(f'{auth_type}/{auth_id} {r_auth_node} 权限节点 {sub_command} 操作成功')
    else:
        logger.error(f'为 {auth_type}/{auth_id} {sub_command} 权限节点 {r_auth_node} 失败: {res.info}')
        await omegaauth.finish(f'{auth_type}/{auth_id} {r_auth_node} 权限节点 {sub_command} 操作失败QAQ, 请稍后再试')
