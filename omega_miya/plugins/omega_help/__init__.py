from nonebot import on_command
from nonebot.plugin import get_loaded_plugins
from nonebot.typing import T_State
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.message import Message
from nonebot.adapters.onebot.v11.event import MessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP, PRIVATE_FRIEND
from nonebot.params import CommandArg, ArgStr

from omega_miya.service.gocqhttp_guild_patch.permission import GUILD
from omega_miya.service.omega_processor_tools import init_processor_state, parse_processor_state


# Custom plugin usage text
__plugin_custom_name__ = '帮助'
__plugin_usage__ = r'''【帮助】
一个简单的帮助插件

用法:
/帮助 [插件名]'''


# 注册事件响应器
bot_help = on_command(
    'help',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='help', level=10),
    aliases={'帮助'},
    permission=GROUP | GUILD | PRIVATE_FRIEND,
    priority=10,
    block=True
)


@bot_help.handle()
async def handle_parse_plugin_name(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    plugin_name = cmd_arg.extract_plain_text().strip()
    if plugin_name:
        state.update({'plugin_name': plugin_name})
    else:
        state.update({'plugin_name': ''})


@bot_help.got('plugin_name', prompt='你想查询哪个插件的用法呢？')
async def handle_help_message(bot: Bot, event: MessageEvent, plugin_name: str = ArgStr('plugin_name')):
    plugin_name = plugin_name.strip()
    if not plugin_name:
        help_msg = await get_all_plugins_desc()
        await bot_help.finish(help_msg)
    else:
        is_superuser = await SUPERUSER(bot=bot, event=event)
        help_msg = await get_plugin_desc(plugin_name=plugin_name, for_superuser=is_superuser)
        await bot_help.finish(help_msg)


async def get_all_plugins_desc() -> str:
    """获取全部配置了自定义信息的插件信息"""
    plugin_custom_name = '\n'.join(str(name) for name in (
        getattr(plugin.module, '__plugin_custom_name__', None) for plugin in get_loaded_plugins()
    ) if name is not None)
    return f'现在已安装的插件有: \n\n{plugin_custom_name}\n\n输入"/help [插件名]"即可查看插件详情及帮助'


async def get_plugin_desc(plugin_name: str, *, for_superuser: bool = False) -> str:
    """获取指定的配置了自定义信息的插件信息"""
    for plugin in get_loaded_plugins():
        plugin_custom_name = getattr(plugin.module, '__plugin_custom_name__', None)
        if plugin_name == plugin_custom_name:
            plugin_usage = getattr(plugin.module, '__plugin_usage__', None)
            if for_superuser:
                processor_info = '\n'.join(
                    f'\n[{s.name}]\nLevel: {s.level if s.level < 4294967296 else "Unlimited"}/Node: {s.auth_node}\n'
                    f'ExtraNode: {", ".join(s.extra_auth_node) if s.extra_auth_node else None}\nCooldown: {s.cool_down}'
                    for s in (parse_processor_state(m._default_state) for m in plugin.matcher)
                    if s.name and s.enable_processor
                )
                desc_msg = f'{plugin_usage}\n\n可配置权限及冷却信息:{processor_info if processor_info else None}'
                break
            else:
                processor_info = '\n'.join(
                    f'\n[{s.name}]\n需求等级: {s.level if s.level < 4294967296 else "Unlimited"}\n'
                    f'命令冷却时间: {s.cool_down}'
                    for s in (parse_processor_state(m._default_state) for m in plugin.matcher)
                    if s.name and s.enable_processor
                )
                desc_msg = f'{plugin_usage}\n\n需要的权限等级和命令冷却时间:{processor_info if processor_info else None}'
                break
    else:
        desc_msg = f'没有{plugin_name}这个插件呢QAQ, 请检查输入插件名是否正确'
    return desc_msg
