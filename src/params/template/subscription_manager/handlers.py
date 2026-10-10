"""
@Author         : Ailitonia
@Date           : 2025/6/4 20:37
@FileName       : handlers
@Project        : omega-miya
@Description    : 订阅插件通用命令模板(基于 nonebot-plugin-alconna)
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import TYPE_CHECKING

from arclet.alconna import Alconna, Args, Arparma, CommandMeta, Subcommand
from nonebot.adapters import Bot as BaseBot
from nonebot.adapters import Event as BaseEvent
from nonebot.exception import MatcherException
from nonebot.log import logger
from nonebot.typing import T_State
from nonebot_plugin_alconna import AlconnaMatcher, Match, on_alconna

from src.service import OmegaMatcherInterface, enable_processor_state, scheduler
from ...depends import EVENT_M_IFACE
from ...permission import IS_ADMIN

if TYPE_CHECKING:
    from nonebot.typing import T_Handler

    from .manager import BaseSubscriptionManager

_CONFIRM_WORDS: frozenset[str] = frozenset({'是', '确认', 'Yes', 'yes', 'Y', 'y'})
"""订阅流程确认消息关键词"""
_HANDLER_PROMPT_TIMEOUT: float = 60
"""订阅流程等待用户响应超时时间"""


async def _check_event_is_admin(event: BaseEvent, bot: BaseBot, _s: T_State, _a: Arparma) -> bool:
    """assign additional 检查: 事件触发对象是否为管理员"""
    return await IS_ADMIN(bot, event)


class SubscriptionHandlerFactory[SM_T: BaseSubscriptionManager]:
    """订阅插件通用命令模板工厂

    基于 nonebot-plugin-alconna 注册订阅管理命令组:
    {command_prefix} <订阅|取消订阅|订阅列表|全体通知开关> [参数]
    """

    def __init__(
            self,
            subscription_manager: type[SM_T],
            command_prefix: str,
            *,
            aliases_command_prefix: set[str] | None = None,
            need_decimal_sub_id: bool = False,
            default_sub_id: str | None = None,
    ) -> None:
        self._subscription_manager = subscription_manager
        self._command_prefix = command_prefix
        self._aliases_command_prefix: set[str] = set() if aliases_command_prefix is None else aliases_command_prefix

        # 相关插件配置参数
        self._need_decimal_sub_id = need_decimal_sub_id
        self._default_sub_id = default_sub_id

    def __str__(self) -> str:
        return f'SubscriptionHandlerFactory | {self.sub_type.upper()}'

    @property
    def sub_type(self) -> str:
        """获取订阅源类型"""
        return self._subscription_manager.get_sub_type()

    def _get_manager(self, sub_id: str | int) -> SM_T:
        """实例化 SubscriptionManager"""
        return self._subscription_manager(sub_id)

    async def _execute_add_subscription(self, interface: OmegaMatcherInterface, sub_id: str) -> None:
        """执行新增订阅流程"""
        await interface.send_reply(f'正在更新{self._command_prefix}订阅信息, 请稍候')

        # 暂停计划任务避免中途检查更新; 调度器未运行时 (STATE_STOPPED) pause/resume 会抛出
        # SchedulerNotRunningError, 此时跳过暂停保护, 不阻断订阅流程
        scheduler_paused = False
        if scheduler.running:
            scheduler.pause()
            scheduler_paused = True
        else:
            logger.warning('Scheduler is not running, skip pausing scheduled jobs during subscription update')

        try:
            await self._get_manager(sub_id).add_entity_sub(interface=interface)
            logger.success(f'{interface}订阅{self._command_prefix}({sub_id})成功')
            msg = f'订阅{self._command_prefix}: {sub_id}成功'
        except MatcherException:
            raise
        except Exception as e:
            logger.error(f'{interface}订阅{self._command_prefix}({sub_id})失败, {e!r}')
            msg = (
                f'订阅{self._command_prefix}: {sub_id}失败, '
                f'可能是网络异常或发生了意外的错误, 请稍后再试或联系管理员处理'
            )
        finally:
            # 恢复计划任务 (仅恢复本流程实际暂停的情况, 且调度器仍在运行)
            if scheduler_paused and scheduler.running:
                scheduler.resume()
        await interface.finish_reply(msg)

    async def _execute_del_subscription(self, interface: OmegaMatcherInterface, sub_id: str) -> None:
        """执行移除订阅流程"""
        try:
            await self._get_manager(sub_id).delete_entity_sub(interface=interface)
            logger.success(f'{interface}取消订阅{self._command_prefix}({sub_id})成功')
            msg = f'取消订阅{self._command_prefix}: {sub_id}成功'
        except MatcherException:
            raise
        except Exception as e:
            logger.error(f'{interface}取消订阅{self._command_prefix}({sub_id})失败, {e!r}')
            msg = f'取消订阅{self._command_prefix}: {sub_id}失败, 请稍后再试或联系管理员处理'
        await interface.finish_reply(msg)

    def _generate_add_subscription_handler(self) -> 'T_Handler':
        """生成新增订阅流程函数以供注册"""

        async def _add_subscription_handler(
                matcher: AlconnaMatcher,
                interface: EVENT_M_IFACE,
                sub_id: Match[str],
        ) -> None:
            """新增订阅(子命令: 订阅)"""
            # 配置了默认订阅 ID 时直接使用默认值执行, 忽略参数且无需确认
            if self._default_sub_id is not None:
                await self._execute_add_subscription(interface=interface, sub_id=self._default_sub_id)
                return

            if not sub_id.available:
                await interface.finish_reply('未提供订阅ID参数, 已取消操作')
            target_sub_id = sub_id.result.strip()
            if not target_sub_id:
                await interface.finish_reply('未提供订阅ID参数, 已取消操作')
            if self._need_decimal_sub_id and not target_sub_id.isdecimal():
                await interface.finish_reply('非有效的订阅ID, 订阅ID应当为纯数字, 已取消操作')

            try:
                sub_source_data = await self._get_manager(target_sub_id).query_sub_source_data()
                # 针对订阅请求的 ID 为短号等场景进行 ID 转换处理
                if target_sub_id != sub_source_data.sub_id:
                    logger.debug(
                        f'订阅{self._command_prefix}请求 ID={target_sub_id!r} 已转换为 {sub_source_data.sub_id!r}'
                    )
                    target_sub_id = sub_source_data.sub_id
            except Exception as e:
                logger.error(f'获取订阅{self._command_prefix}({target_sub_id})信息失败, {e!r}')
                await interface.finish_reply('获取订阅源信息失败, 可能是网络原因或没有这个订阅源, 请稍后再试')

            # 确认流程
            ensure_resp = await matcher.prompt(
                f'即将订阅{self._command_prefix}【{sub_source_data.sub_user_name}】\n\n确认吗?\n【是/否】',
                timeout=_HANDLER_PROMPT_TIMEOUT,
            )
            if ensure_resp is None:
                await interface.finish_reply('确认超时, 已取消操作')
            if ensure_resp.extract_plain_text().strip() not in _CONFIRM_WORDS:
                await interface.finish_reply('已取消操作')

            await self._execute_add_subscription(interface=interface, sub_id=target_sub_id)

        return _add_subscription_handler

    def _generate_del_subscription_handler(self) -> 'T_Handler':
        """生成移除订阅流程函数以供注册"""

        async def _del_subscription_handler(
                matcher: AlconnaMatcher,
                interface: EVENT_M_IFACE,
                sub_id: Match[str],
        ) -> None:
            """移除订阅(子命令: 取消订阅)"""
            # 配置了默认订阅 ID 时直接使用默认值执行, 忽略参数且无需确认
            if self._default_sub_id is not None:
                await self._execute_del_subscription(interface=interface, sub_id=self._default_sub_id)
                return

            if not sub_id.available:
                await interface.finish_reply('未提供订阅ID参数, 已取消操作')
            target_sub_id = sub_id.result.strip()
            if not target_sub_id:
                await interface.finish_reply('未提供订阅ID参数, 已取消操作')
            if self._need_decimal_sub_id and not target_sub_id.isdecimal():
                await interface.finish_reply('非有效的订阅ID, 订阅ID应当为纯数字, 已取消操作')

            try:
                exist_sub = await self._subscription_manager.query_entity_subscribed_sub_source(interface=interface)
            except Exception as e:
                logger.error(f'获取{interface}已订阅的{self._command_prefix}列表失败, {e!r}')
                await interface.finish_reply(f'获取已订阅的{self._command_prefix}列表失败, 请稍后再试或联系管理员处理')

            if target_sub_id not in exist_sub:
                exist_text = '\n'.join(f'{id_}: {user_nickname}' for id_, user_nickname in exist_sub.items())
                await interface.finish_reply(
                    f'未订阅{self._command_prefix}: {target_sub_id}, '
                    f'请确认已订阅的{self._command_prefix}列表:\n\n{exist_text if exist_text else "无"}'
                )

            # 确认流程
            ensure_resp = await matcher.prompt(
                f'取消订阅{self._command_prefix}【{exist_sub.get(target_sub_id)}】\n\n确认吗?\n【是/否】',
                timeout=_HANDLER_PROMPT_TIMEOUT,
            )
            if ensure_resp is None:
                await interface.finish_reply('确认超时, 已取消操作')
            if ensure_resp.extract_plain_text().strip() not in _CONFIRM_WORDS:
                await interface.finish_reply('已取消操作')

            await self._execute_del_subscription(interface=interface, sub_id=target_sub_id)

        return _del_subscription_handler

    def _generate_list_subscription_handler(self) -> 'T_Handler':
        """生成查询订阅列表流程函数以供注册"""

        async def _list_subscription_handler(
                interface: EVENT_M_IFACE,
        ) -> None:
            """查询订阅列表(子命令: 订阅列表)"""
            try:
                exist_sub = await self._subscription_manager.query_entity_subscribed_sub_source(interface=interface)
                exist_text = '\n'.join(f'{id_}: {user_nickname}' for id_, user_nickname in exist_sub.items())
                await interface.send_reply(
                    f'当前已订阅的{self._command_prefix}列表:\n\n{exist_text if exist_text else "无"}'
                )
            except Exception as e:
                logger.error(f'获取{interface}已订阅的{self._command_prefix}列表失败, {e!r}')
                await interface.finish_reply(f'获取已订阅的{self._command_prefix}列表失败, 请稍后再试或联系管理员处理')

        return _list_subscription_handler

    def _generate_switch_subscription_notice_at_all_handler(self) -> 'T_Handler':
        """生成切换订阅通知@所有人开关的流程函数以供注册"""

        async def _switch_subscription_notice_at_all_handler(
                matcher: AlconnaMatcher,
                interface: EVENT_M_IFACE,
                switch: Match[str],
        ) -> None:
            """切换订阅通知@所有人开关(子命令: 全体通知开关)"""
            if switch.available:
                switch_arg = switch.result.strip().lower()
            else:
                # 未提供开关参数时进行追问
                switch_resp = await matcher.prompt(
                    f'启用或关闭{self._command_prefix}订阅通知@所有人功能:\n【ON/OFF】',
                    timeout=_HANDLER_PROMPT_TIMEOUT,
                )
                if switch_resp is None:
                    await interface.finish_reply('等待输入超时, 已取消操作')
                switch_arg = switch_resp.extract_plain_text().strip().lower()

            match switch_arg:
                case 'on':
                    switch_func = self._subscription_manager.enable_entity_notice_at_all_node
                case 'off':
                    switch_func = self._subscription_manager.disable_entity_notice_at_all_node
                case _:
                    await interface.finish_reply('无效选项, 请输入【ON/OFF】以启用或关闭订阅通知@所有人, 操作已取消')

            try:
                async with interface.create_current_entity_session() as entity:
                    await switch_func(entity)
                logger.success(f'{interface}设置{self._command_prefix}订阅通知@所有人功能为 {switch_arg!r} 成功')
                await interface.send_reply(f'已设置{self._command_prefix}订阅通知@所有人功能为【{switch_arg.upper()}】')
            except Exception as e:
                logger.error(f'{interface}设置{self._command_prefix}订阅通知@所有人功能为 {switch_arg!r} 失败, {e!r}')
                await interface.send_reply(f'设置{self._command_prefix}订阅通知@所有人功能失败, 请联系管理员处理')

        return _switch_subscription_notice_at_all_handler

    def register_handlers(
            self,
            *,
            priority: int = 20,
            block: bool = True,
            permission_level: int = 20,
            handler_echo_processor_result: bool = True,
    ) -> type[AlconnaMatcher]:
        """注册插件命令

        命令结构: {command_prefix} <订阅|取消订阅|订阅列表|全体通知开关> [参数],
        订阅/取消订阅/全体通知开关仅限管理员触发, 订阅列表对所有用户开放
        :return: 注册的 AlconnaMatcher, 可通过 .shortcut()/.assign() 等方法进行扩展
        """

        sub_matcher = on_alconna(
            Alconna(
                self._command_prefix,
                Subcommand(
                    '订阅',
                    Args['sub_id?#订阅ID', str],
                    help_text=f'添加{self._command_prefix}订阅',
                ),
                Subcommand(
                    '取消订阅',
                    Args['sub_id?#订阅ID', str],
                    alias=['删除订阅', '退订'],
                    help_text=f'取消{self._command_prefix}订阅',
                ),
                Subcommand(
                    '订阅列表',
                    alias=['列表'],
                    help_text=f'查询已订阅的{self._command_prefix}列表',
                ),
                Subcommand(
                    '全体通知开关',
                    Args['switch?#ON/OFF', str],
                    alias=['全体通知'],
                    help_text=f'启用或关闭{self._command_prefix}订阅通知@所有人',
                ),
                meta=CommandMeta(
                    description=f'{self._command_prefix}订阅管理',
                    usage=f'{self._command_prefix} <订阅|取消订阅|订阅列表|全体通知开关> [参数]',
                    example=f'{self._command_prefix} 订阅 12345',
                    compact=True,
                ),
            ),
            use_cmd_start=True,
            aliases=self._aliases_command_prefix if self._aliases_command_prefix else None,
            priority=priority,
            block=block,
            default_state=enable_processor_state(
                name=f'{self.sub_type.title().replace('_', '').strip()}SubscriptionManager',
                level=permission_level,
                echo_processor_result=handler_echo_processor_result,
            ),
        )

        sub_matcher.assign('订阅', additional=_check_event_is_admin)(
            self._generate_add_subscription_handler()
        )
        sub_matcher.assign('取消订阅', additional=_check_event_is_admin)(
            self._generate_del_subscription_handler()
        )
        sub_matcher.assign('订阅列表')(
            self._generate_list_subscription_handler()
        )
        sub_matcher.assign('全体通知开关', additional=_check_event_is_admin)(
            self._generate_switch_subscription_notice_at_all_handler()
        )

        # 注册声明式自检, 启动时解析失败将输出 ERROR 日志
        sub_matcher.test(f'{self._command_prefix} 订阅 12345')
        sub_matcher.test(f'{self._command_prefix}订阅 12345')
        sub_matcher.test(f'{self._command_prefix} 取消订阅 54321')
        sub_matcher.test(f'{self._command_prefix}取消订阅 54321')
        sub_matcher.test(f'{self._command_prefix} 订阅列表')
        sub_matcher.test(f'{self._command_prefix} 全体通知开关 ON')
        sub_matcher.test(f'{self._command_prefix}全体通知 OFF')

        return sub_matcher


__all__ = [
    'SubscriptionHandlerFactory',
]
