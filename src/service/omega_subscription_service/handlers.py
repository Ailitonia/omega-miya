"""
@Author         : Ailitonia
@Date           : 2025/6/4 20:37
@FileName       : handlers
@Project        : omega-miya
@Description    : 订阅插件通用命令模板
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import TYPE_CHECKING, Annotated

from nonebot.log import logger
from nonebot.params import ArgStr, Depends
from nonebot.plugin import CommandGroup

from src.params.handler import get_command_str_single_arg_parser_handler, get_set_default_state_handler
from src.params.permission import IS_ADMIN
from src.service import OmegaMatcherInterface as OmMI
from src.service import enable_processor_state, scheduler

if TYPE_CHECKING:
    from nonebot.typing import T_Handler

    from .manager import BaseSubscriptionManager


class SubscriptionHandlerManager[SM_T: 'BaseSubscriptionManager']:
    """订阅插件通用命令模板"""

    def __init__(
            self,
            subscription_manager: type[SM_T],
            command_prefix: str,
            *,
            aliases_command_prefix: set[str] | None = None,
            need_digit_sub_id: bool = False,
            default_sub_id: str | None = None,
    ) -> None:
        self._subscription_manager = subscription_manager
        self._command_prefix = command_prefix
        self._aliases_command_prefix: set[str] = set() if aliases_command_prefix is None else aliases_command_prefix

        # 相关插件配置参数
        self._need_digit_sub_id = need_digit_sub_id
        self._default_sub_id = default_sub_id

    def __str__(self) -> str:
        return f'SubscriptionHandlerManager | {self.sub_type.upper()}'

    @property
    def sub_type(self) -> str:
        """获取订阅源类型"""
        return self._subscription_manager.get_sub_type()

    def _get_manager(self, sub_id: str | int) -> SM_T:
        """实例化 SubscriptionManager"""
        return self._subscription_manager.init_from_sub_id(sub_id)

    def _generate_add_subscription_handler(self) -> 'T_Handler':
        """生成新增订阅流程函数以供注册"""

        async def _interface_entity_add_subscription(
                interface: Annotated[OmMI, Depends(OmMI.depend())],
                sub_id: str,
        ) -> None:
            """为 Entity 添加订阅"""
            await interface.send_reply(f'正在更新{self._command_prefix}订阅信息, 请稍候')

            # 暂停计划任务避免中途检查更新
            scheduler.pause()

            try:
                await self._get_manager(sub_id).add_entity_sub(interface=interface)
                await interface.entity.commit_session()
                logger.success(f'{interface.entity}订阅{self._command_prefix}({sub_id})成功')
                msg = f'订阅{self._command_prefix}: {sub_id}成功'
            except Exception as e:
                logger.error(f'{interface.entity}订阅{self._command_prefix}({sub_id})失败, {e!r}')
                msg = f'订阅{self._command_prefix}: {sub_id}失败, 可能是网络异常或发生了意外的错误, 请稍后再试或联系管理员处理'

            # 恢复计划任务
            scheduler.resume()
            await interface.finish_reply(msg)

        async def _add_subscription_handler_with_default_sub_id(
                interface: Annotated[OmMI, Depends(OmMI.depend())],
        ) -> None:
            if self._default_sub_id is not None:
                await _interface_entity_add_subscription(interface=interface, sub_id=self._default_sub_id)

        async def _add_subscription_handler(
                interface: Annotated[OmMI, Depends(OmMI.depend())],
                ensure: Annotated[str | None, ArgStr('ensure')],
                sub_id: Annotated[str | None, ArgStr('sub_id')],
        ) -> None:
            # 检查是否收到确认消息后执行新增订阅
            if ensure is None or sub_id is None:
                pass
            elif ensure in ['是', '确认', 'Yes', 'yes', 'Y', 'y']:
                await _interface_entity_add_subscription(interface=interface, sub_id=sub_id)
            else:
                await interface.finish_reply('已取消操作')

            # 未收到确认消息后则为首次触发命令执行订阅源检查
            if sub_id is None:
                await interface.finish_reply('未提供订阅ID参数, 已取消操作')
            sub_id = sub_id.strip()
            if self._need_digit_sub_id and not sub_id.isdigit():
                await interface.finish_reply('非有效的订阅ID, 订阅ID应当为纯数字, 已取消操作')

            try:
                sub_source_data = await self._get_manager(sub_id).query_sub_source_data()
                # 针对订阅请求的 ID 为短号等场景进行 ID 转换处理
                if sub_id != sub_source_data.sub_id:
                    logger.debug(f'订阅{self._command_prefix}请求 ID={sub_id!r} 已转换为 {sub_source_data.sub_id!r}')
                    interface.matcher.state.update({'sub_id': sub_source_data.sub_id})
            except Exception as e:
                logger.error(f'获取订阅{self._command_prefix}({sub_id})信息失败, {e!r}')
                await interface.finish_reply('获取订阅源信息失败, 可能是网络原因或没有这个订阅源, 请稍后再试')

            ensure_msg = f'即将订阅{self._command_prefix}【{sub_source_data.sub_user_name}】\n\n确认吗?\n【是/否】'
            await interface.reject_arg_reply('ensure', ensure_msg)

        if self._default_sub_id is not None:
            return _add_subscription_handler_with_default_sub_id
        else:
            return _add_subscription_handler

    def _generate_del_subscription_handler(self) -> 'T_Handler':
        """生成移除订阅流程函数以供注册"""

        async def _interface_entity_del_subscription(
                interface: Annotated[OmMI, Depends(OmMI.depend())],
                sub_id: str,
        ) -> None:
            """为 Entity 删除订阅"""
            try:
                await self._get_manager(sub_id).delete_entity_sub(interface=interface)
                await interface.entity.commit_session()
                logger.success(f'{interface.entity}取消订阅{self._command_prefix}({sub_id})成功')
                msg = f'取消订阅{self._command_prefix}: {sub_id}成功'
            except Exception as e:
                logger.error(f'{interface.entity}取消订阅{self._command_prefix}({sub_id})失败, {e!r}')
                msg = f'取消订阅{self._command_prefix}: {sub_id}失败, 请稍后再试或联系管理员处理'
            await interface.finish_reply(msg)

        async def _del_subscription_handler_with_default_sub_id(
                interface: Annotated[OmMI, Depends(OmMI.depend())],
        ) -> None:
            if self._default_sub_id is not None:
                await _interface_entity_del_subscription(interface=interface, sub_id=self._default_sub_id)

        async def _del_subscription_handler(
                interface: Annotated[OmMI, Depends(OmMI.depend())],
                ensure: Annotated[str | None, ArgStr('ensure')],
                sub_id: Annotated[str | None, ArgStr('sub_id')],
        ) -> None:
            # 检查是否收到确认消息后执行删除订阅
            if ensure is None or sub_id is None:
                pass
            elif ensure in ['是', '确认', 'Yes', 'yes', 'Y', 'y']:
                await _interface_entity_del_subscription(interface=interface, sub_id=sub_id)
            else:
                await interface.finish_reply('已取消操作')

            # 未收到确认消息后则为首次触发命令执行订阅源检查
            if sub_id is None:
                await interface.finish_reply('未提供订阅ID参数, 已取消操作')
            sub_id = sub_id.strip()
            if self._need_digit_sub_id and not sub_id.isdigit():
                await interface.finish_reply('非有效的订阅ID, 订阅ID应当为纯数字, 已取消操作')

            try:
                exist_sub = await self._get_manager(sub_id).query_entity_subscribed_sub_source(interface=interface)
                if sub_id in exist_sub.keys():
                    ensure_msg = f'取消订阅{self._command_prefix}【{exist_sub.get(sub_id)}】\n\n确认吗?\n【是/否】'
                    reject_key = 'ensure'
                else:
                    exist_text = '\n'.join(f'{sub_id}: {user_nickname}' for sub_id, user_nickname in exist_sub.items())
                    ensure_msg = (
                        f'未订阅{self._command_prefix}: {sub_id}, '
                        f'请确认已订阅的{self._command_prefix}列表:\n\n{exist_text if exist_text else "无"}'
                    )
                    reject_key = None
            except Exception as e:
                logger.error(f'获取{interface.entity}已订阅的{self._command_prefix}列表失败, {e!r}')
                await interface.finish_reply(f'获取已订阅的{self._command_prefix}列表失败, 请稍后再试或联系管理员处理')

            await interface.send_reply(ensure_msg)
            if reject_key is not None:
                await interface.matcher.reject_arg(reject_key)
            else:
                await interface.matcher.finish()

        if self._default_sub_id is not None:
            return _del_subscription_handler_with_default_sub_id
        else:
            return _del_subscription_handler

    def _generate_list_subscription_handler(self) -> 'T_Handler':
        """生成查询订阅列表流程函数以供注册"""

        async def _list_subscription_handler(
                interface: Annotated[OmMI, Depends(OmMI.depend())],
        ) -> None:
            try:
                exist_sub = await self._subscription_manager.query_entity_subscribed_sub_source(interface=interface)
                exist_text = '\n'.join(f'{sub_id}: {user_nickname}' for sub_id, user_nickname in exist_sub.items())
                await interface.send_reply(
                    f'当前已订阅的{self._command_prefix}列表:\n\n{exist_text if exist_text else "无"}'
                )
            except Exception as e:
                logger.error(f'获取{interface.entity}已订阅的{self._command_prefix}列表失败, {e!r}')
                await interface.finish_reply(f'获取已订阅的{self._command_prefix}列表失败, 请稍后再试或联系管理员处理')

        return _list_subscription_handler

    def _generate_switch_subscription_notice_at_all_handler(self) -> 'T_Handler':
        """生成切换订阅通知@所有人开关的流程函数以供注册"""

        async def _switch_subscription_notice_at_all_handler(
                interface: Annotated[OmMI, Depends(OmMI.depend())],
                switch: Annotated[str, ArgStr('switch')],
        ) -> None:
            switch = switch.strip().lower()

            match switch:
                case 'on':
                    switch_coro = self._subscription_manager.enable_entity_notice_at_all_node(interface.entity)
                case 'off':
                    switch_coro = self._subscription_manager.disable_entity_notice_at_all_node(interface.entity)
                case _:
                    await interface.finish_reply('无效选项, 请输入【ON/OFF】以启用或关闭订阅通知@所有人, 操作已取消')

            try:
                await switch_coro
                await interface.entity.commit_session()
                logger.success(f'{interface.entity} 设置{self._command_prefix}订阅通知@所有人功能为 {switch!r} 成功')
                await interface.send_reply(f'已设置{self._command_prefix}订阅通知@所有人功能为【{switch.upper()}】')
            except Exception as e:
                logger.error(f'{interface.entity} 设置{self._command_prefix}订阅通知@所有人功能为 {switch!r} 失败, {e}')
                await interface.send_reply(f'设置{self._command_prefix}订阅通知@所有人功能失败, 请联系管理员处理')

        return _switch_subscription_notice_at_all_handler

    def register_handlers(
            self,
            *,
            priority: int = 20,
            block: bool = True,
            permission_level: int = 20,
            handler_echo_processor_result: bool = True,
    ) -> CommandGroup:
        """注册插件命令"""

        sub_command_group = CommandGroup(
            f'{self.sub_type}-subscription-manager'.replace('_', '-').strip(),
            permission=IS_ADMIN,
            priority=priority,
            block=block,
            state=enable_processor_state(
                name=f'{self.sub_type.title().replace('_', '').strip()}SubscriptionManager',
                level=permission_level,
                echo_processor_result=handler_echo_processor_result,
            ),
        )

        sub_command_group.command(
            'add-subscription',
            aliases={
                f'{self._command_prefix}订阅',
                f'订阅{self._command_prefix}',
                *(f'{x}订阅' for x in self._aliases_command_prefix),
                *(f'订阅{x}' for x in self._aliases_command_prefix),
            },
            handlers=[
                get_set_default_state_handler('ensure', value=None),
                get_command_str_single_arg_parser_handler('sub_id', ensure_key=True)
            ],
        ).got('ensure')(self._generate_add_subscription_handler())

        sub_command_group.command(
            'del-subscription',
            aliases={
                f'取消{self._command_prefix}订阅',
                f'取消订阅{self._command_prefix}',
                *(f'取消{x}订阅' for x in self._aliases_command_prefix),
                *(f'取消订阅{x}' for x in self._aliases_command_prefix),
            },
            handlers=[
                get_set_default_state_handler('ensure', value=None),
                get_command_str_single_arg_parser_handler('sub_id', ensure_key=True)
            ],
        ).got('ensure')(self._generate_del_subscription_handler())

        sub_command_group.command(
            'list-subscription',
            aliases={
                f'{self._command_prefix}订阅列表',
                *(f'{x}订阅列表' for x in self._aliases_command_prefix),
            },
            permission=None,
            priority=10,
        ).handle()(self._generate_list_subscription_handler())

        sub_command_group.command(
            'switch-subscription-notice-at-all',
            aliases={
                f'{self._command_prefix}订阅全体通知开关',
                *(f'{x}订阅全体通知开关' for x in self._aliases_command_prefix),
            },
            handlers=[get_command_str_single_arg_parser_handler('switch')],
            priority=10,
        ).got(
            'switch',
            prompt=f'启用或关闭{self._command_prefix}订阅通知@所有人功能:\n【ON/OFF】'
        )(self._generate_switch_subscription_notice_at_all_handler())

        return sub_command_group


__all__ = [
    'SubscriptionHandlerManager',
]
