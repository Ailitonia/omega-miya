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

from typing import Annotated, Literal

from nonebot.adapters.onebot.v11 import (
    Bot as OneBotV11Bot,
    GroupMessageEvent as OneBotV11GroupMessageEvent,
    GroupUploadNoticeEvent as OneBotV11GroupUploadNoticeEvent,
)
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.params import ArgStr, Depends
from nonebot.permission import SUPERUSER
from nonebot.plugin import on_command, on_notice

from src.params.handler import get_command_str_single_arg_parser_handler
from src.params.rule import event_has_permission_node
from src.service import OmegaMatcherInterface as OmMI, enable_processor_state
from .helpers import ZhouChecker, download_file, upload_result_file

_ZHOUSHEN_HIME_CUSTOM_MODULE_NAME: Literal['Omega.ZhoushenHime'] = 'Omega.ZhoushenHime'
"""固定写入数据库的 module name 参数"""
_ZHOUSHEN_HIME_CUSTOM_PLUGIN_NAME: Literal['zhoushen_hime'] = 'zhoushen_hime'
"""固定写入数据库的 plugin name 参数"""
_ENABLE_ZHOUSHEN_HIME_NODE: Literal['enable_zhoushen_hime'] = 'enable_zhoushen_hime'
"""启用审轴姬的权限节点"""


@on_command(
    'zhoushen_hime_manager',
    aliases={'审轴姬', '审轴机'},
    permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER,
    handlers=[get_command_str_single_arg_parser_handler('switch')],
    priority=20,
    block=True,
    state=enable_processor_state(name='ZhoushenHimeManager', level=10, auth_node='zhoushen_hime_manager'),
).got('switch', prompt='启用或关闭审轴姬:\n【ON/OFF】')
async def handle_zhoushen_hime_manager(
        __bot: OneBotV11Bot,
        __event: OneBotV11GroupMessageEvent,
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        switch: Annotated[str, ArgStr('switch')],
) -> None:
    switch = switch.strip().lower()

    match switch:
        case 'on':
            switch_coro = interface.entity.set_auth_setting(
                module=_ZHOUSHEN_HIME_CUSTOM_MODULE_NAME, plugin=_ZHOUSHEN_HIME_CUSTOM_PLUGIN_NAME,
                node=_ENABLE_ZHOUSHEN_HIME_NODE, available=1
            )
        case 'off':
            switch_coro = interface.entity.set_auth_setting(
                module=_ZHOUSHEN_HIME_CUSTOM_MODULE_NAME, plugin=_ZHOUSHEN_HIME_CUSTOM_PLUGIN_NAME,
                node=_ENABLE_ZHOUSHEN_HIME_NODE, available=0
            )
        case _:
            await interface.finish_reply('无效选项, 请输入【ON/OFF】以启用或关闭审轴姬, 操作已取消')

    try:
        await switch_coro
        logger.success(f"ZhoushenHimeManager | {interface.entity} 设置审轴姬功能开关为 {switch} 成功")
        await interface.send_reply(f'已设置审轴姬功能开关为 {switch}!')
    except Exception as e:
        logger.error(f"ZhoushenHimeManager | {interface.entity} 设置审轴姬功能开关为 {switch} 失败, {e}")
        await interface.send_reply(f'设置审轴姬功能开关失败, 请稍后重试或联系管理员处理')


@on_notice(
    rule=event_has_permission_node(
        module=_ZHOUSHEN_HIME_CUSTOM_MODULE_NAME,
        plugin=_ZHOUSHEN_HIME_CUSTOM_PLUGIN_NAME,
        node=_ENABLE_ZHOUSHEN_HIME_NODE
    ),
    state=enable_processor_state(name='ZhoushenHime', enable_processor=False, echo_processor_result=False),
    priority=100,
    block=False
).handle()
async def handle_zhoushen_hime_process(bot: OneBotV11Bot, event: OneBotV11GroupUploadNoticeEvent, matcher: Matcher):
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

    try:
        ass_file = await download_file(url=file_url, file_name=file_name)
    except Exception as e:
        logger.error(f'ZhoushenHime | 下载文件失败, {e}')
        await matcher.finish()

    await matcher.send('你刚刚上传了一份轴呢, 让我来帮你看看吧!', at_sender=True)

    try:
        handle_result = await ZhouChecker(file=ass_file, flash_mode=True).handle(auto_style=True)
    except Exception as e:
        logger.error(f'ZhoushenHime | 处理时轴文件失败, {e}')
        await matcher.finish('审轴姬处理轴时出错了QAQ, 请稍后重试或联系管理员处理')

    # 没有检查到错误的话就直接结束
    if handle_result.character_count + handle_result.flash_count + handle_result.overlap_count == 0:
        await matcher.finish('看完了! 没有发现符号错误、疑问文本、叠轴和闪轴, 真棒~')

    try:
        await upload_result_file(group_id=event.group_id, bot=bot, file_data=handle_result)
    except Exception as e:
        logger.error(f'ZhoushenHime | 上传结果时时发生了意外的错误, {e}')
        await matcher.finish('审轴姬上传审轴结果失败了QAQ, 请稍后重试或联系管理员处理')

    result_msg = f'看完了! 以下是结果:\n\n符号及疑问文本共{handle_result.character_count}处\n' \
                 f'叠轴共{handle_result.overlap_count}处\n闪轴共{handle_result.flash_count}处\n\n锤轴结果已上传, 请参考修改哟~'
    await matcher.finish(result_msg)


__all__ = []
