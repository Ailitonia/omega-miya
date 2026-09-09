"""
@Author         : Ailitonia
@Date           : 2026/9/8 00:52
@FileName       : test_010_omega_base_internal
@Project        : omega-miya
@Description    : omega_base.internal 模块单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import random
import time
from typing import Any
from uuid import uuid4

import nonebot
import pytest
from nonebug import App


@pytest.fixture(scope='class')
async def onebot_v11_version_info() -> dict[str, Any]:
    """OneBot V11 get_version_info 接口返回的客户端版本信息"""
    return {
        'app_name': f'cqhttp-{uuid4().hex[:8]}',
        'app_version': '1.0.1',
        'protocol_version': 'v11',
        'app_full_name': 'test-go-cqhttp-client-1.0.1',
    }


@pytest.fixture(scope='class')
async def onebot_v11_group_info() -> list[dict[str, Any]]:
    """OneBot V11 get_group_list 接口返回的群信息"""

    def _random_group_info() -> dict[str, Any]:
        return {
            'group_id': random.randint(10000000, 99999999),
            'group_name': uuid4().hex[:8],
            'member_count': random.randint(1, 255),
            'max_member_count': 500,
            'group_memo': 'test_group',
            'group_create_time': int(time.time()),
            'group_level': 1,
        }

    return [_random_group_info() for _ in range(8)]


@pytest.fixture(scope='class')
async def onebot_v11_friend_info() -> list[dict[str, Any]]:
    """OneBot V11 get_friend_list 接口返回的好友信息"""

    def _random_friend_info() -> dict[str, Any]:
        return {
            'user_id': random.randint(10000000, 99999999),
            'nickname': uuid4().hex[:8],
            'remark': 'test_user',
        }

    return [_random_friend_info() for _ in range(8)]


@pytest.fixture
async def telegram_me_info() -> dict[str, Any]:
    """Telegram Bot get_me 接口返回的 Bot 信息"""
    return {
        'id': random.randint(10000000, 99999999),
        'is_bot': True,
        'first_name': uuid4().hex[:8],
        'username': uuid4().hex[:8],
    }


class TestBotActions:
    """Bot 事件测试"""

    async def test_onebot_v11_bot_connected(
            self,
            app: App,
            test_onebot_v11_bot,
            onebot_v11_version_info: dict[str, Any],
            onebot_v11_group_info: list[dict[str, Any]],
            onebot_v11_friend_info: list[dict[str, Any]],
    ) -> None:
        from nonebot.adapters.onebot.v11 import Adapter, Bot
        from nonebot.message import handle_event

        from src.database.internal.bot import BotSelf, BotSelfDAL, BotStatus, BotType
        from src.database.internal.entity import EntityDAL
        from src.service.omega_base.internal import BotConnectEvent

        test_bot_self_id = test_onebot_v11_bot.self_id
        async with app.test_api() as ctx:
            adapter = nonebot.get_adapter(Adapter)
            # auto_connect=False: 不触发后台连接钩子任务, 由下方 handle_event 同步驱动
            bot = ctx.create_bot(self_id=test_bot_self_id, base=Bot, adapter=adapter, auto_connect=False)

            # 不带 adapter= 约束: ApiContext 已将真实 adapter 的 _call_api 替换为
            # 临时 fake adapter 实例的绑定方法, 声明真实 adapter 身份永远无法匹配
            ctx.should_call_api('get_version_info', {}, onebot_v11_version_info)
            ctx.should_call_api('get_group_list', {}, onebot_v11_group_info)
            ctx.should_call_api('get_friend_list', {}, onebot_v11_friend_info)

            # 同步驱动 BotConnectEvent 的真实处理管线 (与 __init_bot_connect 同路径):
            # event_preprocessor __obv11_bot_connect 会按序调用上述三个 API 并同步 Bot 状态与群组/好友数据
            await handle_event(
                bot=bot,
                event=BotConnectEvent(bot_id=bot.self_id, bot_type=bot.adapter.get_name()),
            )

            # 三个 API 期望应全部被连接钩子按顺序消费
            assert ctx.wait_list.empty()

        # 验证连接同步逻辑的落库结果
        expected_bot_info = (
            f'{onebot_v11_version_info["app_name"]}-'
            f'{onebot_v11_version_info["app_version"]}-'
            f'{onebot_v11_version_info["protocol_version"]}'
        )
        async with BotSelfDAL.create() as dal:
            bot_self: BotSelf = await dal.query_unique(bot_type=BotType.ONEBOT_V11, self_id=test_bot_self_id)
        assert bot_self.bot_status == BotStatus.ENABLED
        assert bot_self.bot_info == expected_bot_info

        async with EntityDAL.create() as dal:
            for group in onebot_v11_group_info:
                entity = await dal.query_unique(
                    bot_type=BotType.ONEBOT_V11,
                    bot_self_id=test_bot_self_id,
                    entity_type='onebot_v11_group',
                    entity_id=str(group['group_id']),
                )
                assert entity.entity_name == group['group_name']
                assert entity.entity_info == group['group_memo']

            for friend in onebot_v11_friend_info:
                entity = await dal.query_unique(
                    bot_type=BotType.ONEBOT_V11,
                    bot_self_id=test_bot_self_id,
                    entity_type='onebot_v11_user',
                    entity_id=str(friend['user_id']),
                )
                assert entity.entity_name == friend['nickname']
                assert entity.entity_info == friend['remark']

    async def test_onebot_v11_bot_disconnected(
            self,
            app: App,
            test_onebot_v11_bot,
    ) -> None:
        from nonebot.adapters.onebot.v11 import Adapter, Bot
        from nonebot.message import handle_event

        from src.database.internal.bot import BotSelfDAL, BotType
        from src.service.omega_base.internal import BotDisconnectEvent

        test_bot_self_id = test_onebot_v11_bot.self_id
        async with app.test_api() as ctx:
            adapter = nonebot.get_adapter(Adapter)
            bot = ctx.create_bot(self_id=test_bot_self_id, base=Bot, adapter=adapter, auto_connect=False)

            # 断开处理不调用任何 API, 期望队列应保持为空
            await handle_event(
                bot=bot,
                event=BotDisconnectEvent(bot_id=bot.self_id, bot_type=bot.adapter.get_name()),
            )
            assert ctx.wait_list.empty()

        # 验证断开处理更新了 Bot 状态信息
        async with BotSelfDAL.create() as dal:
            bot_self = await dal.query_unique(bot_type=BotType.ONEBOT_V11, self_id=test_bot_self_id)
        assert bot_self.bot_info == 'Bot Offline'

    async def test_console_bot_connected(
            self,
            app: App,
            test_console_bot,
    ) -> None:
        from nonebot.adapters.console import Adapter
        from nonebot.adapters.console import Bot as ConsoleBot
        from nonebot.message import handle_event
        from nonechat.model import Robot

        from src.database.internal.bot import BotSelfDAL, BotStatus, BotType
        from src.service.omega_base.internal import BotConnectEvent

        test_bot_self_id = test_console_bot.self_id
        async with app.test_api() as ctx:
            adapter = nonebot.get_adapter(Adapter)
            # Console Bot 构造签名为 __init__(adapter, info: Robot), 与 nonebug 的
            # create_bot(self_id=...) 不兼容, 手动构造实例 (不注册进 driver)
            bot = ConsoleBot(adapter=adapter, info=Robot(id=test_bot_self_id))

            # 连接处理不调用任何 API, 期望队列应保持为空
            await handle_event(
                bot=bot,
                event=BotConnectEvent(bot_id=bot.self_id, bot_type=bot.adapter.get_name()),
            )
            assert ctx.wait_list.empty()

        # 验证连接同步逻辑的落库结果
        async with BotSelfDAL.create() as dal:
            bot_self = await dal.query_unique(bot_type=BotType.CONSOLE, self_id=test_bot_self_id)
        assert bot_self.bot_status == BotStatus.ENABLED
        assert bot_self.bot_info == 'Bot Online'

    async def test_console_bot_disconnected(
            self,
            app: App,
            test_console_bot,
    ) -> None:
        from nonebot.adapters.console import Adapter
        from nonebot.adapters.console import Bot as ConsoleBot
        from nonebot.message import handle_event
        from nonechat.model import Robot

        from src.database.internal.bot import BotSelfDAL, BotStatus, BotType
        from src.service.omega_base.internal import BotDisconnectEvent

        test_bot_self_id = test_console_bot.self_id
        async with app.test_api() as ctx:
            adapter = nonebot.get_adapter(Adapter)
            bot = ConsoleBot(adapter=adapter, info=Robot(id=test_bot_self_id))

            # 断开处理不调用任何 API, 期望队列应保持为空
            await handle_event(
                bot=bot,
                event=BotDisconnectEvent(bot_id=bot.self_id, bot_type=bot.adapter.get_name()),
            )
            assert ctx.wait_list.empty()

        # 验证断开处理更新了 Bot 状态信息
        async with BotSelfDAL.create() as dal:
            bot_self = await dal.query_unique(bot_type=BotType.CONSOLE, self_id=test_bot_self_id)
        assert bot_self.bot_status == BotStatus.DISABLED
        assert bot_self.bot_info == 'Bot Offline'

    async def test_telegram_bot_connected(
            self,
            app: App,
            test_telegram_bot,
            telegram_me_info: dict[str, Any],
    ) -> None:
        from nonebot.adapters.telegram import Adapter, Bot
        from nonebot.adapters.telegram.config import BotConfig as TelegramBotConfig
        from nonebot.message import handle_event

        from src.database.internal.bot import BotSelfDAL, BotStatus, BotType
        from src.service.omega_base.internal import BotConnectEvent

        test_bot_self_id = test_telegram_bot.self_id
        async with app.test_api() as ctx:
            adapter = nonebot.get_adapter(Adapter)
            # auto_connect=False: 不触发后台连接钩子任务, 由下方 handle_event 同步驱动
            # Telegram Bot 构造强制要求 config 参数, 经 create_bot 的 **kwargs 透传
            bot = ctx.create_bot(
                self_id=test_bot_self_id,
                base=Bot,
                adapter=adapter,
                auto_connect=False,
                config=TelegramBotConfig(token='123456:TEST_TOKEN'),
            )

            # 不带 adapter= 约束 (同 OneBot V11 测试); get_me 的返回值会经
            # Telegram Bot.call_api 类型化包装校验为 User 模型, mock 须为合法载荷
            ctx.should_call_api('get_me', {}, telegram_me_info)

            # 同步驱动 BotConnectEvent 的真实处理管线:
            # event_preprocessor __telegram_bot_connect 会调用 get_me 并更新 Bot 状态
            await handle_event(
                bot=bot,
                event=BotConnectEvent(bot_id=bot.self_id, bot_type=bot.adapter.get_name()),
            )
            assert ctx.wait_list.empty()

        # 验证连接同步逻辑的落库结果
        expected_bot_info = (
            f'{telegram_me_info["id"]}-'
            f'{telegram_me_info["first_name"]}@'
            f'{telegram_me_info["username"]}'
        )
        async with BotSelfDAL.create() as dal:
            bot_self = await dal.query_unique(bot_type=BotType.TELEGRAM, self_id=test_bot_self_id)
        assert bot_self.bot_status == BotStatus.ENABLED
        assert bot_self.bot_info == expected_bot_info

    async def test_telegram_bot_disconnected(
            self,
            app: App,
            test_telegram_bot,
    ) -> None:
        from nonebot.adapters.telegram import Adapter, Bot
        from nonebot.adapters.telegram.config import BotConfig as TelegramBotConfig
        from nonebot.message import handle_event

        from src.database.internal.bot import BotSelfDAL, BotStatus, BotType
        from src.service.omega_base.internal import BotDisconnectEvent

        test_bot_self_id = test_telegram_bot.self_id
        async with app.test_api() as ctx:
            adapter = nonebot.get_adapter(Adapter)
            bot = ctx.create_bot(
                self_id=test_bot_self_id,
                base=Bot,
                adapter=adapter,
                auto_connect=False,
                config=TelegramBotConfig(token='123456:TEST_TOKEN'),
            )

            # 断开处理不调用任何 API, 期望队列应保持为空
            await handle_event(
                bot=bot,
                event=BotDisconnectEvent(bot_id=bot.self_id, bot_type=bot.adapter.get_name()),
            )
            assert ctx.wait_list.empty()

        # 验证断开处理更新了 Bot 状态信息
        async with BotSelfDAL.create() as dal:
            bot_self = await dal.query_unique(bot_type=BotType.TELEGRAM, self_id=test_bot_self_id)
        assert bot_self.bot_status == BotStatus.DISABLED
        assert bot_self.bot_info == 'Bot Offline'
