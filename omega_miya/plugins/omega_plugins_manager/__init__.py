"""
@Author         : Ailitonia
@Date           : 2021/09/12 14:02
@FileName       : __init__.py.py
@Project        : nonebot2_miya 
@Description    : 插件管理器
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import pathlib
from nonebot import CommandGroup, get_loaded_plugins, logger
from nonebot.plugin.export import export
from nonebot.rule import to_me
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent
from nonebot.adapters.cqhttp.message import MessageSegment
from omega_miya.database import DBPlugin
from omega_miya.utils.omega_plugin_utils import init_export, TextUtils


# Custom plugin usage text
__plugin_custom_name__ = 'Omega Plugins Manager'
__plugin_usage__ = r'''【OmegaPluginsManager 插件管理器】
插件管理器
仅限超级管理员使用

**Usage**
**SuperUser Only**
/OPM'''


# Init plugin export
init_export(export(), __plugin_custom_name__, __plugin_usage__)


# 注册事件响应器
OmegaPluginsManager = CommandGroup(
    'OPM',
    rule=to_me(),
    permission=SUPERUSER,
    priority=10,
    block=True
)

enable_plugin = OmegaPluginsManager.command('enable', aliases={'启用插件'})
disable_plugin = OmegaPluginsManager.command('disable', aliases={'禁用插件'})
list_plugins = OmegaPluginsManager.command('list', aliases={'插件列表'})


# 修改默认参数处理
@enable_plugin.args_parser
async def parse(bot: Bot, event: MessageEvent, state: T_State):
    args = event.get_plaintext().strip()
    if not args:
        await enable_plugin.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args
    if state[state["_current_key"]] == '取消':
        await enable_plugin.finish('操作已取消')


@enable_plugin.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    args = event.get_plaintext().strip()
    if args:
        state['plugin_name'] = args
    else:
        plugin_list = get_loaded_plugins()
        # 提示的时候仅显示有 matcher 的插件
        plugin_msg = '\n'.join([x.name for x in plugin_list if len(x.matcher) > 0])
        msg = f'当前已加载的插件有:\n\n{plugin_msg}'
        await enable_plugin.send(msg)


@enable_plugin.got('plugin_name', prompt='请输入需要启用的插件名称:')
async def handle_enable_plugin(bot: Bot, event: MessageEvent, state: T_State):
    plugin_name = state['plugin_name']
    plugin_list = [x.name for x in get_loaded_plugins()]
    if plugin_name not in plugin_list:
        await enable_plugin.reject('没有这个插件, 请重新输入需要启用的插件名称:\n取消操作请发送【取消】')

    result = await DBPlugin(plugin_name=plugin_name).update(enabled=1)
    if result.success():
        logger.info(f'OPM | Success enabled plugin {plugin_name} by user {event.user_id}')
        await enable_plugin.finish(f'启用插件 {plugin_name} 成功')
    else:
        logger.error(f'OPM | Failed to enable {plugin_name}, {result.info}')
        await enable_plugin.finish(f'启用插件 {plugin_name} 失败, 详细信息请参见日志')


# 修改默认参数处理
@disable_plugin.args_parser
async def parse(bot: Bot, event: MessageEvent, state: T_State):
    args = event.get_plaintext().strip()
    if not args:
        await disable_plugin.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args
    if state[state["_current_key"]] == '取消':
        await disable_plugin.finish('操作已取消')


@disable_plugin.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    args = event.get_plaintext().strip()
    if args:
        state['plugin_name'] = args
    else:
        plugin_list = get_loaded_plugins()
        # 提示的时候仅显示有 matcher 的插件
        plugin_msg = '\n'.join([x.name for x in plugin_list if len(x.matcher) > 0])
        msg = f'当前已加载的插件有:\n\n{plugin_msg}'
        await disable_plugin.send(msg)


@disable_plugin.got('plugin_name', prompt='请输入需要禁用的插件名称:')
async def handle_disable_plugin(bot: Bot, event: MessageEvent, state: T_State):
    plugin_name = state['plugin_name']
    plugin_list = [x.name for x in get_loaded_plugins()]
    if plugin_name not in plugin_list:
        await disable_plugin.reject('没有这个插件, 请重新输入需要禁用的插件名称:\n取消操作请发送【取消】')

    result = await DBPlugin(plugin_name=plugin_name).update(enabled=0)
    if result.success():
        logger.info(f'OPM | Success enabled plugin {plugin_name} by user {event.user_id}')
        await disable_plugin.finish(f'禁用插件 {plugin_name} 成功')
    else:
        logger.error(f'OPM | Failed to enable {plugin_name}, {result.info}')
        await disable_plugin.finish(f'禁用插件 {plugin_name} 失败, 详细信息请参见日志')


# 显示所有插件状态
@list_plugins.handle()
async def handle_list_plugins(bot: Bot, event: MessageEvent, state: T_State):
    # 只显示有 matcher 的插件信息
    plugin_list = [plugin.name for plugin in get_loaded_plugins() if len(plugin.matcher) > 0]

    # 获取插件启用状态
    enabled_plugins_result = await DBPlugin.list_plugins(enabled=1)
    disabled_plugins_result = await DBPlugin.list_plugins(enabled=0)

    if enabled_plugins_result.error or disabled_plugins_result.error:
        logger.error(f'OPM | Getting plugins info failed, '
                     f'enabled result: {enabled_plugins_result}, disabled result: {disabled_plugins_result}')
        await list_plugins.finish('获取插件信息失败, 详细信息请参见日志')

    enabled_plugins = '\n'.join(x for x in enabled_plugins_result.result if x in plugin_list)
    disabled_plugins = '\n'.join(x for x in disabled_plugins_result.result if x in plugin_list)

    text = f'已启用的插件:\n{"="*12}\n{enabled_plugins}\n\n\n被禁用的插件:\n{"="*12}\n{disabled_plugins}'
    text_img_result = await TextUtils(text=text).text_to_img()

    if text_img_result.error:
        logger.error(f'OPM | Generate plugins list image failed, {text_img_result.info}')
        await list_plugins.finish('生成插件信息失败, 详细信息请参见日志')

    img_seg = MessageSegment.image(file=pathlib.Path(text_img_result.result).as_uri())
    await list_plugins.finish(img_seg)
