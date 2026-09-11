"""
@Author         : Ailitonia
@Date           : 2026/9/11 11:38
@FileName       : test_012_omega_processor
@Project        : omega-miya
@Description    : omega processor 单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import json
import random
import time
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import nonebot
import pytest
from nonebug import App

if TYPE_CHECKING:
    from nonebot.adapters import Event as BaseEvent
    from nonebot.matcher import Matcher


# ------------------------------------------------------------------ #
# 通用工具
# ------------------------------------------------------------------ #

def _unique_id(prefix: str) -> str:
    return f'{prefix}_{uuid4().hex[:8]}'


def _get_omega_processor_plugin_id() -> str:
    """获取已加载的 omega_processor 插件 id, 使动态 matcher 的 plugin 属性生效"""
    plugin = nonebot.get_plugin('omega_processor')
    assert plugin is not None, 'omega_processor 插件未加载'
    return plugin.id_


def _get_metadata_plugin_info() -> tuple[str, str, str]:
    """获取任一携带 metadata 的已加载插件 (plugin_id, module_name, metadata.name), 用于统计测试"""
    for plugin in nonebot.get_loaded_plugins():
        if plugin.metadata is not None:
            return plugin.id_, plugin.module_name, plugin.metadata.name
    raise AssertionError('无携带 metadata 的已加载插件')


def _make_plugin_matcher(
        *,
        temp: bool = False,
        plugin_id: str | None = None,
        module_name: str | None = None,
        **state_kwargs: Any,
) -> 'Matcher':
    """构造带 processor state 且归属指定插件 (默认 omega_processor) 的 matcher 实例 (不注册进全局表)

    Matcher.plugin 为读取 _source 的 classproperty, 需设置 MatcherSource 使其归属插件
    state_kwargs 透传 enable_processor_state (name 参数自动生成唯一名)
    """
    from nonebot.matcher import Matcher, MatcherSource

    from src.service.omega_processor import enable_processor_state

    processor_state = enable_processor_state(name=_unique_id('matcher'), **state_kwargs)
    matcher_cls = type(
        _unique_id('TestMatcher').upper(),
        (Matcher,),
        {
            '_source': MatcherSource(
                plugin_id=plugin_id or _get_omega_processor_plugin_id(),
                module_name=module_name or 'src.service.omega_processor',
            ),
            'temp': temp,
            '_default_state': processor_state,
        },
    )
    return matcher_cls()


def _make_obv11_private_event(
        *,
        user_id: int = 10001,
        text: str = '/test',
        self_id: int = 10086,
        message_id: int = 1,
) -> 'BaseEvent':
    from nonebot.adapters.onebot.v11 import Message
    from nonebot.adapters.onebot.v11.event import PrivateMessageEvent, Sender

    return PrivateMessageEvent(
        time=1,
        self_id=self_id,
        post_type='message',
        message_type='private',
        sub_type='friend',
        message_id=message_id,
        user_id=user_id,
        message=Message(text),
        original_message=Message(text),
        raw_message=text,
        font=0,
        sender=Sender(user_id=user_id, nickname='tester'),
    )


def _make_obv11_group_event(
        *,
        group_id: int = 10000,
        user_id: int = 10001,
        self_id: int = 10086,
        message_id: int = 1,
) -> 'BaseEvent':
    from nonebot.adapters.onebot.v11 import Message
    from nonebot.adapters.onebot.v11.event import GroupMessageEvent, Sender

    return GroupMessageEvent(
        time=1,
        self_id=self_id,
        post_type='message',
        sub_type='normal',
        message_id=message_id,
        user_id=user_id,
        message_type='group',
        group_id=group_id,
        message=Message('/test'),
        original_message=Message('/test'),
        raw_message='/test',
        font=0,
        sender=Sender(user_id=user_id, nickname='tester'),
    )


def _make_fake_message_event(*, user_id: str = '10001') -> 'BaseEvent':
    """构造带文本消息的轻量自定义事件 (用于超级用户等不依赖具体适配器的场景)"""
    from nonebot.adapters.onebot.v11 import Message

    from src.service.omega_base.internal import OmegaBaseEvent

    class _FakeMessageEvent(OmegaBaseEvent):
        event_type: str = 'fake_message'
        message: Message
        user_id: str

        def get_message(self) -> Message:
            return self.message

        def get_user_id(self) -> str:
            return self.user_id

        def get_session_id(self) -> str:
            return f'fake_session_{self.user_id}'

        def is_tome(self) -> bool:
            return True

    return _FakeMessageEvent(message=Message('/test'), user_id=user_id)


def _make_mock_bot(*, self_id: str = '10086') -> MagicMock:
    """构造轻量 mock Bot

    注意: 仅在不需要经 NoneBot 依赖注入 (如 SUPERUSER) 的场景使用;
    涉及实体落库的调用必须将 self_id 设置为数据库中已存在的 Bot (如 test_onebot_v11_bot.self_id)
    """
    bot = MagicMock()
    bot.self_id = self_id
    bot.type = 'fake_adapter'
    bot.adapter.get_name.return_value = 'OneBot V11'
    # SUPERUSER 等依赖读取 bot.config, 提供真实 Driver 配置
    bot.config = nonebot.get_driver().config
    return bot


def _make_real_bot(ctx: Any, self_id: str) -> Any:
    """在 nonebug test_api 上下文中创建真实 OneBot V11 Bot

    NoneBot 依赖注入 (如 SUPERUSER) 对 bot/event 参数做 isinstance 校验, MagicMock 不通过,
    涉及 SUPERUSER 路径的用例必须使用真实 Bot
    """
    from nonebot.adapters.onebot.v11 import Adapter, Bot

    adapter = nonebot.get_adapter(Adapter)
    return ctx.create_bot(self_id=self_id, base=Bot, adapter=adapter, auto_connect=False)


async def _grant_entity_permissions(
        bot_type: str,
        bot_id: str,
        entity_type: str,
        entity_id: str,
        *,
        level: int = 1,
) -> None:
    """为指定 Entity 开启全局功能并授予权限等级 (独立会话, 退出即提交)"""
    from src.database.helpers import database_session
    from src.service.omega_base import OmegaEntity

    async with database_session() as session:
        entity = OmegaEntity(
            session=session,
            bot_type=bot_type,
            bot_id=bot_id,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        await entity.enable_global_permission()
        await entity.set_permission_level(level=level)


class TestModuleContract:
    """模块导出契约测试"""

    def test_package_all(self) -> None:
        import src.service.omega_processor as processor_package

        assert processor_package.__all__ == ['enable_processor_state']
        assert processor_package.enable_processor_state is not None

    def test_submodule_all(self) -> None:
        from src.service.omega_processor.universal import (
            cancellation,
            cooldown,
            cost,
            friendship,
            history,
            permission,
            plugin,
            rate_limiting,
            statistic,
        )

        assert cancellation.__all__ == ['preprocessor_cancellation']
        assert cooldown.__all__ == ['preprocessor_cooldown']
        assert cost.__all__ == ['preprocessor_plugin_cost']
        assert friendship.__all__ == ['postprocessor_friendship']
        assert history.__all__ == ['postprocessor_history']
        assert permission.__all__ == ['preprocessor_permission']
        assert plugin.__all__ == ['preprocessor_plugin_manager']
        assert rate_limiting.__all__ == ['preprocessor_rate_limiting']
        assert statistic.__all__ == ['postprocessor_statistic']


class TestProcessorUtils:
    """processor state 工具测试"""

    def test_enable_processor_state_defaults(self) -> None:
        from src.service.omega_processor import enable_processor_state
        from src.service.omega_processor.universal.processor_utils import OmegaProcessorState, parse_processor_state

        processor_state = parse_processor_state(enable_processor_state(name='test_matcher'))

        assert isinstance(processor_state, OmegaProcessorState)
        assert processor_state.name == 'test_matcher'
        assert processor_state.enable_processor is True
        assert processor_state.level == 2 ** 15 - 1
        assert processor_state.auth_node == 'test_matcher'
        assert processor_state.extra_auth_node == set()
        assert processor_state.cooldown == 0
        assert processor_state.cooldown_type == 'event'
        assert processor_state.cost == 0
        assert processor_state.echo_processor_result is True

    def test_enable_processor_state_custom_and_clamping(self) -> None:
        from src.service.omega_processor import enable_processor_state
        from src.service.omega_processor.universal.processor_utils import parse_processor_state

        state = enable_processor_state(
            'custom',
            enable_processor=False,
            level=10,
            auth_node='custom_node',
            extra_auth_node={'node_a', 'node_b'},
            cooldown=-5,
            cooldown_type='user',
            cost=-1.5,
            echo_processor_result=False,
        )
        processor_state = parse_processor_state(state)

        assert processor_state.enable_processor is False
        assert processor_state.level == 10
        assert processor_state.auth_node == 'custom_node'
        assert processor_state.extra_auth_node == {'node_a', 'node_b'}
        # 负值冷却与消耗应钳位为 0
        assert processor_state.cooldown == 0
        assert processor_state.cooldown_type == 'user'
        assert processor_state.cost == 0
        assert processor_state.echo_processor_result is False

    def test_parse_processor_state_unconfigured_fallback(self) -> None:
        from src.service.omega_processor.universal.processor_utils import parse_processor_state

        processor_state = parse_processor_state({})

        assert processor_state.enable_processor is False
        assert processor_state.level == 0
        assert processor_state.auth_node == 'undefined'
        assert processor_state.echo_processor_result is False
        assert processor_state.name.startswith('undefined_')

    def test_parse_processor_state_fallback_names_unique(self) -> None:
        from src.service.omega_processor.universal.processor_utils import parse_processor_state

        first = parse_processor_state({})
        second = parse_processor_state({})

        assert first.name != second.name

    def test_enable_processor_state_json_safe(self) -> None:
        """processor state 应可直接 JSON 序列化 (含 extra_auth_node 集合), 且回读等价 (F1 回归)"""
        import json

        from src.service.omega_processor import enable_processor_state
        from src.service.omega_processor.universal.processor_utils import parse_processor_state

        state = enable_processor_state('json_safe', extra_auth_node={'node_a', 'node_b'})

        # set 等 python 模式值不应出现在 state 中, 须可直接序列化 (统计后处理器会将其写入 JSON 列)
        serialized = json.dumps(state)

        processor_state = parse_processor_state(json.loads(serialized))
        assert processor_state.extra_auth_node == {'node_a', 'node_b'}
        assert processor_state.name == 'json_safe'


class TestCancellation:
    """用户取消处理测试"""

    @pytest.mark.parametrize(('text', 'expected'), [
        ('算了', True),
        ('那算了吧', True),
        ('别', True),
        ('停', True),
        ('不', True),
        ('不干了', True),
        ('取消', True),
        ('那取消了吧', True),
        ('帮我取消吧', True),
        ('取消了吗', False),
        ('取消一下啊好不好', False),
        ('hello', False),
        ('', False),
        ('取消不', False),
    ])
    def test_is_cancellation(self, text: str, expected: bool) -> None:
        from src.service.omega_processor.universal.cancellation import is_cancellation

        assert is_cancellation(text) is expected

    def test_is_cancellation_with_message_object(self) -> None:
        from nonebot.adapters.onebot.v11 import Message

        from src.service.omega_processor.universal.cancellation import is_cancellation

        assert is_cancellation(Message('算了')) is True
        assert is_cancellation(Message('正常消息')) is False

    async def test_preprocessor_cancel_on_temp_matcher(self) -> None:
        from nonebot.adapters.onebot.v11 import Message
        from nonebot.exception import IgnoredException

        from src.service.omega_processor.universal.cancellation import CANCEL_PROMPT, preprocessor_cancellation

        matcher = MagicMock()
        matcher.temp = True
        matcher.send = AsyncMock()

        with pytest.raises(IgnoredException, match='用户取消操作'):
            await preprocessor_cancellation(matcher=matcher, message=Message('算了'))

        matcher.send.assert_awaited_once_with(message=CANCEL_PROMPT)

    async def test_preprocessor_normal_message_not_cancelled(self) -> None:
        from nonebot.adapters.onebot.v11 import Message

        from src.service.omega_processor.universal.cancellation import preprocessor_cancellation

        matcher = MagicMock()
        matcher.temp = True
        matcher.send = AsyncMock()

        await preprocessor_cancellation(matcher=matcher, message=Message('正常消息'))

        matcher.send.assert_not_awaited()

    async def test_preprocessor_non_temp_matcher_ignored(self) -> None:
        from nonebot.adapters.onebot.v11 import Message

        from src.service.omega_processor.universal.cancellation import preprocessor_cancellation

        matcher = MagicMock()
        matcher.temp = False
        matcher.send = AsyncMock()

        await preprocessor_cancellation(matcher=matcher, message=Message('算了'))

        matcher.send.assert_not_awaited()

    async def test_preprocessor_send_failure_still_raises(self) -> None:
        from nonebot.adapters.onebot.v11 import Message
        from nonebot.exception import IgnoredException

        from src.service.omega_processor.universal.cancellation import preprocessor_cancellation

        matcher = MagicMock()
        matcher.temp = True
        matcher.send = AsyncMock(side_effect=RuntimeError('send failed'))

        with pytest.raises(IgnoredException, match='用户取消操作'):
            await preprocessor_cancellation(matcher=matcher, message=Message('取消'))


@pytest.fixture
def rate_limiting_sandbox():
    """限流跟踪字典沙箱: 清空后测试, 测试后恢复原状态"""
    from src.service.omega_processor.universal import rate_limiting

    snapshot = {
        'last_msg': dict(rate_limiting._USER_LAST_MSG_TIME),
        'count': dict(rate_limiting._RATE_LIMITING_COUNT),
        'temp': dict(rate_limiting._RATE_LIMITING_USER_TEMP),
    }
    rate_limiting._USER_LAST_MSG_TIME.clear()
    rate_limiting._RATE_LIMITING_COUNT.clear()
    rate_limiting._RATE_LIMITING_USER_TEMP.clear()
    yield rate_limiting
    rate_limiting._USER_LAST_MSG_TIME.clear()
    rate_limiting._USER_LAST_MSG_TIME.update(snapshot['last_msg'])
    rate_limiting._RATE_LIMITING_COUNT.clear()
    rate_limiting._RATE_LIMITING_COUNT.update(snapshot['count'])
    rate_limiting._RATE_LIMITING_USER_TEMP.clear()
    rate_limiting._RATE_LIMITING_USER_TEMP.update(snapshot['temp'])


class TestRateLimiting:
    """速率限制测试 (直接调用, 沙箱隔离全局字典)"""

    async def test_first_message_passes(self, rate_limiting_sandbox) -> None:
        await rate_limiting_sandbox.preprocessor_rate_limiting(
            bot=_make_mock_bot(), event=_make_fake_message_event(user_id='50001'),
        )

    async def test_threshold_triggers_limiting(self, rate_limiting_sandbox) -> None:
        from nonebot.exception import IgnoredException

        bot = _make_mock_bot()
        event = _make_fake_message_event(user_id='50002')

        # 第 1 条建立基线, 第 2~11 条窗口内计数 1..10 (未超阈值), 第 12 条计数 11 触发限制
        for _ in range(11):
            await rate_limiting_sandbox.preprocessor_rate_limiting(bot=bot, event=event)

        with pytest.raises(IgnoredException, match='触发速率限制'):
            await rate_limiting_sandbox.preprocessor_rate_limiting(bot=bot, event=event)

        # 触发后计数被重置
        user_flag = f'{bot.type}_{bot.self_id}_50002'
        assert rate_limiting_sandbox._RATE_LIMITING_COUNT[user_flag] == 0

    async def test_limited_user_blocked(self, rate_limiting_sandbox) -> None:
        from nonebot.exception import IgnoredException

        bot = _make_mock_bot()
        event = _make_fake_message_event(user_id='50003')
        user_flag = f'{bot.type}_{bot.self_id}_50003'
        rate_limiting_sandbox._RATE_LIMITING_USER_TEMP[user_flag] = int(time.time()) + 100

        with pytest.raises(IgnoredException, match='速率限制中'):
            await rate_limiting_sandbox.preprocessor_rate_limiting(bot=bot, event=event)

    async def test_expired_limit_allows_message(self, rate_limiting_sandbox) -> None:
        """已过期的限制条目应放行并刷新消息时间戳 (过期条目惰性保留, 由规模剪枝统一清理)"""
        bot = _make_mock_bot()
        event = _make_fake_message_event(user_id='50004')
        user_flag = f'{bot.type}_{bot.self_id}_50004'
        rate_limiting_sandbox._RATE_LIMITING_USER_TEMP[user_flag] = int(time.time()) - 1

        await rate_limiting_sandbox.preprocessor_rate_limiting(bot=bot, event=event)

        assert rate_limiting_sandbox._USER_LAST_MSG_TIME[user_flag] == pytest.approx(int(time.time()), abs=2)

    async def test_non_message_event_ignored(self, rate_limiting_sandbox) -> None:
        from src.service.omega_base.internal import OmegaBaseEvent

        await rate_limiting_sandbox.preprocessor_rate_limiting(
            bot=_make_mock_bot(), event=OmegaBaseEvent(event_type='meta'),
        )

    async def test_bot_self_ignored(self, rate_limiting_sandbox) -> None:
        await rate_limiting_sandbox.preprocessor_rate_limiting(
            bot=_make_mock_bot(self_id='50005'), event=_make_fake_message_event(user_id='50005'),
        )

    async def test_superuser_ignored(self, app: App, rate_limiting_sandbox) -> None:
        """超级用户消息不进入限流跟踪 (SUPERUSER 经 NoneBot 依赖注入, 须使用真实 Bot)"""
        async with app.test_api() as ctx:
            bot = _make_real_bot(ctx, _unique_id('TEST_RL_SU_BOT'))

            # 测试配置中 superusers 为 {'User'}
            await rate_limiting_sandbox.preprocessor_rate_limiting(
                bot=bot, event=_make_fake_message_event(user_id='User'),
            )

        # 断言真实跳过证据: 未产生限流跟踪条目
        user_flag = f'{bot.type}_{bot.self_id}_User'
        assert user_flag not in rate_limiting_sandbox._USER_LAST_MSG_TIME

    async def test_gap_over_window_resets_count(self, rate_limiting_sandbox) -> None:
        bot = _make_mock_bot()
        event = _make_fake_message_event(user_id='50006')
        user_flag = f'{bot.type}_{bot.self_id}_50006'

        await rate_limiting_sandbox.preprocessor_rate_limiting(bot=bot, event=event)
        rate_limiting_sandbox._RATE_LIMITING_COUNT[user_flag] = 9
        rate_limiting_sandbox._USER_LAST_MSG_TIME[user_flag] = int(time.time()) - 10

        # 间隔超过时间阈值, 计数应重置而非累加
        await rate_limiting_sandbox.preprocessor_rate_limiting(bot=bot, event=event)

        assert rate_limiting_sandbox._RATE_LIMITING_COUNT[user_flag] == 0

    async def test_stale_entries_pruned(self, rate_limiting_sandbox) -> None:
        """字典规模超阈值时应清理长期未活跃条目"""
        now = int(time.time())
        stale_flag = f'fake_adapter_10086_stale_{uuid4().hex[:6]}'
        active_flag = 'fake_adapter_10086_50007'

        for i in range(rate_limiting_sandbox._RATE_LIMITING_PRUNE_THRESHOLD + 10):
            rate_limiting_sandbox._USER_LAST_MSG_TIME[f'fake_adapter_10086_bulk_{i}_{uuid4().hex[:4]}'] = now - 99999
        rate_limiting_sandbox._USER_LAST_MSG_TIME[stale_flag] = now - 99999
        rate_limiting_sandbox._RATE_LIMITING_COUNT[stale_flag] = 5
        rate_limiting_sandbox._RATE_LIMITING_USER_TEMP[stale_flag] = now - 99999

        await rate_limiting_sandbox.preprocessor_rate_limiting(
            bot=_make_mock_bot(), event=_make_fake_message_event(user_id='50007'),
        )

        assert stale_flag not in rate_limiting_sandbox._USER_LAST_MSG_TIME
        assert stale_flag not in rate_limiting_sandbox._RATE_LIMITING_COUNT
        assert stale_flag not in rate_limiting_sandbox._RATE_LIMITING_USER_TEMP
        # 活跃用户条目保留
        assert any(flag.endswith('_50007') for flag in rate_limiting_sandbox._USER_LAST_MSG_TIME)
        assert active_flag in rate_limiting_sandbox._USER_LAST_MSG_TIME


class TestPermission:
    """权限预处理器测试 (直接调用, 真实数据库)"""

    async def test_non_plugin_matcher_ignored(self) -> None:
        from nonebot.matcher import Matcher

        from src.database.helpers import database_session
        from src.service.omega_processor.universal.permission import preprocessor_permission

        matcher = type('NonPluginMatcher', (Matcher,), {'plugin_id': None, 'temp': False})()

        async with database_session() as session:
            await preprocessor_permission(
                bot=_make_mock_bot(), event=_make_obv11_private_event(), matcher=matcher, db_session=session,
            )

    async def test_super_user_ignored(self, app: App, test_onebot_v11_bot) -> None:
        """超级用户跳过权限检查; 对照组普通用户无授权时被阻断

        SUPERUSER 经 NoneBot 依赖注入且对 bot/event 做 isinstance 校验, 必须使用真实 Bot
        """
        from nonebot.exception import IgnoredException

        from src.database.helpers import database_session
        from src.service.omega_processor.universal.permission import preprocessor_permission

        # 默认满级权限要求, 未授权的普通用户必不满足
        matcher = _make_plugin_matcher(level=2 ** 15 - 1)

        async with app.test_api() as ctx:
            bot = _make_real_bot(ctx, test_onebot_v11_bot.self_id)

            async with database_session() as session:
                # 超级用户跳过全部权限检查
                await preprocessor_permission(
                    bot=bot, event=_make_fake_message_event(user_id='User'), matcher=matcher, db_session=session,
                )

                # 对照: 普通用户无任何授权, 全局功能未开启即被阻断
                with pytest.raises(IgnoredException, match='权限不足'):
                    await preprocessor_permission(
                        bot=bot, event=_make_obv11_private_event(user_id=51901), matcher=matcher, db_session=session,
                    )

    async def test_disabled_processor_ignored(self, test_onebot_v11_bot) -> None:
        from src.database.helpers import database_session
        from src.service.omega_processor.universal.permission import preprocessor_permission

        matcher = _make_plugin_matcher(enable_processor=False, level=1)

        async with database_session() as session:
            await preprocessor_permission(
                bot=_make_mock_bot(self_id=test_onebot_v11_bot.self_id),
                event=_make_obv11_private_event(user_id=51001),
                matcher=matcher,
                db_session=session,
            )

    async def test_global_permission_denied_raises_ignored(self, test_onebot_v11_bot) -> None:
        """全局功能未启用应抛出 IgnoredException 而非日志解析异常"""
        from nonebot.exception import IgnoredException

        from src.database.helpers import database_session
        from src.service.omega_processor.universal.permission import preprocessor_permission

        matcher = _make_plugin_matcher(level=1)

        async with database_session() as session:
            with pytest.raises(IgnoredException, match='权限不足'):
                await preprocessor_permission(
                    bot=_make_mock_bot(self_id=test_onebot_v11_bot.self_id),
                    event=_make_obv11_private_event(user_id=51002),
                    matcher=matcher, db_session=session,
                )

    async def test_insufficient_level_denied(self, test_onebot_v11_bot) -> None:
        from nonebot.exception import IgnoredException

        from src.database.helpers import database_session
        from src.service.omega_processor.universal.permission import preprocessor_permission

        user_id = 51003
        await _grant_entity_permissions(
            test_onebot_v11_bot.bot_type, test_onebot_v11_bot.self_id, 'onebot_v11_user', str(user_id), level=1,
        )
        matcher = _make_plugin_matcher(level=10)

        async with database_session() as session:
            with pytest.raises(IgnoredException, match='权限不足'):
                await preprocessor_permission(
                    bot=_make_mock_bot(self_id=test_onebot_v11_bot.self_id),
                    event=_make_obv11_private_event(user_id=user_id),
                    matcher=matcher, db_session=session,
                )

    async def test_level_grant_allows(self, test_onebot_v11_bot) -> None:
        from src.database.helpers import database_session
        from src.service.omega_processor.universal.permission import preprocessor_permission

        user_id = 51004
        await _grant_entity_permissions(
            test_onebot_v11_bot.bot_type, test_onebot_v11_bot.self_id, 'onebot_v11_user', str(user_id), level=10,
        )
        matcher = _make_plugin_matcher(level=5)

        async with database_session() as session:
            await preprocessor_permission(
                bot=_make_mock_bot(self_id=test_onebot_v11_bot.self_id),
                event=_make_obv11_private_event(user_id=user_id),
                matcher=matcher, db_session=session,
            )

    async def test_auth_node_grant_allows(self, test_onebot_v11_bot) -> None:
        from src.database.helpers import database_session
        from src.service.omega_base import OmegaEntity
        from src.service.omega_processor.universal.permission import preprocessor_permission

        user_id = 51005
        matcher = _make_plugin_matcher(level=100, auth_node='granted_node')

        async with database_session() as session:
            entity = OmegaEntity(
                session=session,
                bot_type=test_onebot_v11_bot.bot_type,
                bot_id=test_onebot_v11_bot.self_id,
                entity_type='onebot_v11_user',
                entity_id=str(user_id),
            )
            await entity.enable_global_permission()
            await entity.set_auth_setting(
                module='src.service.omega_processor',
                plugin='omega_processor',
                node='granted_node',
                available=1,
                value={},
            )

            # node 验证通过时无视 level 不足
            await preprocessor_permission(
                bot=_make_mock_bot(self_id=test_onebot_v11_bot.self_id),
                event=_make_obv11_private_event(user_id=user_id),
                matcher=matcher, db_session=session,
            )


class TestCooldown:
    """冷却预处理器测试 (直接调用, 真实数据库)"""

    async def test_zero_cooldown_ignored(self) -> None:
        from src.database.helpers import database_session
        from src.service.omega_processor.universal.cooldown import preprocessor_cooldown

        matcher = _make_plugin_matcher(cooldown=0)

        async with database_session() as session:
            await preprocessor_cooldown(
                bot=_make_mock_bot(), event=_make_obv11_private_event(user_id=52001),
                matcher=matcher, db_session=session,
            )

    async def test_temp_matcher_ignored(self) -> None:
        from src.database.helpers import database_session
        from src.service.omega_processor.universal.cooldown import preprocessor_cooldown

        matcher = _make_plugin_matcher(cooldown=60, temp=True)

        async with database_session() as session:
            await preprocessor_cooldown(
                bot=_make_mock_bot(), event=_make_obv11_private_event(user_id=52002),
                matcher=matcher, db_session=session,
            )

    async def test_super_user_ignored(self, app: App, test_onebot_v11_bot) -> None:
        """超级用户跳过冷却检查 (SUPERUSER 经依赖注入做 isinstance 校验, 须使用真实 Bot)"""
        from src.database.helpers import database_session
        from src.service.omega_processor.universal.cooldown import preprocessor_cooldown

        matcher = _make_plugin_matcher(cooldown=60)

        async with app.test_api() as ctx:
            bot = _make_real_bot(ctx, test_onebot_v11_bot.self_id)

            async with database_session() as session:
                await preprocessor_cooldown(
                    bot=bot, event=_make_fake_message_event(user_id='User'), matcher=matcher, db_session=session,
                )

    async def test_user_cooldown_second_call_blocked(self, test_onebot_v11_bot) -> None:
        from nonebot.exception import IgnoredException

        from src.database.helpers import database_session
        from src.service.omega_processor.universal.cooldown import preprocessor_cooldown

        matcher = _make_plugin_matcher(cooldown=60, cooldown_type='user', echo_processor_result=False)
        bot = _make_mock_bot(self_id=test_onebot_v11_bot.self_id)
        event = _make_obv11_private_event(user_id=52003)

        async with database_session() as session:
            await preprocessor_cooldown(bot=bot, event=event, matcher=matcher, db_session=session)

            with pytest.raises(IgnoredException, match='冷却中'):
                await preprocessor_cooldown(bot=bot, event=event, matcher=matcher, db_session=session)

    async def test_event_cooldown_second_call_blocked(self, test_onebot_v11_bot) -> None:
        from nonebot.exception import IgnoredException

        from src.database.helpers import database_session
        from src.service.omega_processor.universal.cooldown import preprocessor_cooldown

        matcher = _make_plugin_matcher(cooldown=60, cooldown_type='event', echo_processor_result=False)
        bot = _make_mock_bot(self_id=test_onebot_v11_bot.self_id)
        event = _make_obv11_group_event(group_id=52004, user_id=52004)

        async with database_session() as session:
            await preprocessor_cooldown(bot=bot, event=event, matcher=matcher, db_session=session)

            with pytest.raises(IgnoredException, match='冷却中'):
                await preprocessor_cooldown(bot=bot, event=event, matcher=matcher, db_session=session)

    async def test_skip_cooldown_permission_allows(self, test_onebot_v11_bot) -> None:
        from src.database.helpers import database_session
        from src.service.omega_base import OmegaEntity
        from src.service.omega_processor.universal.cooldown import preprocessor_cooldown

        user_id = 52005
        matcher = _make_plugin_matcher(cooldown=60, cooldown_type='user')

        async with database_session() as session:
            entity = OmegaEntity(
                session=session,
                bot_type=test_onebot_v11_bot.bot_type,
                bot_id=test_onebot_v11_bot.self_id,
                entity_type='onebot_v11_user',
                entity_id=str(user_id),
            )
            await entity.enable_plugin_skip_cooldown_permission(
                module='src.service.omega_processor', plugin='omega_processor',
            )
            event = _make_obv11_private_event(user_id=user_id)

            await preprocessor_cooldown(
                bot=_make_mock_bot(self_id=test_onebot_v11_bot.self_id),
                event=event, matcher=matcher, db_session=session,
            )
            await preprocessor_cooldown(
                bot=_make_mock_bot(self_id=test_onebot_v11_bot.self_id),
                event=event, matcher=matcher, db_session=session,
            )

    async def test_global_cooldown_shared_key_enforced(self, test_onebot_v11_bot) -> None:
        """global 类型冷却经实体全局冷却键生效: 首次放行后二次阻断, 且写入全局键而非插件键"""
        from datetime import datetime

        from nonebot.exception import IgnoredException
        from sqlalchemy.exc import NoResultFound

        from src.database.helpers import database_session
        from src.service.omega_base import OmegaEntity
        from src.service.omega_base.internal.consts import GLOBAL_COOLDOWN_EVENT
        from src.service.omega_processor.universal.cooldown import preprocessor_cooldown
        from src.service.omega_processor.universal.processor_utils import parse_processor_state

        user_id = 52006
        matcher = _make_plugin_matcher(cooldown=60, cooldown_type='global', echo_processor_result=False)
        bot = _make_mock_bot(self_id=test_onebot_v11_bot.self_id)
        event = _make_obv11_private_event(user_id=user_id)

        plugin_cd_event = f'plugin_cd_{matcher.plugin.name}_{parse_processor_state(matcher.state).name}'

        async with database_session() as session:
            await preprocessor_cooldown(bot=bot, event=event, matcher=matcher, db_session=session)

            # 首次放行后: 全局冷却键已设置, 插件冷却键未设置
            entity = OmegaEntity(
                session=session,
                bot_type=test_onebot_v11_bot.bot_type,
                bot_id=test_onebot_v11_bot.self_id,
                entity_type='onebot_v11_user',
                entity_id=str(user_id),
            )
            global_cooldown = await entity.query_cooldown(GLOBAL_COOLDOWN_EVENT)
            assert global_cooldown.stop_at > datetime.now()
            with pytest.raises(NoResultFound):
                await entity.query_cooldown(plugin_cd_event)

            with pytest.raises(IgnoredException, match='冷却中'):
                await preprocessor_cooldown(bot=bot, event=event, matcher=matcher, db_session=session)

    async def test_global_cooldown_admin_global_key_blocks(self, test_onebot_v11_bot) -> None:
        """管理端设置的全局冷却应阻断 global 类型调用"""
        from datetime import timedelta

        from nonebot.exception import IgnoredException

        from src.database.helpers import database_session
        from src.service.omega_base import OmegaEntity
        from src.service.omega_processor.universal.cooldown import preprocessor_cooldown

        user_id = 52007
        matcher = _make_plugin_matcher(cooldown=60, cooldown_type='global', echo_processor_result=False)

        async with database_session() as session:
            entity = OmegaEntity(
                session=session,
                bot_type=test_onebot_v11_bot.bot_type,
                bot_id=test_onebot_v11_bot.self_id,
                entity_type='onebot_v11_user',
                entity_id=str(user_id),
            )
            await entity.set_global_cooldown(expired_time=timedelta(seconds=3600))

            with pytest.raises(IgnoredException, match='冷却中'):
                await preprocessor_cooldown(
                    bot=_make_mock_bot(self_id=test_onebot_v11_bot.self_id),
                    event=_make_obv11_private_event(user_id=user_id),
                    matcher=matcher, db_session=session,
                )

    async def test_global_cooldown_shared_across_matchers(self, test_onebot_v11_bot) -> None:
        """同一实体的不同 global 类型 matcher 共享同一全局冷却 (matcher A 调用后 matcher B 被阻断)"""
        from nonebot.exception import IgnoredException

        from src.database.helpers import database_session
        from src.service.omega_processor.universal.cooldown import preprocessor_cooldown
        from src.service.omega_processor.universal.processor_utils import parse_processor_state

        user_id = 52008
        matcher_a = _make_plugin_matcher(cooldown=60, cooldown_type='global', echo_processor_result=False)
        matcher_b = _make_plugin_matcher(cooldown=60, cooldown_type='global', echo_processor_result=False)
        assert parse_processor_state(matcher_a.state).name != parse_processor_state(matcher_b.state).name

        bot = _make_mock_bot(self_id=test_onebot_v11_bot.self_id)
        event = _make_obv11_private_event(user_id=user_id)

        async with database_session() as session:
            await preprocessor_cooldown(bot=bot, event=event, matcher=matcher_a, db_session=session)

            with pytest.raises(IgnoredException, match='冷却中'):
                await preprocessor_cooldown(bot=bot, event=event, matcher=matcher_b, db_session=session)

    async def test_global_cooldown_not_skippable_by_skip_permission(self, test_onebot_v11_bot) -> None:
        """全局冷却不受跳过冷却权限影响: 持有 skip 权限的用户二次调用仍被阻断"""
        from nonebot.exception import IgnoredException

        from src.database.helpers import database_session
        from src.service.omega_base import OmegaEntity
        from src.service.omega_processor.universal.cooldown import preprocessor_cooldown

        user_id = 52009
        matcher = _make_plugin_matcher(cooldown=60, cooldown_type='global', echo_processor_result=False)
        bot = _make_mock_bot(self_id=test_onebot_v11_bot.self_id)
        event = _make_obv11_private_event(user_id=user_id)

        async with database_session() as session:
            entity = OmegaEntity(
                session=session,
                bot_type=test_onebot_v11_bot.bot_type,
                bot_id=test_onebot_v11_bot.self_id,
                entity_type='onebot_v11_user',
                entity_id=str(user_id),
            )
            await entity.enable_plugin_skip_cooldown_permission(
                module='src.service.omega_processor', plugin='omega_processor',
            )

            # 首次放行 (全局冷却未设置), 并写入全局冷却
            await preprocessor_cooldown(bot=bot, event=event, matcher=matcher, db_session=session)

            # skip 权限不能绕过全局冷却
            with pytest.raises(IgnoredException, match='冷却中'):
                await preprocessor_cooldown(bot=bot, event=event, matcher=matcher, db_session=session)


class TestCost:
    """命令消耗预处理器测试 (直接调用, 真实数据库)"""

    async def test_zero_cost_ignored(self) -> None:
        from src.database.helpers import database_session
        from src.service.omega_processor.universal.cost import preprocessor_plugin_cost

        matcher = _make_plugin_matcher(cost=0)

        async with database_session() as session:
            await preprocessor_plugin_cost(
                bot=_make_mock_bot(), event=_make_obv11_private_event(user_id=53001),
                matcher=matcher, db_session=session,
            )

    async def test_insufficient_currency_blocked(self, test_onebot_v11_bot) -> None:
        from nonebot.exception import IgnoredException

        from src.database.helpers import database_session
        from src.service.omega_processor.universal.cost import preprocessor_plugin_cost

        matcher = _make_plugin_matcher(cost=1.5)

        async with database_session() as session:
            with pytest.raises(IgnoredException, match='硬币不足'):
                await preprocessor_plugin_cost(
                    bot=_make_mock_bot(self_id=test_onebot_v11_bot.self_id),
                    event=_make_obv11_private_event(user_id=53002),
                    matcher=matcher, db_session=session,
                )

    async def test_sufficient_currency_charged_even_if_send_fails(self, test_onebot_v11_bot) -> None:
        """余额充足时先扣费, 即使提示消息发送失败 (matcher.send 在管线外抛 LookupError) 也完成扣费"""

        from src.database.helpers import database_session
        from src.service.omega_base import OmegaEntity
        from src.service.omega_processor.universal.cost import preprocessor_plugin_cost

        user_id = 53003
        matcher = _make_plugin_matcher(cost=1.5)

        async with database_session() as session:
            entity = OmegaEntity(
                session=session,
                bot_type=test_onebot_v11_bot.bot_type,
                bot_id=test_onebot_v11_bot.self_id,
                entity_type='onebot_v11_user',
                entity_id=str(user_id),
            )
            await entity.set_friendship(currency=Decimal('10'))

            await preprocessor_plugin_cost(
                bot=_make_mock_bot(self_id=test_onebot_v11_bot.self_id),
                event=_make_obv11_private_event(user_id=user_id),
                matcher=matcher, db_session=session,
            )

            friendship = await entity.query_friendship()
            assert friendship.currency == Decimal('8.50')


class TestFriendship:
    """好感度后处理器测试 (直接调用, 真实数据库)"""

    async def test_friendship_increment(self, app: App, test_onebot_v11_bot) -> None:
        """每条消息事件应为用户增加能量与货币 (精度: 0.5/0.125, 量化到 0.0001)"""
        from src.database.helpers import database_session
        from src.service.omega_base import OmegaEntity
        from src.service.omega_processor.universal.friendship import postprocessor_friendship

        user_id = random.randint(10_000_000, 99_999_999)

        async with app.test_api() as ctx:
            bot = _make_real_bot(ctx, test_onebot_v11_bot.self_id)
            event = _make_obv11_private_event(user_id=user_id)

            async with database_session() as session:
                await postprocessor_friendship(bot=bot, event=event, db_session=session)
                await postprocessor_friendship(bot=bot, event=event, db_session=session)

                entity = OmegaEntity(
                    session=session,
                    bot_type=test_onebot_v11_bot.bot_type,
                    bot_id=test_onebot_v11_bot.self_id,
                    entity_type='onebot_v11_user',
                    entity_id=str(user_id),
                )
                friendship = await entity.query_friendship()

        assert friendship.energy == Decimal('1.0')
        assert friendship.currency == Decimal('0.25')


class TestHistory:
    """消息历史后处理器测试 (直接调用, 真实数据库)"""

    async def test_history_recorded(self, app: App, test_onebot_v11_bot) -> None:
        from src.database import HistoryDAL
        from src.database.helpers import database_session
        from src.service.omega_processor.universal.history import postprocessor_history

        user_id = random.randint(10_000_000, 99_999_999)
        message_id = random.randint(1_000_000, 9_999_999)

        async with app.test_api() as ctx:
            bot = _make_real_bot(ctx, test_onebot_v11_bot.self_id)
            event = _make_obv11_private_event(
                user_id=user_id, message_id=message_id, text='/test history',
            )

            async with database_session() as session:
                await postprocessor_history(
                    bot=bot, event=event, message=event.get_message(), db_session=session,
                )

        async with HistoryDAL.create() as dal:
            records = await dal.query_records_by_condition(
                bot_self_id=test_onebot_v11_bot.self_id, user_entity_id=str(user_id),
            )

        matched = [x for x in records if x.message_id == str(message_id)]
        assert len(matched) == 1
        assert matched[0].message_plain_text == '/test history'

    async def test_history_failure_contained_by_savepoint(self, app: App, test_onebot_v11_bot) -> None:
        """重复 message_id 触发唯一键冲突时应被 SAVEPOINT 容纳, 共享会话保持可用 (F2 回归)"""
        from src.database import HistoryDAL
        from src.database.helpers import database_session
        from src.service.omega_processor.universal.history import postprocessor_history

        user_id = random.randint(10_000_000, 99_999_999)
        duplicated_id = random.randint(1_000_000, 9_999_999)
        another_id = duplicated_id + 1

        async with app.test_api() as ctx:
            bot = _make_real_bot(ctx, test_onebot_v11_bot.self_id)
            event_1 = _make_obv11_private_event(user_id=user_id, message_id=duplicated_id)
            event_2 = _make_obv11_private_event(user_id=user_id, message_id=duplicated_id)
            event_3 = _make_obv11_private_event(user_id=user_id, message_id=another_id)

            async with database_session() as session:
                # 第一次写入成功; 第二次同 (bot, message_id) 触发唯一键冲突;
                # 若失败未被隔离, 会话将被污染, 第三次写入及最终提交均会失败
                await postprocessor_history(bot=bot, event=event_1, message=event_1.get_message(), db_session=session)
                await postprocessor_history(bot=bot, event=event_2, message=event_2.get_message(), db_session=session)
                await postprocessor_history(bot=bot, event=event_3, message=event_3.get_message(), db_session=session)

        async with HistoryDAL.create() as dal:
            records = await dal.query_records_by_condition(
                bot_self_id=test_onebot_v11_bot.self_id, user_entity_id=str(user_id),
            )

        recorded_ids = [x.message_id for x in records]
        assert recorded_ids.count(str(duplicated_id)) == 1
        assert str(another_id) in recorded_ids


class TestStatistic:
    """插件调用统计后处理器测试 (直接调用, 真实数据库)"""

    async def test_statistic_recorded_with_processor_state(self, app: App, test_onebot_v11_bot) -> None:
        """携带 processor state (含集合类型字段) 的 matcher 调用应正常统计落库 (F1 回归)"""
        from src.database import StatisticDAL
        from src.database.helpers import database_session
        from src.service.omega_processor.universal.statistic import postprocessor_statistic

        plugin_id, module_name, custom_name = _get_metadata_plugin_info()
        matcher = _make_plugin_matcher(plugin_id=plugin_id, module_name=module_name, extra_auth_node={'node_x'})
        user_id = random.randint(10_000_000, 99_999_999)

        async with app.test_api() as ctx:
            bot = _make_real_bot(ctx, test_onebot_v11_bot.self_id)
            event = _make_obv11_private_event(user_id=user_id)

            async with database_session() as session:
                await postprocessor_statistic(bot=bot, event=event, matcher=matcher, db_session=session)

        async with StatisticDAL.create() as dal:
            records = await dal.query_by_condition(plugin_name=custom_name, module_name=module_name)

        matched = [x for x in records if x.call_data.get('_OMEGA_INTERNAL_PROCESSOR', {}).get('name')]
        assert matched, '统计行未落库或缺少 processor state'
        # call_data 应为合法 JSON 可序列化结构 (set 已转换为 list)
        json.dumps(matched[-1].call_data)

    async def test_statistic_dirty_state_fallback(self, app: App, test_onebot_v11_bot) -> None:
        """matcher.state 中的不可序列化运行时值应以 repr 兜底记录, 不影响统计落库"""
        from src.database import StatisticDAL
        from src.database.helpers import database_session
        from src.service.omega_processor.universal.statistic import postprocessor_statistic

        plugin_id, module_name, custom_name = _get_metadata_plugin_info()
        matcher = _make_plugin_matcher(plugin_id=plugin_id, module_name=module_name)
        dirty_value = object()
        matcher.state['dirty_runtime_value'] = dirty_value
        user_id = random.randint(10_000_000, 99_999_999)

        async with app.test_api() as ctx:
            bot = _make_real_bot(ctx, test_onebot_v11_bot.self_id)
            event = _make_obv11_private_event(user_id=user_id)

            async with database_session() as session:
                await postprocessor_statistic(bot=bot, event=event, matcher=matcher, db_session=session)

        async with StatisticDAL.create() as dal:
            records = await dal.query_by_condition(plugin_name=custom_name, module_name=module_name)

        matched = [x for x in records if x.call_data.get('dirty_runtime_value') is not None]
        assert matched, '脏值兜底记录未落库'
        assert isinstance(matched[-1].call_data['dirty_runtime_value'], str)

    async def test_statistic_skips_temp_matcher(self, app: App, test_onebot_v11_bot) -> None:
        """临时会话 matcher 不参与统计"""
        from src.database import StatisticDAL
        from src.database.helpers import database_session
        from src.service.omega_processor.universal.statistic import postprocessor_statistic

        plugin_id, module_name, custom_name = _get_metadata_plugin_info()
        matcher = _make_plugin_matcher(temp=True, plugin_id=plugin_id, module_name=module_name)

        async with app.test_api() as ctx:
            bot = _make_real_bot(ctx, test_onebot_v11_bot.self_id)
            event = _make_obv11_private_event(user_id=53901)

            async with database_session() as session:
                before = await StatisticDAL(session=session).count_by_condition(module_name=module_name)
                await postprocessor_statistic(bot=bot, event=event, matcher=matcher, db_session=session)
                after = await StatisticDAL(session=session).count_by_condition(module_name=module_name)

        assert after == before


@pytest.fixture
async def plugin_enabled_guard():
    """保证 omega_processor 插件行存在且启用, 测试后恢复原状态

    全量套件中 test_001_database 的迁移检查会 drop_all_tables 清空插件表,
    不能依赖会话启动时播种的插件行仍然存在
    """
    from sqlalchemy.exc import NoResultFound

    from src.database import PluginDAL
    from src.database.helpers import database_session

    # 快照原状态并确保插件行存在且启用
    async with database_session() as session:
        dal = PluginDAL(session=session)
        try:
            plugin = await dal.query_unique(plugin_name='omega_processor', module_name='src.service.omega_processor')
            original_enabled, original_info = plugin.enabled, plugin.info
        except NoResultFound:
            original_enabled, original_info = None, None
        await dal.add_update_exist(
            plugin_name='omega_processor',
            module_name='src.service.omega_processor',
            enabled=1,
            info=original_info,
        )

    yield

    # 恢复原状态 (原不存在则删除, 否则恢复 enabled/info 原值)
    async with database_session() as session:
        dal = PluginDAL(session=session)
        if original_enabled is None:
            await dal.delete(plugin_name='omega_processor', module_name='src.service.omega_processor')
        else:
            await dal.add_update_exist(
                plugin_name='omega_processor',
                module_name='src.service.omega_processor',
                enabled=original_enabled,
                info=original_info,
            )


class TestPluginManager:
    """插件管理预处理器测试 (真实数据库, save/restore 保护)"""

    async def test_enabled_plugin_passes(self, plugin_enabled_guard) -> None:
        from src.database.helpers import database_session
        from src.service.omega_processor.universal.plugin import preprocessor_plugin_manager

        matcher = _make_plugin_matcher()

        async with database_session() as session:
            await preprocessor_plugin_manager(
                bot=_make_mock_bot(), event=_make_obv11_private_event(), matcher=matcher, db_session=session,
            )

    async def test_disabled_plugin_blocked(self, plugin_enabled_guard) -> None:
        from nonebot.exception import IgnoredException

        from src.database import PluginDAL
        from src.database.helpers import database_session
        from src.service.omega_processor.universal.plugin import preprocessor_plugin_manager

        async with database_session() as session:
            await PluginDAL(session=session).add_update_exist(
                plugin_name='omega_processor',
                module_name='src.service.omega_processor',
                enabled=0,
                info='Disabled for test',
            )

        matcher = _make_plugin_matcher()

        async with database_session() as session:
            with pytest.raises(IgnoredException, match='插件未启用'):
                await preprocessor_plugin_manager(
                    bot=_make_mock_bot(), event=_make_obv11_private_event(), matcher=matcher, db_session=session,
                )

    async def test_unregistered_plugin_blocked(self, plugin_enabled_guard) -> None:
        from nonebot.exception import IgnoredException

        from src.database import PluginDAL
        from src.database.helpers import database_session
        from src.service.omega_processor.universal.plugin import preprocessor_plugin_manager

        async with database_session() as session:
            await PluginDAL(session=session).delete(
                plugin_name='omega_processor', module_name='src.service.omega_processor',
            )

        matcher = _make_plugin_matcher()

        async with database_session() as session:
            with pytest.raises(IgnoredException, match='插件未启用'):
                await preprocessor_plugin_manager(
                    bot=_make_mock_bot(), event=_make_obv11_private_event(), matcher=matcher, db_session=session,
                )

    async def test_non_plugin_matcher_ignored(self) -> None:
        from nonebot.matcher import Matcher

        from src.database.helpers import database_session
        from src.service.omega_processor.universal.plugin import preprocessor_plugin_manager

        matcher = type('NonPluginMatcher', (Matcher,), {'plugin_id': None, 'temp': False})()

        async with database_session() as session:
            await preprocessor_plugin_manager(
                bot=_make_mock_bot(), event=_make_obv11_private_event(), matcher=matcher, db_session=session,
            )

    async def test_super_user_ignored(self, app: App, plugin_enabled_guard) -> None:
        """超级用户跳过插件启用检查 (以禁用插件为背景, 对照组普通用户被阻断, 排除假阳性)"""
        from nonebot.exception import IgnoredException

        from src.database import PluginDAL
        from src.database.helpers import database_session
        from src.service.omega_processor.universal.plugin import preprocessor_plugin_manager

        async with database_session() as session:
            await PluginDAL(session=session).add_update_exist(
                plugin_name='omega_processor',
                module_name='src.service.omega_processor',
                enabled=0,
                info='Disabled for superuser test',
            )

        matcher = _make_plugin_matcher()

        async with app.test_api() as ctx:
            bot = _make_real_bot(ctx, _unique_id('TEST_PM_SU_BOT'))

            async with database_session() as session:
                # 超级用户在插件已禁用时仍跳过检查
                await preprocessor_plugin_manager(
                    bot=bot, event=_make_fake_message_event(user_id='User'), matcher=matcher, db_session=session,
                )

                # 对照: 普通用户在插件禁用时被阻断
                with pytest.raises(IgnoredException, match='插件未启用'):
                    await preprocessor_plugin_manager(
                        bot=bot, event=_make_fake_message_event(user_id='10001'), matcher=matcher, db_session=session,
                    )

    async def test_startup_init_preserves_disabled_plugin(self, plugin_enabled_guard) -> None:
        """启动初始化不应重置已禁用插件的启用状态"""
        from src.database import PluginDAL
        from src.database.helpers import database_session
        from src.service.omega_processor.universal.plugin import _startup_init_plugins

        async with database_session() as session:
            await PluginDAL(session=session).add_update_exist(
                plugin_name='omega_processor',
                module_name='src.service.omega_processor',
                enabled=0,
                info='Disabled by OPM',
            )

        await _startup_init_plugins()

        async with database_session() as session:
            plugin = await PluginDAL(session=session).query_unique(
                plugin_name='omega_processor', module_name='src.service.omega_processor',
            )
        assert plugin.enabled == 0
        assert plugin.info == 'Disabled by OPM'

    async def test_startup_init_inserts_missing_plugin(self, plugin_enabled_guard) -> None:
        """启动初始化应以启用状态补插缺失的插件行"""
        from src.database import PluginDAL
        from src.database.helpers import database_session
        from src.service.omega_processor.universal.plugin import _startup_init_plugins

        async with database_session() as session:
            await PluginDAL(session=session).delete(
                plugin_name='omega_processor', module_name='src.service.omega_processor',
            )

        await _startup_init_plugins()

        async with database_session() as session:
            plugin = await PluginDAL(session=session).query_unique(
                plugin_name='omega_processor', module_name='src.service.omega_processor',
            )
        assert plugin.enabled == 1


@pytest.fixture(scope='class')
async def test_pipeline_bot(test_db_data_factory):
    """管线测试用 Bot: 数字 self_id (OneBot V11 事件模型要求 int) 且已落库

    omega_base 中间件的 self_id 校验预处理器要求 event.self_id == bot.self_id,
    且好感度/历史后处理器会经实体初始化要求 bot 行存在, 故 bot 身份须全程一致
    """
    from src.database.internal.bot import BotType

    self_id = str(random.randint(10_000_000, 99_999_999))
    bot = await test_db_data_factory.create_test_bot(bot_type=BotType.ONEBOT_V11, bot_self_id=self_id)

    try:
        yield bot
    finally:
        await test_db_data_factory.delete_test_bot(bot=bot)


class TestFullPipeline:
    """完整事件管线测试 (nonebug test_matcher 驱动真实处理器链)"""

    @staticmethod
    def _make_pipeline_matcher(cmd: str, **state_kwargs: Any) -> 'Matcher':
        """创建注册进全局表的命令 matcher, 归属 omega_processor 插件并携带 processor state"""
        from nonebot import on_command
        from nonebot.matcher import MatcherSource

        from src.service.omega_processor import enable_processor_state

        matcher = on_command(cmd, state=enable_processor_state(name=cmd, **state_kwargs))
        # Matcher.plugin 为读取 _source 的 classproperty, 经 MatcherSource 归属插件
        matcher._source = MatcherSource(
            plugin_id=_get_omega_processor_plugin_id(),
            module_name='src.service.omega_processor',
        )
        return matcher

    @staticmethod
    def _make_pipeline_bot(ctx, self_id: str):
        from nonebot.adapters.onebot.v11 import Adapter, Bot

        adapter = nonebot.get_adapter(Adapter)
        return ctx.create_bot(self_id=self_id, base=Bot, adapter=adapter, auto_connect=False)

    @staticmethod
    def _make_pipeline_event(bot_self_id: str, user_id: int, text: str) -> 'BaseEvent':
        """构造与 bot 身份一致且 message_id 唯一的管线事件 (history 唯一键约束要求)"""
        return _make_obv11_private_event(
            user_id=user_id,
            text=text,
            self_id=int(bot_self_id),
            message_id=random.randint(1_000_000, 2_000_000_000),
        )

    async def test_authorized_command_runs_handler(self, app: App, test_pipeline_bot, plugin_enabled_guard) -> None:
        """授权链路: 预配置实体权限后命令经全部预处理器正常执行"""

        cmd = _unique_id('pipe_ok')
        matcher = self._make_pipeline_matcher(cmd, level=1)
        user_id = random.randint(10_000_000, 99_999_999)

        await _grant_entity_permissions(
            test_pipeline_bot.bot_type, test_pipeline_bot.self_id, 'onebot_v11_user', str(user_id), level=1,
        )

        @matcher.handle()
        async def _handle() -> None:
            await matcher.finish('done')

        async with app.test_matcher(matcher) as ctx:
            bot = self._make_pipeline_bot(ctx, test_pipeline_bot.self_id)
            event = self._make_pipeline_event(test_pipeline_bot.self_id, user_id, f'/{cmd}')

            ctx.receive_event(bot, event)
            ctx.should_pass_rule(matcher=matcher)
            ctx.should_pass_permission(matcher=matcher)
            ctx.should_call_send(event, 'done', 'result', bot=bot)
            ctx.should_finished(matcher=matcher)

    async def test_global_permission_denied_blocks_handler(
            self, app: App, test_pipeline_bot, plugin_enabled_guard,
    ) -> None:
        """全局权限拒绝链路: 发送初始化提示后命令被忽略, handler 不执行"""
        cmd = _unique_id('pipe_deny')
        matcher = self._make_pipeline_matcher(cmd, level=1)
        user_id = random.randint(10_000_000, 99_999_999)

        async with app.test_matcher(matcher) as ctx:
            bot = self._make_pipeline_bot(ctx, test_pipeline_bot.self_id)
            event = self._make_pipeline_event(test_pipeline_bot.self_id, user_id, f'/{cmd}')

            ctx.receive_event(bot, event)
            ctx.should_pass_rule(matcher=matcher)
            ctx.should_pass_permission(matcher=matcher)
            # 权限预处理器发送全局功能未启用提示后被忽略, 不声明 handler 动作
            ctx.should_call_send(
                event, 'Omega Miya 未启用, 请尝试使用 "/Start" 命令初始化, 或联系管理员处理', 'result', bot=bot,
            )

    async def test_cooldown_blocks_second_invocation(self, app: App, test_pipeline_bot, plugin_enabled_guard) -> None:
        """冷却链路: 同一用户两轮事件, 第二轮在冷却期内被忽略"""
        cmd = _unique_id('pipe_cd')
        matcher = self._make_pipeline_matcher(
            cmd, level=1, cooldown=60, cooldown_type='user', echo_processor_result=False,
        )
        user_id = random.randint(10_000_000, 99_999_999)

        await _grant_entity_permissions(
            test_pipeline_bot.bot_type, test_pipeline_bot.self_id, 'onebot_v11_user', str(user_id), level=1,
        )

        @matcher.handle()
        async def _handle() -> None:
            await matcher.finish('done')

        async with app.test_matcher(matcher) as ctx:
            bot = self._make_pipeline_bot(ctx, test_pipeline_bot.self_id)

            # 第一轮: 通过全部检查并执行 handler
            event_1 = self._make_pipeline_event(test_pipeline_bot.self_id, user_id, f'/{cmd}')
            ctx.receive_event(bot, event_1)
            ctx.should_pass_rule(matcher=matcher)
            ctx.should_pass_permission(matcher=matcher)
            ctx.should_call_send(event_1, 'done', 'result', bot=bot)
            ctx.should_finished(matcher=matcher)

            # 第二轮: 冷却期内被忽略 (echo 已关闭, 无任何发送), handler 不执行
            event_2 = self._make_pipeline_event(test_pipeline_bot.self_id, user_id, f'/{cmd}')
            ctx.receive_event(bot, event_2)
            ctx.should_pass_rule(matcher=matcher)
            ctx.should_pass_permission(matcher=matcher)

    async def test_non_plugin_matcher_bypasses_processors(
            self, app: App, test_pipeline_bot, plugin_enabled_guard,
    ) -> None:
        """非插件 matcher: 全部预处理器跳过, handler 直接执行"""
        from nonebot import on_command

        cmd = _unique_id('pipe_bare')
        matcher = on_command(cmd)

        @matcher.handle()
        async def _handle() -> None:
            await matcher.finish('bare done')

        async with app.test_matcher(matcher) as ctx:
            bot = self._make_pipeline_bot(ctx, test_pipeline_bot.self_id)
            event = self._make_pipeline_event(test_pipeline_bot.self_id, 54001, f'/{cmd}')

            ctx.receive_event(bot, event)
            ctx.should_pass_rule(matcher=matcher)
            ctx.should_pass_permission(matcher=matcher)
            ctx.should_call_send(event, 'bare done', 'result', bot=bot)
            ctx.should_finished(matcher=matcher)


def _make_telegram_photo_event(*, with_reply: bool = False) -> 'BaseEvent':
    """构造携带 photo 消息段的 Telegram 私聊消息事件"""
    from nonebot.adapters.telegram.event import PrivateMessageEvent

    payload: dict[str, Any] = {
        'message_id': 1,
        'date': 1,
        'chat': {'id': 10001, 'type': 'private', 'first_name': 'Tester'},
        'from': {'id': 10001, 'is_bot': False, 'first_name': 'Tester'},
        'message': [{'type': 'photo', 'data': {'file': 'file_id_1'}}],
        'original_message': [{'type': 'photo', 'data': {'file': 'file_id_1'}}],
    }
    if with_reply:
        payload['reply_to_message'] = {
            'message_id': 2,
            'date': 1,
            'chat': {'id': 10001, 'type': 'private', 'first_name': 'Tester'},
            'from': {'id': 10001, 'is_bot': False, 'first_name': 'Tester'},
            'message': [{'type': 'photo', 'data': {'file': 'file_id_2'}}],
            'original_message': [{'type': 'photo', 'data': {'file': 'file_id_2'}}],
        }
    return PrivateMessageEvent.model_validate(payload)


class TestTelegramImageParser:
    """Telegram 图片解析预处理器测试 (nonebug test_api)"""

    @staticmethod
    def _make_telegram_bot(ctx):
        from nonebot.adapters.telegram import Adapter, Bot
        from nonebot.adapters.telegram.config import BotConfig as TelegramBotConfig

        adapter = nonebot.get_adapter(Adapter)
        return ctx.create_bot(
            self_id='TEST_TG_PARSER_BOT',
            base=Bot,
            adapter=adapter,
            auto_connect=False,
            config=TelegramBotConfig(token='123456:TEST_TOKEN'),
        )

    async def test_photo_segment_parsed_with_url(self, app: App) -> None:
        from src.service.omega_processor.message.telegram_image_parser import (
            handle_parse_message_image_event_preprocessor,
        )

        async with app.test_api() as ctx:
            bot = self._make_telegram_bot(ctx)
            event = _make_telegram_photo_event()

            ctx.should_call_api(
                'get_file', {'file_id': 'file_id_1'},
                {'file_id': 'file_id_1', 'file_unique_id': 'uniq_1', 'file_path': 'photos/file_1.jpg'},
            )

            await handle_parse_message_image_event_preprocessor(bot=bot, event=event)

            assert event.message[0].data['_parsed_url'] == (
                'https://api.telegram.org/file/bot123456%3ATEST_TOKEN/photos/file_1.jpg'
            )
            assert ctx.wait_list.empty()

    async def test_reply_message_also_parsed(self, app: App) -> None:
        from src.service.omega_processor.message.telegram_image_parser import (
            handle_parse_message_image_event_preprocessor,
        )

        async with app.test_api() as ctx:
            bot = self._make_telegram_bot(ctx)
            event = _make_telegram_photo_event(with_reply=True)

            ctx.should_call_api(
                'get_file', {'file_id': 'file_id_1'},
                {'file_id': 'file_id_1', 'file_unique_id': 'uniq_1', 'file_path': 'photos/file_1.jpg'},
            )
            ctx.should_call_api(
                'get_file', {'file_id': 'file_id_2'},
                {'file_id': 'file_id_2', 'file_unique_id': 'uniq_2', 'file_path': 'photos/file_2.jpg'},
            )

            await handle_parse_message_image_event_preprocessor(bot=bot, event=event)

            assert '_parsed_url' in event.message[0].data
            assert '_parsed_url' in event.reply_to_message.message[0].data
            assert ctx.wait_list.empty()

    async def test_sticker_segment_parsed(self, app: App) -> None:
        from nonebot.adapters.telegram.event import PrivateMessageEvent

        from src.service.omega_processor.message.telegram_image_parser import (
            handle_parse_message_image_event_preprocessor,
        )

        async with app.test_api() as ctx:
            bot = self._make_telegram_bot(ctx)
            payload: dict[str, Any] = {
                'message_id': 1,
                'date': 1,
                'chat': {'id': 10001, 'type': 'private', 'first_name': 'Tester'},
                'from': {'id': 10001, 'is_bot': False, 'first_name': 'Tester'},
                'message': [{'type': 'sticker', 'data': {'file': 'sticker_file_id'}}],
                'original_message': [{'type': 'sticker', 'data': {'file': 'sticker_file_id'}}],
            }
            event = PrivateMessageEvent.model_validate(payload)

            ctx.should_call_api(
                'get_file', {'file_id': 'sticker_file_id'},
                {'file_id': 'sticker_file_id', 'file_unique_id': 'uniq_s', 'file_path': 'stickers/sticker.webp'},
            )

            await handle_parse_message_image_event_preprocessor(bot=bot, event=event)

            assert '_parsed_url' in event.message[0].data

    async def test_empty_file_path_keeps_segment(self, app: App) -> None:
        from src.service.omega_processor.message.telegram_image_parser import (
            handle_parse_message_image_event_preprocessor,
        )

        async with app.test_api() as ctx:
            bot = self._make_telegram_bot(ctx)
            event = _make_telegram_photo_event()

            ctx.should_call_api('get_file', {'file_id': 'file_id_1'}, {'file_id': 'file_id_1', 'file_path': None})

            await handle_parse_message_image_event_preprocessor(bot=bot, event=event)

            assert '_parsed_url' not in event.message[0].data

    async def test_api_failure_falls_back_to_original(self, app: App) -> None:
        from src.service.omega_processor.message.telegram_image_parser import (
            handle_parse_message_image_event_preprocessor,
        )

        async with app.test_api() as ctx:
            bot = self._make_telegram_bot(ctx)
            event = _make_telegram_photo_event()

            ctx.should_call_api('get_file', {'file_id': 'file_id_1'}, exception=RuntimeError('telegram error'))

            await handle_parse_message_image_event_preprocessor(bot=bot, event=event)

            assert '_parsed_url' not in event.message[0].data
            assert event.message[0].data['file'] == 'file_id_1'

    async def test_text_segment_untouched(self, app: App) -> None:
        from nonebot.adapters.telegram.event import PrivateMessageEvent

        from src.service.omega_processor.message.telegram_image_parser import (
            handle_parse_message_image_event_preprocessor,
        )

        async with app.test_api() as ctx:
            bot = self._make_telegram_bot(ctx)
            payload: dict[str, Any] = {
                'message_id': 1,
                'date': 1,
                'chat': {'id': 10001, 'type': 'private', 'first_name': 'Tester'},
                'from': {'id': 10001, 'is_bot': False, 'first_name': 'Tester'},
                'message': [{'type': 'text', 'data': {'text': 'plain text'}}],
            }
            event = PrivateMessageEvent.model_validate(payload)

            await handle_parse_message_image_event_preprocessor(bot=bot, event=event)

            assert event.message[0].type == 'text'
            assert event.message[0].data == {'text': 'plain text'}
            assert ctx.wait_list.empty()

    async def test_event_preprocessor_guard_non_message_event(self) -> None:
        """事件级预处理器对非 Telegram 消息事件不做处理"""
        from src.service.omega_processor.message.telegram_image_parser import handle_telegram_event_preprocessor

        await handle_telegram_event_preprocessor(bot=_make_mock_bot(), event=_make_obv11_private_event())
