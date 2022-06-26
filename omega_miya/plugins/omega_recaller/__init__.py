"""
@Author         : Ailitonia
@Date           : 2021/07/17 22:36
@FileName       : omega_recaller.py
@Project        : nonebot2_miya 
@Description    : 快速撤回 bot 发送的消息
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import logger
from nonebot.plugin import on_command
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11.permission import GROUP_OWNER, GROUP_ADMIN
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent

from omega_miya.service import init_processor_state
from omega_miya.utils.process_utils import run_async_catching_exception
from omega_miya.onebot_api import GoCqhttpBot


# Custom plugin usage text
__plugin_custom_name__ = '快速撤回'
__plugin_usage__ = r'''【快速撤回】
快速撤回 bot 发送的消息
仅限群管或超管使用

用法:
回复需撤回的消息
/撤回'''


self_recall = on_command(
    'recall',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='SelfRecall', level=0),
    aliases={'撤回'},
    permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER,
    priority=10,
    block=True
)


@self_recall.handle()
async def handle_recall(bot: Bot, event: MessageEvent):
    # 特别处理管理员撤回bot发送的消息
    if event.reply:
        if event.reply.sender.user_id == event.self_id:
            recall_msg_id = event.reply.message_id
            result = await run_async_catching_exception(GoCqhttpBot(bot=bot).delete_msg)(message_id=recall_msg_id)

            if isinstance(result, Exception):
                logger.error(f'Self Recall | User({event.user_id}) 撤回Bot消息失败, {result}')
                await self_recall.finish('撤回消息部分或全部失败了QAQ', at_sender=True)
            else:
                logger.success(f'Self Recall | User({event.user_id}) 撤回了Bot消息: {recall_msg_id}')
