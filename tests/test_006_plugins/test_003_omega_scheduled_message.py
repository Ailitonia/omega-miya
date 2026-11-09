"""
@Author         : Ailitonia
@Date           : 2026/11/2 10:01
@FileName       : test_003_omega_scheduled_message
@Project        : omega-miya
@Description    : omega_scheduled_message 插件单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import random
import shutil
from collections.abc import AsyncGenerator, Generator
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock

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
    from nonebot.adapters import Event as BaseEvent

    from src.database.internal.bot import BotSelf
    from src.service.omega_base import OmegaMatcherInterface


@pytest.fixture(scope='class')
async def scheduled_message_enabled_guard() -> AsyncGenerator[None, None]:
    """保证 omega_scheduled_message 插件行存在且启用, 测试后恢复原状态"""
    async with preserve_plugin_row(
            'omega_scheduled_message', 'src.plugins.omega_scheduled_message', ensure_enabled=True,
    ):
        yield


@pytest.fixture(autouse=True)
def scheduled_job_sandbox() -> Generator[None, None, None]:
    """调度器任务与媒体目录沙箱: 测试后移除本测试新增的定时消息调度任务与媒体目录"""
    from src.plugins.omega_scheduled_message.helpers import _SAVE_MEDIA_FOLDER
    from src.service import scheduler

    before_jobs = {job.id for job in scheduler.get_jobs()}
    before_media = {p.name for p in _SAVE_MEDIA_FOLDER.path.iterdir()} if _SAVE_MEDIA_FOLDER.is_dir else set()
    yield
    # 调度器未启动时重复添加的同 id 任务会暂存多个 pending 项, 循环移除直至清空
    new_job_ids = {job.id for job in scheduler.get_jobs() if job.id.startswith('SchedMsgJob_')} - before_jobs
    for job_id in new_job_ids:
        while scheduler.get_job(job_id) is not None:
            scheduler.remove_job(job_id)
    if _SAVE_MEDIA_FOLDER.is_dir:
        for path in _SAVE_MEDIA_FOLDER.path.iterdir():
            if path.name not in before_media and path.is_dir():
                shutil.rmtree(path, ignore_errors=True)


def _random_user_id(bot_self_id: str) -> int:
    """随机非超管用户 ID (8 位段, 避开 bot self_id)"""
    user_id = random.randint(10_000_000, 99_999_999)
    while str(user_id) == bot_self_id:
        user_id = random.randint(10_000_000, 99_999_999)
    return user_id


def _random_message_id() -> int:
    """随机消息 ID (history 表对 (bot, message_id) 有唯一约束, 随机化避免跨用例冲突)"""
    return random.randint(1, 2 ** 31 - 1)


def _private_event(bot: 'BotSelf', user_id: int, text: str) -> 'BaseEvent':
    """构造指向测试 Bot 的私聊消息事件"""
    return make_obv11_private_message_event(
        user_id=user_id, text=text, self_id=int(bot.self_id), message_id=_random_message_id(),
    )


async def _seed_user_permissions(bot: 'BotSelf', user_id: int) -> None:
    """播种私聊用户权限: 启用全局开关并授予满足插件 level=10 要求的权限等级"""
    await seed_entity_permissions(
        bot, 'onebot_v11_user', str(user_id), enable_global=True, permission_level=30,
    )


async def _query_job_rows(bot: 'BotSelf', user_id: int) -> list:
    """查询用户实体下定时消息插件的全部配置行"""
    from src.plugins.omega_scheduled_message.helpers import (
        _SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME,
        _SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME,
    )

    async with obv11_user_entity(bot, str(user_id)) as entity:
        return await entity.query_plugin_all_auth_setting(
            module=_SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME,
            plugin=_SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME,
        )


def _make_interface(bot: 'BotSelf', obv11_bot, user_id: int) -> 'OmegaMatcherInterface':
    """以真实适配器 Bot 与构造事件直接实例化 OmegaMatcherInterface (供 helpers 单元测试)"""
    from src.plugins.omega_scheduled_message.command import schedule_message_manager
    from src.service import OmegaMatcherInterface

    return OmegaMatcherInterface(
        bot=obv11_bot,
        event=_private_event(bot, user_id, '/定时消息'),
        matcher=schedule_message_manager,
    )


class TestPluginMetadata:
    """插件元信息契约测试"""

    def test_plugin_metadata_loaded(self) -> None:
        from nonebot.plugin import get_plugin

        plugin = get_plugin('omega_scheduled_message')
        assert plugin is not None
        assert plugin.metadata is not None
        assert plugin.metadata.name == '定时消息'
        assert plugin.metadata.description is not None
        assert plugin.metadata.usage is not None


class TestHelpers:
    """helpers.py 纯函数及调度器/文件系统交互测试"""

    @staticmethod
    def _make_entity_params(**overrides):
        from src.database.internal.bot import BotType
        from src.database.internal.entity import EntityType
        from src.service.omega_base.internal import EntityInitParams

        params = {
            'bot_type': BotType.ONEBOT_V11,
            'bot_id': '10086',
            'entity_type': EntityType.ONEBOT_V11_USER,
            'entity_id': '10001',
            'entity_extra': {},
        }
        params.update(overrides)
        return EntityInitParams(**params)

    def test_generate_job_unique_id_deterministic(self) -> None:
        from src.plugins.omega_scheduled_message.helpers import _generate_job_unique_id

        params = self._make_entity_params()
        job_id = _generate_job_unique_id('任务', params)
        assert job_id == _generate_job_unique_id('任务', self._make_entity_params())
        assert job_id.startswith('SchedMsgJob_')

    @pytest.mark.parametrize(
        'field',
        ['bot_id', 'entity_type', 'entity_id'],
        ids=['bot_id', 'entity_type', 'entity_id'],
    )
    def test_generate_job_unique_id_entity_sensitive(self, field: str) -> None:
        """任务 ID 对实体参数敏感: 任一实体参数变化结果均不同"""
        from src.database.internal.entity import EntityType
        from src.plugins.omega_scheduled_message.helpers import _generate_job_unique_id

        origin = _generate_job_unique_id('任务', self._make_entity_params())
        changed_value = EntityType.ONEBOT_V11_GROUP if field == 'entity_type' else '99999'
        assert origin != _generate_job_unique_id('任务', self._make_entity_params(**{field: changed_value}))
        assert origin != _generate_job_unique_id('另一个任务', self._make_entity_params())

    def test_job_model_round_trip(self) -> None:
        """ScheduleMessageJob 序列化/反序列化往返一致, job_unique_id 稳定"""
        from nonebot_plugin_alconna.uniseg import UniMessage

        from src.plugins.omega_scheduled_message.helpers import ScheduleMessageJob

        job_data = ScheduleMessageJob.model_validate({
            'readable_job_name': '单元测试任务',
            'crontab': '0 8 * * *',
            'entity_init_params': self._make_entity_params(),
            'message': UniMessage('单元测试内容').dump(),
        })
        restored = ScheduleMessageJob.model_validate(job_data.model_dump(mode='json'))
        assert restored == job_data
        assert restored.job_unique_id == job_data.job_unique_id

    def test_add_and_remove_schedule_job(self) -> None:
        """真实调度器注册/替换/移除, 移除不存在任务不抛出异常"""
        from nonebot_plugin_alconna.uniseg import UniMessage

        from src.plugins.omega_scheduled_message.helpers import (
            ScheduleMessageJob,
            add_schedule_job,
            remove_schedule_job,
        )
        from src.service import scheduler

        job_data = ScheduleMessageJob.model_validate({
            'readable_job_name': '单元测试调度任务',
            'crontab': '0 8 * * *',
            'entity_init_params': self._make_entity_params(),
            'message': UniMessage('单元测试内容').dump(),
        })
        add_schedule_job(job_data=job_data)
        assert scheduler.get_job(job_data.job_unique_id) is not None

        # 同名任务重复添加整体替换, 不应抛出异常
        # 注意: 测试环境调度器未启动 (APSCHEDULER_AUTOSTART=false), 停止态下任务以 pending 列表暂存,
        # replace_existing 不会对 pending 项去重 (apscheduler 停止态行为), 同 id 任务存在多个暂存项, 需移除多次
        add_schedule_job(job_data=job_data)
        assert scheduler.get_job(job_data.job_unique_id) is not None

        while scheduler.get_job(job_data.job_unique_id) is not None:
            remove_schedule_job(job_unique_id=job_data.job_unique_id)

        # 调度器中不存在对应任务时仅记录日志, 不抛出异常
        remove_schedule_job(job_unique_id=job_data.job_unique_id)

    def test_remove_schedule_job_media(self) -> None:
        """媒体目录不存在时忽略; 存在时连同内容一并移除"""
        from src.plugins.omega_scheduled_message.helpers import _SAVE_MEDIA_FOLDER, remove_schedule_job_media

        media_folder = _SAVE_MEDIA_FOLDER('test_media_not_exist')
        if media_folder.is_dir:  # 脏数据兜底清理, 保证测试前置条件
            media_folder.rmtree(ignore_errors=True)
        remove_schedule_job_media(job_unique_id='test_media_not_exist')

        media_folder.path.mkdir(parents=True)
        (media_folder.path / 'test_file.txt').write_text('test', encoding='utf-8')
        remove_schedule_job_media(job_unique_id='test_media_not_exist')
        assert not media_folder.is_dir

    async def test_query_and_restore_job_value(
            self,
            app: App,
            numeric_bot: 'BotSelf',
    ) -> None:
        """query_schedule_message_job_value / restore_schedule_message_job_value 读写闭环"""
        from nonebot_plugin_alconna.uniseg import UniMessage

        from src.plugins.omega_scheduled_message.command import schedule_message_manager
        from src.plugins.omega_scheduled_message.helpers import (
            generate_schedule_job_data,
            query_schedule_message_job_value,
            restore_schedule_message_job_value,
            set_schedule_message_job,
        )

        user_id = _random_user_id(numeric_bot.self_id)
        async with app.test_matcher(schedule_message_manager) as ctx:
            interface = _make_interface(numeric_bot, create_real_obv11_bot(ctx, numeric_bot.self_id), user_id)

            job_data = await generate_schedule_job_data(
                interface=interface, readable_job_name='读写闭环任务',
                crontab='0 8 * * *', message=UniMessage('初始内容'),
            )
            assert await query_schedule_message_job_value(
                interface=interface, job_unique_id=job_data.job_unique_id,
            ) is None

            await set_schedule_message_job(interface=interface, job_data=job_data)
            assert await query_schedule_message_job_value(
                interface=interface, job_unique_id=job_data.job_unique_id,
            ) == job_data.model_dump(mode='json')

            restored_job_data = await generate_schedule_job_data(
                interface=interface, readable_job_name='读写闭环任务',
                crontab='30 9 * * *', message=UniMessage('恢复内容'),
            )
            await restore_schedule_message_job_value(
                interface=interface,
                job_unique_id=job_data.job_unique_id,
                value=restored_job_data.model_dump(mode='json'),
            )
            current_value = await query_schedule_message_job_value(
                interface=interface, job_unique_id=job_data.job_unique_id,
            )
        assert current_value is not None
        assert current_value['crontab'] == '30 9 * * *'

        # 测试数据清理: 移除播种的配置行
        async with obv11_user_entity(numeric_bot, str(user_id)) as entity:
            from src.plugins.omega_scheduled_message.helpers import (
                _SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME,
                _SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME,
            )

            await entity.delete_auth_setting(
                module=_SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME,
                plugin=_SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME,
                node=job_data.job_unique_id,
            )

    async def test_remove_schedule_message_job_idempotent_when_row_missing(
            self,
            app: App,
            numeric_bot: 'BotSelf',
    ) -> None:
        """数据库配置行不存在时移除操作幂等, 不抛出异常"""
        from src.plugins.omega_scheduled_message.command import schedule_message_manager
        from src.plugins.omega_scheduled_message.helpers import remove_schedule_message_job

        user_id = _random_user_id(numeric_bot.self_id)
        async with app.test_matcher(schedule_message_manager) as ctx:
            interface = _make_interface(numeric_bot, create_real_obv11_bot(ctx, numeric_bot.self_id), user_id)
            await remove_schedule_message_job(interface=interface, readable_job_name='不存在任务')


class TestMatcherAdd:
    """add 子命令测试 (管理员私聊事件)"""

    async def test_add_success(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            scheduled_message_enabled_guard: None,
    ) -> None:
        from src.plugins.omega_scheduled_message.command import schedule_message_manager
        from src.service import scheduler

        user_id = _random_user_id(numeric_bot.self_id)
        await _seed_user_permissions(numeric_bot, user_id)
        event = _private_event(numeric_bot, user_id, '/定时消息 新增 -n 测试任务 -c 0 8 * * * -m 早上好')

        async with app.test_matcher(schedule_message_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, "添加定时消息'测试任务'成功!"))
            ctx.should_finished(schedule_message_manager)

        # 验证数据库状态: 配置行启用且内容一致
        job_rows = await _query_job_rows(numeric_bot, user_id)
        assert len(job_rows) == 1
        assert job_rows[0].available == 1
        assert job_rows[0].value['readable_job_name'] == '测试任务'
        assert job_rows[0].value['crontab'] == '0 8 * * *'
        # 验证调度器状态: 任务已注册
        assert scheduler.get_job(job_rows[0].node) is not None

    async def test_add_overwrite_same_name(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            scheduled_message_enabled_guard: None,
    ) -> None:
        """同名任务重复新增应整体替换"""
        from nonebot_plugin_alconna.uniseg import UniMessage

        from src.plugins.omega_scheduled_message.command import schedule_message_manager

        user_id = _random_user_id(numeric_bot.self_id)
        await _seed_user_permissions(numeric_bot, user_id)

        async with app.test_matcher(schedule_message_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            for content in ('第一版内容', '第二版内容'):
                event = _private_event(numeric_bot, user_id, f'/定时消息 新增 -n 覆写任务 -c 0 8 * * * -m {content}')
                ctx.receive_event(bot, event)
                ctx.should_call_send(event, expected_reply(event, "添加定时消息'覆写任务'成功!"))
                ctx.should_finished(schedule_message_manager)

        job_rows = await _query_job_rows(numeric_bot, user_id)
        assert len(job_rows) == 1
        message_text = UniMessage.load(data=job_rows[0].value['message']).extract_plain_text()
        assert message_text == '第二版内容'

    async def test_add_via_prompt_full_flow(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            scheduled_message_enabled_guard: None,
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """命令不带任何选项时依次追问任务名称/crontab/消息内容

        nonebug 顺序处理事件, 无法驱动 nonebot_plugin_waiter 的实时等待, 追问流程打桩 ensure_arg_* 验证参数透传
        (ensure_arg_* 自身行为由 tests/test_002_core/test_013_omega_internal_params.py 覆盖)
        """
        from nonebot_plugin_alconna.uniseg import UniMessage

        import src.plugins.omega_scheduled_message.command as command_module
        from src.plugins.omega_scheduled_message.command import schedule_message_manager

        prompt_calls: list[str] = []

        async def fake_ensure_arg_text(*, arg, prompt_text: str, timeout: float, **_kwargs) -> str:
            prompt_calls.append(prompt_text)
            assert not arg.available
            assert timeout == command_module._HANDLER_PROMPT_TIMEOUT
            return {
                '请输入为定时消息设置的任务名称:': '追问任务',
                '请输入调度的定时任务的crontab表达式:': '0 9 * * *',
            }[prompt_text]

        async def fake_ensure_arg_message(*, arg, prompt_text: str, timeout: float, **_kwargs) -> UniMessage:
            prompt_calls.append(prompt_text)
            assert not arg.available
            assert timeout == command_module._HANDLER_PROMPT_TIMEOUT
            return UniMessage('追问内容')

        monkeypatch.setattr(command_module, 'ensure_arg_text', fake_ensure_arg_text)
        monkeypatch.setattr(command_module, 'ensure_arg_message', fake_ensure_arg_message)

        user_id = _random_user_id(numeric_bot.self_id)
        await _seed_user_permissions(numeric_bot, user_id)
        event = _private_event(numeric_bot, user_id, '/定时消息 新增')

        async with app.test_matcher(schedule_message_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, "添加定时消息'追问任务'成功!"))
            ctx.should_finished(schedule_message_manager)

        assert prompt_calls == [
            '请输入为定时消息设置的任务名称:',
            '请输入调度的定时任务的crontab表达式:',
            '请输入设置的定时消息内容:',
        ]
        job_rows = await _query_job_rows(numeric_bot, user_id)
        assert len(job_rows) == 1
        assert job_rows[0].value['crontab'] == '0 9 * * *'

    async def test_add_prompt_timeout(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            scheduled_message_enabled_guard: None,
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """缺少参数进入追问, 缩短超时时间验证超时取消分支"""
        import src.plugins.omega_scheduled_message.command as command_module
        from src.plugins.omega_scheduled_message.command import schedule_message_manager

        monkeypatch.setattr(command_module, '_HANDLER_PROMPT_TIMEOUT', 0.05)

        user_id = _random_user_id(numeric_bot.self_id)
        await _seed_user_permissions(numeric_bot, user_id)
        event = _private_event(numeric_bot, user_id, '/定时消息 新增')

        async with app.test_matcher(schedule_message_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            # prompt 消息经 matcher.send 发送, 无 reply 段
            ctx.should_call_send(event, '请输入为定时消息设置的任务名称:')
            ctx.should_call_send(event, expected_reply(event, '等待输入超时, 已取消操作'))
            ctx.should_finished(schedule_message_manager)

    async def test_add_invalid_crontab(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            scheduled_message_enabled_guard: None,
    ) -> None:
        from src.plugins.omega_scheduled_message.command import schedule_message_manager

        user_id = _random_user_id(numeric_bot.self_id)
        await _seed_user_permissions(numeric_bot, user_id)
        event = _private_event(numeric_bot, user_id, '/定时消息 新增 -n 非法任务 -c 1 2 3 -m 内容')

        async with app.test_matcher(schedule_message_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event, expected_reply(event, "设置的crontab表达式'1 2 3'非法, 请修改后重新执行命令"),
            )
            ctx.should_finished(schedule_message_manager)

        assert await _query_job_rows(numeric_bot, user_id) == []

    async def test_add_name_too_long(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            scheduled_message_enabled_guard: None,
    ) -> None:
        from src.plugins.omega_scheduled_message.command import _MAX_READABLE_JOB_NAME_LENGTH, schedule_message_manager

        user_id = _random_user_id(numeric_bot.self_id)
        await _seed_user_permissions(numeric_bot, user_id)
        long_name = '名' * (_MAX_READABLE_JOB_NAME_LENGTH + 1)
        event = _private_event(numeric_bot, user_id, f'/定时消息 新增 -n {long_name} -c 0 8 * * * -m 内容')

        async with app.test_matcher(schedule_message_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event,
                expected_reply(
                    event,
                    f'设置的定时消息任务名称过长(超过{_MAX_READABLE_JOB_NAME_LENGTH}字), 请修改后重新执行命令',
                ),
            )
            ctx.should_finished(schedule_message_manager)

        assert await _query_job_rows(numeric_bot, user_id) == []

    async def test_add_empty_message_option_prompts(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            scheduled_message_enabled_guard: None,
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """-m 选项无内容时 AllParam 不可用, 进入消息追问"""
        from nonebot_plugin_alconna.uniseg import UniMessage

        import src.plugins.omega_scheduled_message.command as command_module
        from src.plugins.omega_scheduled_message.command import schedule_message_manager

        async def fake_ensure_arg_message(*, arg, prompt_text: str, timeout: float, **_kwargs) -> UniMessage:
            assert not arg.available
            assert prompt_text == '请输入设置的定时消息内容:'
            assert timeout == command_module._HANDLER_PROMPT_TIMEOUT
            return UniMessage('补充内容')

        monkeypatch.setattr(command_module, 'ensure_arg_message', fake_ensure_arg_message)

        user_id = _random_user_id(numeric_bot.self_id)
        await _seed_user_permissions(numeric_bot, user_id)
        event = _private_event(numeric_bot, user_id, '/定时消息 新增 -n 空选项任务 -c 0 8 * * * -m')

        async with app.test_matcher(schedule_message_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, "添加定时消息'空选项任务'成功!"))
            ctx.should_finished(schedule_message_manager)

        job_rows = await _query_job_rows(numeric_bot, user_id)
        assert len(job_rows) == 1
        assert UniMessage.load(data=job_rows[0].value['message']).extract_plain_text() == '补充内容'

    async def test_add_db_write_failure(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            scheduled_message_enabled_guard: None,
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """数据库写入失败时应回复失败提示, 不注册调度任务且不产生配置行"""
        import src.plugins.omega_scheduled_message.command as command_module
        from src.plugins.omega_scheduled_message.command import schedule_message_manager
        from src.service import scheduler

        monkeypatch.setattr(
            command_module, 'set_schedule_message_job', AsyncMock(side_effect=RuntimeError('boom')),
        )

        user_id = _random_user_id(numeric_bot.self_id)
        await _seed_user_permissions(numeric_bot, user_id)
        before_jobs = {job.id for job in scheduler.get_jobs()}
        event = _private_event(numeric_bot, user_id, '/定时消息 新增 -n 写库失败任务 -c 0 8 * * * -m 内容')

        async with app.test_matcher(schedule_message_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, '保存定时消息失败, 请稍后再试或联系管理员处理'))
            ctx.should_finished(schedule_message_manager)

        assert await _query_job_rows(numeric_bot, user_id) == []
        assert {job.id for job in scheduler.get_jobs()} == before_jobs

    async def test_add_scheduler_failure_new_job_rollback(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            scheduled_message_enabled_guard: None,
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """全新任务注册调度器失败: 回滚数据库配置 (行被停用)"""
        import src.plugins.omega_scheduled_message.command as command_module
        from src.plugins.omega_scheduled_message.command import schedule_message_manager

        monkeypatch.setattr(
            command_module, 'add_schedule_job', Mock(side_effect=RuntimeError('boom')),
        )

        user_id = _random_user_id(numeric_bot.self_id)
        await _seed_user_permissions(numeric_bot, user_id)
        event = _private_event(numeric_bot, user_id, '/定时消息 新增 -n 回滚任务 -c 0 8 * * * -m 内容')

        async with app.test_matcher(schedule_message_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, '设置消息定时任务失败, 请稍后再试或联系管理员处理'))
            ctx.should_finished(schedule_message_manager)

        job_rows = await _query_job_rows(numeric_bot, user_id)
        assert len(job_rows) == 1
        assert job_rows[0].available == 0

    async def test_add_scheduler_failure_overwrite_restore(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            scheduled_message_enabled_guard: None,
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """覆盖更新注册调度器失败: 恢复旧配置, 旧调度任务与媒体目录不受影响"""
        from nonebot_plugin_alconna.uniseg import UniMessage

        import src.plugins.omega_scheduled_message.command as command_module
        from src.plugins.omega_scheduled_message.command import schedule_message_manager
        from src.service import scheduler

        user_id = _random_user_id(numeric_bot.self_id)
        await _seed_user_permissions(numeric_bot, user_id)

        # 先成功新增一个任务
        add_event = _private_event(numeric_bot, user_id, '/定时消息 新增 -n 恢复任务 -c 0 8 * * * -m 第一版内容')
        async with app.test_matcher(schedule_message_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, add_event)
            ctx.should_call_send(add_event, expected_reply(add_event, "添加定时消息'恢复任务'成功!"))
            ctx.should_finished(schedule_message_manager)

        job_rows = await _query_job_rows(numeric_bot, user_id)
        assert len(job_rows) == 1
        job_node = job_rows[0].node

        # 覆盖更新时注册调度器失败
        monkeypatch.setattr(
            command_module, 'add_schedule_job', Mock(side_effect=RuntimeError('boom')),
        )
        update_event = _private_event(numeric_bot, user_id, '/定时消息 新增 -n 恢复任务 -c 30 9 * * * -m 第二版内容')
        async with app.test_matcher(schedule_message_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, update_event)
            ctx.should_call_send(
                update_event, expected_reply(update_event, '设置消息定时任务失败, 请稍后再试或联系管理员处理'),
            )
            ctx.should_finished(schedule_message_manager)

        # 验证数据库已恢复为旧配置
        job_rows = await _query_job_rows(numeric_bot, user_id)
        assert len(job_rows) == 1
        assert job_rows[0].available == 1
        assert job_rows[0].value['crontab'] == '0 8 * * *'
        assert UniMessage.load(data=job_rows[0].value['message']).extract_plain_text() == '第一版内容'
        # 旧调度任务仍保留
        assert scheduler.get_job(job_node) is not None


class TestMatcherRemove:
    """remove 子命令测试 (管理员私聊事件)"""

    @staticmethod
    async def _add_job(app: App, bot: 'BotSelf', user_id: int, name: str) -> None:
        """经命令流程播种一个定时消息任务"""
        from src.plugins.omega_scheduled_message.command import schedule_message_manager

        event = _private_event(bot, user_id, f'/定时消息 新增 -n {name} -c 0 8 * * * -m 内容')
        async with app.test_matcher(schedule_message_manager) as ctx:
            obv11_bot = create_real_obv11_bot(ctx, bot.self_id)
            ctx.receive_event(obv11_bot, event)
            ctx.should_call_send(event, expected_reply(event, f"添加定时消息'{name}'成功!"))
            ctx.should_finished(schedule_message_manager)

    async def test_remove_success(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            scheduled_message_enabled_guard: None,
    ) -> None:
        from src.plugins.omega_scheduled_message.command import schedule_message_manager
        from src.service import scheduler

        user_id = _random_user_id(numeric_bot.self_id)
        await _seed_user_permissions(numeric_bot, user_id)
        await self._add_job(app, numeric_bot, user_id, '待移除任务')

        job_rows = await _query_job_rows(numeric_bot, user_id)
        job_node = job_rows[0].node
        assert scheduler.get_job(job_node) is not None

        event = _private_event(numeric_bot, user_id, '/定时消息 移除 -n 待移除任务')
        async with app.test_matcher(schedule_message_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, "移除定时消息'待移除任务'成功!"))
            ctx.should_finished(schedule_message_manager)

        # 验证数据库与调度器状态: 行停用且调度任务移除
        job_rows = await _query_job_rows(numeric_bot, user_id)
        assert len(job_rows) == 1
        assert job_rows[0].available == 0
        assert scheduler.get_job(job_node) is None

    async def test_remove_not_exist_with_existing_jobs(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            scheduled_message_enabled_guard: None,
    ) -> None:
        from src.plugins.omega_scheduled_message.command import schedule_message_manager

        user_id = _random_user_id(numeric_bot.self_id)
        await _seed_user_permissions(numeric_bot, user_id)
        await self._add_job(app, numeric_bot, user_id, '既有任务')

        event = _private_event(numeric_bot, user_id, '/定时消息 移除 -n 不存在任务')
        async with app.test_matcher(schedule_message_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event,
                expected_reply(event, "没有名为'不存在任务'定时消息任务, 请确认已配置的定时消息:\n\n既有任务"),
            )
            ctx.should_finished(schedule_message_manager)

    async def test_remove_not_exist_empty(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            scheduled_message_enabled_guard: None,
    ) -> None:
        from src.plugins.omega_scheduled_message.command import schedule_message_manager

        user_id = _random_user_id(numeric_bot.self_id)
        await _seed_user_permissions(numeric_bot, user_id)

        event = _private_event(numeric_bot, user_id, '/定时消息 移除 -n 不存在任务')
        async with app.test_matcher(schedule_message_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            expected_text = "没有名为'不存在任务'定时消息任务, 请确认已配置的定时消息:\n\n无已配置的定时消息"
            ctx.should_call_send(event, expected_reply(event, expected_text))
            ctx.should_finished(schedule_message_manager)

    async def test_remove_via_prompt(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            scheduled_message_enabled_guard: None,
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """remove 缺少任务名称时进入追问 (打桩 ensure_arg_text 验证参数透传)"""
        import src.plugins.omega_scheduled_message.command as command_module
        from src.plugins.omega_scheduled_message.command import schedule_message_manager

        async def fake_ensure_arg_text(*, arg, prompt_text: str, timeout: float, **_kwargs) -> str:
            assert not arg.available
            assert prompt_text == '请输入将要删除的定时消息任务名称:'
            assert timeout == command_module._HANDLER_PROMPT_TIMEOUT
            return '追问移除任务'

        user_id = _random_user_id(numeric_bot.self_id)
        await _seed_user_permissions(numeric_bot, user_id)
        await self._add_job(app, numeric_bot, user_id, '追问移除任务')

        # 打桩须在播种之后, 避免影响播种流程自身的参数处理
        monkeypatch.setattr(command_module, 'ensure_arg_text', fake_ensure_arg_text)

        event = _private_event(numeric_bot, user_id, '/定时消息 移除')
        async with app.test_matcher(schedule_message_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, "移除定时消息'追问移除任务'成功!"))
            ctx.should_finished(schedule_message_manager)

        job_rows = await _query_job_rows(numeric_bot, user_id)
        assert len(job_rows) == 1
        assert job_rows[0].available == 0


class TestMatcherList:
    """list 子命令测试 (管理员私聊事件)"""

    async def test_list_empty(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            scheduled_message_enabled_guard: None,
    ) -> None:
        from src.plugins.omega_scheduled_message.command import schedule_message_manager

        user_id = _random_user_id(numeric_bot.self_id)
        await _seed_user_permissions(numeric_bot, user_id)
        event = _private_event(numeric_bot, user_id, '/定时消息 清单')

        async with app.test_matcher(schedule_message_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, '当前已配置定时消息任务有:\n\n无已配置的定时消息'))
            ctx.should_finished(schedule_message_manager)

    async def test_list_after_add(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            scheduled_message_enabled_guard: None,
    ) -> None:
        from src.plugins.omega_scheduled_message.command import schedule_message_manager

        user_id = _random_user_id(numeric_bot.self_id)
        await _seed_user_permissions(numeric_bot, user_id)
        await TestMatcherRemove._add_job(app, numeric_bot, user_id, '清单任务')

        event = _private_event(numeric_bot, user_id, '/定时消息 list')
        async with app.test_matcher(schedule_message_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, '当前已配置定时消息任务有:\n\n清单任务'))
            ctx.should_finished(schedule_message_manager)


class TestMatcherDefault:
    """$main 默认响应测试"""

    async def test_main_usage(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            scheduled_message_enabled_guard: None,
    ) -> None:
        from src.plugins.omega_scheduled_message.command import schedule_message_manager

        user_id = _random_user_id(numeric_bot.self_id)
        await _seed_user_permissions(numeric_bot, user_id)
        event = _private_event(numeric_bot, user_id, '/定时消息')

        async with app.test_matcher(schedule_message_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event,
                expected_reply(event, '定时消息插件, 可用子命令：<新增|移除|清单>, 使用帮助查看详细使用方法'),
            )
            ctx.should_finished(schedule_message_manager)


class TestPermissionGate:
    """权限门控测试"""

    @pytest.mark.parametrize(
        'text',
        ['/定时消息 新增 -n 任务 -c 0 8 * * * -m 内容', '/定时消息 移除 -n 任务', '/定时消息 清单'],
        ids=['add', 'remove', 'list'],
    )
    async def test_group_member_silenced(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            scheduled_message_enabled_guard: None,
            text: str,
    ) -> None:
        """群成员非管理员, 处理器放行后由 admin 门控拦截, 不应有任何回复"""
        from src.plugins.omega_scheduled_message.command import schedule_message_manager

        group_id = random.randint(10_000_000, 99_999_999)
        await seed_entity_permissions(
            numeric_bot, 'onebot_v11_group', str(group_id), enable_global=True, permission_level=30,
        )
        event = make_obv11_group_message_event(
            group_id=group_id,
            user_id=_random_user_id(numeric_bot.self_id),
            text=text,
            self_id=int(numeric_bot.self_id),
            message_id=_random_message_id(),
            role='member',
        )

        async with app.test_matcher(schedule_message_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            # 群成员非管理员, 不应有任何回复

    async def test_private_user_without_permission_echo(
            self,
            app: App,
            numeric_bot: 'BotSelf',
            scheduled_message_enabled_guard: None,
    ) -> None:
        """未初始化权限的私聊用户被权限处理器拦截并收到未启用提示"""
        from src.plugins.omega_scheduled_message.command import schedule_message_manager

        user_id = _random_user_id(numeric_bot.self_id)
        event = _private_event(numeric_bot, user_id, '/定时消息 清单')

        async with app.test_matcher(schedule_message_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            # 处理器经 matcher.send 发送提示, 无 reply 段
            ctx.should_call_send(
                event, 'Omega Miya 未启用, 请尝试使用 "/omega start" 命令初始化, 或联系管理员处理',
            )


class TestStartupInit:
    """启动时定时任务注册流程测试"""

    async def test_init_registers_seeded_jobs_and_skips_corrupted(
            self,
            app: App,
            numeric_bot: 'BotSelf',
    ) -> None:
        """启动初始化注册数据库中全部有效任务, 损坏配置被跳过且不抛出异常"""
        from nonebot_plugin_alconna.uniseg import UniMessage

        from src.plugins.omega_scheduled_message.command import schedule_message_manager
        from src.plugins.omega_scheduled_message.helpers import (
            _SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME,
            _SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME,
            _init_schedule_message_job,
            generate_schedule_job_data,
        )
        from src.service import scheduler

        user_id = _random_user_id(numeric_bot.self_id)
        async with app.test_matcher(schedule_message_manager) as ctx:
            interface = _make_interface(numeric_bot, create_real_obv11_bot(ctx, numeric_bot.self_id), user_id)
            job_data = await generate_schedule_job_data(
                interface=interface, readable_job_name='启动注册任务',
                crontab='0 8 * * *', message=UniMessage('启动内容'),
            )

        corrupted_node = 'SchedMsgJob_corrupted_startup_test'
        async with obv11_user_entity(numeric_bot, str(user_id)) as entity:
            await entity.set_auth_setting(
                module=_SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME,
                plugin=_SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME,
                node=job_data.job_unique_id,
                available=1,
                value=job_data.model_dump(mode='json'),
            )
            await entity.set_auth_setting(
                module=_SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME,
                plugin=_SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME,
                node=corrupted_node,
                available=1,
                value={'bad': 'data'},
            )

        await _init_schedule_message_job()
        assert scheduler.get_job(job_data.job_unique_id) is not None
        assert scheduler.get_job(corrupted_node) is None

        # 测试数据清理
        async with obv11_user_entity(numeric_bot, str(user_id)) as entity:
            await entity.delete_auth_setting(
                module=_SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME,
                plugin=_SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME,
                node=job_data.job_unique_id,
            )
            await entity.delete_auth_setting(
                module=_SCHEDULE_MESSAGE_CUSTOM_MODULE_NAME,
                plugin=_SCHEDULE_MESSAGE_CUSTOM_PLUGIN_NAME,
                node=corrupted_node,
            )
