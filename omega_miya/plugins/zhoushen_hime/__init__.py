"""
@Author         : Ailitonia
@Date           : 2021/12/24 16:09
@FileName       : zhoushen_hime.py
@Project        : nonebot2_miya
@Description    : 审轴姬
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm

要求go-cqhttp v0.9.40以上
"""

from typing import Literal
from nonebot import on_command, on_notice, logger
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.message import Message
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.adapters.onebot.v11.event import GroupMessageEvent, GroupUploadNoticeEvent
from nonebot.params import CommandArg, ArgStr

from omega_miya.database import InternalBotGroup
from omega_miya.service import init_processor_state
from omega_miya.utils.process_utils import run_async_catching_exception
from omega_miya.utils.rule import group_has_permission_node

from .utils import ZhouChecker, download_file, upload_result_file


# Custom plugin usage text
__plugin_custom_name__ = '自动审轴姬'
__plugin_usage__ = r'''【自动审轴姬】
检测群内上传文件并自动锤轴
仅限群聊使用

用法:
仅限群管理员使用:
/审轴姬 <ON|OFF>'''


_ZHOUSHEN_HIME_CUSTOM_MODULE_NAME: Literal['Omega.ZhoushenHime'] = 'Omega.ZhoushenHime'
"""固定写入数据库的 module name 参数"""
_ZHOUSHEN_HIME_CUSTOM_PLUGIN_NAME: Literal['zhoushen_hime'] = 'zhoushen_hime'
"""固定写入数据库的 plugin name 参数"""
_ENABLE_ZHOUSHEN_HIME_NODE: Literal['enable_zhoushen_hime'] = 'enable_zhoushen_hime'
"""启用审轴姬的权限节点"""


# 注册事件响应器
ZhoushenHimeManager = on_command(
    'ZhoushenHimeManager',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='ZhoushenHimeManager', level=10, auth_node='zhoushen_hime_manager'),
    aliases={'审轴姬', '审轴机'},
    permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER,
    priority=10,
    block=True
)


@ZhoushenHimeManager.handle()
async def handle_parse_switch(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    switch = cmd_arg.extract_plain_text().strip().lower()
    if switch in ('on', 'off'):
        state.update({'switch': switch})


@ZhoushenHimeManager.got('switch', prompt='启用或关闭审轴姬:\n【ON/OFF】')
async def handle_switch(bot: Bot, matcher: Matcher, event: GroupMessageEvent, switch: str = ArgStr('switch')):
    switch = switch.strip().lower()
    group_id = str(event.group_id)
    group = InternalBotGroup(bot_id=bot.self_id, parent_id=bot.self_id, entity_id=group_id)

    match switch:
        case 'on':
            switch_result = await run_async_catching_exception(group.set_auth_setting)(
                module=_ZHOUSHEN_HIME_CUSTOM_MODULE_NAME, plugin=_ZHOUSHEN_HIME_CUSTOM_PLUGIN_NAME,
                node=_ENABLE_ZHOUSHEN_HIME_NODE, available=1
            )
        case 'off':
            switch_result = await run_async_catching_exception(group.set_auth_setting)(
                module=_ZHOUSHEN_HIME_CUSTOM_MODULE_NAME, plugin=_ZHOUSHEN_HIME_CUSTOM_PLUGIN_NAME,
                node=_ENABLE_ZHOUSHEN_HIME_NODE, available=0
            )
        case _:
            await matcher.reject('没有这个选项哦, 选择【ON/OFF】以启用或关闭审轴姬:')
            return

    if isinstance(switch_result, Exception) or switch_result.error:
        logger.error(f"ZhoushenHimeManager | Group({group_id}) 设置审轴姬功能开关为 {switch} 失败, {switch_result}")
        await matcher.finish(f'设置审轴姬功能开关失败QAQ, 请联系管理员处理')
    else:
        logger.success(f"ZhoushenHimeManager | Group({group_id}) 设置审轴姬功能开关为 {switch} 成功")
        await matcher.finish(f'已设置审轴姬功能开关为 {switch}!')


ZhoushenHime = on_notice(
    rule=group_has_permission_node(
        module=_ZHOUSHEN_HIME_CUSTOM_MODULE_NAME,
        plugin=_ZHOUSHEN_HIME_CUSTOM_PLUGIN_NAME,
        node=_ENABLE_ZHOUSHEN_HIME_NODE
    ),
    state=init_processor_state(name='ZhoushenHime', enable_processor=False, echo_processor_result=False),
    priority=100,
    block=False
)


@ZhoushenHime.handle()
async def hime_handle(bot: Bot, event: GroupUploadNoticeEvent, matcher: Matcher):
    file_name = event.file.name
    file_url = getattr(event.file, 'url')

    # 不响应自己上传的文件
    if int(event.user_id) == int(bot.self_id):
        await matcher.finish()

    if file_name.split('.')[-1] not in ['ass', 'ASS']:
        await matcher.finish()

    # 只处理文件名中含"未校""待校""需校"的文件
    if not any(key in file_name for key in ['未校', '待校', '需校']):
        await matcher.finish()

    ass_file = await download_file(url=file_url, file_name=file_name)
    if isinstance(ass_file, Exception):
        logger.error(f'ZhoushenHime | 下载文件失败, {ass_file}')
        await matcher.finish()

    await matcher.send('你刚刚上传了一份轴呢, 让我来帮你看看吧!', at_sender=True)

    checker = ZhouChecker(file=ass_file, flash_mode=True)
    handle_result = await run_async_catching_exception(checker.handle)(auto_style=True)
    if isinstance(handle_result, Exception):
        logger.error(f'ZhoushenHime | 处理时轴文件失败, {handle_result}')
        await matcher.finish('审轴姬出错了QAQ')

    # 没有检查到错误的话就直接结束
    if handle_result.character_count + handle_result.flash_count + handle_result.overlap_count == 0:
        await matcher.finish('看完了! 没有发现符号错误、疑问文本、叠轴和闪轴, 真棒~')

    upload_result = await upload_result_file(group_id=event.group_id, bot=bot, result_data=handle_result)
    if isinstance(upload_result, Exception):
        logger.error(f'ZhoushenHime | 上传结果时时发生了意外的错误, {upload_result}')
        await matcher.finish('审轴姬出错了QAQ')

    result_msg = f'看完了! 以下是结果:\n\n符号及疑问文本共{handle_result.character_count}处\n' \
                 f'叠轴共{handle_result.overlap_count}处\n闪轴共{handle_result.flash_count}处\n\n锤轴结果已上传, 请参考修改哟~'
    await matcher.finish(result_msg)
