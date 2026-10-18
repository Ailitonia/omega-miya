"""
@Author         : Ailitonia
@Date           : 2026/10/10 12:50
@FileName       : test_013_omega_internal_params
@Project        : omega-miya
@Description    : omega params 模块单元测试 (通用参数补全/权限规则/子依赖/订阅管理与图站浏览模板)
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import random
from collections.abc import AsyncGenerator, Generator, Sequence
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, ClassVar
from unittest.mock import AsyncMock, MagicMock

import nonebot
import pytest
from nonebug import App

from tests.utils import (
    create_real_obv11_bot,
    make_fake_event,
    make_fake_message_event,
    make_mock_bot,
    make_non_plugin_matcher,
    make_obv11_group_message_event,
    make_obv11_private_message_event,
    make_real_obv11_bot,
    make_telegram_message_event,
    registered_online_bot,
    seed_entity_permissions,
    unique_test_id,
)

if TYPE_CHECKING:
    from src.service import OmegaMatcherInterface


def _make_prompt_matcher(response: Any) -> Any:
    """构造 prompt 替身 (组合式, 仅提供被测函数实际调用的 prompt 方法)"""
    return SimpleNamespace(prompt=AsyncMock(return_value=response))


def _match(result: Any, available: bool) -> Any:
    """构造 alconna Match 参数"""
    from nonebot_plugin_alconna import Match

    return Match(result, available)


class _RecordingFinishInterface:
    """组合式 Matcher 接口替身: 记录 finish_reply 消息并按真实语义抛出 FinishedException"""

    def __init__(self) -> None:
        self.finished: list[str] = []

    async def finish_reply(self, message: str, **kwargs: Any) -> None:
        from nonebot.exception import FinishedException

        self.finished.append(message)
        raise FinishedException


def _make_matcher_interface(bot_self_id: str = '10086', user_id: int = 10001) -> 'OmegaMatcherInterface':
    """构造绑定 mock Bot 与私聊消息事件的 OmegaMatcherInterface"""
    from src.service import OmegaMatcherInterface

    return OmegaMatcherInterface(
        bot=make_mock_bot(self_id=bot_self_id),
        event=make_obv11_private_message_event(user_id=user_id),
        matcher=make_non_plugin_matcher(),
    )


def _stub_running_scheduler(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """以运行中的调度器替身替换订阅管理 handlers 模块内的 scheduler 名字, 返回 pause/resume 调用记录列表"""
    import src.params.template.subscription_manager.handlers as handlers_module

    calls: list[str] = []
    monkeypatch.setattr(handlers_module, 'scheduler', SimpleNamespace(
        running=True,
        pause=lambda: calls.append('pause'),
        resume=lambda: calls.append('resume'),
    ))
    return calls


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
        ('src.params.handler', {'ensure_arg_text', 'ensure_multi_args_text'}),
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
        ('src.params.template.artwork_viewer', {
            'ALLOW_R18_NODE',
            'ArtworkViewerHandlerFactory',
            'ArtworkProcessHandler',
        }),
    ])
    def test_module_all(self, module_path: str, expected_all: set) -> None:
        import importlib

        module = importlib.import_module(module_path)

        assert set(module.__all__) == expected_all
        for name in module.__all__:
            assert getattr(module, name) is not None


class TestEnsureArgText:
    """ensure_arg_text 单参数补全测试 (直接调用, 组合式替身)"""

    async def test_arg_available_returned_stripped_without_prompt(self) -> None:
        from src.params.handler import ensure_arg_text

        prompt_matcher = _make_prompt_matcher(None)
        text = await ensure_arg_text(prompt_matcher, _RecordingFinishInterface(), _match('  1000  ', True), 'p:', 60)

        assert text == '1000'
        prompt_matcher.prompt.assert_not_awaited()

    @pytest.mark.parametrize(('arg_result', 'arg_available'), [('', False), ('   ', True)])
    async def test_missing_arg_prompted_and_stripped(self, arg_result: str, arg_available: bool) -> None:
        from nonebot_plugin_alconna.uniseg import UniMessage

        from src.params.handler import ensure_arg_text

        text = await ensure_arg_text(
            _make_prompt_matcher(UniMessage(' 2000 ')),
            _RecordingFinishInterface(),
            _match(arg_result, arg_available),
            'p:',
            60,
        )

        assert text == '2000'

    async def test_prompt_text_and_timeout_passed_through(self) -> None:
        from nonebot_plugin_alconna.uniseg import UniMessage

        from src.params.handler import ensure_arg_text

        prompt_matcher = _make_prompt_matcher(UniMessage('x'))
        await ensure_arg_text(prompt_matcher, _RecordingFinishInterface(), _match('', False), '请输入:', 60)

        assert prompt_matcher.prompt.await_args.args[0] == '请输入:'
        assert prompt_matcher.prompt.await_args.kwargs == {'timeout': 60}

    async def test_prompt_timeout_finishes(self) -> None:
        from nonebot.exception import FinishedException

        from src.params.handler import ensure_arg_text

        interface = _RecordingFinishInterface()

        with pytest.raises(FinishedException):
            await ensure_arg_text(_make_prompt_matcher(None), interface, _match('', False), 'p:', 60)

        assert interface.finished == ['等待输入超时, 已取消操作']

    async def test_prompt_empty_response_finishes(self) -> None:
        from nonebot.exception import FinishedException
        from nonebot_plugin_alconna.uniseg import UniMessage

        from src.params.handler import ensure_arg_text

        interface = _RecordingFinishInterface()

        with pytest.raises(FinishedException):
            await ensure_arg_text(_make_prompt_matcher(UniMessage('   ')), interface, _match('', False), 'p:', 60)

        assert interface.finished == ['未提供有效参数, 已取消操作']


class TestEnsureMultiArgsText:
    """ensure_multi_args_text 多参数补全测试 (直接调用, 组合式替身)"""

    async def test_sequence_args_stripped_and_filtered_without_prompt(self) -> None:
        from src.params.handler import ensure_multi_args_text

        prompt_matcher = _make_prompt_matcher(None)
        args = await ensure_multi_args_text(
            prompt_matcher, _RecordingFinishInterface(), _match(['  a  ', '', 'b'], True), 'p:', 60,
        )

        assert args == ['a', 'b']
        prompt_matcher.prompt.assert_not_awaited()

    async def test_str_result_wrapped_without_prompt(self) -> None:
        from src.params.handler import ensure_multi_args_text

        prompt_matcher = _make_prompt_matcher(None)
        args = await ensure_multi_args_text(
            prompt_matcher, _RecordingFinishInterface(), _match('  solo  ', True), 'p:', 60,
        )

        assert args == ['solo']
        prompt_matcher.prompt.assert_not_awaited()

    @pytest.mark.parametrize(('args_result', 'available'), [
        ([], False),
        ([], True),
        ([' ', ''], True),
    ])
    async def test_missing_args_prompted_and_split(self, args_result: list, available: bool) -> None:
        from nonebot_plugin_alconna.uniseg import UniMessage

        from src.params.handler import ensure_multi_args_text

        args = await ensure_multi_args_text(
            _make_prompt_matcher(UniMessage('foo  bar ')),
            _RecordingFinishInterface(),
            _match(args_result, available),
            'p:',
            60,
        )

        assert args == ['foo', 'bar']

    async def test_prompt_text_and_timeout_passed_through(self) -> None:
        from nonebot_plugin_alconna.uniseg import UniMessage

        from src.params.handler import ensure_multi_args_text

        prompt_matcher = _make_prompt_matcher(UniMessage('x'))
        await ensure_multi_args_text(prompt_matcher, _RecordingFinishInterface(), _match([], False), '请输入:', 60)

        assert prompt_matcher.prompt.await_args.args[0] == '请输入:'
        assert prompt_matcher.prompt.await_args.kwargs == {'timeout': 60}

    async def test_prompt_timeout_finishes(self) -> None:
        from nonebot.exception import FinishedException

        from src.params.handler import ensure_multi_args_text

        interface = _RecordingFinishInterface()

        with pytest.raises(FinishedException):
            await ensure_multi_args_text(_make_prompt_matcher(None), interface, _match([], False), 'p:', 60)

        assert interface.finished == ['等待输入超时, 已取消操作']

    async def test_prompt_empty_response_finishes(self) -> None:
        from nonebot.exception import FinishedException
        from nonebot_plugin_alconna.uniseg import UniMessage

        from src.params.handler import ensure_multi_args_text

        interface = _RecordingFinishInterface()

        with pytest.raises(FinishedException):
            await ensure_multi_args_text(
                _make_prompt_matcher(UniMessage('  ')), interface, _match([], False), 'p:', 60,
            )

        assert interface.finished == ['未提供有效参数, 已取消操作']


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

        bot = make_real_obv11_bot()
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

        bot = make_real_obv11_bot(self_id='10086')
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

        bot = make_real_obv11_bot()
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

        bot = make_real_obv11_bot()
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

    async def test_event_global_permission_rule(self, test_onebot_v11_bot) -> None:
        from src.params.rule import EventGlobalPermissionRule

        bot, event, user_id = self._make_private_case(test_onebot_v11_bot.self_id)

        rule = EventGlobalPermissionRule()
        assert await rule(bot, event) is False

        await seed_entity_permissions(test_onebot_v11_bot, 'onebot_v11_user', user_id, enable_global=True)
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
        await seed_entity_permissions(
            test_onebot_v11_bot, 'onebot_v11_user', user_id,
            enable_global=enable_global, permission_level=granted_level,
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
        await seed_entity_permissions(
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

        await seed_entity_permissions(test_onebot_v11_bot, 'onebot_v11_group', str(group_id), enable_global=True)

        assert await EventGlobalPermissionRule()(bot, event) is True
        assert await UserGlobalPermissionRule()(bot, event) is False

        await seed_entity_permissions(test_onebot_v11_bot, 'onebot_v11_user', str(user_id), enable_global=True)
        assert await UserGlobalPermissionRule()(bot, event) is True

    async def test_rule_check_failure_denies_with_warning(self, log_capture) -> None:
        """检查过程抛出异常 (未注册 EventDepend 的事件类型) 时应拒绝并记录警告, 不向事件分发层抛出"""
        from src.params.rule import (
            EventGlobalPermissionRule,
            EventPermissionLevelRule,
            UserGlobalPermissionRule,
        )

        bot = make_real_obv11_bot()
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
        assert await IS_ADMIN(make_real_obv11_bot(), make_fake_message_event(user_id='User')) is True

    async def test_onebot_v11_private(self) -> None:
        from src.params.permission import IS_ADMIN

        assert await IS_ADMIN(make_real_obv11_bot(), make_obv11_private_message_event()) is True

    @pytest.mark.parametrize(('role', 'expected'), [
        ('admin', True),
        ('owner', True),
        ('member', False),
        (None, False),
    ])
    async def test_onebot_v11_group_role(self, role: str | None, expected: bool) -> None:
        from src.params.permission import IS_ADMIN

        event = make_obv11_group_message_event(role=role)
        assert await IS_ADMIN(make_real_obv11_bot(), event) is expected

    async def test_telegram_private(self) -> None:
        from src.params.permission import IS_ADMIN

        event = make_telegram_message_event(
            'private',
            chat_id=10001,
            user_id=10001,
            original_message=[{'type': 'text', 'data': {'text': 'hi'}}],
        )
        assert await IS_ADMIN(make_real_obv11_bot(), event) is True

    async def test_non_privileged_event(self) -> None:
        from src.params.permission import IS_ADMIN

        assert await IS_ADMIN(make_real_obv11_bot(), make_fake_message_event(user_id='nobody')) is False

    async def test_check_event_is_admin_additional(self) -> None:
        """alconna assign additional 检查函数: 参数序为 (event, bot, state, arparma), 委托 IS_ADMIN"""
        from src.params.permission import check_event_is_admin

        bot = make_real_obv11_bot()
        assert await check_event_is_admin(make_obv11_private_message_event(), bot, {}, MagicMock()) is True
        assert await check_event_is_admin(make_obv11_group_message_event(role='member'), bot, {}, MagicMock()) is False
        assert await check_event_is_admin(make_obv11_group_message_event(role='admin'), bot, {}, MagicMock()) is True

    async def test_check_event_is_superuser_additional(self) -> None:
        """alconna assign additional 检查函数: 委托 SUPERUSER (测试配置中 superusers 包含 'User')"""
        from src.params.permission import check_event_is_superuser

        bot = make_real_obv11_bot()
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
        manager_cls = subscription_manager_stub_cls()
        source = await test_db_data_factory.create_test_subscription_source(sub_type=manager_cls.get_sub_type())
        manager = manager_cls(source.sub_id)

        interface = _make_matcher_interface(
            bot_self_id=test_onebot_v11_bot.self_id,
            user_id=random.randint(10_000_000, 99_999_999),
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
            await handler(prompt_matcher, interface or _make_matcher_interface(), match)
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

        calls = _stub_running_scheduler(monkeypatch)

        factory, manager_cls = handler_factory

        with pytest.raises(FinishedException):
            await factory._execute_add_subscription(interface=_make_matcher_interface(), sub_id='123')

        assert calls == ['pause', 'resume']
        assert manager_cls.add_sub_calls == ['123']

    async def test_add_handler_failure_still_resumes_scheduler(
            self, handler_factory, recording_uni_message, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """订阅执行失败时应返回友好提示且仍恢复调度器"""
        from nonebot.exception import FinishedException

        calls = _stub_running_scheduler(monkeypatch)

        factory, manager_cls = handler_factory
        manager_cls.fail_add = True

        with pytest.raises(FinishedException):
            await factory._execute_add_subscription(interface=_make_matcher_interface(), sub_id='123')

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
            await factory._execute_del_subscription(interface=_make_matcher_interface(), sub_id='123')

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

        await handler(_make_matcher_interface())

        assert self._sent_texts(recording_uni_message) == [expected_message]

    async def test_list_handler_query_failed(self, handler_factory, recording_uni_message) -> None:
        from nonebot.exception import FinishedException

        factory, manager_cls = handler_factory
        manager_cls.fail_query_exist = True
        handler = factory._generate_list_subscription_handler()

        with pytest.raises(FinishedException):
            await handler(_make_matcher_interface())

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
        interface = _make_matcher_interface(bot_self_id=test_onebot_v11_bot.self_id, user_id=user_id)
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
            await handler(self._make_prompt_matcher(None), _make_matcher_interface(), self._match('xxx', True))

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
        interface = _make_matcher_interface(bot_self_id=test_onebot_v11_bot.self_id, user_id=user_id)
        prompt_matcher = self._make_prompt_matcher(UniMessage('on'))
        await handler(prompt_matcher, interface, self._match('', False))

        prompt_matcher.prompt.assert_awaited_once()
        assert self._sent_texts(recording_uni_message) == ['已设置测试源订阅通知@所有人功能为【ON】']

    async def test_switch_notice_at_all_prompt_timeout(self, handler_factory, recording_uni_message) -> None:
        from nonebot.exception import FinishedException

        factory, _ = handler_factory
        handler = factory._generate_switch_subscription_notice_at_all_handler()

        with pytest.raises(FinishedException):
            await handler(self._make_prompt_matcher(None), _make_matcher_interface(), self._match('', False))

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
        interface = _make_matcher_interface(bot_self_id=test_onebot_v11_bot.self_id, user_id=user_id)
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


# ------------------------------------------------------------------ #
# artwork_viewer 模板测试辅助
# ------------------------------------------------------------------ #

class _StubHostedFile:
    """已托管文件替身: 仅提供 get_hosting_path"""

    def __init__(self, name: str) -> None:
        self.name = name

    async def get_hosting_path(self) -> str:
        return f'https://host.test/{self.name}'


class _RecordingArtworkInterface:
    """组合式 Matcher 接口替身: 记录 send/finish/revoke 调用, finish 语义抛出 FinishedException"""

    def __init__(self) -> None:
        self.sent: list = []
        self.finished: list = []
        self.revoked: list[tuple[Any, int]] = []

    async def send_reply(self, message: Any, **kwargs: Any) -> Any:
        self.sent.append(message)
        return SimpleNamespace(bot=SimpleNamespace(self_id='10086'), msg_ids=[f'msg_{len(self.sent)}'])

    async def finish_reply(self, message: Any, **kwargs: Any) -> None:
        self.finished.append(message)
        from nonebot.exception import FinishedException

        raise FinishedException

    async def revoke_bot_sent_msg(self, receipt: Any, *, revoke_delay: int = 0) -> None:
        self.revoked.append((receipt, revoke_delay))


def _make_artwork_query_data(
        aid: str = '1000',
        *,
        rating: int = 0,
        page_indexes: Sequence[int] = (0, 1),
) -> Any:
    """构造测试用 ArtworkProxyData (分级与页索引可编程)"""
    from src.database.internal.artwork_collection import ArtworkClassification
    from src.service.artwork_proxy.models import ArtworkPage, ArtworkPageFile, ArtworkProxyData

    page_file = ArtworkPageFile(url='https://img.test/page.jpg', file_ext='jpg')
    return ArtworkProxyData(
        origin='test_gallery',
        aid=aid,
        uid='2000',
        title='test artwork',
        uname='test artist',
        classification=ArtworkClassification.HUMAN_CONFIRMED,
        rating=rating,
        width=1000,
        height=1000,
        source=f'https://source.test/{aid}',
        pages=[
            ArtworkPage(page_index=i, preview_file=page_file, regular_file=page_file, original_file=page_file)
            for i in page_indexes
        ],
    )


def _make_plugin_matcher(module_name: str = 'TestModule', plugin_name: str = 'TestPlugin') -> Any:
    """构造携带假 plugin 对象的 Matcher 实例 (子类属性遮蔽 classproperty, 供权限节点检查路径使用)"""
    from nonebot.matcher import Matcher

    fake_plugin = SimpleNamespace(module_name=module_name, name=plugin_name)
    return type('FakePluginMatcher', (Matcher,), {'plugin': fake_plugin, 'temp': False})()


@pytest.fixture
def artwork_stub_cls() -> type:
    """构造行为可编程的 BaseArtworkProxy 测试子类 (类级记录容器随每次 fixture 调用重建)"""
    from src.service.artwork_proxy.internal import BaseArtworkProxy

    class _StubArtworkProxy(BaseArtworkProxy):
        """测试用图站代理: 查询结果与各分类查询的返回值均由类属性编程"""

        query_results: ClassVar[dict[str, Any]] = {}
        random_ids: ClassVar[list[str]] = []
        search_ids: ClassVar[list[str]] = []
        ranking_ids: ClassVar[list[str]] = []
        bookmark_ids: ClassVar[list[str]] = []
        user_data: ClassVar[Any] = None
        random_limits: ClassVar[list[int]] = []
        search_received: ClassVar[list[tuple[str, int | None]]] = []
        ranking_received: ClassVar[list[tuple[str, int]]] = []
        bookmark_received: ClassVar[list[tuple[str, int]]] = []
        user_received: ClassVar[list[str]] = []
        proceed_calls: ClassVar[list[tuple[int, str]]] = []
        preview_calls: ClassVar[list[dict]] = []

        @classmethod
        def _get_base_origin_name(cls) -> str:
            return 'test_gallery'

        @classmethod
        async def _get_resource_as_bytes(cls, url: str, *, timeout: int = 30) -> bytes:
            raise NotImplementedError

        @classmethod
        async def _random(cls, *, limit: int = 20) -> list[str]:
            cls.random_limits.append(limit)
            return list(cls.random_ids)

        @classmethod
        async def _search(cls, keyword: str, *, page: int | None = None, **kwargs: Any) -> list[str]:
            cls.search_received.append((keyword, page))
            return list(cls.search_ids)

        async def _query(self) -> Any:
            raise NotImplementedError

        async def get_std_desc(self, *, split_len: int = 128) -> str:
            return f'{self.origin_name.title()} {self.s_aid} desc'

        async def get_std_preview_desc(self, *, split_len: int = 12) -> str:
            return self.s_aid

        @classmethod
        async def _query_pool(cls, pool_id: str | int) -> Any:
            raise NotImplementedError

        @classmethod
        async def _discovery(cls, *, limit: int = 20) -> list[str]:
            raise NotImplementedError

        @classmethod
        async def _recommend(cls, base_aid: str | int | None = None, *, limit: int = 20) -> list[str]:
            raise NotImplementedError

        @classmethod
        async def _daily_ranking(cls, page: int) -> list[str]:
            cls.ranking_received.append(('daily', page))
            return list(cls.ranking_ids)

        @classmethod
        async def _weekly_ranking(cls, page: int) -> list[str]:
            cls.ranking_received.append(('weekly', page))
            return list(cls.ranking_ids)

        @classmethod
        async def _monthly_ranking(cls, page: int) -> list[str]:
            cls.ranking_received.append(('monthly', page))
            return list(cls.ranking_ids)

        @classmethod
        async def _query_user(cls, uid: str | int) -> Any:
            raise NotImplementedError

        @classmethod
        async def query_user(cls, uid: str | int, *, use_cache: bool = True) -> Any:
            cls.user_received.append(str(uid))
            return cls.user_data

        @classmethod
        async def _query_user_bookmark_artworks(cls, uid: str | int, page: int) -> list[str]:
            cls.bookmark_received.append((str(uid), page))
            return list(cls.bookmark_ids)

        @classmethod
        async def _query_follow_latest(cls, page: int, *, filter_tag: str | None = None) -> list[str]:
            raise NotImplementedError

        async def query(self, *, use_cache: bool = True) -> Any:
            if (data := self.query_results.get(self.s_aid)) is None:
                raise ValueError(f'no preset query result for {self.s_aid}')
            self.artwork_data = data
            return data

        async def get_custom_proceed_page_file(
                self,
                page_index: int = 0,
                *,
                page_type: str = 'regular',
                process_mode: str = 'mark',
        ) -> Any:
            type(self).proceed_calls.append((page_index, process_mode))
            return _StubHostedFile(name=f'{self.s_aid}_p{page_index}_{process_mode}')

        @classmethod
        async def generate_artworks_preview(
                cls,
                preview_name: str,
                artworks: Sequence[Any],
                *,
                page_type: str = 'preview',
                process_handler: Any = None,
                preview_size: tuple[int, int] = (256, 256),
                header_color: tuple[int, int, int] = (0, 150, 250),
                edge_scale: float = 1 / 32,
                num_of_line: int = 6,
                limit: int = 100,
        ) -> Any:
            cls.preview_calls.append({
                'preview_name': preview_name,
                'artworks': list(artworks),
                'process_handler': process_handler,
                'limit': limit,
            })
            return _StubHostedFile(name=f'preview_{preview_name}')

    return _StubArtworkProxy


@pytest.fixture
def recording_artwork_context(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """以记录型替身重绑定 artwork_viewer.handlers 命名空间内的 ARTWORK_CONTEXT_MANAGER"""
    import src.params.template.artwork_viewer.handlers as artwork_handlers_module

    recorded: list[dict] = []

    async def _set_message_context(receipt: Any, data: Any = None, **context_data: Any) -> str:
        recorded.append(context_data)
        return 'test_cache_key'

    monkeypatch.setattr(
        artwork_handlers_module,
        'ARTWORK_CONTEXT_MANAGER',
        SimpleNamespace(set_message_context=_set_message_context),
    )
    return recorded


class TestArtworkFactoryInit:
    """ArtworkViewerHandlerFactory 构造与基础属性测试"""

    def test_default_prefix_from_origin_name(self, artwork_stub_cls) -> None:
        from src.params.template.artwork_viewer import ArtworkViewerHandlerFactory

        factory = ArtworkViewerHandlerFactory(artwork_stub_cls)

        assert factory._command_prefix == 'test_gallery'
        assert factory._aliases_command_prefix == set()
        assert factory._need_decimal_artwork_id is False
        assert factory._need_decimal_user_id is False
        assert factory.origin == 'test_gallery'
        assert str(factory) == 'ArtworkViewerHandlerFactory | Test_Gallery'

    def test_explicit_prefix_normalized(self, artwork_stub_cls) -> None:
        from src.params.template.artwork_viewer import ArtworkViewerHandlerFactory

        factory = ArtworkViewerHandlerFactory(
            artwork_stub_cls,
            '  CustomCMD  ',
            aliases_command_prefix={'Alias_One', 'two'},
        )

        assert factory._command_prefix == 'customcmd'
        assert factory._aliases_command_prefix == {'Alias_One', 'two'}

    @pytest.mark.parametrize('bad_prefix', ['', '   ', '\t'])
    def test_blank_prefix_rejected(self, artwork_stub_cls, bad_prefix: str) -> None:
        """显式提供的空/纯空白前缀应当抛出 ValueError 而非静默回退"""
        from src.params.template.artwork_viewer import ArtworkViewerHandlerFactory

        with pytest.raises(ValueError, match='command_prefix must not be empty'):
            ArtworkViewerHandlerFactory(artwork_stub_cls, bad_prefix)


class TestParseRankingMode:
    """榜单类型解析真值表测试"""

    @pytest.mark.parametrize(('mode', 'expected'), [
        ('', 'monthly'),
        ('月榜', 'monthly'),
        ('每月', 'monthly'),
        ('月', 'monthly'),
        ('month', 'monthly'),
        ('  Monthly ', 'monthly'),
        ('日榜', 'daily'),
        ('每日', 'daily'),
        ('日', 'daily'),
        ('day', 'daily'),
        ('DAILY', 'daily'),
        ('周榜', 'weekly'),
        ('每周', 'weekly'),
        ('周', 'weekly'),
        ('week', 'weekly'),
        ('Weekly', 'weekly'),
        ('年榜', None),
        ('foo', None),
    ])
    def test_parse_ranking_mode(self, mode: str, expected: str | None) -> None:
        from src.params.template.artwork_viewer import ArtworkViewerHandlerFactory

        assert ArtworkViewerHandlerFactory._parse_ranking_mode(mode) == expected


class TestArtworkCheckAllowR18:
    """allow_r18 权限节点检查测试"""

    async def test_non_plugin_matcher_denied(self, artwork_stub_cls) -> None:
        from src.params.template.artwork_viewer import ArtworkViewerHandlerFactory

        factory = ArtworkViewerHandlerFactory(artwork_stub_cls)

        assert await factory.check_allow_r18(interface=_make_matcher_interface()) is False

    async def test_checker_failure_denies_with_warning(
            self, artwork_stub_cls, monkeypatch: pytest.MonkeyPatch, log_capture,
    ) -> None:
        import src.params.template.artwork_viewer.handlers as artwork_handlers_module
        from src.params.template.artwork_viewer import ArtworkViewerHandlerFactory

        async def _broken_checker(interface: Any) -> bool:
            raise RuntimeError('broken checker')

        monkeypatch.setattr(artwork_handlers_module, '_allow_r18_node_checker', _broken_checker)

        factory = ArtworkViewerHandlerFactory(artwork_stub_cls)

        assert await factory.check_allow_r18(interface=_make_matcher_interface()) is False
        assert any('ALLOW_R18_NODE node failed' in message for message in log_capture)

    async def test_grant_flow_with_real_permissions(self, artwork_stub_cls, test_onebot_v11_bot) -> None:
        """全局功能与 allow_r18 节点必须同时授权"""
        from src.params.template.artwork_viewer import ArtworkViewerHandlerFactory
        from src.service import OmegaMatcherInterface

        factory = ArtworkViewerHandlerFactory(artwork_stub_cls)

        granted_user = random.randint(10_000_000, 99_999_999)
        denied_user = random.randint(10_000_000, 99_999_999)
        global_only_user = random.randint(10_000_000, 99_999_999)
        node_only_user = random.randint(10_000_000, 99_999_999)

        def _interface(user_id: int) -> 'OmegaMatcherInterface':
            return OmegaMatcherInterface(
                bot=make_mock_bot(self_id=test_onebot_v11_bot.self_id),
                event=make_obv11_private_message_event(user_id=user_id),
                matcher=_make_plugin_matcher('TestModule', 'TestPlugin'),
            )

        assert await factory.check_allow_r18(interface=_interface(granted_user)) is False

        await seed_entity_permissions(test_onebot_v11_bot, 'onebot_v11_user', str(global_only_user), enable_global=True)
        assert await factory.check_allow_r18(interface=_interface(global_only_user)) is False

        await seed_entity_permissions(
            test_onebot_v11_bot,
            'onebot_v11_user',
            str(node_only_user),
            enable_global=False,
            auth_nodes=[('TestModule', 'TestPlugin', 'allow_r18', 1)],
        )
        assert await factory.check_allow_r18(interface=_interface(node_only_user)) is False

        await seed_entity_permissions(
            test_onebot_v11_bot,
            'onebot_v11_user',
            str(granted_user),
            enable_global=True,
            auth_nodes=[('TestModule', 'TestPlugin', 'allow_r18', 1)],
        )
        assert await factory.check_allow_r18(interface=_interface(granted_user)) is True

        await seed_entity_permissions(
            test_onebot_v11_bot,
            'onebot_v11_user',
            str(denied_user),
            enable_global=True,
            auth_nodes=[('TestModule', 'TestPlugin', 'allow_r18', 0)],
        )
        assert await factory.check_allow_r18(interface=_interface(denied_user)) is False


class TestSendArtworkMessage:
    """send_artwork_message 边界测试 (组合式接口替身)"""

    @pytest.fixture
    def factory(self, artwork_stub_cls) -> Any:
        from src.params.template.artwork_viewer import ArtworkViewerHandlerFactory

        return ArtworkViewerHandlerFactory(artwork_stub_cls)

    async def test_empty_pages_raises(self, factory, artwork_stub_cls) -> None:
        artwork_stub_cls.query_results = {'1000': _make_artwork_query_data('1000', page_indexes=())}

        with pytest.raises(ValueError, match='has no available pages'):
            await factory.send_artwork_message(_RecordingArtworkInterface(), artwork_stub_cls('1000'))

    @pytest.mark.parametrize('bad_limiting', [0, -1])
    async def test_invalid_limiting_raises(self, factory, artwork_stub_cls, bad_limiting: int) -> None:
        artwork_stub_cls.query_results = {'1000': _make_artwork_query_data('1000')}

        with pytest.raises(ValueError, match='show_pages_limiting'):
            await factory.send_artwork_message(
                _RecordingArtworkInterface(), artwork_stub_cls('1000'), show_pages_limiting=bad_limiting,
            )

    @pytest.mark.parametrize(('rating', 'allow_r18', 'expected_mode', 'expected_revoke_count'), [
        (-1, False, 'mark', 0),
        (-1, True, 'mark', 0),
        (0, False, 'mark', 0),
        (0, True, 'mark', 0),
        (1, False, 'mark', 0),
        (1, True, 'mark', 0),
        (2, False, 'blur', 0),
        (2, True, 'noise', 1),
        (3, False, 'blur', 0),
        (3, True, 'noise', 1),
    ])
    async def test_rating_process_and_revoke(
            self,
            factory,
            artwork_stub_cls,
            recording_artwork_context,
            rating: int,
            allow_r18: bool,
            expected_mode: str,
            expected_revoke_count: int,
    ) -> None:
        """默认分级处理与撤回策略真值表"""
        artwork_stub_cls.query_results = {'1000': _make_artwork_query_data('1000', rating=rating, page_indexes=(0,))}
        interface = _RecordingArtworkInterface()

        await factory.send_artwork_message(interface, artwork_stub_cls('1000'), allow_r18=allow_r18)

        assert artwork_stub_cls.proceed_calls == [(0, expected_mode)]
        assert len(interface.revoked) == expected_revoke_count
        if expected_revoke_count:
            assert interface.revoked[0][1] == 90
        assert len(interface.sent) == 1

    @pytest.mark.parametrize(('process_mode', 'expected_revoke_count'), [
        ('mark', 1),
        ('blur', 0),
        ('noise', 1),
    ])
    async def test_custom_process_mode_and_revoke(
            self,
            artwork_stub_cls,
            recording_artwork_context,
            process_mode: str,
            expected_revoke_count: int,
    ) -> None:
        """QUESTIONABLE 以上作品仅在实际处理模式不是 blur 时撤回"""
        from src.params.template.artwork_viewer import ArtworkViewerHandlerFactory

        factory = ArtworkViewerHandlerFactory(
            artwork_stub_cls,
            normal_artwork_process_handler=lambda _: process_mode,
        )
        artwork_stub_cls.query_results = {'1000': _make_artwork_query_data('1000', rating=3, page_indexes=(0,))}
        interface = _RecordingArtworkInterface()

        await factory.send_artwork_message(interface, artwork_stub_cls('1000'))

        assert artwork_stub_cls.proceed_calls == [(0, process_mode)]
        assert len(interface.revoked) == expected_revoke_count

    @pytest.mark.parametrize(('allow_r18', 'expected_mode'), [(False, 'blur'), (True, 'noise')])
    async def test_custom_process_handler_for_unknown(
            self,
            artwork_stub_cls,
            recording_artwork_context,
            allow_r18: bool,
            expected_mode: str,
    ) -> None:
        """UNKNOWN 图片处理策略可由应用层注入的 handler 覆盖"""
        from src.params.template.artwork_viewer import ArtworkViewerHandlerFactory

        factory = ArtworkViewerHandlerFactory(
            artwork_stub_cls,
            normal_artwork_process_handler=lambda _: 'blur',
            allow_r18_artwork_process_handler=lambda _: 'noise',
        )
        artwork_stub_cls.query_results = {'1000': _make_artwork_query_data('1000', rating=-1, page_indexes=(0,))}
        interface = _RecordingArtworkInterface()

        await factory.send_artwork_message(interface, artwork_stub_cls('1000'), allow_r18=allow_r18)

        assert artwork_stub_cls.proceed_calls == [(0, expected_mode)]
        assert interface.revoked == []

    async def test_pages_truncated_with_desc_prefix(
            self, factory, artwork_stub_cls, recording_artwork_context,
    ) -> None:
        """页数超出限制时仅发送前若干页, 描述前缀标注 (n of m pages)"""
        artwork_stub_cls.query_results = {'1000': _make_artwork_query_data('1000', page_indexes=(0, 1, 2))}
        interface = _RecordingArtworkInterface()

        await factory.send_artwork_message(interface, artwork_stub_cls('1000'), show_pages_limiting=2)

        assert [call[0] for call in artwork_stub_cls.proceed_calls] == [0, 1]
        assert '(2 of 3 pages)' in interface.sent[0].extract_plain_text()

    async def test_context_failure_warns_only(
            self, factory, artwork_stub_cls, monkeypatch: pytest.MonkeyPatch, log_capture,
    ) -> None:
        """上下文写入失败时仅记录警告, 消息发送不受影响"""
        import src.params.template.artwork_viewer.handlers as artwork_handlers_module

        async def _broken_set_context(receipt: Any, data: Any = None, **kwargs: Any) -> str:
            raise RuntimeError('broken context')

        monkeypatch.setattr(
            artwork_handlers_module,
            'ARTWORK_CONTEXT_MANAGER',
            SimpleNamespace(set_message_context=_broken_set_context),
        )

        artwork_stub_cls.query_results = {'1000': _make_artwork_query_data('1000', page_indexes=(0,))}
        interface = _RecordingArtworkInterface()

        await factory.send_artwork_message(interface, artwork_stub_cls('1000'))

        assert len(interface.sent) == 1
        assert any('Set' in message and 'context failed' in message for message in log_capture)

    async def test_revoke_failure_warns_only(
            self, factory, artwork_stub_cls, recording_artwork_context, monkeypatch: pytest.MonkeyPatch, log_capture,
    ) -> None:
        """撤回调度失败时仅记录警告, 消息发送不受影响"""
        artwork_stub_cls.query_results = {'1000': _make_artwork_query_data('1000', rating=3, page_indexes=(0,))}
        interface = _RecordingArtworkInterface()

        async def _broken_revoke(receipt: Any, *, revoke_delay: int = 0) -> None:
            raise RuntimeError('broken revoke')

        monkeypatch.setattr(interface, 'revoke_bot_sent_msg', _broken_revoke)

        await factory.send_artwork_message(interface, artwork_stub_cls('1000'), allow_r18=True)

        assert len(interface.sent) == 1
        assert any('Schedule revoking' in message and 'failed' in message for message in log_capture)


class TestSendArtworksPreviewMessage:
    """send_artworks_preview_message 边界测试"""

    @pytest.fixture
    def factory(self, artwork_stub_cls) -> Any:
        from src.params.template.artwork_viewer import ArtworkViewerHandlerFactory

        return ArtworkViewerHandlerFactory(artwork_stub_cls)

    @pytest.mark.parametrize('bad_limiting', [0, -1])
    async def test_invalid_limiting_raises(self, factory, artwork_stub_cls, bad_limiting: int) -> None:
        with pytest.raises(ValueError, match='show_artworks_limiting'):
            await factory.send_artworks_preview_message(
                _RecordingArtworkInterface(),
                'title',
                [artwork_stub_cls('1')],
                show_artworks_limiting=bad_limiting,
            )

    async def test_empty_artworks_raises(self, factory, artwork_stub_cls) -> None:
        with pytest.raises(ValueError, match='artworks must not be empty'):
            await factory.send_artworks_preview_message(_RecordingArtworkInterface(), 'title', [])

    @pytest.mark.parametrize(('allow_r18', 'expected_handler_attr'), [
        (False, '_aph_normal'),
        (True, '_aph_allow_r18'),
    ])
    async def test_slice_and_process_handler_passed(
            self, factory, artwork_stub_cls, allow_r18: bool, expected_handler_attr: str,
    ) -> None:
        artworks = [artwork_stub_cls(str(i)) for i in range(5)]
        interface = _RecordingArtworkInterface()

        await factory.send_artworks_preview_message(
            interface, 'preview title', artworks, allow_r18=allow_r18, show_artworks_limiting=3,
        )

        assert len(artwork_stub_cls.preview_calls) == 1
        preview_call = artwork_stub_cls.preview_calls[0]
        assert preview_call['preview_name'] == 'preview title'
        assert preview_call['limit'] == 3
        assert preview_call['artworks'] == artworks[:3]
        assert preview_call['process_handler'] is getattr(factory, expected_handler_attr)
        assert len(interface.sent) == 1

    @pytest.mark.parametrize(('allow_r18', 'expected_revoke_num'), [(False, 0), (True, 1)])
    async def test_revoke_only_for_allow_r18(
            self, factory, artwork_stub_cls, allow_r18: bool, expected_revoke_num: int,
    ) -> None:
        interface = _RecordingArtworkInterface()

        await factory.send_artworks_preview_message(
            interface, 'title', [artwork_stub_cls('1')], allow_r18=allow_r18,
        )

        assert len(interface.revoked) == expected_revoke_num

    async def test_revoke_failure_warns_only(
            self, factory, artwork_stub_cls, monkeypatch: pytest.MonkeyPatch, log_capture,
    ) -> None:
        """预览消息撤回调度失败时仅记录警告"""
        interface = _RecordingArtworkInterface()

        async def _broken_revoke(receipt: Any, *, revoke_delay: int = 0) -> None:
            raise RuntimeError('broken revoke')

        monkeypatch.setattr(interface, 'revoke_bot_sent_msg', _broken_revoke)

        await factory.send_artworks_preview_message(
            interface, 'title', [artwork_stub_cls('1')], allow_r18=True,
        )

        assert len(interface.sent) == 1
        assert any('Schedule revoking' in message and 'failed' in message for message in log_capture)


class TestExecuteQueryAndSendResult:
    """execute_query_and_send_result 分支测试"""

    @pytest.fixture
    def factory(self, artwork_stub_cls) -> Any:
        from src.params.template.artwork_viewer import ArtworkViewerHandlerFactory

        return ArtworkViewerHandlerFactory(artwork_stub_cls)

    @staticmethod
    def _query_coro(artworks: list, title: str = 't') -> Any:
        async def _query() -> tuple[list, str]:
            return artworks, title

        return _query()

    async def test_empty_result_finishes_with_hint(self, factory) -> None:
        from nonebot.exception import FinishedException

        interface = _RecordingArtworkInterface()

        with pytest.raises(FinishedException):
            await factory.execute_query_and_send_result(
                interface, self._query_coro([]), allow_r18=False,
            )

        assert interface.finished == ['未找到相关作品, 请尝试调整查询条件后重试']

    async def test_single_artwork_sends_detail(
            self, factory, artwork_stub_cls, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        artwork = artwork_stub_cls('1000')
        detail_calls: list[dict] = []

        async def _record_detail(interface: Any, artwork: Any, **kwargs: Any) -> None:
            detail_calls.append({'artwork': artwork, **kwargs})

        monkeypatch.setattr(factory, 'send_artwork_message', _record_detail)

        await factory.execute_query_and_send_result(
            _RecordingArtworkInterface(), self._query_coro([artwork]), allow_r18=True,
        )

        assert detail_calls == [{'artwork': artwork, 'allow_r18': True}]

    async def test_multiple_artworks_sends_preview(
            self, factory, artwork_stub_cls, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        artworks = [artwork_stub_cls('1'), artwork_stub_cls('2')]
        preview_calls: list[dict] = []

        async def _record_preview(interface: Any, title: str, artworks: Any, **kwargs: Any) -> None:
            preview_calls.append({'title': title, 'artworks': artworks, **kwargs})

        monkeypatch.setattr(factory, 'send_artworks_preview_message', _record_preview)

        await factory.execute_query_and_send_result(
            _RecordingArtworkInterface(), self._query_coro(artworks, 'search title'), allow_r18=False,
        )

        assert preview_calls == [{
            'title': 'search title',
            'artworks': artworks,
            'allow_r18': False,
            'show_artworks_limiting': 60,
        }]

    async def test_not_implemented_finishes_friendly(self, factory) -> None:
        from nonebot.exception import FinishedException

        async def _unsupported() -> tuple[list, str]:
            raise NotImplementedError('search not supported')

        interface = _RecordingArtworkInterface()

        with pytest.raises(FinishedException):
            await factory.execute_query_and_send_result(interface, _unsupported(), allow_r18=False)

        assert interface.finished == ['Test_Gallery不支持该功能, 请确认后再重试']

    async def test_generic_exception_finishes_friendly(self, factory) -> None:
        from nonebot.exception import FinishedException

        async def _failed() -> tuple[list, str]:
            raise RuntimeError('network down')

        interface = _RecordingArtworkInterface()

        with pytest.raises(FinishedException):
            await factory.execute_query_and_send_result(interface, _failed(), allow_r18=False)

        assert interface.finished == ['获取作品失败了, 可能是网络原因或者作品已经被删除, 请稍后再试']

    async def test_matcher_exception_reraised(self, factory) -> None:
        """MatcherException (含 FinishedException) 必须原样透传, 不被转换为友好提示"""
        from nonebot.exception import FinishedException

        async def _finish_like_query() -> tuple[list, str]:
            raise FinishedException

        with pytest.raises(FinishedException):
            await factory.execute_query_and_send_result(
                _RecordingArtworkInterface(), _finish_like_query(), allow_r18=False,
            )


class TestArtworkEnsureArgs:
    """_ensure_arg_text / _ensure_keywords 参数补全测试"""

    @staticmethod
    def _match(result: Any, available: bool) -> Any:
        from nonebot_plugin_alconna import Match

        return Match(result, available)

    async def test_arg_text_stripped(self) -> None:
        from src.params.template.artwork_viewer import ArtworkViewerHandlerFactory

        text = await ArtworkViewerHandlerFactory._ensure_arg_text(
            TestSubscriptionHandlerFactory._make_prompt_matcher(None),
            _RecordingArtworkInterface(),
            self._match('  1000  ', True),
            'prompt:',
        )
        assert text == '1000'

    @pytest.mark.parametrize(('arg_result', 'arg_available'), [('', False), ('   ', True)])
    async def test_arg_prompted_when_missing(self, arg_result: str, arg_available: bool) -> None:
        from nonebot_plugin_alconna.uniseg import UniMessage

        from src.params.template.artwork_viewer import ArtworkViewerHandlerFactory

        text = await ArtworkViewerHandlerFactory._ensure_arg_text(
            TestSubscriptionHandlerFactory._make_prompt_matcher(UniMessage(' 2000 ')),
            _RecordingArtworkInterface(),
            self._match(arg_result, arg_available),
            'prompt:',
        )
        assert text == '2000'

    async def test_arg_prompt_timeout_finishes(self) -> None:
        from nonebot.exception import FinishedException

        from src.params.template.artwork_viewer import ArtworkViewerHandlerFactory

        interface = _RecordingArtworkInterface()

        with pytest.raises(FinishedException):
            await ArtworkViewerHandlerFactory._ensure_arg_text(
                TestSubscriptionHandlerFactory._make_prompt_matcher(None),
                interface,
                self._match('', False),
                'prompt:',
            )

        assert interface.finished == ['等待输入超时, 已取消操作']

    async def test_arg_prompt_empty_finishes(self) -> None:
        from nonebot.exception import FinishedException
        from nonebot_plugin_alconna.uniseg import UniMessage

        from src.params.template.artwork_viewer import ArtworkViewerHandlerFactory

        interface = _RecordingArtworkInterface()

        with pytest.raises(FinishedException):
            await ArtworkViewerHandlerFactory._ensure_arg_text(
                TestSubscriptionHandlerFactory._make_prompt_matcher(UniMessage('   ')),
                interface,
                self._match('', False),
                'prompt:',
            )

        assert interface.finished == ['未提供有效参数, 已取消操作']

    @pytest.mark.parametrize(('keywords_result', 'expected'), [
        (['foo', 'bar'], 'foo bar'),
        ('solo', 'solo'),
        (['  a  ', 'b'], 'a b'),
    ])
    async def test_keywords_merged(self, keywords_result: Any, expected: str) -> None:
        from src.params.template.artwork_viewer import ArtworkViewerHandlerFactory

        text = await ArtworkViewerHandlerFactory._ensure_keywords(
            TestSubscriptionHandlerFactory._make_prompt_matcher(None),
            _RecordingArtworkInterface(),
            self._match(keywords_result, True),
        )
        assert text == expected

    @pytest.mark.parametrize(('keywords_result', 'available'), [([], False), ([' ', ''], True)])
    async def test_keywords_prompted_when_missing(self, keywords_result: Any, available: bool) -> None:
        from nonebot_plugin_alconna.uniseg import UniMessage

        from src.params.template.artwork_viewer import ArtworkViewerHandlerFactory

        text = await ArtworkViewerHandlerFactory._ensure_keywords(
            TestSubscriptionHandlerFactory._make_prompt_matcher(UniMessage('foo bar')),
            _RecordingArtworkInterface(),
            self._match(keywords_result, available),
        )
        assert text == 'foo bar'

    @pytest.mark.parametrize(('response_text', 'expected_message'), [
        (None, '等待输入超时, 已取消操作'),
        ('   ', '未提供有效搜索关键词, 已取消操作'),
    ])
    async def test_keywords_prompt_failure_finishes(self, response_text: str | None, expected_message: str) -> None:
        from nonebot.exception import FinishedException
        from nonebot_plugin_alconna.uniseg import UniMessage

        from src.params.template.artwork_viewer import ArtworkViewerHandlerFactory

        response = UniMessage(response_text) if response_text is not None else None
        interface = _RecordingArtworkInterface()

        with pytest.raises(FinishedException):
            await ArtworkViewerHandlerFactory._ensure_keywords(
                TestSubscriptionHandlerFactory._make_prompt_matcher(response),
                interface,
                self._match([], False),
            )

        assert interface.finished == [expected_message]


class TestArtworkGeneratedHandlers:
    """生成的各子命令 handler 参数校验与分发测试"""

    @pytest.fixture
    def factory(self, artwork_stub_cls) -> Any:
        from src.params.template.artwork_viewer import ArtworkViewerHandlerFactory

        return ArtworkViewerHandlerFactory(artwork_stub_cls, 'test_gallery')

    @staticmethod
    def _match(result: Any, available: bool) -> Any:
        from nonebot_plugin_alconna import Match

        return Match(result, available)

    @staticmethod
    def _patch_execute(monkeypatch: pytest.MonkeyPatch, factory: Any) -> list[dict]:
        """以消费并记录查询协程结果的替身替换 execute_query_and_send_result"""
        calls: list[dict] = []

        async def _record(interface: Any, query_handler: Any, **kwargs: Any) -> None:
            artworks, title = await query_handler
            calls.append({'artworks': artworks, 'title': title, **kwargs})

        monkeypatch.setattr(factory, 'execute_query_and_send_result', _record)
        return calls

    async def test_view_rejects_non_decimal_id(self, artwork_stub_cls) -> None:
        from nonebot.exception import FinishedException

        from src.params.template.artwork_viewer import ArtworkViewerHandlerFactory

        factory = ArtworkViewerHandlerFactory(artwork_stub_cls, 'test_gallery', need_decimal_artwork_id=True)
        interface = _RecordingArtworkInterface()

        with pytest.raises(FinishedException):
            await factory._generate_view_artwork_handler()(
                TestSubscriptionHandlerFactory._make_prompt_matcher(None),
                interface,
                self._match('abc', True),
            )

        assert interface.finished == ['作品ID应当为纯数字, 请确认后重试']

    async def test_view_dispatches_query(self, factory, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(factory, 'check_allow_r18', AsyncMock(return_value=False))
        calls = self._patch_execute(monkeypatch, factory)
        interface = _RecordingArtworkInterface()

        await factory._generate_view_artwork_handler()(
            TestSubscriptionHandlerFactory._make_prompt_matcher(None),
            interface,
            self._match('123456', True),
        )

        assert interface.sent
        assert interface.sent[0] == '稍等, 正在获取作品信息~'
        assert len(calls) == 1
        assert [artwork.s_aid for artwork in calls[0]['artworks']] == ['123456']
        assert calls[0]['title'] == ''
        assert calls[0]['allow_r18'] is False

    @pytest.mark.parametrize(('num', 'valid'), [(0, False), (61, False), (-1, False), (1, True), (60, True)])
    async def test_random_num_bounds(self, factory, monkeypatch: pytest.MonkeyPatch, num: int, valid: bool) -> None:
        from nonebot.exception import FinishedException

        monkeypatch.setattr(factory, 'check_allow_r18', AsyncMock(return_value=False))
        calls = self._patch_execute(monkeypatch, factory)
        interface = _RecordingArtworkInterface()

        if valid:
            await factory._generate_random_artworks_handler()(interface, self._match(num, True))
            assert calls[0]['show_artworks_limiting'] == num
        else:
            with pytest.raises(FinishedException):
                await factory._generate_random_artworks_handler()(interface, self._match(num, True))
            assert interface.finished == ['作品数量应当在 1~60 之间, 请确认后重试']

    async def test_random_defaults_and_queries(
            self, factory, artwork_stub_cls, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        artwork_stub_cls.random_ids = ['1', '2', '3']
        monkeypatch.setattr(factory, 'check_allow_r18', AsyncMock(return_value=False))
        calls = self._patch_execute(monkeypatch, factory)

        await factory._generate_random_artworks_handler()(_RecordingArtworkInterface(), self._match(0, False))

        assert artwork_stub_cls.random_limits == [60]
        assert [artwork.s_aid for artwork in calls[0]['artworks']] == ['1', '2', '3']
        assert calls[0]['show_artworks_limiting'] == 60
        assert 'Random Artworks' in calls[0]['title']

    async def test_search_invalid_page_rejected(self, factory) -> None:
        from nonebot.exception import FinishedException

        interface = _RecordingArtworkInterface()

        with pytest.raises(FinishedException):
            await factory._generate_search_artworks_handler()(
                TestSubscriptionHandlerFactory._make_prompt_matcher(None),
                interface,
                self._match(['foo'], True),
                self._match(0, True),
            )

        assert interface.finished == ['查询页码应当为正整数, 请确认后重试']

    async def test_search_dispatches_query(self, factory, artwork_stub_cls, monkeypatch: pytest.MonkeyPatch) -> None:
        artwork_stub_cls.search_ids = ['1', '2']
        monkeypatch.setattr(factory, 'check_allow_r18', AsyncMock(return_value=False))
        calls = self._patch_execute(monkeypatch, factory)

        await factory._generate_search_artworks_handler()(
            TestSubscriptionHandlerFactory._make_prompt_matcher(None),
            _RecordingArtworkInterface(),
            self._match(['foo', 'bar'], True),
            self._match(2, True),
        )

        assert artwork_stub_cls.search_received == [('foo bar', 2)]
        assert [artwork.s_aid for artwork in calls[0]['artworks']] == ['1', '2']
        assert calls[0]['title'] == 'Test_Gallery Search: foo bar'

    async def test_ranking_invalid_mode_rejected(self, factory) -> None:
        from nonebot.exception import FinishedException

        interface = _RecordingArtworkInterface()

        with pytest.raises(FinishedException):
            await factory._generate_ranking_artworks_handler()(
                interface,
                self._match('年榜', True),
                self._match(1, True),
            )

        assert interface.finished == ['榜单类型应当为【日榜/周榜/月榜】, 请确认后重试']

    async def test_ranking_invalid_page_rejected(self, factory, artwork_stub_cls) -> None:
        from nonebot.exception import FinishedException

        interface = _RecordingArtworkInterface()

        with pytest.raises(FinishedException):
            await factory._generate_ranking_artworks_handler()(
                interface,
                self._match('日榜', True),
                self._match(0, True),
            )

        assert interface.finished == ['查询页码应当为正整数, 请确认后重试']
        assert artwork_stub_cls.ranking_received == []

    @pytest.mark.parametrize(('mode', 'expected_ranking'), [
        ('', 'monthly'),
        ('日榜', 'daily'),
        ('weekly', 'weekly'),
    ])
    async def test_ranking_dispatches_query(
            self, factory, artwork_stub_cls, monkeypatch: pytest.MonkeyPatch, mode: str, expected_ranking: str,
    ) -> None:
        artwork_stub_cls.ranking_ids = ['1']
        monkeypatch.setattr(factory, 'check_allow_r18', AsyncMock(return_value=False))
        calls = self._patch_execute(monkeypatch, factory)

        await factory._generate_ranking_artworks_handler()(
            _RecordingArtworkInterface(),
            self._match(mode, bool(mode)),
            self._match(1, False),
        )

        assert artwork_stub_cls.ranking_received == [(expected_ranking, 1)]
        assert [artwork.s_aid for artwork in calls[0]['artworks']] == ['1']
        assert expected_ranking.title() in calls[0]['title']

    async def test_bookmark_rejects_non_decimal_uid(self, artwork_stub_cls) -> None:
        from nonebot.exception import FinishedException

        from src.params.template.artwork_viewer import ArtworkViewerHandlerFactory

        factory = ArtworkViewerHandlerFactory(artwork_stub_cls, 'test_gallery', need_decimal_user_id=True)
        interface = _RecordingArtworkInterface()

        with pytest.raises(FinishedException):
            await factory._generate_bookmark_artworks_handler()(
                TestSubscriptionHandlerFactory._make_prompt_matcher(None),
                interface,
                self._match('abc', True),
                self._match(1, True),
            )

        assert interface.finished == ['用户ID应当为纯数字, 请确认后重试']

    async def test_bookmark_invalid_page_rejected(self, factory, artwork_stub_cls) -> None:
        from nonebot.exception import FinishedException

        interface = _RecordingArtworkInterface()

        with pytest.raises(FinishedException):
            await factory._generate_bookmark_artworks_handler()(
                TestSubscriptionHandlerFactory._make_prompt_matcher(None),
                interface,
                self._match('12345', True),
                self._match(-1, True),
            )

        assert interface.finished == ['查询页码应当为正整数, 请确认后重试']
        assert artwork_stub_cls.bookmark_received == []

    async def test_bookmark_dispatches_query(self, factory, artwork_stub_cls, monkeypatch: pytest.MonkeyPatch) -> None:
        artwork_stub_cls.bookmark_ids = ['1', '2']
        monkeypatch.setattr(factory, 'check_allow_r18', AsyncMock(return_value=False))
        calls = self._patch_execute(monkeypatch, factory)

        await factory._generate_bookmark_artworks_handler()(
            TestSubscriptionHandlerFactory._make_prompt_matcher(None),
            _RecordingArtworkInterface(),
            self._match('12345', True),
            self._match(2, True),
        )

        assert artwork_stub_cls.bookmark_received == [('12345', 2)]
        assert calls[0]['title'] == 'Test_Gallery User Bookmark - UID: 12345'

    async def test_user_dispatches_query(
            self, factory, artwork_stub_cls, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from src.service.artwork_proxy.models import ArtistUserData

        artwork_stub_cls.user_data = ArtistUserData(
            origin='test_gallery',
            uid='2000',
            name='test artist',
            artwork_ids=['a1', 'a2', 'a3'],
        )
        monkeypatch.setattr(factory, 'check_allow_r18', AsyncMock(return_value=False))
        calls = self._patch_execute(monkeypatch, factory)

        await factory._generate_user_artworks_handler()(
            TestSubscriptionHandlerFactory._make_prompt_matcher(None),
            _RecordingArtworkInterface(),
            self._match('2000', True),
            self._match(1, False),
        )

        assert artwork_stub_cls.user_received == ['2000']
        assert [artwork.s_aid for artwork in calls[0]['artworks']] == ['a1', 'a2', 'a3']
        assert calls[0]['title'] == 'Test_Gallery User Artwork - test artist/UID: 2000'

    @pytest.mark.parametrize(
        ('page', 'expected_count', 'expected_first', 'expected_last'),
        [(1, 60, 'a0', 'a59'), (2, 1, 'a60', 'a60'), (3, 0, None, None)],
    )
    async def test_query_user_pagination(
            self,
            factory,
            artwork_stub_cls,
            page: int,
            expected_count: int,
            expected_first: str | None,
            expected_last: str | None,
    ) -> None:
        from src.service.artwork_proxy.models import ArtistUserData

        artwork_stub_cls.user_data = ArtistUserData(
            origin='test_gallery',
            uid='2000',
            name='test artist',
            artwork_ids=[f'a{i}' for i in range(61)],
        )

        artworks, _ = await factory.query_user('2000', page)
        artwork_ids = [artwork.s_aid for artwork in artworks]

        assert len(artwork_ids) == expected_count
        if expected_count == 0:
            assert artwork_ids == []
        else:
            assert artwork_ids[0] == expected_first
            assert artwork_ids[-1] == expected_last
        assert artwork_stub_cls.user_received == ['2000']

    async def test_user_rejects_non_decimal_uid(self, artwork_stub_cls) -> None:
        from nonebot.exception import FinishedException

        from src.params.template.artwork_viewer import ArtworkViewerHandlerFactory

        factory = ArtworkViewerHandlerFactory(artwork_stub_cls, 'test_gallery', need_decimal_user_id=True)
        interface = _RecordingArtworkInterface()

        with pytest.raises(FinishedException):
            await factory._generate_user_artworks_handler()(
                TestSubscriptionHandlerFactory._make_prompt_matcher(None),
                interface,
                self._match('abc', True),
                self._match(1, True),
            )

        assert interface.finished == ['用户ID应当为纯数字, 请确认后重试']
        assert artwork_stub_cls.user_received == []

    async def test_user_invalid_page_rejected(self, factory, artwork_stub_cls) -> None:
        from nonebot.exception import FinishedException

        interface = _RecordingArtworkInterface()

        with pytest.raises(FinishedException):
            await factory._generate_user_artworks_handler()(
                TestSubscriptionHandlerFactory._make_prompt_matcher(None),
                interface,
                self._match('2000', True),
                self._match(-1, True),
            )

        assert interface.finished == ['查询页码应当为正整数, 请确认后重试']
        assert artwork_stub_cls.user_received == []


class TestRegisterArtworkHandlers:
    """register_handlers 注册与命令路由行为测试"""

    @pytest.fixture
    def registered_factory(self, artwork_stub_cls) -> tuple[Any, Any]:
        from src.params.template.artwork_viewer import ArtworkViewerHandlerFactory

        command_prefix = unique_test_id('testacv').lower()
        factory = ArtworkViewerHandlerFactory(artwork_stub_cls, command_prefix)
        return factory, factory.register_handlers(permission_level=30)

    def test_register_handlers(self, registered_factory) -> None:
        """注册应创建 AlconnaMatcher 并携带 processor state 与 allow_r18 额外权限节点"""
        from nonebot_plugin_alconna import AlconnaMatcher

        from src.service.omega_processor.universal.processor_utils import parse_processor_state

        factory, matcher = registered_factory
        try:
            assert issubclass(matcher, AlconnaMatcher)

            processor_state = parse_processor_state(matcher._default_state)
            assert processor_state.name == factory._command_prefix.title()
            assert processor_state.level == 30
            assert 'allow_r18' in processor_state.extra_auth_node
        finally:
            matcher._tests.clear()
            matcher.destroy()

    async def test_full_flow_main_args_routes_to_view_handler(
            self,
            app: App,
            artwork_stub_cls,
            recording_artwork_context,
            recording_uni_message,
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """主参数命令路由到详情查看流程 (非插件 matcher 跳过全部预处理器)"""
        from src.params.template.artwork_viewer import ArtworkViewerHandlerFactory

        command_prefix = unique_test_id('testacvmain').lower()
        factory = ArtworkViewerHandlerFactory(artwork_stub_cls, command_prefix)
        artwork_stub_cls.query_results = {'123456': _make_artwork_query_data('123456', page_indexes=(0,))}
        matcher = factory.register_handlers()

        prompt_messages: list = []

        async def _prompt(cls, message: Any, timeout: float = 120, block: bool = True) -> None:
            prompt_messages.append(message)
            return None

        monkeypatch.setattr(matcher, 'prompt', classmethod(_prompt))

        try:
            async with app.test_matcher(matcher) as ctx:
                bot = create_real_obv11_bot(ctx, '10086')
                event = make_obv11_private_message_event(
                    user_id=random.randint(10_000_000, 99_999_999),
                    message_id=random.randint(1_000_000, 2_000_000_000),
                    text=f'/{command_prefix} 123456',
                )

                ctx.receive_event(bot, event)
                ctx.should_pass_rule(matcher=matcher)
                ctx.should_pass_permission(matcher=matcher)

            # 详情流程已执行: 页面按真实索引处理, 未追问作品 ID, 消息上下文已写入
            assert artwork_stub_cls.proceed_calls == [(0, 'mark')]
            assert prompt_messages == []
            assert len(recording_uni_message) == 2
            assert recording_uni_message[0].extract_plain_text() == '稍等, 正在获取作品信息~'
            assert recording_artwork_context[0]['aid'] == '123456'
            assert recording_artwork_context[0]['origin'] == 'test_gallery'
        finally:
            matcher._tests.clear()
            matcher.destroy()

    @pytest.mark.parametrize('subcommand_args', ['随机 --num 3', 'random -n 3'])
    async def test_full_flow_subcommand_does_not_trigger_view_prompt(
            self,
            app: App,
            artwork_stub_cls,
            recording_artwork_context,
            recording_uni_message,
            monkeypatch: pytest.MonkeyPatch,
            subcommand_args: str,
    ) -> None:
        """中文与英文随机子命令均路由到随机流程, 不触发详情查看追问"""
        from src.params.template.artwork_viewer import ArtworkViewerHandlerFactory

        command_prefix = unique_test_id('testacvsub').lower()
        factory = ArtworkViewerHandlerFactory(artwork_stub_cls, command_prefix)
        artwork_stub_cls.random_ids = ['1', '2']
        matcher = factory.register_handlers()

        prompt_messages: list = []

        async def _prompt(cls, message: Any, timeout: float = 120, block: bool = True) -> None:
            prompt_messages.append(message)
            return None

        monkeypatch.setattr(matcher, 'prompt', classmethod(_prompt))

        try:
            async with app.test_matcher(matcher) as ctx:
                bot = create_real_obv11_bot(ctx, '10086')
                event = make_obv11_private_message_event(
                    user_id=random.randint(10_000_000, 99_999_999),
                    message_id=random.randint(1_000_000, 2_000_000_000),
                    text=f'/{command_prefix} {subcommand_args}',
                )

                ctx.receive_event(bot, event)
                ctx.should_pass_rule(matcher=matcher)
                ctx.should_pass_permission(matcher=matcher)

            # 随机流程已执行且仅执行随机流程: 无页面处理, 无追问, 预览图生成收到限定量
            assert artwork_stub_cls.random_limits == [3]
            assert artwork_stub_cls.proceed_calls == []
            assert prompt_messages == []
            assert len(artwork_stub_cls.preview_calls) == 1
            assert artwork_stub_cls.preview_calls[0]['limit'] == 3
            assert len(recording_uni_message) == 2
        finally:
            matcher._tests.clear()
            matcher.destroy()
