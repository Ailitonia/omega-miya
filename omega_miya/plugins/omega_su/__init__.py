"""
@Author         : Ailitonia
@Date           : 2021/05/31 21:14
@FileName       : omega_su.py
@Project        : nonebot2_miya
@Description    : go-cqhttp 适配专用, 用于人工同时登陆 bot 账号时将自己发送的消息转成 message 类型便于执行命令,
                  bot 账号发送命令前添加 !SU 即可将消息事件由 message_sent 转换为对应 MessageEvent,
                  为避免命令恶意执行, bot 不能为 superuser
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot import logger
from nonebot.plugin import on, on_command
from nonebot.typing import T_State
from nonebot.message import handle_event
from nonebot.rule import to_me
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.message import Message
from nonebot.adapters.onebot.v11.event import GroupMessageEvent, PrivateMessageEvent
from nonebot.params import CommandArg, ArgStr

from omega_miya.service import init_processor_state
from omega_miya.service.gocqhttp_self_sent_patch import MessageSentEvent, SU_SELF_SENT


_SU_TAG: bool = False


# Custom plugin usage text
__plugin_custom_name__ = '自调用消息'
__plugin_usage__ = r'''【OmegaSu 自调用消息插件】
让人工登陆机器人账号时可以通过特殊命令来自己调用自己

用法:
/su <on|off>

人工登录 bot 使用命令:
!SU [command]'''


# 注册事件响应器
su_manager = on_command(
    'su',
    rule=to_me(),
    state=init_processor_state(name='SuManager', enable_processor=False),
    aliases={'SU', 'Su'},
    permission=SUPERUSER,
    priority=10,
    block=True
)


@su_manager.handle()
async def handle_parse_switch(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    switch = cmd_arg.extract_plain_text().strip().lower()
    if switch in ('on', 'off'):
        state.update({'switch': switch})


@su_manager.got('switch', prompt='启用或关闭特权命令:\n【ON/OFF】')
async def handle_switch(switch: str = ArgStr('switch')):
    global _SU_TAG

    switch = switch.strip().lower()
    match switch:
        case 'on':
            _SU_TAG = True
            logger.info(f'SuManager: 特权命令已启用, 下一条 !SU 命令将以管理员身份执行')
            await su_manager.finish(f'特权命令已启用, 下一条 !SU 命令将以管理员身份执行')
        case 'off':
            _SU_TAG = False
            logger.info(f'SuManager: 特权命令已禁用')
            await su_manager.finish(f'特权命令已禁用')
        case _:
            await su_manager.reject('没有这个选项哦, 选择【ON/OFF】以启用或关闭特权命令:')
            return


su = on(
    type='message_sent',
    state=init_processor_state(name='Su', enable_processor=False),
    permission=SU_SELF_SENT,
    priority=100,
    block=False
)


@su.handle()
async def handle_su(bot: Bot, event: MessageSentEvent):
    if str(event.self_id) not in bot.config.superusers and event.message and event.message[0].type == 'text':
        if event.message[0].data['text'].startswith('!SU'):
            event.message[0].data["text"] = event.message[0].data["text"].removeprefix('!SU').lstrip()
            event.raw_message = str(event.message)
            event.post_type = 'message'

            global _SU_TAG
            if _SU_TAG and list(bot.config.superusers):
                event.user_id = int(list(bot.config.superusers)[0])
                logger.info(f'OmegaSu | 已启用超级管理员权限, 赋权: {event.user_id}')

            if event.group_id != 0:
                new_event = GroupMessageEvent.parse_obj(event)
            else:
                new_event = PrivateMessageEvent.parse_obj(event)

            try:
                logger.info(f'OmegaSu | New event {new_event} will be handling')
                await handle_event(bot=bot, event=new_event)
            except Exception as e:
                logger.error(f'OmegaSu | Handle new event failed, {e}, origin event: {event}, new event: {new_event}')
            finally:
                _SU_TAG = False
                logger.info('OmegaSu | Event has been handled, SU_TAG is reset')
