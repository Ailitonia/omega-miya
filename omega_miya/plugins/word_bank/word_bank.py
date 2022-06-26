"""
@Author         : Ailitonia
@Date           : 2021/12/12 21:50
@FileName       : data_source.py
@Project        : nonebot2_miya 
@Description    : WordBank Data Source
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from rapidfuzz import process, fuzz
from nonebot.adapters.onebot.v11.message import Message
from nonebot.adapters.onebot.v11.event import MessageEvent, GroupMessageEvent

from omega_miya.result import BoolResult
from omega_miya.database import WordBank
from omega_miya.service.gocqhttp_guild_patch import GuildMessageEvent
from omega_miya.utils.message_tools import MessageTools
from omega_miya.utils.process_utils import run_async_catching_exception


class WordBankManager(object):
    """WordBank 管理工具"""
    def __init__(self, event: MessageEvent, key_word: str):
        self.reply_entity = self._get_reply_entity(event=event)
        self.key_word = key_word

    @staticmethod
    def _get_reply_entity(event: MessageEvent) -> str:
        """获取 event 对应 reply_entity"""
        if isinstance(event, GroupMessageEvent):
            reply_entity = f'group_{event.group_id}'
        elif isinstance(event, GuildMessageEvent):
            reply_entity = f'guild_channel_{event.guild_id}_{event.channel_id}'
        else:
            reply_entity = f'user_{event.user_id}'
        return reply_entity

    @classmethod
    @run_async_catching_exception
    async def list_rule(cls, event: MessageEvent) -> list[str]:
        """获取所有已配置问答"""
        reply_entity = cls._get_reply_entity(event=event)
        result = await WordBank.query_all_by_reply_entity(reply_entity=reply_entity)
        if result.error:
            raise RuntimeError(result.info)
        return [x.key_word for x in result.result]

    @run_async_catching_exception
    async def set_rule(self, reply: Message) -> BoolResult:
        """设置问答回复"""
        message_data = MessageTools.dumps(message=reply)
        result = await WordBank(reply_entity=self.reply_entity,
                                key_word=self.key_word).add_upgrade_unique_self(result_word=message_data)
        return result

    @run_async_catching_exception
    async def delete_rule(self) -> BoolResult:
        """删除问答回复"""
        result = await WordBank(reply_entity=self.reply_entity, key_word=self.key_word).query_and_delete_unique_self()
        return result


class WordBankMatcher(object):
    """WordBank 模糊匹配工具"""
    def __init__(self, message: Message, event: MessageEvent):
        self.message = message
        self.event = event

    def _get_reply_entity(self) -> str:
        """获取 event 对应 reply_entity"""
        if isinstance(self.event, GroupMessageEvent):
            reply_entity = f'group_{self.event.group_id}'
        elif isinstance(self.event, GuildMessageEvent):
            reply_entity = f'guild_channel_{self.event.guild_id}_{self.event.channel_id}'
        else:
            reply_entity = f'user_{self.event.user_id}'
        return reply_entity

    def _default_matcher(self) -> Message:
        """全等匹配"""
        raise NotImplemented

    def _regular_matcher(self) -> Message:
        """正则匹配"""
        raise NotImplemented

    async def _fuzz_matcher(self) -> Message | None:
        """模糊匹配"""
        reply_entity = self._get_reply_entity()
        rules = await WordBank.query_all_by_reply_entity(reply_entity=reply_entity)
        if rules.error:
            raise RuntimeError(rules.info)
        elif not rules.result:
            return None

        choices = {rule.key_word: rule.result_word for rule in rules.result}
        choice, similarity, index = process.extractOne(
            query=self.message.extract_plain_text(),
            choices=choices.keys(),
            scorer=fuzz.WRatio
        )

        if similarity >= 80:
            reply_message = MessageTools.loads(message_data=choices.get(choice))
        else:
            reply_message = None
        return reply_message

    @run_async_catching_exception
    async def match(self) -> Message | None:
        """异步执行匹配:return: TextResult: 匹配结果"""
        fuzz_match_result = await self._fuzz_matcher()
        return fuzz_match_result


__all__ = [
    'WordBankManager',
    'WordBankMatcher'
]
