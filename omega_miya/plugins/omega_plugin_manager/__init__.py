"""
@Author         : Ailitonia
@Date           : 2021/09/12 14:02
@FileName       : __init__.py.py
@Project        : nonebot2_miya 
@Description    : 插件管理器
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.log import logger
from nonebot.plugin import CommandGroup, get_plugin, get_loaded_plugins, PluginMetadata
from nonebot.rule import to_me
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11.message import Message
from nonebot.adapters.onebot.v11.message import MessageSegment
from nonebot.params import CommandArg, ArgStr

from omega_miya.database import Plugin
from omega_miya.service import init_processor_state
from omega_miya.utils.text_utils import TextUtils
from omega_miya.utils.process_utils import run_async_catching_exception


__plugin_meta__ = PluginMetadata(
    name="插件管理",
    description="【OmegaPluginManager 插件管理器】\n"
                "管理启用和禁用插件\n"
                "仅限管理员使用",
    usage="/OPM.[管理操作] [插件名]\n"
          "或使用别名:\n"
          "/启用插件 [插件名]\n"
          "/禁用插件 [插件名]\n"
          "/插件列表\n\n"
          "可用管理操作:\n"
          "enable: 启用插件\n"
          "disable: 禁用插件\n"
          "list: 显示插件列表",
    extra={"author": "Ailitonia"},
)


_log_prefix: str = '<lc>OmegaPluginManager</lc> | '


# 注册事件响应器
OmegaPluginsManager = CommandGroup(
    'OPM',
    rule=to_me(),
    state=init_processor_state(name='OmegaPluginManager', enable_processor=False),
    permission=SUPERUSER,
    priority=10,
    block=True
)

enable_plugin = OmegaPluginsManager.command('enable', aliases={'启用插件'})
disable_plugin = OmegaPluginsManager.command('disable', aliases={'禁用插件'})
list_plugins = OmegaPluginsManager.command('list', aliases={'插件列表'})


@enable_plugin.handle()
async def handle_parse_plugin_name(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    plugin_name = cmd_arg.extract_plain_text().strip()
    if plugin_name:
        state.update({'plugin_name': plugin_name})
    else:
        plugin_list = get_loaded_plugins()
        # 提示的时候仅显示有 matcher 的插件
        plugin_msg = '\n'.join([x.name for x in plugin_list if len(x.matcher) > 0])
        msg = f'当前已加载的插件有:\n\n{plugin_msg}'
        await enable_plugin.send(msg)


@enable_plugin.got('plugin_name', prompt='请输入需要启用的插件名称:')
async def handle_enable_plugin(plugin_name: str = ArgStr('plugin_name')):
    """处理需要启用插件操作"""
    plugin_name = plugin_name.strip()
    if plugin_name not in (x.name for x in get_loaded_plugins()):
        await enable_plugin.reject('没有这个插件, 请检查并重新输入需要启用的插件名称:')

    plugin = Plugin(plugin_name=plugin_name, module_name=get_plugin(name=plugin_name).module_name)
    result = await run_async_catching_exception(plugin.add_upgrade_unique_self)(enabled=1, info='Enabled by OPM')
    if isinstance(result, Exception) or result.error:
        logger.opt(colors=True).error(f'{_log_prefix}Failed to enable plugin {plugin_name}, {result}')
        await enable_plugin.finish(f'启用插件 {plugin_name} 失败, 详细信息请参见日志')
    else:
        logger.opt(colors=True).success(f'{_log_prefix}Success to enable plugin {plugin_name}')
        await enable_plugin.finish(f'启用插件 {plugin_name} 成功')


@disable_plugin.handle()
async def handle_parse_plugin_name(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    plugin_name = cmd_arg.extract_plain_text().strip()
    if plugin_name:
        state.update({'plugin_name': plugin_name})
    else:
        plugin_list = get_loaded_plugins()
        # 提示的时候仅显示有 matcher 的插件
        plugin_msg = '\n'.join([x.name for x in plugin_list if len(x.matcher) > 0])
        msg = f'当前已加载的插件有:\n\n{plugin_msg}'
        await disable_plugin.send(msg)


@disable_plugin.got('plugin_name', prompt='请输入需要禁用的插件名称:')
async def handle_disable_plugin(plugin_name: str = ArgStr('plugin_name')):
    """处理需要禁用插件操作"""
    plugin_name = plugin_name.strip()
    if plugin_name not in (x.name for x in get_loaded_plugins()):
        await disable_plugin.reject('没有这个插件, 请检查并重新输入需要禁用的插件名称:')

    plugin = Plugin(plugin_name=plugin_name, module_name=get_plugin(name=plugin_name).module_name)
    result = await run_async_catching_exception(plugin.add_upgrade_unique_self)(enabled=0, info='Disabled by OPM')
    if isinstance(result, Exception) or result.error:
        logger.opt(colors=True).error(f'{_log_prefix}Failed to disable plugin {plugin_name}, {result}')
        await disable_plugin.finish(f'禁用插件 {plugin_name} 失败, 详细信息请参见日志')
    else:
        logger.opt(colors=True).success(f'{_log_prefix}Success to disable plugin {plugin_name}')
        await disable_plugin.finish(f'禁用插件 {plugin_name} 成功')


@list_plugins.handle()
async def handle_list_plugins():
    # 只显示有 matcher 的插件信息
    plugin_list = [plugin.name for plugin in get_loaded_plugins() if len(plugin.matcher) > 0]

    # 获取插件启用状态
    enabled_result = await run_async_catching_exception(Plugin.query_by_enabled)(enabled=1)
    disabled_result = await run_async_catching_exception(Plugin.query_by_enabled)(enabled=0)

    if (isinstance(enabled_result, Exception)
            or isinstance(disabled_result, Exception)
            or enabled_result.error
            or disabled_result.error):
        logger.opt(colors=True).error(f'{_log_prefix}Getting plugins status failed, '
                                      f'enabled result: {enabled_result},\ndisabled result: {disabled_result}')
        await list_plugins.finish('获取插件信息失败, 详细信息请参见日志')

    enabled_plugins = '\n'.join(_desc(x.plugin_name) for x in enabled_result.result if x.plugin_name in plugin_list)
    disabled_plugins = '\n'.join(_desc(x.plugin_name) for x in disabled_result.result if x.plugin_name in plugin_list)

    text = f'已启用的插件:\n{"="*12}\n{enabled_plugins}\n\n\n已禁用的插件:\n{"="*12}\n{disabled_plugins}'
    text_img = await run_async_catching_exception(TextUtils(text=text).text_to_img)()

    if isinstance(text_img, Exception):
        logger.opt(colors=True).error(f'{_log_prefix}Generate plugins list image failed, {text_img}')
        await list_plugins.finish('生成插件信息失败, 详细信息请参见日志')

    img_seg = MessageSegment.image(file=text_img.file_uri)
    await list_plugins.finish(img_seg)


def _desc(plugin_name: str) -> str:
    """根据 plugin name 获取插件自定义名称"""
    plugin = get_plugin(name=plugin_name)
    if plugin is None:
        return plugin_name
    elif plugin.metadata is None:
        return plugin_name

    return f'{plugin_name}({plugin.metadata.name})'
