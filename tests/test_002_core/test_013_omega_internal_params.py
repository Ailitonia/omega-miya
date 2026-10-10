"""
@Author         : Ailitonia
@Date           : 2026/10/10 12:50
@FileName       : test_013_omega_internal_params
@Project        : omega-miya
@Description    : omega params 模块单元测试 (handler 工厂/权限规则/子依赖/订阅管理模板)
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import random
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, ClassVar
from unittest.mock import AsyncMock, MagicMock

import nonebot
import pytest
from nonebug import App

from tests.test_002_core.helpers import (
    make_fake_message_event,
    make_mock_bot,
    make_non_plugin_matcher,
    make_obv11_group_message_event,
    make_obv11_private_message_event,
    registered_online_bot,
    unique_test_id,
)
from tests.utils import make_fake_event

if TYPE_CHECKING:
    from nonebot.adapters.onebot.v11 import Bot as OneBotV11Bot

    from src.service import OmegaMatcherInterface


def _make_real_obv11_bot(self_id: str = '10086') -> 'OneBotV11Bot':
    """构造真实 OneBot V11 Bot 实例 (不建立连接, 仅满足依赖注入的实例校验)"""
    from nonebot.adapters.onebot.v11 import Adapter, Bot

    return Bot(nonebot.get_adapter(Adapter), self_id)


def _flatten_exceptions(exc: BaseException) -> list[BaseException]:
    """递归展开 ExceptionGroup 为扁平异常列表"""
    if isinstance(exc, BaseExceptionGroup):
        return [sub for group in exc.exceptions for sub in _flatten_exceptions(group)]
    return [exc]


@pytest.fixture
def log_capture() -> Generator[list[str], None, None]:
    """捕获 WARNING 及以上级别日志文本, 测试结束后移除临时 sink"""
    from loguru import logger

    records: list[str] = []
    sink_id = logger.add(lambda message: records.append(str(message)), level='WARNING')
    try:
        yield records
    finally:
        logger.remove(sink_id)


@pytest.fixture
def recording_uni_message(monkeypatch: pytest.MonkeyPatch) -> list:
    """以记录型替身子类重绑定 omega_base 适配器模块命名空间内的 UniMessage 名字

    仅替换 src.service.omega_base.internal.adapter 模块内的名字绑定 (不污染第三方类本身),
    经统一接口发送的消息实例被记录到返回的列表中, send 返回 MagicMock 作为 Receipt 替身
    """
    from nonebot_plugin_alconna.uniseg import UniMessage

    import src.service.omega_base.internal.adapter as adapter_module

    sent_messages: list = []

    class _RecordingUniMessage(UniMessage):
        async def send(self, *args: Any, **kwargs: Any) -> Any:
            sent_messages.append(self)
            return MagicMock()

    monkeypatch.setattr(adapter_module, 'UniMessage', _RecordingUniMessage)
    return sent_messages


@pytest.fixture
async def subscription_manager_stub_cls() -> AsyncGenerator[Any, None]:
    """构造行为可编程的 BaseSubscriptionManager 测试子类工厂

    每次调用生成一个使用唯一 sub_type 的 stub 子类, 测试结束后清理该 sub_type 产生的
    SocialMediaContent 行与 SubscriptionSource 行 (级联清理订阅关系行)
    """
    from sqlalchemy import delete

    from src.database import SubscriptionSourceDAL
    from src.database.helpers import database_session
    from src.database.internal.social_media_content import SocialMediaContent
    from src.database.internal.subscription_source import SubscriptionSource
    from src.database.schema import SocialMediaContentOrm
    from src.params.template.subscription_manager import BaseSubscriptionManager

    created_sub_types: list[str] = []

    def _factory(
            *,
            items: list[dict] | None = None,
            format_none: bool = False,
            parse_fail_mids: frozenset[str] | set[str] = frozenset(),
    ) -> type:
        sub_type = unique_test_id('TEST_STUB_SUB')
        created_sub_types.append(sub_type)

        class _StubSubscriptionManager(BaseSubscriptionManager[dict]):
            """测试用订阅管理器: 内存数据源, 内容以 {'mid': str} 字典表示"""

            _items = list(items) if items else []
            _format_none = format_none
            _parse_fail_mids = frozenset(parse_fail_mids)
            postprocessed: ClassVar[list] = []

            @classmethod
            def get_sub_type(cls) -> str:
                return sub_type

            @staticmethod
            def _get_smc_item_mid(smc_item: dict) -> str:
                return smc_item['mid']

            async def _query_sub_source_smc_items(self) -> list[dict]:
                return list(self._items)

            @classmethod
            def _parse_smc_item(cls, smc_item: dict) -> 'SocialMediaContent':
                mid = smc_item['mid']
                if mid in cls._parse_fail_mids:
                    raise ValueError(f'parse failed for {mid}')
                return SocialMediaContent(
                    id=-1,
                    source=cls.get_sub_type(),
                    m_type='test',
                    m_id=mid,
                    m_uid='test_uid',
                    title=f'test title {mid}',
                    raw_data={'mid': mid},
                    content=None,
                    ref_content=None,
                    published_at=None,
                    created_at=None,
                    updated_at=None,
                )

            async def query_sub_source_data(self) -> 'SubscriptionSource':
                return SubscriptionSource(
                    id=-1,
                    sub_type=sub_type,
                    sub_id=self.sub_id,
                    sub_user_name=f'test_user_{self.sub_id}',
                    sub_info=None,
                    created_at=None,
                    updated_at=None,
                )

            @classmethod
            async def _format_smc_item_message(cls, smc_item: dict) -> str | None:
                if cls._format_none:
                    return None
                return f'formatted:{smc_item["mid"]}'

            async def _entity_message_send_postprocessor(self, receipt: Any, smc_item: dict) -> None:
                self.postprocessed.append(smc_item)

        return _StubSubscriptionManager

    yield _factory

    # 清理 stub 子类产生的数据库行
    for sub_type in created_sub_types:
        async with SubscriptionSourceDAL.create() as dal:
            for source in await dal.query_type_all(sub_type=sub_type):
                await dal.delete(sub_type=sub_type, sub_id=source.sub_id)
        async with database_session() as session:
            await session.execute(delete(SocialMediaContentOrm).where(SocialMediaContentOrm.source == sub_type))


class TestModuleContract:
    """模块导出契约测试"""

    @pytest.mark.parametrize(('module_path', 'expected_all'), [
        ('src.params.handler', {
            'get_command_str_single_arg_parser_handler',
            'get_command_str_multi_args_parser_handler',
            'get_command_message_arg_parser_handler',
            'get_set_default_state_handler',
            'get_shell_command_parse_failed_handler',
        }),
        ('src.params.rule', {
            'event_has_global_permission',
            'event_has_permission_level',
            'event_has_permission_node',
            'user_has_global_permission',
            'user_has_permission_level',
            'user_has_permission_node',
        }),
        ('src.params.permission', {'IS_ADMIN', 'check_event_is_admin', 'check_event_is_superuser'}),
        ('src.params.depends', {
            'ARTWORK_COLLECTION_DAL',
            'BOT_SELF_DAL',
            'ENTITY_DAL',
            'EVENT_E_IFACE',
            'EVENT_ENTITY_PROFILE_IMAGE_URL',
            'EVENT_M_IFACE',
            'GLOBAL_CACHE_DAL',
            'HISTORY_DAL',
            'PLUGIN_DAL',
            'SOCIAL_MEDIA_CONTENT_DAL',
            'STATISTIC_DAL',
            'SUBSCRIPTION_SOURCE_DAL',
            'SYSTEM_SETTING_DAL',
            'USER_E_IFACE',
            'USER_ENTITY_PROFILE_IMAGE_URL',
            'USER_M_IFACE',
            'state_plain_text',
        }),
        ('src.params.template.subscription_manager', {'BaseSubscriptionManager', 'SubscriptionHandlerFactory'}),
    ])
    def test_module_all(self, module_path: str, expected_all: set) -> None:
        import importlib

        module = importlib.import_module(module_path)

        assert set(module.__all__) == expected_all
        for name in module.__all__:
            assert getattr(module, name) is not None


class TestCommandStrSingleArgParserHandler:
    """单个文本命令参数解析 handler 测试 (直接调用)"""

    @staticmethod
    async def _run(handler: Any, text: str) -> dict:
        from nonebot.adapters.onebot.v11 import Message

        state: dict = {}
        await handler(state, Message(text))
        return state

    async def test_arg_extracted_and_stripped(self) -> None:
        from src.params.handler import get_command_str_single_arg_parser_handler

        handler = get_command_str_single_arg_parser_handler('test_key')
        assert await self._run(handler, '  hello  ') == {'test_key': 'hello'}

    async def test_whitespace_arg_treated_as_empty(self) -> None:
        from src.params.handler import get_command_str_single_arg_parser_handler

        handler = get_command_str_single_arg_parser_handler('test_key')
        assert await self._run(handler, '   ') == {}

    async def test_default_used_when_empty(self) -> None:
        from src.params.handler import get_command_str_single_arg_parser_handler

        handler = get_command_str_single_arg_parser_handler('test_key', default='200')
        assert await self._run(handler, '') == {'test_key': '200'}

    async def test_empty_string_default_is_honored(self) -> None:
        """显式传入空字符串默认值时应写入空字符串而非忽略"""
        from src.params.handler import get_command_str_single_arg_parser_handler

        handler = get_command_str_single_arg_parser_handler('test_key', default='')
        assert await self._run(handler, '') == {'test_key': ''}

    async def test_ensure_key_sets_none(self) -> None:
        from src.params.handler import get_command_str_single_arg_parser_handler

        handler = get_command_str_single_arg_parser_handler('test_key', ensure_key=True)
        assert await self._run(handler, '') == {'test_key': None}

    async def test_default_and_ensure_key_priority(self) -> None:
        from src.params.handler import get_command_str_single_arg_parser_handler

        handler = get_command_str_single_arg_parser_handler('test_key', default='fallback', ensure_key=True)
        # 无参数时 default 优先于 ensure_key
        assert await self._run(handler, '') == {'test_key': 'fallback'}
        # 有参数时参数优先于 default
        assert await self._run(handler, 'value') == {'test_key': 'value'}


class TestCommandStrMultiArgsParserHandler:
    """多个文本命令参数解析 handler 测试 (直接调用)"""

    @staticmethod
    async def _run(handler: Any, text: str) -> dict:
        from nonebot.adapters.onebot.v11 import Message

        state: dict = {}
        await handler(state, Message(text))
        return state

    async def test_split_all_args(self) -> None:
        from src.params.handler import get_command_str_multi_args_parser_handler

        handler = get_command_str_multi_args_parser_handler('arg')
        assert await self._run(handler, 'a b  c') == {'arg_0': 'a', 'arg_1': 'b', 'arg_2': 'c'}

    async def test_extra_args_merged_into_last_key(self) -> None:
        """ensure_keys_num 限定了分割次数, 超出数量的参数以空白连接合并入末位 key"""
        from src.params.handler import get_command_str_multi_args_parser_handler

        handler = get_command_str_multi_args_parser_handler('arg', ensure_keys_num=2)
        assert await self._run(handler, 'a b c d') == {'arg_0': 'a', 'arg_1': 'b c d'}

    async def test_missing_args_filled_with_default(self) -> None:
        from src.params.handler import get_command_str_multi_args_parser_handler

        handler = get_command_str_multi_args_parser_handler('arg', default='d', ensure_keys_num=2)
        assert await self._run(handler, 'x') == {'arg_0': 'x', 'arg_1': 'd'}

    async def test_missing_args_filled_with_none(self) -> None:
        """default 缺省时以 None 填充缺位"""
        from src.params.handler import get_command_str_multi_args_parser_handler

        handler = get_command_str_multi_args_parser_handler('arg', ensure_keys_num=2)
        assert await self._run(handler, 'x') == {'arg_0': 'x', 'arg_1': None}

    async def test_ensure_one_key_disables_splitting(self) -> None:
        """ensure_keys_num=1 时全部文本作为单个参数不分割"""
        from src.params.handler import get_command_str_multi_args_parser_handler

        handler = get_command_str_multi_args_parser_handler('arg', ensure_keys_num=1)
        assert await self._run(handler, 'a b c') == {'arg_0': 'a b c'}

    async def test_empty_input_without_ensure_keeps_state(self) -> None:
        from src.params.handler import get_command_str_multi_args_parser_handler

        handler = get_command_str_multi_args_parser_handler('arg')
        assert await self._run(handler, '   ') == {}

    async def test_empty_input_with_ensure_fills_default(self) -> None:
        from src.params.handler import get_command_str_multi_args_parser_handler

        handler = get_command_str_multi_args_parser_handler('arg', default='d', ensure_keys_num=2)
        assert await self._run(handler, '') == {'arg_0': 'd', 'arg_1': 'd'}

    async def test_negative_ensure_keys_num_behaves_as_zero(self) -> None:
        from src.params.handler import get_command_str_multi_args_parser_handler

        handler = get_command_str_multi_args_parser_handler('arg', ensure_keys_num=-1)
        assert await self._run(handler, 'a b') == {'arg_0': 'a', 'arg_1': 'b'}

    async def test_default_without_ensure_keys_num_is_ignored(self) -> None:
        """default 仅在 ensure_keys_num > 0 时生效, 单独传入不产生效果"""
        from src.params.handler import get_command_str_multi_args_parser_handler

        handler = get_command_str_multi_args_parser_handler('arg', default='d')
        assert await self._run(handler, 'a b') == {'arg_0': 'a', 'arg_1': 'b'}
        assert await self._run(handler, '') == {}


class TestCommandMessageArgParserHandler:
    """单个消息命令参数解析 handler 测试 (真实 matcher 实例)"""

    async def test_message_arg_set_as_is(self) -> None:
        from nonebot.adapters.onebot.v11 import Message

        from src.params.handler import get_command_message_arg_parser_handler

        matcher = make_non_plugin_matcher()
        message = Message('hello')
        handler = get_command_message_arg_parser_handler('arg')
        await handler(matcher, message)

        assert matcher.state['arg'] is message

    async def test_empty_message_uses_default(self) -> None:
        from nonebot.adapters.onebot.v11 import Message

        from src.params.handler import get_command_message_arg_parser_handler

        matcher = make_non_plugin_matcher()
        handler = get_command_message_arg_parser_handler('arg', default='fallback')
        await handler(matcher, Message())

        assert matcher.state['arg'].extract_plain_text() == 'fallback'

    async def test_empty_string_default_is_honored(self) -> None:
        from nonebot.adapters.onebot.v11 import Message

        from src.params.handler import get_command_message_arg_parser_handler

        matcher = make_non_plugin_matcher()
        handler = get_command_message_arg_parser_handler('arg', default='')
        await handler(matcher, Message())

        assert matcher.state['arg'].extract_plain_text() == ''

    async def test_empty_message_with_ensure_key(self) -> None:
        from nonebot.adapters.onebot.v11 import Message

        from src.params.handler import get_command_message_arg_parser_handler

        matcher = make_non_plugin_matcher()
        handler = get_command_message_arg_parser_handler('arg', ensure_key=True)
        await handler(matcher, Message())

        assert matcher.state['arg'].extract_plain_text() == ''

    async def test_empty_message_without_config_keeps_state(self) -> None:
        from nonebot.adapters.onebot.v11 import Message

        from src.params.handler import get_command_message_arg_parser_handler

        matcher = make_non_plugin_matcher()
        handler = get_command_message_arg_parser_handler('arg')
        await handler(matcher, Message())

        assert 'arg' not in matcher.state


class TestGetSetDefaultStateHandler:
    """State 默认值设置 handler 测试 (直接调用)"""

    async def test_set_key_and_value(self) -> None:
        from src.params.handler import get_set_default_state_handler

        state: dict = {}
        await get_set_default_state_handler('k', 'v')(state)
        assert state == {'k': 'v'}

    async def test_extra_data_merged(self) -> None:
        from src.params.handler import get_set_default_state_handler

        state: dict = {}
        await get_set_default_state_handler('k', 'v', extra_data={'a': 1, 'b': None})(state)
        assert state == {'k': 'v', 'a': 1, 'b': None}

    async def test_existing_keys_not_overwritten(self) -> None:
        from src.params.handler import get_set_default_state_handler

        state: dict = {'k': 'original', 'a': 'existing'}
        await get_set_default_state_handler('k', 'v', extra_data={'a': 1, 'b': 2})(state)
        assert state == {'k': 'original', 'a': 'existing', 'b': 2}

    async def test_extra_data_shadows_primary_key(self) -> None:
        """extra_data 与主 key 同名时按 dict.update 语义由 extra_data 覆盖"""
        from src.params.handler import get_set_default_state_handler

        state: dict = {}
        await get_set_default_state_handler('k', 'v', extra_data={'k': 'extra'})(state)
        assert state == {'k': 'extra'}


class TestShellCommandParseFailedHandler:
    """Shell 命令解析失败 handler 测试"""

    async def test_finish_with_error_message(self) -> None:
        from nonebot.exception import ParserExit

        from src.params.handler import get_shell_command_parse_failed_handler

        # matcher 为 don't-care 载体, 以 mock 断言 finish 调用
        matcher = MagicMock()
        matcher.finish = AsyncMock()

        handler = get_shell_command_parse_failed_handler()
        await handler(matcher, ParserExit(status=2, message='usage text'))

        matcher.finish.assert_awaited_once()
        sent_message = matcher.finish.await_args.args[0]
        assert '命令参数解析错误' in sent_message
        assert 'usage text' in sent_message


class TestStatePlainText:
    """state_plain_text 子依赖测试"""

    @pytest.mark.parametrize(('value', 'expected'), [
        ('plain', 'plain'),
        (123, '123'),
        (['a', 'b'], "['a', 'b']"),
    ])
    def test_value_coercion(self, value: Any, expected: str) -> None:
        from src.params.depends.handler import StatePlainTextInner

        assert StatePlainTextInner(key='k')(state={'k': value}) == expected

    def test_message_value_extracted(self) -> None:
        from nonebot.adapters.onebot.v11 import Message

        from src.params.depends.handler import StatePlainTextInner

        assert StatePlainTextInner(key='k')(state={'k': Message('hello')}) == 'hello'

    @pytest.mark.parametrize('state', [
        {},
        {'k': None},
        {'other': 'v'},
    ])
    def test_missing_key_raises_key_error(self, state: dict) -> None:
        from src.params.depends.handler import StatePlainTextInner

        with pytest.raises(KeyError, match="State has no key: '?k'?"):
            StatePlainTextInner(key='k')(state=state)

    async def test_depend_wiring(self, app: App) -> None:
        """依赖注入接线: Annotated + Depends 元数据应正确解析 State 中的值"""
        from typing import Annotated

        from nonebot.params import DependParam, StateParam

        from src.params.depends import state_plain_text

        async def dep(text: Annotated[str, state_plain_text('test_key')]) -> str:
            return text

        async with app.test_dependent(dep, allow_types=[DependParam, StateParam]) as ctx:
            ctx.pass_params(state={'test_key': 'wired'})
            ctx.should_return('wired')

    async def test_depend_wiring_missing_key_raises(self, app: App) -> None:
        from typing import Annotated

        from nonebot.params import DependParam, StateParam

        from src.params.depends import state_plain_text

        async def dep(text: Annotated[str, state_plain_text('absent_key')]) -> str:
            return text

        with pytest.raises(BaseExceptionGroup) as exc_info:
            async with app.test_dependent(dep, allow_types=[DependParam, StateParam]) as ctx:
                ctx.pass_params(state={})

        # 子依赖异常经依赖求解任务组包装为 ExceptionGroup 传播
        flattened = _flatten_exceptions(exc_info.value)
        assert any(isinstance(e, KeyError) and 'absent_key' in str(e) for e in flattened)


class TestDalDepends:
    """DAL 子依赖别名测试"""

    _DAL_ALIAS_PARAMS: ClassVar[list[tuple[str, str]]] = [
        ('ARTWORK_COLLECTION_DAL', 'ArtworkCollectionDAL'),
        ('BOT_SELF_DAL', 'BotSelfDAL'),
        ('ENTITY_DAL', 'EntityDAL'),
        ('GLOBAL_CACHE_DAL', 'GlobalCacheDAL'),
        ('HISTORY_DAL', 'HistoryDAL'),
        ('PLUGIN_DAL', 'PluginDAL'),
        ('SOCIAL_MEDIA_CONTENT_DAL', 'SocialMediaContentDAL'),
        ('STATISTIC_DAL', 'StatisticDAL'),
        ('SUBSCRIPTION_SOURCE_DAL', 'SubscriptionSourceDAL'),
        ('SYSTEM_SETTING_DAL', 'SystemSettingDAL'),
    ]

    def test_dal_alias_structure(self) -> None:
        """别名应为 Annotated[DAL, Depends(DAL.dal_dependence)] 结构"""
        import typing

        from src import database as database_module
        from src.params.depends import dal as dal_module

        for alias_name, dal_name in self._DAL_ALIAS_PARAMS:
            alias = getattr(dal_module, alias_name)
            dal_cls = getattr(database_module, dal_name)

            args = typing.get_args(alias.__value__)
            assert args[0] is dal_cls, alias_name
            assert args[1].dependency == dal_cls.dal_dependence, alias_name

    @pytest.mark.parametrize(('alias_name', 'dal_name'), _DAL_ALIAS_PARAMS)
    async def test_dal_depend_resolves(self, app: App, alias_name: str, dal_name: str) -> None:
        """经依赖注入解析应得到对应 DAL 实例 (真实数据库会话)"""
        from nonebot.params import DependParam

        from src import database as database_module
        from src.params.depends import dal as dal_module

        alias = getattr(dal_module, alias_name)
        dal_cls = getattr(database_module, dal_name)

        captured: dict = {}

        async def dep(dal):
            captured['dal'] = dal

        dep.__annotations__['dal'] = alias

        async with app.test_dependent(dep, allow_types=[DependParam]):
            pass

        assert type(captured['dal']) is dal_cls


class TestEntityDepends:
    """实体接口子依赖测试"""

    @staticmethod
    async def _run_dependent(app: App, dep: Any, **params: Any) -> None:
        """以统一的 Param 类型白名单驱动 test_dependent 并传入依赖参数"""
        from nonebot.params import BotParam, DependParam, EventParam, MatcherParam

        async with app.test_dependent(dep, allow_types=[DependParam, BotParam, EventParam, MatcherParam]) as ctx:
            ctx.pass_params(**params)

    async def test_matcher_interface_depends(self, app: App) -> None:
        from src.params.depends import EVENT_M_IFACE, USER_M_IFACE
        from src.service import OmegaMatcherInterface

        captured: dict = {}

        async def dep(event_iface: EVENT_M_IFACE, user_iface: USER_M_IFACE) -> None:
            captured['event_iface'] = event_iface
            captured['user_iface'] = user_iface

        bot = _make_real_obv11_bot()
        event = make_obv11_group_message_event(group_id=10000, user_id=10001)
        matcher = make_non_plugin_matcher()

        await self._run_dependent(app, dep, bot=bot, event=event, matcher=matcher)

        event_iface = captured['event_iface']
        user_iface = captured['user_iface']
        assert isinstance(event_iface, OmegaMatcherInterface)
        assert isinstance(user_iface, OmegaMatcherInterface)
        assert event_iface.acquire_type == 'event'
        assert user_iface.acquire_type == 'user'
        assert event_iface.bot is bot
        assert event_iface.event is event
        assert event_iface.matcher is matcher

    async def test_entity_interface_depends_distinguish_acquire_type(self, app: App) -> None:
        """群消息事件: event 实体为群, user 实体为发送者用户"""
        from src.database.internal.bot import BotType
        from src.database.internal.entity import EntityType
        from src.params.depends import EVENT_E_IFACE, USER_E_IFACE
        from src.service import OmegaEntityInterface

        captured: dict = {}

        async def dep(event_iface: EVENT_E_IFACE, user_iface: USER_E_IFACE) -> None:
            captured['event_iface'] = event_iface
            captured['user_iface'] = user_iface

        bot = _make_real_obv11_bot(self_id='10086')
        event = make_obv11_group_message_event(group_id=10000, user_id=10001)
        matcher = make_non_plugin_matcher()

        await self._run_dependent(app, dep, bot=bot, event=event, matcher=matcher)

        event_iface = captured['event_iface']
        user_iface = captured['user_iface']
        assert isinstance(event_iface, OmegaEntityInterface)
        assert isinstance(user_iface, OmegaEntityInterface)

        event_params = event_iface.entity_params
        assert event_params.bot_type is BotType.ONEBOT_V11
        assert event_params.bot_id == '10086'
        assert event_params.entity_type is EntityType.ONEBOT_V11_GROUP
        assert event_params.entity_id == '10000'

        user_params = user_iface.entity_params
        assert user_params.bot_type is BotType.ONEBOT_V11
        assert user_params.entity_type is EntityType.ONEBOT_V11_USER
        assert user_params.entity_id == '10001'

    async def test_profile_image_url_depends(self, app: App) -> None:
        """OneBot V11 头像 URL 为纯字符串构造 (无 API 调用), 直接断言 URL 形态"""
        from src.params.depends import EVENT_ENTITY_PROFILE_IMAGE_URL, USER_ENTITY_PROFILE_IMAGE_URL

        captured: dict = {}

        async def dep(event_url: EVENT_ENTITY_PROFILE_IMAGE_URL, user_url: USER_ENTITY_PROFILE_IMAGE_URL) -> None:
            captured['event_url'] = event_url
            captured['user_url'] = user_url

        bot = _make_real_obv11_bot()
        event = make_obv11_group_message_event(group_id=10000, user_id=10001)
        matcher = make_non_plugin_matcher()

        await self._run_dependent(app, dep, bot=bot, event=event, matcher=matcher)

        assert captured['event_url'] == 'https://p.qlogo.cn/gh/10000/10000/640/'
        assert captured['user_url'] == 'https://q1.qlogo.cn/g?b=qq&nk=10001&s=5'

    async def test_unregistered_event_type_raises(self, app: App) -> None:
        """未注册 EventDepend 的事件类型应在解析实体接口时抛出 ValueError"""
        from src.params.depends import EVENT_E_IFACE

        captured: dict = {}

        async def dep(event_iface: EVENT_E_IFACE) -> None:
            captured['event_iface'] = event_iface

        bot = _make_real_obv11_bot()
        event = make_fake_event()()
        matcher = make_non_plugin_matcher()

        with pytest.raises(BaseExceptionGroup) as exc_info:
            await self._run_dependent(app, dep, bot=bot, event=event, matcher=matcher)

        # 子依赖异常经依赖求解任务组包装为 ExceptionGroup 传播
        flattened = _flatten_exceptions(exc_info.value)
        assert any(isinstance(e, ValueError) and 'Event not supported' in str(e) for e in flattened)


class TestPermissionRules:
    """权限 Rule 测试 (直接调用检查器, 真实数据库)"""

    @staticmethod
    def _make_private_case(bot_self_id: str) -> tuple[Any, Any, str]:
        """构造绑定 mock bot 的私聊消息事件, 返回 (bot, event, user_id)"""
        user_id = random.randint(10_000_000, 99_999_999)
        return (
            make_mock_bot(self_id=bot_self_id),
            make_obv11_private_message_event(user_id=user_id),
            str(user_id),
        )

    @staticmethod
    async def _grant_entity_auth(
            bot: Any,
            entity_type: str,
            entity_id: str,
            *,
            enable_global: bool = False,
            level: int | None = None,
            auth_nodes: list[tuple[str, str, str, int]] | None = None,
    ) -> None:
        """为指定 Entity 授予权限 (独立会话, 退出即提交)

        :param bot: BotSelf 数据记录 (读取 bot_type/self_id)
        """
        from src.database.helpers import database_session
        from src.service import OmegaEntity

        async with database_session() as session:
            entity = OmegaEntity(
                session=session,
                bot_type=bot.bot_type,
                bot_id=bot.self_id,
                entity_type=entity_type,
                entity_id=entity_id,
            )
            if enable_global:
                await entity.enable_global_permission()
            if level is not None:
                await entity.set_permission_level(level=level)
            for module, plugin, node, available in auth_nodes or []:
                await entity.set_auth_setting(module=module, plugin=plugin, node=node, available=available, value={})

    async def test_event_global_permission_rule(self, test_onebot_v11_bot) -> None:
        from src.params.rule import EventGlobalPermissionRule

        bot, event, user_id = self._make_private_case(test_onebot_v11_bot.self_id)

        rule = EventGlobalPermissionRule()
        assert await rule(bot, event) is False

        await self._grant_entity_auth(test_onebot_v11_bot, 'onebot_v11_user', user_id, enable_global=True)
        assert await rule(bot, event) is True

    @pytest.mark.parametrize('rule_cls_name', ['EventPermissionLevelRule', 'UserPermissionLevelRule'])
    @pytest.mark.parametrize(('granted_level', 'required_level', 'enable_global', 'expected'), [
        (10, 5, True, True),
        (5, 5, True, True),
        (1, 5, True, False),
        (10, 5, False, False),
    ])
    async def test_permission_level_rule(
            self,
            test_onebot_v11_bot,
            rule_cls_name: str,
            granted_level: int,
            required_level: int,
            enable_global: bool,
            expected: bool,
    ) -> None:
        """权限等级检查: 全局功能未启用时即使等级足够也应拒绝 (私聊事件中 event/user 实体解析一致)"""
        from src.params import rule as rule_module

        bot, event, user_id = self._make_private_case(test_onebot_v11_bot.self_id)
        await self._grant_entity_auth(
            test_onebot_v11_bot, 'onebot_v11_user', user_id,
            enable_global=enable_global, level=granted_level,
        )

        rule = getattr(rule_module, rule_cls_name)(level=required_level)
        assert await rule(bot, event) is expected

    @pytest.mark.parametrize('rule_cls_name', ['EventPermissionNodeRule', 'UserPermissionNodeRule'])
    @pytest.mark.parametrize(('node_available', 'enable_global', 'expected'), [
        (1, True, True),
        (0, True, False),
        (None, True, False),
        (1, False, False),
    ])
    async def test_permission_node_rule(
            self,
            test_onebot_v11_bot,
            rule_cls_name: str,
            node_available: int | None,
            enable_global: bool,
            expected: bool,
    ) -> None:
        """权限节点检查: 全局功能未启用时即使节点已授权也应拒绝 (私聊事件中 event/user 实体解析一致)"""
        from src.params import rule as rule_module

        bot, event, user_id = self._make_private_case(test_onebot_v11_bot.self_id)
        auth_nodes = [('TestModule', 'TestPlugin', 'test_node', node_available)] if node_available is not None else None
        await self._grant_entity_auth(
            test_onebot_v11_bot, 'onebot_v11_user', user_id,
            enable_global=enable_global, auth_nodes=auth_nodes,
        )

        rule = getattr(rule_module, rule_cls_name)(module='TestModule', plugin='TestPlugin', node='test_node')
        assert await rule(bot, event) is expected

    async def test_event_and_user_rules_distinguish_acquire_type(self, test_onebot_v11_bot) -> None:
        """群消息事件中 event 实体为群, user 实体为发送者: 授权群不授权用户, 反之亦然"""
        from src.params.rule import EventGlobalPermissionRule, UserGlobalPermissionRule

        group_id = random.randint(10_000_000, 99_999_999)
        user_id = random.randint(10_000_000, 99_999_999)
        bot = make_mock_bot(self_id=test_onebot_v11_bot.self_id)
        event = make_obv11_group_message_event(group_id=group_id, user_id=user_id)

        await self._grant_entity_auth(test_onebot_v11_bot, 'onebot_v11_group', str(group_id), enable_global=True)

        assert await EventGlobalPermissionRule()(bot, event) is True
        assert await UserGlobalPermissionRule()(bot, event) is False

        await self._grant_entity_auth(test_onebot_v11_bot, 'onebot_v11_user', str(user_id), enable_global=True)
        assert await UserGlobalPermissionRule()(bot, event) is True

    async def test_rule_check_failure_denies_with_warning(self, log_capture) -> None:
        """检查过程抛出异常 (未注册 EventDepend 的事件类型) 时应拒绝并记录警告, 不向事件分发层抛出"""
        from src.params.rule import (
            EventGlobalPermissionRule,
            EventPermissionLevelRule,
            UserGlobalPermissionRule,
        )

        bot = _make_real_obv11_bot()
        event = make_fake_event()()

        assert await EventGlobalPermissionRule()(bot, event) is False
        assert await EventPermissionLevelRule(level=1)(bot, event) is False
        assert await UserGlobalPermissionRule()(bot, event) is False

        assert any('Permission check failed, denied' in message for message in log_capture)

    @pytest.mark.parametrize(('factory_name', 'checker_name'), [
        ('event_has_global_permission', 'EventGlobalPermissionRule'),
        ('event_has_permission_level', 'EventPermissionLevelRule'),
        ('event_has_permission_node', 'EventPermissionNodeRule'),
        ('user_has_global_permission', 'UserGlobalPermissionRule'),
        ('user_has_permission_level', 'UserPermissionLevelRule'),
        ('user_has_permission_node', 'UserPermissionNodeRule'),
    ])
    def test_rule_factories(self, factory_name: str, checker_name: str) -> None:
        """Rule 工厂应返回以对应检查器装配的 Rule, 且构造参数透传"""
        from nonebot.rule import Rule

        from src.params import rule as rule_module

        factory = getattr(rule_module, factory_name)
        if 'level' in factory_name:
            rule = factory(5)
        elif 'node' in factory_name:
            rule = factory('m', 'p', 'n')
        else:
            rule = factory()

        assert isinstance(rule, Rule)
        assert {type(d.call).__name__ for d in rule.checkers} == {checker_name}

        checker = next(iter(rule.checkers)).call
        if 'level' in factory_name:
            assert checker.level == 5
        if 'node' in factory_name:
            assert (checker.module, checker.plugin, checker.node) == ('m', 'p', 'n')


class TestIsAdmin:
    """IS_ADMIN 组合权限测试 (直接调用, 真值表)"""

    async def test_superuser(self) -> None:
        from src.params.permission import IS_ADMIN

        # 测试配置中 superusers 包含 'User'
        assert await IS_ADMIN(_make_real_obv11_bot(), make_fake_message_event(user_id='User')) is True

    async def test_onebot_v11_private(self) -> None:
        from src.params.permission import IS_ADMIN

        assert await IS_ADMIN(_make_real_obv11_bot(), make_obv11_private_message_event()) is True

    @pytest.mark.parametrize(('role', 'expected'), [
        ('admin', True),
        ('owner', True),
        ('member', False),
        (None, False),
    ])
    async def test_onebot_v11_group_role(self, role: str | None, expected: bool) -> None:
        from src.params.permission import IS_ADMIN

        event = make_obv11_group_message_event(role=role)
        assert await IS_ADMIN(_make_real_obv11_bot(), event) is expected

    async def test_telegram_private(self) -> None:
        from nonebot.adapters.telegram.event import PrivateMessageEvent

        from src.params.permission import IS_ADMIN

        event = PrivateMessageEvent.model_validate({
            'message_id': 1,
            'date': 1,
            'chat': {'id': 10001, 'type': 'private', 'first_name': 'Tester'},
            'from': {'id': 10001, 'is_bot': False, 'first_name': 'Tester'},
            'message': [{'type': 'text', 'data': {'text': 'hi'}}],
            'original_message': [{'type': 'text', 'data': {'text': 'hi'}}],
        })
        assert await IS_ADMIN(_make_real_obv11_bot(), event) is True

    async def test_non_privileged_event(self) -> None:
        from src.params.permission import IS_ADMIN

        assert await IS_ADMIN(_make_real_obv11_bot(), make_fake_message_event(user_id='nobody')) is False

    async def test_check_event_is_admin_additional(self) -> None:
        """assign additional 检查函数: 参数序为 (event, bot, state, arparma), 委托 IS_ADMIN"""
        from src.params.permission import check_event_is_admin

        bot = _make_real_obv11_bot()
        assert await check_event_is_admin(make_obv11_private_message_event(), bot, {}, MagicMock()) is True
        assert await check_event_is_admin(make_obv11_group_message_event(role='member'), bot, {}, MagicMock()) is False
        assert await check_event_is_admin(make_obv11_group_message_event(role='admin'), bot, {}, MagicMock()) is True

    async def test_check_event_is_superuser_additional(self) -> None:
        """assign additional 检查函数: 委托 SUPERUSER (测试配置中 superusers 包含 'User')"""
        from src.params.permission import check_event_is_superuser

        bot = _make_real_obv11_bot()
        assert await check_event_is_superuser(make_fake_message_event(user_id='User'), bot, {}, MagicMock()) is True
        assert await check_event_is_superuser(make_fake_message_event(user_id='nobody'), bot, {}, MagicMock()) is False


class TestBaseSubscriptionManager:
    """BaseSubscriptionManager 订阅管理基类测试 (stub 子类 + 真实数据库)"""

    @staticmethod
    async def _count_smc_rows(source: str) -> int:
        from src.database import SocialMediaContentDAL

        async with SocialMediaContentDAL.create() as dal:
            return len(await dal.query_source_all(source=source))

    @staticmethod
    @asynccontextmanager
    async def _with_online_bot(app: App, self_id: str) -> AsyncGenerator[None, None]:
        """在 nonebug API 上下文中登记一个在线 OneBot V11 Bot (退出时移除登记)"""
        from nonebot.adapters.onebot.v11 import Adapter, Bot

        async with app.test_api() as ctx:
            adapter = nonebot.get_adapter(Adapter)
            async with registered_online_bot(ctx, self_id=self_id, base=Bot, adapter=adapter):
                yield

    @staticmethod
    async def _seed_subscribed_entity(
            manager_cls: type,
            test_db_data_factory,
            test_onebot_v11_entity_factory,
    ) -> Any:
        """创建订阅源并令一个测试实体订阅后提交, 返回绑定该订阅源的 manager 实例"""
        source = await test_db_data_factory.create_test_subscription_source(sub_type=manager_cls.get_sub_type())
        entity = test_onebot_v11_entity_factory()
        await entity.add_subscription(subscription_source=source)
        # 跨会话可见性要求显式提交
        await entity.commit_session()
        return manager_cls(source.sub_id)

    def test_abstract_methods_enforced(self) -> None:
        from src.params.template.subscription_manager import BaseSubscriptionManager

        class _IncompleteManager(BaseSubscriptionManager[dict]):
            pass

        with pytest.raises(TypeError, match='abstract'):
            _IncompleteManager(1)

    async def test_init_coerces_sub_id_and_formatting(self, subscription_manager_stub_cls) -> None:
        manager_cls = subscription_manager_stub_cls()
        manager = manager_cls(12345)

        assert manager.sub_id == '12345'
        assert repr(manager) == f'{manager_cls.__name__}(sub_id=12345)'
        assert str(manager) == f'SubscriptionManager | {manager_cls.get_sub_type().upper()} | 12345'
        assert manager.sub_type == manager_cls.get_sub_type()

    async def test_subscription_source_crud(self, subscription_manager_stub_cls) -> None:
        from sqlalchemy.exc import NoResultFound

        manager_cls = subscription_manager_stub_cls()
        manager = manager_cls('source_1')

        assert await manager_cls._query_type_all_subscription_sources() == []

        source = await manager._add_upgrade_subscription_source(sub_user_name='user_a', sub_info='info_a')
        assert source.id > 0
        assert source.sub_type == manager_cls.get_sub_type()
        assert source.sub_id == 'source_1'
        assert source.sub_user_name == 'user_a'
        assert source.sub_info == 'info_a'

        updated = await manager._add_upgrade_subscription_source(sub_user_name='user_b')
        assert updated.id == source.id
        assert updated.sub_user_name == 'user_b'
        assert updated.sub_info is None

        queried = await manager._query_subscription_source()
        assert queried.id == source.id
        assert len(await manager_cls._query_type_all_subscription_sources()) == 1

        await manager._delete_subscription_source()
        with pytest.raises(NoResultFound):
            await manager._query_subscription_source()

    async def test_query_all_entity_index_ids_subscribed_with_type_filter(
            self, subscription_manager_stub_cls, test_onebot_v11_entity_factory,
    ) -> None:
        from src.database.internal.entity import EntityType

        manager_cls = subscription_manager_stub_cls()
        manager = manager_cls('source_with_subs')
        source = await manager._add_upgrade_subscription_source(sub_user_name='user_a')

        user_entity = test_onebot_v11_entity_factory()
        group_entity = test_onebot_v11_entity_factory(
            entity_type=EntityType.ONEBOT_V11_GROUP,
            entity_id=unique_test_id('TEST_GROUP'),
        )
        await user_entity.add_subscription(subscription_source=source)
        await group_entity.add_subscription(subscription_source=source)
        # 跨会话可见性要求显式提交
        await user_entity.commit_session()

        user_index_id = (await user_entity.query_entity_self()).id
        group_index_id = (await group_entity.query_entity_self()).id

        all_ids = await manager._query_all_entity_index_ids_subscribed()
        assert set(all_ids) == {user_index_id, group_index_id}

        user_ids = await manager._query_all_entity_index_ids_subscribed(entity_type=EntityType.ONEBOT_V11_USER)
        assert user_ids == [user_index_id]

        group_ids = await manager._query_all_entity_index_ids_subscribed(entity_type='onebot_v11_group')
        assert group_ids == [group_index_id]

    async def test_check_new_smc_item(self, subscription_manager_stub_cls) -> None:
        from src.database import SocialMediaContentDAL

        manager_cls = subscription_manager_stub_cls()

        async with SocialMediaContentDAL.create() as dal:
            await dal.add(
                source=manager_cls.get_sub_type(), m_type='test', m_id='m1',
                m_uid='u', title='t', raw_data={},
            )

        items = [{'mid': 'm1'}, {'mid': 'm2'}, {'mid': 'm3'}]
        new_items = await manager_cls._check_new_smc_item(items)
        assert [x['mid'] for x in new_items] == ['m2', 'm3']

        assert await manager_cls._check_new_smc_item([]) == []
        assert await manager_cls._check_new_smc_item([{'mid': 'm1'}]) == []

    async def test_filter_new_smc_item_default_identity(self, subscription_manager_stub_cls) -> None:
        manager_cls = subscription_manager_stub_cls()

        items = [{'mid': 'a'}, {'mid': 'b'}]
        filtered = await manager_cls._filter_new_smc_item(items)

        assert filtered == items
        assert filtered is not items

    async def test_add_upgrade_smc_item(self, subscription_manager_stub_cls) -> None:
        from src.database import SocialMediaContentDAL

        manager_cls = subscription_manager_stub_cls()
        await manager_cls._add_upgrade_smc_item({'mid': 'm1'})

        async with SocialMediaContentDAL.create() as dal:
            item = await dal.query_unique(source=manager_cls.get_sub_type(), m_type='test', m_id='m1')

        assert item.source == manager_cls.get_sub_type()
        assert item.m_uid == 'test_uid'
        assert item.title == 'test title m1'
        assert item.raw_data == {'mid': 'm1'}

    async def test_add_sub_source_new_smc_content_idempotent(self, subscription_manager_stub_cls) -> None:
        manager_cls = subscription_manager_stub_cls(items=[{'mid': 'm1'}, {'mid': 'm2'}])
        manager = manager_cls('sub_x')

        await manager._add_sub_source_new_smc_content()
        assert await self._count_smc_rows(manager_cls.get_sub_type()) == 2

        # 重复执行应判定为已存在内容, 不重复写入
        await manager._add_sub_source_new_smc_content()
        assert await self._count_smc_rows(manager_cls.get_sub_type()) == 2

    async def test_add_upgrade_sub_source_preserves_existing_content(self, subscription_manager_stub_cls) -> None:
        """新增订阅源时应先将存量内容入库 (避免首次订阅推送存量内容), 返回真实数据库索引 ID"""
        manager_cls = subscription_manager_stub_cls(items=[{'mid': 'm1'}, {'mid': 'm2'}])
        manager = manager_cls('sub_real')

        source = await manager._add_upgrade_sub_source()

        assert source.id > 0
        assert source.sub_user_name == 'test_user_sub_real'
        assert await self._count_smc_rows(manager_cls.get_sub_type()) == 2

    async def test_entity_subscription_flow(
            self, subscription_manager_stub_cls, test_onebot_v11_bot, test_db_data_factory,
    ) -> None:
        from src.service import OmegaMatcherInterface

        manager_cls = subscription_manager_stub_cls()
        source = await test_db_data_factory.create_test_subscription_source(sub_type=manager_cls.get_sub_type())
        manager = manager_cls(source.sub_id)

        interface = OmegaMatcherInterface(
            bot=make_mock_bot(self_id=test_onebot_v11_bot.self_id),
            event=make_obv11_private_message_event(user_id=random.randint(10_000_000, 99_999_999)),
            matcher=make_non_plugin_matcher(),
        )

        await manager.add_entity_sub(interface=interface)

        subscribed = await manager_cls.query_entity_subscribed_sub_source(interface=interface)
        assert subscribed == {source.sub_id: f'test_user_{source.sub_id}'}

        assert source.sub_id in await manager_cls.query_all_subscribed_sub_source_ids()

        entity_index_ids = await manager.query_subscribed_entity_index_ids_by_sub_source()
        assert len(entity_index_ids) == 1

        await manager.delete_entity_sub(interface=interface)
        assert await manager_cls.query_entity_subscribed_sub_source(interface=interface) == {}

    async def test_notice_at_all_node_toggle(
            self, subscription_manager_stub_cls, test_onebot_v11_entity_factory,
    ) -> None:
        manager_cls = subscription_manager_stub_cls()
        entity = test_onebot_v11_entity_factory()

        assert await manager_cls._check_entity_has_notice_at_all_node(entity=entity) is False

        await manager_cls.enable_entity_notice_at_all_node(entity=entity)
        assert await manager_cls._check_entity_has_notice_at_all_node(entity=entity) is True

        await manager_cls.disable_entity_notice_at_all_node(entity=entity)
        assert await manager_cls._check_entity_has_notice_at_all_node(entity=entity) is False

    async def test_check_notice_at_all_node_failure_returns_false(
            self, subscription_manager_stub_cls, log_capture,
    ) -> None:
        """检查过程抛出异常时应记录警告并返回 False"""
        manager_cls = subscription_manager_stub_cls()

        class _BrokenEntity:
            async def verify_auth_setting(self, **kwargs: Any) -> int:
                raise RuntimeError('broken entity')

        result = await manager_cls._check_entity_has_notice_at_all_node(entity=_BrokenEntity())

        assert result is False
        assert any('notice at all node failed' in message for message in log_capture)

    @pytest.mark.parametrize('enable_notice', [False, True])
    async def test_send_entity_message(
            self,
            app: App,
            subscription_manager_stub_cls,
            test_onebot_v11_bot,
            test_onebot_v11_entity_factory,
            recording_uni_message,
            enable_notice: bool,
    ) -> None:
        manager_cls = subscription_manager_stub_cls()
        manager = manager_cls('sub_send')

        entity = test_onebot_v11_entity_factory()
        if enable_notice:
            await manager_cls.enable_entity_notice_at_all_node(entity=entity)
        index_id = (await entity.query_entity_self()).id
        await entity.commit_session()

        async with self._with_online_bot(app, test_onebot_v11_bot.self_id):
            await manager._send_entity_message(entity_index_id=index_id, message='hello', smc_item={'mid': 'm1'})

        assert len(recording_uni_message) == 1
        sent_message = recording_uni_message[0]
        if enable_notice:
            from nonebot_plugin_alconna.uniseg import AtAll

            assert isinstance(sent_message[0], AtAll)
        assert sent_message.extract_plain_text() == 'hello'
        assert manager_cls.postprocessed == [{'mid': 'm1'}]

    async def test_send_entity_message_to_nonexistent_entity(
            self, subscription_manager_stub_cls, log_capture,
    ) -> None:
        """目标 Entity 已删除 (失效订阅) 时应静默跳过并记录警告, 不抛出异常"""
        manager = subscription_manager_stub_cls()('sub_x')

        await manager._send_entity_message(entity_index_id=-1, message='x', smc_item={'mid': 'm1'})

        assert any('no longer exists' in message for message in log_capture)

    async def test_check_update_and_send_full_flow(
            self,
            app: App,
            subscription_manager_stub_cls,
            test_onebot_v11_bot,
            test_db_data_factory,
            test_onebot_v11_entity_factory,
            recording_uni_message,
    ) -> None:
        manager_cls = subscription_manager_stub_cls(items=[{'mid': 'm1'}, {'mid': 'm2'}])
        manager = await self._seed_subscribed_entity(manager_cls, test_db_data_factory, test_onebot_v11_entity_factory)

        async with self._with_online_bot(app, test_onebot_v11_bot.self_id):
            await manager.check_subscription_source_update_and_send_entity_message()

            # 新内容已入库且已向订阅者发送
            assert await self._count_smc_rows(manager_cls.get_sub_type()) == 2
            assert {m.extract_plain_text() for m in recording_uni_message} == {'formatted:m1', 'formatted:m2'}

            # 再次检查无新内容, 不重复发送
            await manager.check_subscription_source_update_and_send_entity_message()
            assert len(recording_uni_message) == 2
            assert await self._count_smc_rows(manager_cls.get_sub_type()) == 2

    async def test_check_update_with_none_format_skips_send_but_keeps_archive(
            self,
            app: App,
            subscription_manager_stub_cls,
            test_onebot_v11_bot,
            test_db_data_factory,
            test_onebot_v11_entity_factory,
            recording_uni_message,
    ) -> None:
        """格式化结果为 None 时不发送通知, 但内容仍入库存档"""
        manager_cls = subscription_manager_stub_cls(items=[{'mid': 'm1'}], format_none=True)
        manager = await self._seed_subscribed_entity(manager_cls, test_db_data_factory, test_onebot_v11_entity_factory)

        async with self._with_online_bot(app, test_onebot_v11_bot.self_id):
            await manager.check_subscription_source_update_and_send_entity_message()

        assert await self._count_smc_rows(manager_cls.get_sub_type()) == 1
        assert recording_uni_message == []

    async def test_check_update_skips_send_for_items_failed_to_archive(
            self,
            app: App,
            subscription_manager_stub_cls,
            test_onebot_v11_bot,
            test_db_data_factory,
            test_onebot_v11_entity_factory,
            recording_uni_message,
            log_capture,
    ) -> None:
        """入库失败的内容应跳过本次发送 (避免数据库故障期间重复推送), 入库成功的内容正常发送"""
        manager_cls = subscription_manager_stub_cls(
            items=[{'mid': 'bad'}, {'mid': 'good'}],
            parse_fail_mids={'bad'},
        )
        manager = await self._seed_subscribed_entity(manager_cls, test_db_data_factory, test_onebot_v11_entity_factory)

        async with self._with_online_bot(app, test_onebot_v11_bot.self_id):
            await manager.check_subscription_source_update_and_send_entity_message()

        assert await self._count_smc_rows(manager_cls.get_sub_type()) == 1
        assert [m.extract_plain_text() for m in recording_uni_message] == ['formatted:good']
        assert any('Add new smc content' in message for message in log_capture)


class TestSubscriptionHandlerFactory:
    """SubscriptionHandlerFactory 订阅命令模板工厂测试

    生成的 handler 以直接调用方式测试: interface 为真实 OmegaMatcherInterface (发送经
    recording_uni_message 记录, finish 语义抛出 FinishedException), manager 为覆盖数据库写操作的
    stub 子类, prompt 为组合式替身
    """

    @pytest.fixture
    async def handler_factory(self, subscription_manager_stub_cls) -> tuple[Any, type]:
        """基于 stub manager 的订阅命令工厂 (订阅写操作替换为调用记录, 与数据库流程解耦)"""
        from src.params.template.subscription_manager import SubscriptionHandlerFactory

        base_cls = subscription_manager_stub_cls()

        class _HandlerStubManager(base_cls):
            add_sub_calls: ClassVar[list[str]]
            del_sub_calls: ClassVar[list[str]]
            exist_subs: ClassVar[dict[str, str]]
            fail_add: ClassVar[bool]
            fail_del: ClassVar[bool]
            fail_query_source: ClassVar[bool]
            fail_query_exist: ClassVar[bool]
            source_id_map: ClassVar[dict[str, str]]

            async def add_entity_sub(self, interface) -> None:
                if self.fail_add:
                    raise RuntimeError('add failed')
                self.add_sub_calls.append(self.sub_id)

            async def delete_entity_sub(self, interface) -> None:
                if self.fail_del:
                    raise RuntimeError('del failed')
                self.del_sub_calls.append(self.sub_id)

            @classmethod
            async def query_entity_subscribed_sub_source(cls, interface) -> dict[str, str]:
                if cls.fail_query_exist:
                    raise RuntimeError('query exist failed')
                return dict(cls.exist_subs)

            async def query_sub_source_data(self):
                if self.fail_query_source:
                    raise RuntimeError('query source failed')
                data = await super().query_sub_source_data()
                return data.model_copy(update={'sub_id': self.source_id_map.get(self.sub_id, self.sub_id)})

        # 每个测试独立的记录容器与开关
        _HandlerStubManager.add_sub_calls = []
        _HandlerStubManager.del_sub_calls = []
        _HandlerStubManager.exist_subs = {}
        _HandlerStubManager.fail_add = False
        _HandlerStubManager.fail_del = False
        _HandlerStubManager.fail_query_source = False
        _HandlerStubManager.fail_query_exist = False
        _HandlerStubManager.source_id_map = {}

        factory = SubscriptionHandlerFactory(_HandlerStubManager, '测试源')
        return factory, _HandlerStubManager

    @staticmethod
    def _make_interface(bot_self_id: str = '10086', user_id: int = 10001) -> 'OmegaMatcherInterface':
        from src.service import OmegaMatcherInterface

        return OmegaMatcherInterface(
            bot=make_mock_bot(self_id=bot_self_id),
            event=make_obv11_private_message_event(user_id=user_id),
            matcher=make_non_plugin_matcher(),
        )

    @staticmethod
    def _make_prompt_matcher(response: Any) -> Any:
        """构造 prompt 替身 (组合式, 仅提供 handler 实际调用的 prompt 方法)"""
        return SimpleNamespace(prompt=AsyncMock(return_value=response))

    @staticmethod
    def _match(result: str, available: bool) -> Any:
        from nonebot_plugin_alconna import Match

        return Match(result, available)

    @staticmethod
    def _sent_texts(recording: list) -> list[str]:
        return [message.extract_plain_text() for message in recording]

    async def _invoke(
            self,
            handler: Any,
            match: Any,
            *,
            prompt_response: str | None = None,
            interface: Any | None = None,
    ) -> Any:
        """直接调用生成的 handler (断言以 FinishedException 结束), 返回 prompt 替身供后续断言"""
        from nonebot.exception import FinishedException
        from nonebot_plugin_alconna.uniseg import UniMessage

        prompt_matcher = self._make_prompt_matcher(UniMessage(prompt_response) if prompt_response is not None else None)
        with pytest.raises(FinishedException):
            await handler(prompt_matcher, interface or self._make_interface(), match)
        return prompt_matcher

    def test_factory_properties(self, handler_factory) -> None:
        manager_cls = handler_factory[1]

        factory, _ = handler_factory
        assert factory.sub_type == manager_cls.get_sub_type()
        assert factory._aliases_command_prefix == set()
        assert factory._need_decimal_sub_id is False
        assert factory._default_sub_id is None
        assert manager_cls.get_sub_type().upper() in str(factory)

        manager = factory._get_manager(12345)
        assert isinstance(manager, manager_cls)
        assert manager.sub_id == '12345'

    async def test_add_handler_with_default_sub_id(self, handler_factory, recording_uni_message) -> None:
        """配置了默认订阅 ID 时直接使用默认值执行, 忽略参数且无需确认"""
        from src.params.template.subscription_manager import SubscriptionHandlerFactory

        _, manager_cls = handler_factory
        factory = SubscriptionHandlerFactory(manager_cls, '测试源', default_sub_id='999')
        handler = factory._generate_add_subscription_handler()

        await self._invoke(handler, self._match('', False))

        assert manager_cls.add_sub_calls == ['999']
        assert self._sent_texts(recording_uni_message) == ['正在更新测试源订阅信息, 请稍候', '订阅测试源: 999成功']

    @pytest.mark.parametrize(('match_result', 'available'), [('', False), ('   ', True)])
    async def test_add_handler_sub_id_not_provided(
            self, handler_factory, recording_uni_message, match_result: str, available: bool,
    ) -> None:
        factory, manager_cls = handler_factory
        handler = factory._generate_add_subscription_handler()

        await self._invoke(handler, self._match(match_result, available))

        assert manager_cls.add_sub_calls == []
        assert self._sent_texts(recording_uni_message) == ['未提供订阅ID参数, 已取消操作']

    async def test_add_handler_non_decimal_sub_id(self, handler_factory, recording_uni_message) -> None:
        from src.params.template.subscription_manager import SubscriptionHandlerFactory

        _, manager_cls = handler_factory
        factory = SubscriptionHandlerFactory(manager_cls, '测试源', need_decimal_sub_id=True)
        handler = factory._generate_add_subscription_handler()

        await self._invoke(handler, self._match('abc', True))

        assert manager_cls.add_sub_calls == []
        assert self._sent_texts(recording_uni_message) == ['非有效的订阅ID, 订阅ID应当为纯数字, 已取消操作']

    async def test_add_handler_query_source_failed(self, handler_factory, recording_uni_message) -> None:
        factory, manager_cls = handler_factory
        manager_cls.fail_query_source = True
        handler = factory._generate_add_subscription_handler()

        await self._invoke(handler, self._match('123', True))

        assert manager_cls.add_sub_calls == []
        assert self._sent_texts(recording_uni_message) == [
            '获取订阅源信息失败, 可能是网络原因或没有这个订阅源, 请稍后再试',
        ]

    async def test_add_handler_sub_id_converted(self, handler_factory, recording_uni_message) -> None:
        """针对订阅请求的 ID 为短号等场景, 确认后以转换后的真实 ID 执行订阅"""
        factory, manager_cls = handler_factory
        manager_cls.source_id_map = {'short': '10001'}
        handler = factory._generate_add_subscription_handler()

        prompt_matcher = await self._invoke(handler, self._match('short', True), prompt_response='是')

        assert manager_cls.add_sub_calls == ['10001']
        # 确认提示经 matcher.prompt 发出
        assert '即将订阅测试源【test_user_short】' in prompt_matcher.prompt.await_args.args[0]
        assert self._sent_texts(recording_uni_message) == ['正在更新测试源订阅信息, 请稍候', '订阅测试源: 10001成功']

    @pytest.mark.parametrize(('prompt_response', 'expected_calls', 'expected_message'), [
        (None, [], '确认超时, 已取消操作'),
        ('否', [], '已取消操作'),
        ('是', ['123'], '订阅测试源: 123成功'),
    ])
    async def test_add_handler_confirm_flow(
            self,
            handler_factory,
            recording_uni_message,
            prompt_response: str | None,
            expected_calls: list,
            expected_message: str,
    ) -> None:
        factory, manager_cls = handler_factory
        handler = factory._generate_add_subscription_handler()

        await self._invoke(handler, self._match('123', True), prompt_response=prompt_response)

        assert manager_cls.add_sub_calls == expected_calls
        assert self._sent_texts(recording_uni_message)[-1] == expected_message

    async def test_add_handler_with_stopped_scheduler(self, handler_factory, recording_uni_message) -> None:
        """调度器未启动时订阅流程应正常完成并跳过暂停/恢复"""
        from src.service import scheduler

        # 测试环境 apscheduler_autostart=False, 调度器处于未启动状态
        assert not scheduler.running

        factory, manager_cls = handler_factory
        handler = factory._generate_add_subscription_handler()

        await self._invoke(handler, self._match('123', True), prompt_response='是')

        assert manager_cls.add_sub_calls == ['123']
        assert self._sent_texts(recording_uni_message)[-1] == '订阅测试源: 123成功'

    async def test_add_handler_pauses_running_scheduler(
            self, handler_factory, recording_uni_message, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """调度器运行时应在订阅更新期间暂停并在结束后恢复"""
        from nonebot.exception import FinishedException

        import src.params.template.subscription_manager.handlers as handlers_module

        calls: list[str] = []
        monkeypatch.setattr(handlers_module, 'scheduler', SimpleNamespace(
            running=True,
            pause=lambda: calls.append('pause'),
            resume=lambda: calls.append('resume'),
        ))

        factory, manager_cls = handler_factory

        with pytest.raises(FinishedException):
            await factory._execute_add_subscription(interface=self._make_interface(), sub_id='123')

        assert calls == ['pause', 'resume']
        assert manager_cls.add_sub_calls == ['123']

    async def test_add_handler_failure_still_resumes_scheduler(
            self, handler_factory, recording_uni_message, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """订阅执行失败时应返回友好提示且仍恢复调度器"""
        from nonebot.exception import FinishedException

        import src.params.template.subscription_manager.handlers as handlers_module

        calls: list[str] = []
        monkeypatch.setattr(handlers_module, 'scheduler', SimpleNamespace(
            running=True,
            pause=lambda: calls.append('pause'),
            resume=lambda: calls.append('resume'),
        ))

        factory, manager_cls = handler_factory
        manager_cls.fail_add = True

        with pytest.raises(FinishedException):
            await factory._execute_add_subscription(interface=self._make_interface(), sub_id='123')

        assert calls == ['pause', 'resume']
        assert manager_cls.add_sub_calls == []
        assert self._sent_texts(recording_uni_message)[-1].startswith('订阅测试源: 123失败')

    async def test_del_handler_with_default_sub_id(self, handler_factory, recording_uni_message) -> None:
        from src.params.template.subscription_manager import SubscriptionHandlerFactory

        _, manager_cls = handler_factory
        factory = SubscriptionHandlerFactory(manager_cls, '测试源', default_sub_id='999')
        handler = factory._generate_del_subscription_handler()

        await self._invoke(handler, self._match('', False))

        assert manager_cls.del_sub_calls == ['999']
        assert self._sent_texts(recording_uni_message) == ['取消订阅测试源: 999成功']

    async def test_del_handler_not_subscribed(self, handler_factory, recording_uni_message) -> None:
        factory, manager_cls = handler_factory
        manager_cls.exist_subs = {'1': 'user_a'}
        handler = factory._generate_del_subscription_handler()

        await self._invoke(handler, self._match('2', True))

        assert manager_cls.del_sub_calls == []
        sent_texts = self._sent_texts(recording_uni_message)
        assert '未订阅测试源: 2' in sent_texts[-1]
        assert '1: user_a' in sent_texts[-1]

    async def test_del_handler_query_exist_failed(self, handler_factory, recording_uni_message) -> None:
        factory, manager_cls = handler_factory
        manager_cls.fail_query_exist = True
        handler = factory._generate_del_subscription_handler()

        await self._invoke(handler, self._match('1', True))

        assert manager_cls.del_sub_calls == []
        assert self._sent_texts(recording_uni_message)[-1] == '获取已订阅的测试源列表失败, 请稍后再试或联系管理员处理'

    @pytest.mark.parametrize(('prompt_response', 'expected_calls', 'expected_message'), [
        (None, [], '确认超时, 已取消操作'),
        ('否', [], '已取消操作'),
        ('是', ['1'], '取消订阅测试源: 1成功'),
    ])
    async def test_del_handler_confirm_flow(
            self,
            handler_factory,
            recording_uni_message,
            prompt_response: str | None,
            expected_calls: list,
            expected_message: str,
    ) -> None:
        factory, manager_cls = handler_factory
        manager_cls.exist_subs = {'1': 'user_a'}
        handler = factory._generate_del_subscription_handler()

        prompt_matcher = await self._invoke(handler, self._match('1', True), prompt_response=prompt_response)

        assert manager_cls.del_sub_calls == expected_calls
        assert self._sent_texts(recording_uni_message)[-1] == expected_message
        if expected_calls:
            # 确认提示经 matcher.prompt 发出
            assert '取消订阅测试源【user_a】' in prompt_matcher.prompt.await_args.args[0]

    async def test_del_handler_execute_failure(self, handler_factory, recording_uni_message) -> None:
        from nonebot.exception import FinishedException

        factory, manager_cls = handler_factory
        manager_cls.fail_del = True

        with pytest.raises(FinishedException):
            await factory._execute_del_subscription(interface=self._make_interface(), sub_id='123')

        assert self._sent_texts(recording_uni_message) == ['取消订阅测试源: 123失败, 请稍后再试或联系管理员处理']

    @pytest.mark.parametrize(('exist_subs', 'expected_message'), [
        ({'1': 'user_a', '2': 'user_b'}, '当前已订阅的测试源列表:\n\n1: user_a\n2: user_b'),
        ({}, '当前已订阅的测试源列表:\n\n无'),
    ])
    async def test_list_handler(
            self, handler_factory, recording_uni_message, exist_subs: dict, expected_message: str,
    ) -> None:
        factory, manager_cls = handler_factory
        manager_cls.exist_subs = exist_subs
        handler = factory._generate_list_subscription_handler()

        await handler(self._make_interface())

        assert self._sent_texts(recording_uni_message) == [expected_message]

    async def test_list_handler_query_failed(self, handler_factory, recording_uni_message) -> None:
        from nonebot.exception import FinishedException

        factory, manager_cls = handler_factory
        manager_cls.fail_query_exist = True
        handler = factory._generate_list_subscription_handler()

        with pytest.raises(FinishedException):
            await handler(self._make_interface())

        assert self._sent_texts(recording_uni_message) == ['获取已订阅的测试源列表失败, 请稍后再试或联系管理员处理']

    @pytest.mark.parametrize(('switch_arg', 'expected_available', 'expected_echo'), [
        ('on', 1, '【ON】'),
        ('OFF', 0, '【OFF】'),
    ])
    async def test_switch_notice_at_all(
            self,
            handler_factory,
            recording_uni_message,
            test_onebot_v11_bot,
            switch_arg: str,
            expected_available: int,
            expected_echo: str,
    ) -> None:
        factory, manager_cls = handler_factory
        handler = factory._generate_switch_subscription_notice_at_all_handler()

        user_id = random.randint(10_000_000, 99_999_999)
        interface = self._make_interface(bot_self_id=test_onebot_v11_bot.self_id, user_id=user_id)
        await handler(self._make_prompt_matcher(None), interface, self._match(switch_arg, True))

        assert self._sent_texts(recording_uni_message) == [f'已设置测试源订阅通知@所有人功能为{expected_echo}']

        # 权限节点应已写入数据库
        from src.database.helpers import database_session
        from src.service import OmegaEntity

        async with database_session() as session:
            entity = OmegaEntity(
                session=session,
                bot_type=test_onebot_v11_bot.bot_type,
                bot_id=test_onebot_v11_bot.self_id,
                entity_type='onebot_v11_user',
                entity_id=str(user_id),
            )
            verified = await entity.verify_auth_setting(
                module=f'Omega.{manager_cls.__name__}',
                plugin=manager_cls.get_sub_type(),
                node='notice_at_all',
                available=expected_available,
            )
        assert verified == 1

    async def test_switch_notice_at_all_invalid_option(self, handler_factory, recording_uni_message) -> None:
        from nonebot.exception import FinishedException

        factory, _ = handler_factory
        handler = factory._generate_switch_subscription_notice_at_all_handler()

        with pytest.raises(FinishedException):
            await handler(self._make_prompt_matcher(None), self._make_interface(), self._match('xxx', True))

        assert self._sent_texts(recording_uni_message) == [
            '无效选项, 请输入【ON/OFF】以启用或关闭订阅通知@所有人, 操作已取消',
        ]

    async def test_switch_notice_at_all_prompt_fallback(
            self, handler_factory, recording_uni_message, test_onebot_v11_bot,
    ) -> None:
        """未提供开关参数时进行追问, 追问结果驱动开关"""
        from nonebot_plugin_alconna.uniseg import UniMessage

        factory, manager_cls = handler_factory
        handler = factory._generate_switch_subscription_notice_at_all_handler()

        user_id = random.randint(10_000_000, 99_999_999)
        interface = self._make_interface(bot_self_id=test_onebot_v11_bot.self_id, user_id=user_id)
        prompt_matcher = self._make_prompt_matcher(UniMessage('on'))
        await handler(prompt_matcher, interface, self._match('', False))

        prompt_matcher.prompt.assert_awaited_once()
        assert self._sent_texts(recording_uni_message) == ['已设置测试源订阅通知@所有人功能为【ON】']

    async def test_switch_notice_at_all_prompt_timeout(self, handler_factory, recording_uni_message) -> None:
        from nonebot.exception import FinishedException

        factory, _ = handler_factory
        handler = factory._generate_switch_subscription_notice_at_all_handler()

        with pytest.raises(FinishedException):
            await handler(self._make_prompt_matcher(None), self._make_interface(), self._match('', False))

        assert self._sent_texts(recording_uni_message) == ['等待输入超时, 已取消操作']

    async def test_switch_notice_at_all_failure(
            self, handler_factory, recording_uni_message, test_onebot_v11_bot, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        factory, manager_cls = handler_factory
        handler = factory._generate_switch_subscription_notice_at_all_handler()

        async def _fail_enable(entity) -> None:
            raise RuntimeError('switch failed')

        monkeypatch.setattr(manager_cls, 'enable_entity_notice_at_all_node', classmethod(_fail_enable))

        user_id = random.randint(10_000_000, 99_999_999)
        interface = self._make_interface(bot_self_id=test_onebot_v11_bot.self_id, user_id=user_id)
        await handler(self._make_prompt_matcher(None), interface, self._match('on', True))

        assert self._sent_texts(recording_uni_message) == ['设置测试源订阅通知@所有人功能失败, 请联系管理员处理']

    async def test_register_handlers(self, handler_factory) -> None:
        """注册应成功创建并登记 AlconnaMatcher, 测试后销毁并清理自检条目避免污染全局注册表"""
        from nonebot_plugin_alconna import AlconnaMatcher

        from src.params.template.subscription_manager import SubscriptionHandlerFactory
        from src.service.omega_processor.universal.processor_utils import parse_processor_state

        _, manager_cls = handler_factory
        command_prefix = unique_test_id('TESTSUBCMD')
        factory = SubscriptionHandlerFactory(
            manager_cls,
            command_prefix,
            aliases_command_prefix={f'{command_prefix}_alias'},
        )

        matcher = factory.register_handlers(permission_level=30)
        try:
            assert issubclass(matcher, AlconnaMatcher)

            # 注册声明式自检应已登记 7 条测试消息 (alconna matcher 注册期行为, 读取其内部条目仅作断言与清理)
            assert len(matcher._tests) == 7

            # default_state 应携带 processor state (名称按 sub_type 生成, 等级透传)
            processor_state = parse_processor_state(matcher._default_state)
            assert processor_state.name.endswith('SubscriptionManager')
            assert processor_state.level == 30
        finally:
            matcher._tests.clear()
            matcher.destroy()
