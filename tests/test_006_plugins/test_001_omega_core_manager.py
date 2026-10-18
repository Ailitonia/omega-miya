"""
@Author         : Ailitonia
@Date           : 2026/10/11 21:10
@FileName       : test_001_omega_core_manager
@Project        : omega-miya
@Description    : omega_core_manager 插件单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import random
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import nonebot
import pytest
from nonebug import App

from tests.test_006_plugins.helpers import expected_reply, obv11_user_entity
from tests.utils import (
    create_real_obv11_bot,
    make_obv11_group_message_event,
    make_obv11_private_message_event,
    preserve_plugin_row,
    seed_entity_permissions,
)

if TYPE_CHECKING:
    from src.database.internal.bot import BotSelf


def _random_user_id(bot_self_id: str) -> int:
    """随机非超管用户 ID (8 位段, 避开注入超管的 9 位段及 bot self_id)"""
    user_id = random.randint(10_000_000, 99_999_999)
    while str(user_id) == bot_self_id:
        user_id = random.randint(10_000_000, 99_999_999)
    return user_id


def _random_message_id() -> int:
    """随机消息 ID (history 表对 (bot, message_id) 有唯一约束, 随机化避免跨用例冲突)"""
    return random.randint(1, 2_147_483_647)


class TestSuperuserInjection:
    """超管注入哨兵测试: 若注入失效, 全部超管用例随之失败并由此定位"""

    async def test_injected_superuser_active(self, app: App, test_superuser_id: int) -> None:
        config = nonebot.get_driver().config
        assert str(test_superuser_id) in config.superusers

    async def test_existing_superusers_preserved(self, app: App) -> None:
        """注入应为合并而非覆盖: .env.test 既有超管 'User' 仍生效 (test_013 依赖)"""
        config = nonebot.get_driver().config
        assert 'User' in config.superusers


class TestPluginMetadata:
    """插件元信息契约测试"""

    def test_plugin_metadata_loaded(self) -> None:
        from nonebot.plugin import get_plugin

        plugin = get_plugin('omega_core_manager')
        assert plugin is not None
        assert plugin.metadata is not None
        assert plugin.metadata.name == 'OmegaCoreManager'
        assert plugin.metadata.description is not None
        assert plugin.metadata.usage is not None


class TestHelpers:
    """helpers.py 纯函数测试"""

    def test_get_all_plugins_desc(self) -> None:
        from src.plugins.omega_core_manager.helpers import get_all_plugins_desc

        desc = get_all_plugins_desc()
        assert '现在已安装的插件有:' in desc
        assert 'OmegaCoreManager' in desc
        assert '/omega help [插件名]' in desc

    def test_get_plugin_desc_found(self) -> None:
        from src.plugins.omega_core_manager.helpers import get_plugin_desc

        desc = get_plugin_desc(plugin_name='OmegaCoreManager')
        assert desc.startswith('OmegaCoreManager\n')
        assert '用法:' in desc
        assert '可配置权限及冷却信息' not in desc

    def test_get_plugin_desc_for_superuser(self) -> None:
        from src.plugins.omega_core_manager.helpers import get_plugin_desc

        desc = get_plugin_desc(plugin_name='OmegaCoreManager', for_superuser=True)
        assert '可配置权限及冷却信息' in desc

    def test_get_plugin_desc_not_found(self) -> None:
        from src.plugins.omega_core_manager.helpers import get_plugin_desc

        desc = get_plugin_desc(plugin_name='DefinitelyNotAPlugin')
        assert desc == "未找到插件'DefinitelyNotAPlugin', 请检查输入插件名是否正确"

    def test_get_plugin_auth_node_self(self) -> None:
        """本插件声明了 processor state (enable_processor=False), 节点为 matcher 自定义名称"""
        from src.plugins.omega_core_manager.helpers import get_plugin_auth_node

        assert get_plugin_auth_node('omega_core_manager') == ['OmegaCoreManager']

    def test_get_plugin_auth_node_not_found(self) -> None:
        from src.plugins.omega_core_manager.helpers import get_plugin_auth_node

        assert get_plugin_auth_node('definitely_not_a_plugin') == []

    def test_get_plugin_auth_node_no_undefined_fallback(self) -> None:
        """任何已加载插件的节点清单都不应包含 parse fallback 产生的伪节点 'undefined'"""
        from nonebot.plugin import get_loaded_plugins

        from src.plugins.omega_core_manager.helpers import get_plugin_auth_node

        for plugin in get_loaded_plugins():
            nodes = get_plugin_auth_node(plugin.name)
            assert 'undefined' not in nodes, f'插件 {plugin.name} 的节点清单包含伪节点'

    def test_list_command_by_priority_structure(self) -> None:
        from src.plugins.omega_core_manager.helpers import list_command_by_priority

        result = list_command_by_priority()
        assert '[Priority - 20]' in result
        assert 'OmegaCoreManager: omega <' in result

        priorities = [
            int(line.removeprefix('[Priority - ').removesuffix(']'))
            for line in result.splitlines()
            if line.startswith('[Priority - ')
        ]
        assert priorities == sorted(priorities)


class TestStatusFunctions:
    """status.py 运行状态函数测试"""

    async def test_get_nonebot_run_time(self, app: App) -> None:
        from datetime import datetime

        from src.plugins.omega_core_manager import status as status_module

        run_time = status_module.get_nonebot_run_time()
        assert isinstance(run_time, datetime)
        assert run_time.tzinfo is not None
        assert run_time <= datetime.now().astimezone()

    async def test_get_nonebot_run_time_not_started(self, app: App, monkeypatch: pytest.MonkeyPatch) -> None:
        """删除模块全局运行时间模拟未启动状态, 应抛出 RuntimeError"""
        from src.plugins.omega_core_manager import status as status_module

        monkeypatch.delattr(status_module, '_NONEBOT_RUN_TIME')
        with pytest.raises(RuntimeError, match='NoneBot not running!'):
            status_module.get_nonebot_run_time()

    async def test_get_cpu_status(self, app: App, monkeypatch: pytest.MonkeyPatch) -> None:
        """重绑定模块内 asyncio 跳过真实 sleep, 采样返回 [0, 100] 浮点"""
        from src.plugins.omega_core_manager import status as status_module
        from tests.utils import rebind_module_namespace

        sleep_mock = AsyncMock()
        rebind_module_namespace(monkeypatch, status_module, 'asyncio', sleep=sleep_mock)

        result = await status_module.get_cpu_status()
        assert isinstance(result, float)
        assert 0 <= result <= 100
        sleep_mock.assert_awaited_once()

    def test_get_memory_and_swap_status(self) -> None:
        from src.plugins.omega_core_manager import status as status_module

        assert 0 <= status_module.get_memory_status().percent <= 100
        assert 0 <= status_module.get_swap_status().percent <= 100

    def test_get_disk_usage_invalid_path_returns_none(self) -> None:
        from src.plugins.omega_core_manager import status as status_module

        assert status_module._get_disk_usage('/definitely/not/exist/path') is None

    def test_get_disk_usage(self) -> None:
        from src.plugins.omega_core_manager import status as status_module

        usage = status_module.get_disk_usage()
        assert isinstance(usage, dict)
        assert len(usage) > 0
        for mount_point, disk_usage in usage.items():
            assert isinstance(mount_point, str)
            assert 0 <= disk_usage.percent <= 100

    def test_get_uptime(self) -> None:
        from datetime import datetime

        from src.plugins.omega_core_manager import status as status_module

        uptime = status_module.get_uptime()
        assert uptime.tzinfo is not None
        assert uptime <= datetime.now().astimezone()

    async def test_get_status(self, app: App) -> None:
        from src.plugins.omega_core_manager import status as status_module

        status = await status_module.get_status()
        for label in ('CPU Usage:', 'Memory Usage:', 'Swap Usage:', 'Disk Usage:', 'Uptime:', 'Runtime:'):
            assert label in status


class TestMatcherGreeting:
    """$main 问候测试"""

    async def test_main_greeting(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            core_manager_enabled_guard: None,
    ) -> None:
        from src.plugins.omega_core_manager.command import omega_cmd

        user_id = _random_user_id(numeric_bot.self_id)
        event = make_obv11_private_message_event(
            user_id=user_id, text='/omega', self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, '你好呀~\n我是Omega Miya~\n请问您今天要来点喵娘吗?'))
            ctx.should_finished(omega_cmd)


class TestMatcherStartDisable:
    """start/disable 子命令测试 (管理员私聊事件)"""

    async def test_start_success(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            core_manager_enabled_guard: None,
    ) -> None:
        from src.plugins.omega_core_manager.command import _DEFAULT_PERMISSION_LEVEL, omega_cmd

        user_id = _random_user_id(numeric_bot.self_id)
        event = make_obv11_private_message_event(
            user_id=user_id, text='/omega start', self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, 'Omega 启用/初始化成功'))
            ctx.should_finished(omega_cmd)

        # 验证数据库状态: 全局开关启用且权限等级重置为默认值
        async with obv11_user_entity(numeric_bot, str(user_id)) as entity:
            assert await entity.check_global_permission() is True
            level_setting = await entity.query_permission_level()
        assert level_setting.available == _DEFAULT_PERMISSION_LEVEL

    async def test_start_failure(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            core_manager_enabled_guard: None,
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """数据库操作异常时应回复失败提示而非抛出异常"""
        from src.plugins.omega_core_manager.command import omega_cmd
        from src.service.omega_base import OmegaEntity

        monkeypatch.setattr(
            OmegaEntity, 'enable_global_permission', AsyncMock(side_effect=RuntimeError('boom')),
        )

        user_id = _random_user_id(numeric_bot.self_id)
        event = make_obv11_private_message_event(
            user_id=user_id, text='/omega start', self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, 'Omega 启用/初始化失败, 请联系管理员处理'))
            ctx.should_finished(omega_cmd)

    async def test_disable_success(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            core_manager_enabled_guard: None,
    ) -> None:
        from src.plugins.omega_core_manager.command import omega_cmd

        user_id = _random_user_id(numeric_bot.self_id)
        event = make_obv11_private_message_event(
            user_id=user_id, text='/omega disable', self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, 'Omega 禁用成功'))
            ctx.should_finished(omega_cmd)

        # 验证数据库状态: 全局开关关闭且权限等级归零
        async with obv11_user_entity(numeric_bot, str(user_id)) as entity:
            assert await entity.check_global_permission() is False
            level_setting = await entity.query_permission_level()
        assert level_setting.available == 0


class TestMatcherStatus:
    """status 子命令测试 (管理员私聊事件, get_status 打桩为固定文本)"""

    @staticmethod
    def _patch_get_status(monkeypatch: pytest.MonkeyPatch, text: str = 'TEST_STATUS_FIXED') -> None:
        import src.plugins.omega_core_manager.command as command_module

        monkeypatch.setattr(command_module, 'get_status', AsyncMock(return_value=text))

    async def test_status_initialized_entity(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            core_manager_enabled_guard: None,
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from src.plugins.omega_core_manager.command import omega_cmd

        self._patch_get_status(monkeypatch)
        user_id = _random_user_id(numeric_bot.self_id)
        await seed_entity_permissions(
            numeric_bot, 'onebot_v11_user', str(user_id), enable_global=True, permission_level=30,
        )

        event = make_obv11_private_message_event(
            user_id=user_id, text='/omega status', self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )
        expected_text = (
            f'Omega 功能开关: 已启用(Enabled)\nOmega 权限等级: Level-30'
            f'\n\nOmega 运行状态:\n{"-" * 16}\nTEST_STATUS_FIXED'
        )

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, expected_text))

    async def test_status_fresh_entity(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            core_manager_enabled_guard: None,
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """未配置过的实体: 全局开关默认禁用, 权限等级未设置"""
        from src.plugins.omega_core_manager.command import omega_cmd

        self._patch_get_status(monkeypatch)
        user_id = _random_user_id(numeric_bot.self_id)
        event = make_obv11_private_message_event(
            user_id=user_id, text='/omega status', self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )
        expected_text = (
            f'Omega 功能开关: 已禁用(Disabled)\nOmega 权限等级: 未设置'
            f'\n\nOmega 运行状态:\n{"-" * 16}\nTEST_STATUS_FIXED'
        )

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, expected_text))

    async def test_status_bot_not_initialized(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            core_manager_enabled_guard: None,
    ) -> None:
        """bot 行不存在时实体初始化抛出 NoResultFound, 应回复未初始化提示"""
        from src.plugins.omega_core_manager.command import omega_cmd

        # 使用未落库的 bot self_id (与 numeric_bot 同 8 位段但不同值)
        uninitialized_self_id = str(_random_user_id(numeric_bot.self_id))
        user_id = _random_user_id(numeric_bot.self_id)
        event = make_obv11_private_message_event(
            user_id=user_id, text='/omega status', self_id=int(uninitialized_self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, uninitialized_self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event,
                expected_reply(event, 'Omega 未初始化, 请尝试使用 "/omega start" 命令初始化, 或联系管理员处理'),
            )
            ctx.should_finished(omega_cmd)


class TestMatcherHelp:
    """help 子命令测试"""

    async def test_help_all_plugins(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            core_manager_enabled_guard: None,
    ) -> None:
        from src.plugins.omega_core_manager.command import omega_cmd
        from src.plugins.omega_core_manager.helpers import get_all_plugins_desc

        user_id = _random_user_id(numeric_bot.self_id)
        event = make_obv11_private_message_event(
            user_id=user_id, text='/omega help', self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, get_all_plugins_desc()))
            ctx.should_finished(omega_cmd)

    async def test_help_named_plugin(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            core_manager_enabled_guard: None,
    ) -> None:
        from src.plugins.omega_core_manager.command import omega_cmd
        from src.plugins.omega_core_manager.helpers import get_plugin_desc

        user_id = _random_user_id(numeric_bot.self_id)
        event = make_obv11_private_message_event(
            user_id=user_id, text='/omega help OmegaCoreManager',
            self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event, expected_reply(event, get_plugin_desc(plugin_name='OmegaCoreManager', for_superuser=False)),
            )
            ctx.should_finished(omega_cmd)

    async def test_help_named_plugin_for_superuser(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            test_superuser_id: int,
    ) -> None:
        """超级用户查询插件帮助应附加处理器配置信息"""
        from src.plugins.omega_core_manager.command import omega_cmd
        from src.plugins.omega_core_manager.helpers import get_plugin_desc

        event = make_obv11_private_message_event(
            user_id=test_superuser_id, text='/omega help OmegaCoreManager',
            self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event, expected_reply(event, get_plugin_desc(plugin_name='OmegaCoreManager', for_superuser=True)),
            )
            ctx.should_finished(omega_cmd)

    async def test_help_unknown_plugin(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            core_manager_enabled_guard: None,
    ) -> None:
        from src.plugins.omega_core_manager.command import omega_cmd

        user_id = _random_user_id(numeric_bot.self_id)
        event = make_obv11_private_message_event(
            user_id=user_id, text='/omega help DefinitelyNotAPlugin',
            self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event,
                expected_reply(event, "未找到插件'DefinitelyNotAPlugin', 请检查输入插件名是否正确"),
            )
            ctx.should_finished(omega_cmd)


class TestMatcherSetLevel:
    """set-level 子命令测试 (管理员私聊事件)"""

    @pytest.mark.parametrize('level', ['0', '50', '100'], ids=['min_boundary', 'normal', 'max_boundary'])
    async def test_set_level_success(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            core_manager_enabled_guard: None,
            level: str,
    ) -> None:
        from src.plugins.omega_core_manager.command import omega_cmd

        user_id = _random_user_id(numeric_bot.self_id)
        event = make_obv11_private_message_event(
            user_id=user_id, text=f'/omega set-level {level}',
            self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, f'Omega 已将当前会话权限等级设置为: Level-{level}'))
            ctx.should_finished(omega_cmd)

        async with obv11_user_entity(numeric_bot, str(user_id)) as entity:
            level_setting = await entity.query_permission_level()
        assert level_setting.available == int(level)

    async def test_set_level_not_a_number(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            core_manager_enabled_guard: None,
    ) -> None:
        from src.plugins.omega_core_manager.command import omega_cmd

        user_id = _random_user_id(numeric_bot.self_id)
        event = make_obv11_private_message_event(
            user_id=user_id, text='/omega set-level abc',
            self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, '异常参数, 权限等级应当为整数, 操作已取消'))
            ctx.should_finished(omega_cmd)

    async def test_set_level_out_of_range(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            core_manager_enabled_guard: None,
    ) -> None:
        from src.plugins.omega_core_manager.command import _MAX_PERMISSION_LEVEL, omega_cmd

        user_id = _random_user_id(numeric_bot.self_id)
        event = make_obv11_private_message_event(
            user_id=user_id, text='/omega set-level 101',
            self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event,
                expected_reply(event, f'异常参数, 可设定的权限等级范围为 0~{_MAX_PERMISSION_LEVEL}, 操作已取消'),
            )
            ctx.should_finished(omega_cmd)

    async def test_set_level_huge_digit_string(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            core_manager_enabled_guard: None,
    ) -> None:
        """超长数字串可通过 isdecimal 检查, 但 int() 转换有 4300 位上限, 应友好取消而非抛出异常"""
        from src.plugins.omega_core_manager.command import omega_cmd

        user_id = _random_user_id(numeric_bot.self_id)
        event = make_obv11_private_message_event(
            user_id=user_id, text=f'/omega set-level {"9" * 5000}',
            self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, '异常参数, 权限等级应当为整数, 操作已取消'))
            ctx.should_finished(omega_cmd)

    async def test_set_level_db_failure(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            core_manager_enabled_guard: None,
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from src.plugins.omega_core_manager.command import omega_cmd
        from src.service.omega_base import OmegaEntity

        monkeypatch.setattr(
            OmegaEntity, 'set_permission_level', AsyncMock(side_effect=RuntimeError('boom')),
        )

        user_id = _random_user_id(numeric_bot.self_id)
        event = make_obv11_private_message_event(
            user_id=user_id, text='/omega set-level 50',
            self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, 'Omega 设置权限等级失败, 请联系管理员处理'))
            ctx.should_finished(omega_cmd)

    async def test_set_level_missing_arg_prompt_timeout(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            core_manager_enabled_guard: None,
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """缺少参数时进入 prompt 追问, 缩短超时时间验证超时取消分支"""
        import src.plugins.omega_core_manager.command as command_module
        from src.plugins.omega_core_manager.command import omega_cmd

        monkeypatch.setattr(command_module, '_HANDLER_PROMPT_TIMEOUT', 0.05)

        user_id = _random_user_id(numeric_bot.self_id)
        event = make_obv11_private_message_event(
            user_id=user_id, text='/omega set-level',
            self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            # prompt 消息经 matcher.send 发送, 无 reply 段
            ctx.should_call_send(event, '请输入需要设定的权限等级:')
            ctx.should_call_send(event, expected_reply(event, '等待输入超时, 已取消操作'))
            ctx.should_finished(omega_cmd)


class TestMatcherListCommands:
    """list-commands 子命令测试 (超级用户)"""

    async def test_list_commands(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            test_superuser_id: int,
    ) -> None:
        from src.plugins.omega_core_manager.command import omega_cmd
        from src.plugins.omega_core_manager.helpers import list_command_by_priority

        event = make_obv11_private_message_event(
            user_id=test_superuser_id, text='/omega list-commands',
            self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )
        expected_text = f'当前可用的命令列表:\n{"-" * 16}\n{list_command_by_priority()}'

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, expected_text))
            ctx.should_finished(omega_cmd)


class TestMatcherListPlugins:
    """list-plugins 子命令测试 (超级用户)"""

    async def test_list_plugins(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            test_superuser_id: int,
            core_manager_enabled_guard: None,
    ) -> None:
        from nonebot.plugin import get_loaded_plugins, get_plugin

        from src.database import PluginDAL
        from src.plugins.omega_core_manager.command import omega_cmd

        # 与被测处理器相同的口径动态计算期望: 仅显示有 matcher 且有 metadata 的已加载插件
        plugin_list = [
            plugin.name
            for plugin in get_loaded_plugins()
            if (len(plugin.matcher) > 0) and (plugin.metadata is not None)
        ]

        async with PluginDAL.create() as dal:
            enabled_result = await dal.query_by_enable_status(enabled=1)
            disabled_result = await dal.query_by_enable_status(enabled=0)

        def _desc(plugin_name: str) -> str:
            plugin = get_plugin(plugin_id=plugin_name)
            if (plugin is None) or (plugin.metadata is None):
                return plugin_name
            return f'{plugin_name}({plugin.metadata.name})'

        enabled_text = '\n'.join(_desc(x.plugin_name) for x in enabled_result if x.plugin_name in plugin_list) or '无'
        disabled_text = '\n'.join(_desc(x.plugin_name) for x in disabled_result if x.plugin_name in plugin_list) or '无'

        # guard 已确保本插件启用, 应出现在已启用列表
        assert 'omega_core_manager(OmegaCoreManager)' in enabled_text

        event = make_obv11_private_message_event(
            user_id=test_superuser_id, text='/omega list-plugins',
            self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )
        expected_text = f'已启用的插件:\n{"-" * 16}\n{enabled_text}\n\n\n已禁用的插件:\n{"-" * 16}\n{disabled_text}'

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, expected_text))
            ctx.should_finished(omega_cmd)


class TestMatcherSwitchPlugin:
    """enable-plugin/disable-plugin 子命令测试 (超级用户)"""

    @staticmethod
    def _pick_target_plugin() -> tuple[str, str]:
        """选取任一非本插件的已加载插件作为启停目标, 返回 (plugin_name, module_name)"""
        from nonebot.plugin import get_loaded_plugins

        candidates = sorted(
            (plugin for plugin in get_loaded_plugins() if plugin.name != 'omega_core_manager'),
            key=lambda plugin: plugin.name,
        )
        if not candidates:
            pytest.fail('无可用于启停测试的目标插件')
        return candidates[0].name, candidates[0].module_name

    @pytest.mark.parametrize(
        ('subcommand', 'verb', 'enabled', 'info'),
        [
            pytest.param('disable-plugin', '禁用', 0, 'Disabled by OPM', id='disable_plugin'),
            pytest.param('enable-plugin', '启用', 1, 'Enabled by OPM', id='enable_plugin'),
        ],
    )
    async def test_switch_plugin_success(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            test_superuser_id: int,
            subcommand: str,
            verb: str,
            enabled: int,
            info: str,
    ) -> None:
        from src.database import PluginDAL
        from src.plugins.omega_core_manager.command import omega_cmd

        target_name, target_module = self._pick_target_plugin()

        async with preserve_plugin_row(target_name, target_module):
            event = make_obv11_private_message_event(
                user_id=test_superuser_id, text=f'/omega {subcommand} {target_name}',
                self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
            )

            async with app.test_matcher(omega_cmd) as ctx:
                bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
                ctx.receive_event(bot, event)
                ctx.should_call_send(event, expected_reply(event, f'Omega {verb}插件{target_name!r}成功'))
                ctx.should_finished(omega_cmd)

            async with PluginDAL.create() as dal:
                row = await dal.query_unique(plugin_name=target_name, module_name=target_module)
            assert int(row.enabled) == enabled
            assert row.info == info

    async def test_plugin_not_found(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            test_superuser_id: int,
    ) -> None:
        from src.plugins.omega_core_manager.command import omega_cmd

        event = make_obv11_private_message_event(
            user_id=test_superuser_id, text='/omega disable-plugin not_exist_plugin_aaa',
            self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, "未找到插件'not_exist_plugin_aaa', 操作已取消"))
            ctx.should_finished(omega_cmd)


class TestMatcherPluginNodes:
    """show-plugin-nodes/allow-plugin-node/deny-plugin-node 子命令测试 (超级用户)"""

    async def test_show_plugin_nodes(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            test_superuser_id: int,
    ) -> None:
        from src.plugins.omega_core_manager.command import omega_cmd

        event = make_obv11_private_message_event(
            user_id=test_superuser_id, text='/omega show-plugin-nodes omega_core_manager',
            self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event, expected_reply(event, "插件'omega_core_manager'可配置权限节点有:\n\nOmegaCoreManager"),
            )
            ctx.should_finished(omega_cmd)

    async def test_show_plugin_nodes_unknown_plugin(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            test_superuser_id: int,
    ) -> None:
        from src.plugins.omega_core_manager.command import omega_cmd

        event = make_obv11_private_message_event(
            user_id=test_superuser_id, text='/omega show-plugin-nodes not_exist_plugin_aaa',
            self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event, expected_reply(event, "插件'not_exist_plugin_aaa'不存在, 或该插件无可配置权限节点"),
            )
            ctx.should_finished(omega_cmd)

    @pytest.mark.parametrize(
        ('subcommand', 'available'),
        [
            pytest.param('allow-plugin-node', 1, id='allow_node'),
            pytest.param('deny-plugin-node', 0, id='deny_node'),
        ],
    )
    async def test_config_plugin_node_success(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            test_superuser_id: int,
            subcommand: str,
            available: int,
    ) -> None:
        from src.plugins.omega_core_manager.command import omega_cmd

        event = make_obv11_private_message_event(
            user_id=test_superuser_id, text=f'/omega {subcommand} omega_core_manager OmegaCoreManager',
            self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        expected_text = f"Omega 配置插件'omega_core_manager'权限节点'OmegaCoreManager' -> {available}成功"

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, expected_text))
            ctx.should_finished(omega_cmd)

        async with obv11_user_entity(numeric_bot, str(test_superuser_id)) as entity:
            setting = await entity.query_auth_setting(
                module='src.plugins.omega_core_manager', plugin='omega_core_manager', node='OmegaCoreManager',
            )
        assert setting.available == available

    async def test_config_invalid_node(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            test_superuser_id: int,
    ) -> None:
        from src.plugins.omega_core_manager.command import omega_cmd

        event = make_obv11_private_message_event(
            user_id=test_superuser_id, text='/omega allow-plugin-node omega_core_manager NotANode',
            self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event,
                expected_reply(event, "权限节点'NotANode'不是插件'omega_core_manager'的可配置权限节点, 操作已取消"),
            )
            ctx.should_finished(omega_cmd)

    async def test_config_node_missing_plugin(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            test_superuser_id: int,
    ) -> None:
        from src.plugins.omega_core_manager.command import omega_cmd

        event = make_obv11_private_message_event(
            user_id=test_superuser_id, text='/omega allow-plugin-node not_exist_plugin_aaa node_x',
            self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event, expected_reply(event, "插件'not_exist_plugin_aaa'不存在, 或该插件无可配置权限节点"),
            )
            ctx.should_finished(omega_cmd)


class TestMatcherListConfiguredAuth:
    """list-configured-auth 子命令测试 (超级用户)"""

    async def test_list_configured_auth_empty(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            test_superuser_id: int,
    ) -> None:
        """未配置任何权限节点的实体应回复 '无'"""
        from src.plugins.omega_core_manager.command import omega_cmd

        event = make_obv11_private_message_event(
            user_id=test_superuser_id, text='/omega list-configured-auth',
            self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, 'Omega 已配置的权限节点有:\n\n无'))
            ctx.should_finished(omega_cmd)

    async def test_list_configured_auth_after_config(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            test_superuser_id: int,
    ) -> None:
        from src.plugins.omega_core_manager.command import omega_cmd

        # 预先为超管用户实体配置一个权限节点
        await seed_entity_permissions(
            numeric_bot, 'onebot_v11_user', str(test_superuser_id),
            auth_nodes=[('test_module', 'test_plugin', 'test_node', 1)],
        )

        event = make_obv11_private_message_event(
            user_id=test_superuser_id, text='/omega list-configured-auth',
            self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, 'Omega 已配置的权限节点有:\n\n1 | test_plugin:test_node'))
            ctx.should_finished(omega_cmd)


class TestPermissionGate:
    """权限门控测试: 不满足 assign additional 检查时应静默 (无回复)"""

    async def test_start_by_non_admin_silenced(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            core_manager_enabled_guard: None,
    ) -> None:
        from src.plugins.omega_core_manager.command import omega_cmd

        event = make_obv11_group_message_event(
            group_id=random.randint(10_000_000, 99_999_999),
            user_id=_random_user_id(numeric_bot.self_id),
            text='/omega start',
            self_id=int(numeric_bot.self_id),
            message_id=_random_message_id(),
            role='member',
        )

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            # 群成员非管理员, 不应有任何回复

    async def test_status_by_non_admin_silenced(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            core_manager_enabled_guard: None,
    ) -> None:
        """status 含主机状态信息, 非管理员不应可查询"""
        from src.plugins.omega_core_manager.command import omega_cmd

        event = make_obv11_group_message_event(
            group_id=random.randint(10_000_000, 99_999_999),
            user_id=_random_user_id(numeric_bot.self_id),
            text='/omega status',
            self_id=int(numeric_bot.self_id),
            message_id=_random_message_id(),
            role='member',
        )

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            # 群成员非管理员, 不应有任何回复

    async def test_superuser_command_by_non_superuser_silenced(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            core_manager_enabled_guard: None,
    ) -> None:
        """管理员但非超级用户触发超管专属命令时应静默"""
        from src.plugins.omega_core_manager.command import omega_cmd

        event = make_obv11_private_message_event(
            user_id=_random_user_id(numeric_bot.self_id), text='/omega list-plugins',
            self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(omega_cmd) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            # 私聊事件属于管理员但非超级用户, 不应有任何回复
