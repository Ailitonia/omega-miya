from nonebot import on_command, logger
from nonebot.rule import to_me
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.message import Message
from nonebot.params import CommandArg, ArgStr

from omega_miya.database import InternalBotGroup
from omega_miya.service import init_processor_state
from omega_miya.onebot_api import GoCqhttpBot
from omega_miya.utils.process_utils import run_async_catching_exception, semaphore_gather


# Custom plugin usage text
__plugin_custom_name__ = '公告'
__plugin_usage__ = r'''【公告插件】
快速批量向启用了bot的群组发送通知公告

用法:
/公告 [公告内容]'''


# 注册事件响应器
announce = on_command(
    'announce',
    rule=to_me(),
    state=init_processor_state(name='announce', enable_processor=False),
    aliases={'公告'},
    permission=SUPERUSER,
    priority=10,
    block=True
)


@announce.handle()
async def handle_parse_announce_content(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    content = cmd_arg.extract_plain_text().strip()
    if content:
        state.update({'content': content})


@announce.got('content', prompt='请输入公告内容:')
async def handle_help_message(bot: Bot, content: str = ArgStr('content')):
    content = content.strip()
    gocq_bot = GoCqhttpBot(bot=bot)
    group_list = await run_async_catching_exception(gocq_bot.get_group_list)()
    if isinstance(group_list, Exception):
        logger.error(f'Announce | 获取群组列表失败, {group_list}')
        await announce.finish('获取群组列表失败')

    send_group = []
    for group in group_list:
        _group = InternalBotGroup(bot_id=bot.self_id, parent_id=bot.self_id, entity_id=group.group_id)
        group_global_permission_result = await run_async_catching_exception(_group.check_global_permission)()
        if group_global_permission_result is True:
            send_group.append(group.group_id)

    send_tasks = [run_async_catching_exception(gocq_bot.send_group_msg)(group_id=group_id, message=content)
                  for group_id in send_group]
    send_result = await semaphore_gather(tasks=send_tasks, semaphore_num=1)

    if any(isinstance(x, BaseException) for x in send_result):
        logger.warning(f'Announce | 公告发送完成, 发送群组: {", ".join(send_group)}, 部分群组发送失败')
        await announce.finish('公告批量发送完成, 部分群组发送失败')
    else:
        logger.success(f'Announce | 公告发送完成, 已发送群组: {", ".join(send_group)}')
        await announce.finish('公告批量发送完成, 所有群组均已发送成功')
