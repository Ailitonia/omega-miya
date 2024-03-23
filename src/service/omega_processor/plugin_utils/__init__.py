"""
@Author         : Ailitonia
@Date           : 2023/3/19 16:18
@FileName       : plugin_utils
@Project        : nonebot2_miya
@Description    : 插件 processor 引入工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.typing import T_State
from pydantic import BaseModel, ConfigDict
from typing import Literal, Optional


__OMEGA_STATE_KEY: str = '_omega_processor'
"""omega_processor 使用的 state key"""


class OmegaServiceBaseModel(BaseModel):
    """Omega Service Model 基类"""

    model_config = ConfigDict(extra='ignore', frozen=True)


class OmegaProcessorState(OmegaServiceBaseModel):
    """在插件注册 matcher 时初始化 state, 写入权限、冷却等配置, 用于后续相关 processor 进行处理

    - name: matcher 的自定义名称
    - enable_processor: 是否启用 processor 处理流程
    - level: matcher 需要的权限等级
    - auth_node: matcher 需要的权限节点
    - extra_auth_node: matcher 在运行中可能需要的权限节点, 供授权管理插件配置, 一般作为运行时判断, 不在 processor 阶段进行处理
    - cooldown: matcher 冷却时间配置, 单位秒
    - cooldown_type: matcher 冷却类型, plugin: 插件冷却, event: 事件独立冷却, user: 用户独立冷却
    - cost: 使用 matcher 所需消耗的费用
    - echo_processor_result: 是否通知用户 processor 权限/冷却/消耗等处理结果
    """
    name: str
    enable_processor: bool
    level: int
    auth_node: str
    extra_auth_node: set[str]
    cooldown: int
    cooldown_type: Literal['event', 'user']
    cost: float
    echo_processor_result: bool


def enable_processor_state(
        name: str,
        enable_processor: bool = True,
        *,
        level: int = 2**31-1,
        auth_node: Optional[str] = None,
        extra_auth_node: Optional[set[str]] = None,
        cooldown: int = 0,
        cooldown_type: Literal['event', 'user'] = 'event',
        cost: float = 0,
        echo_processor_result: bool = True
) -> T_State:
    """matcher state 初始化函数, 用于声明当前 matcher 权限及冷却等信息, 用于 processor 集中处理

    :param name: matcher 的自定义名称, 用于识别 matcher
    :param enable_processor: matcher 是否启用 processor 处理流程
    :param level: matcher 需要的权限等级
    :param auth_node: matcher 需要的权限节点名称
    :param extra_auth_node: matcher 在运行中可能需要的权限节点, 供授权管理插件配置, 一般作为运行时判断, 不在 processor 阶段进行处理
    :param cooldown: matcher 冷却时间配置, 单位秒
    :param cooldown_type: matcher 冷却类型, event: 事件独立冷却, user: 用户独立冷却
    :param cost: 使用 matcher 所需消耗的费用
    :param echo_processor_result: 是否需要通知用户权限/冷却等处理结果
    """
    auth_node = name if auth_node is None else auth_node
    extra_auth_node = set() if extra_auth_node is None else extra_auth_node
    cooldown = 0 if cooldown < 0 else cooldown
    cost = 0 if cost < 0 else cost

    state_model = OmegaProcessorState(
        name=name,
        enable_processor=enable_processor,
        level=level,
        auth_node=auth_node,
        extra_auth_node=extra_auth_node,
        cooldown=cooldown,
        cooldown_type=cooldown_type,
        cost=cost,
        echo_processor_result=echo_processor_result
    )
    return {__OMEGA_STATE_KEY: state_model.dict()}


def parse_processor_state(state: T_State) -> OmegaProcessorState:
    """从 state 中解析 processor 配置信息"""
    state_data = state.get(__OMEGA_STATE_KEY, None)
    if state_data is None:
        processor_state = OmegaProcessorState(
            name='',
            enable_processor=False,
            level=0,
            auth_node='',
            extra_auth_node=set(),
            cooldown=0,
            cooldown_type='event',
            cost=0,
            echo_processor_result=False
        )
    else:
        processor_state = OmegaProcessorState.parse_obj(state_data)
    return processor_state


__all__ = [
    'enable_processor_state',
    'parse_processor_state'
]
