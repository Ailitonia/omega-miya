"""
@Author         : Ailitonia
@Date           : 2022/03/30 19:38
@FileName       : bot.py
@Project        : nonebot2_miya 
@Description    : Internal Bot Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pydantic import BaseModel
from typing import Type, Literal, Optional
from omega_miya.result import BoolResult

from ..schemas.bot_self import BotSelf, BotSelfModel


BOT_TYPE = Literal[
    'OneBot V11',
    'OneBot V12',
    'Telegram'
]


class BaseBot(BaseModel):
    """实体模型基类"""
    self_id: str
    bot_type: BOT_TYPE

    class Config:
        extra = 'ignore'
        orm_mode = True
        allow_mutation = False


class OneBotV11Bot(BaseBot):
    bot_type: Literal['OneBot V11'] = 'OneBot V11'


class OneBotV12Bot(BaseBot):
    bot_type: Literal['OneBot V12'] = 'OneBot V12'


class TelegramBot(BaseBot):
    bot_type: Literal['Telegram'] = 'Telegram'


class BaseInternalBot(object):
    """封装后用于插件调用的数据库 Bot 基类"""
    _base_bot_model: Type[BaseBot] = BaseBot

    def __init__(self, bot_self_id: str, bot_type: str):
        self.bot_self_id = bot_self_id
        self.bot_type = bot_type
        self.bot_self = self._base_bot_model.parse_obj({
            'self_id': bot_self_id,
            'bot_type': bot_type
        })
        self.bot_self_model: Optional[BotSelfModel] = None

    def __repr__(self):
        return f'<InternalBot|{str(self.bot_self.bot_type)}(self_id={self.bot_self_id}, bot_type={self.bot_type})>'

    async def get_bot_self_model(self) -> BotSelfModel:
        """获取并初始化 bot self model"""
        if not isinstance(self.bot_self_model, BotSelfModel):
            bot_self = BotSelf(self_id=self.bot_self_id)
            self.bot_self_model = (await bot_self.query()).result

        assert isinstance(self.bot_self_model, BotSelfModel), 'Query bot self model failed'
        return self.bot_self_model

    async def add_upgrade(self, bot_status: int, bot_info: Optional[str] = None) -> BoolResult:
        """新增或更新 Bot 信息"""
        return await BotSelf(self_id=self.bot_self_id).add_upgrade_unique_self(
            bot_type=self.bot_type,
            bot_status=bot_status,
            bot_info=bot_info
        )


class InternalOneBotV11Bot(BaseInternalBot):
    _base_bot_model: Type[BaseBot] = OneBotV11Bot


class InternalOneBotV12Bot(BaseInternalBot):
    _base_bot_model: Type[BaseBot] = OneBotV12Bot


class InternalTelegramBot(BaseInternalBot):
    _base_bot_model: Type[BaseBot] = TelegramBot


__all__ = [
    'InternalOneBotV11Bot',
    'InternalOneBotV12Bot',
    'InternalTelegramBot'
]
