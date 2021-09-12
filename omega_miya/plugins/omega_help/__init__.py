from nonebot import on_command
from nonebot.plugin.export import export
from nonebot.plugin import get_loaded_plugins
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent
from nonebot.adapters.cqhttp.permission import GROUP, PRIVATE_FRIEND
from omega_miya.utils.omega_plugin_utils import init_export, init_processor_state, PluginCoolDown


# Custom plugin usage text
__plugin_custom_name__ = '帮助'
__plugin_usage__ = r'''【帮助】
一个简单的帮助插件

**Permission**
Friend Private
Command & Lv.10
or AuthNode

**AuthNode**
basic

**Usage**
/帮助 [插件名]'''


# Init plugin export
init_export(export(), __plugin_custom_name__, __plugin_usage__)


# 注册事件响应器
bot_help = on_command(
    'help',
    aliases={'Help', '帮助'},
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='help',
        command=True,
        level=10,
        cool_down=[
            PluginCoolDown(PluginCoolDown.user_type, 300),
            PluginCoolDown(PluginCoolDown.group_type, 60)
        ]),
    permission=GROUP | PRIVATE_FRIEND,
    priority=10,
    block=True)


@bot_help.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    # 获取设置了名称的插件列表
    plugins = list(filter(lambda p: set(p.export.keys()).issuperset({'custom_name', 'usage'}), get_loaded_plugins()))
    if not plugins:
        await bot_help.finish('暂时没有可用的插件QAQ')
    state['plugin_list'] = plugins
    # 首次发送命令时跟随的参数，例：/天气 上海，则args为上海
    args = str(event.get_plaintext()).strip().lower().split()
    if args:
        # 如果用户发送了参数则直接赋值
        state['plugin_name'] = args[0]
    else:
        # 如果用户没有发送参数, 则发送功能列表并结束此命令
        plugins_list = '\n'.join(p.export.custom_name for p in plugins)
        await bot_help.finish(f'我现在支持的插件有: \n\n{plugins_list}\n\n'
                              f'注意: 群组权限等级未达到要求的, 或非好友或未启用私聊功能的命令不会被响应\n\n'
                              f'输入"/help [插件]"即可查看插件详情及帮助')


@bot_help.got('plugin_name', prompt='你想查询哪个插件的用法呢？')
async def handle_plugin_name(bot: Bot, event: MessageEvent, state: T_State):
    plugin_custom_name = state["plugin_name"]
    # 如果发了参数则发送相应命令的使用帮助
    for p in state['plugin_list']:
        if p.export.custom_name.lower() == plugin_custom_name:
            await bot_help.finish(p.export.usage)
    await bot_help.finish('没有这个插件呢QAQ, 请检查输入插件名是否正确~')
