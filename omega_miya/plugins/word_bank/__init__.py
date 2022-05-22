"""
@Author         : Ailitonia
@Date           : 2021/12/12 21:49
@FileName       : word_bank.py
@Project        : nonebot2_miya 
@Description    : 使用模糊匹配的自动问答插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import MatcherGroup, logger
from nonebot.typing import T_State
from nonebot.rule import to_me
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11.permission import GROUP, GROUP_ADMIN, GROUP_OWNER
from nonebot.adapters.onebot.v11.message import Message
from nonebot.adapters.onebot.v11.event import MessageEvent, GroupMessageEvent
from nonebot.params import CommandArg, ArgStr, Arg, EventMessage


from omega_miya.service import init_processor_state
from omega_miya.service.gocqhttp_guild_patch import GuildMessageEvent
from omega_miya.service.gocqhttp_guild_patch.permission import GUILD

from .word_bank import WordBankManager, WordBankMatcher


# Custom plugin usage text
__plugin_custom_name__ = '自动问答'
__plugin_usage__ = r'''【自动问答】
使用模糊匹配的轻量化问答插件
仅限群聊使用

用法:
@Bot [关键词]
若匹配成功则会回复

仅限群管理员使用:
/添加问答
/删除问答
/问答列表'''


# 注册事件响应器
WordBank = MatcherGroup(
    type='message',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='word_bank',
        level=10,
        auth_node='word_bank'
    ),
    permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER,
    priority=10,
    block=True
)


set_word_bank = WordBank.on_command('添加问答', aliases={'设置问答'})


@set_word_bank.got('key_word', prompt='请输入问题文本:')
@set_word_bank.got('reply', prompt='请输入回答内容:')
async def handle_word_bank(matcher: Matcher, event: GroupMessageEvent | GuildMessageEvent,
                           key_word: str = ArgStr('key_word'), reply: Message = Arg('reply')):
    key_word = key_word.strip()
    if not key_word:
        await matcher.reject_arg('key_word', '问题文本不能为空, 请重新输入:')

    if not reply:
        await matcher.reject_arg('reply', '回答消息不能为空, 请重新输入:')

    result = await WordBankManager(event=event, key_word=key_word).set_rule(reply=reply)
    if isinstance(result, Exception) or result.error:
        logger.error(f'WordBank | 添加问答失败失败, {result}')
        await matcher.finish('添加问答失败了QAQ, 请稍后再试或联系管理员处理')
    else:
        await matcher.finish(f'已成功添加问答:\n\n{key_word}')


del_word_bank = WordBank.on_command('删除问答', aliases={'移除问答'})


@del_word_bank.handle()
async def handle_parse_key_word(event: GroupMessageEvent | GuildMessageEvent, matcher: Matcher, state: T_State,
                                cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    key_word = cmd_arg.extract_plain_text().strip()
    if key_word:
        state.update({'key_word': key_word})
    else:
        exist_word_bank = await WordBankManager.list_rule(event=event)
        if isinstance(exist_word_bank, Exception):
            logger.error(f'WordBank | 获取({event})已配置问答失败, {exist_word_bank}')
            await matcher.finish('获取已配置问答失败QAQ, 请稍后再试或联系管理员处理')
        elif not exist_word_bank:
            await matcher.finish(f'当前没有已配置问答')
        else:
            exist_text = '\n'.join(exist_word_bank)
            await matcher.send(f'当前已配置问答:\n\n{exist_text}')


@del_word_bank.got('key_word', prompt='请输入想要删除的问答:')
async def handle_delete_word_bank(event: GroupMessageEvent | GuildMessageEvent, matcher: Matcher,
                                  key_word: str = ArgStr('key_word')):
    exist_word_bank = await WordBankManager.list_rule(event=event)
    if isinstance(exist_word_bank, Exception):
        logger.error(f'WordBank | 获取({event})已配置问答失败, {exist_word_bank}')
        await matcher.finish('获取已配置问答失败QAQ, 请稍后再试或联系管理员处理')

    for k in exist_word_bank:
        if key_word == k:
            break
    else:
        exist_text = '\n'.join(exist_word_bank)
        await matcher.reject(f'当前没有配置这个问答哦, 请在已配置问答中选择并重新输入:\n\n{exist_text}')
        return

    delete_result = await WordBankManager(event=event, key_word=key_word).delete_rule()
    if isinstance(delete_result, Exception) or delete_result.error:
        logger.error(f"WordBank | 删除问答失败, {delete_result}")
        await matcher.finish(f'删除问答失败了QAQ, 发生了意外的错误, 请联系管理员处理')
    else:
        await matcher.finish(f'已成功删除问答:\n\n{key_word}')


list_word_bank = WordBank.on_command('问答列表', aliases={'查看问答'})


@list_word_bank.handle()
async def handle_list_word_bank(event: GroupMessageEvent | GuildMessageEvent, matcher: Matcher):
    exist_word_bank = await WordBankManager.list_rule(event=event)
    if isinstance(exist_word_bank, Exception):
        logger.error(f'WordBank | 获取({event})已配置问答失败, {exist_word_bank}')
        await matcher.finish('获取已配置问答失败QAQ, 请稍后再试或联系管理员处理')

    exist_text = '\n'.join(exist_word_bank)
    await matcher.finish(f'当前已配置问答:\n\n{exist_text}')


word_bank_matcher = WordBank.on_message(
    rule=to_me(),
    permission=GROUP | GUILD,
    priority=100,
    block=False
)


@word_bank_matcher.handle()
async def handle_word_bank_matcher(event: MessageEvent, matcher: Matcher, message: Message = EventMessage()):
    match_result = await WordBankMatcher(message=message, event=event).match()
    if isinstance(match_result, Exception):
        logger.error(f'WordBankMatcher | An exception raised in matcher, {matcher}')
    elif not match_result:
        logger.debug(f'WordBankMatcher | No result matched')
    else:
        await matcher.finish(match_result)
