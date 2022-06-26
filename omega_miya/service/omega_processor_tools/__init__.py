"""
@Author         : Ailitonia
@Date           : 2022/04/17 14:18
@FileName       : __init__.py.py
@Project        : nonebot2_miya 
@Description    : 插件 processor 配置工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.typing import T_State
from .model import OmegaProcessorState


OMEGA_STATE_KEY: str = '_omega_processor'
"""omega_processor 使用的 state key"""


def init_processor_state(
        name: str,
        enable_processor: bool = True,
        level: int = 4294967296,
        auth_node: str | None = None,
        extra_auth_node: set[str] | None = None,
        cool_down: int = 0,
        user_cool_down_override: int = 1,
        echo_processor_result: bool = True
) -> T_State:
    """matcher state 初始化函数, 用于声明当前 matcher 权限及冷却等信息, 用于 processor 集中处理

    :param name: matcher 的自定义名称, 用于识别 matcher
    :param enable_processor: matcher 是否启用 processor 处理流程
    :param level: matcher 需要的权限等级
    :param auth_node: matcher 需要的权限节点名称
    :param extra_auth_node: matcher 在运行中可能需要的权限节点, 供授权管理插件配置, 一般作为运行时判断, 不在 processor 阶段进行处理
    :param cool_down: matcher 需要的群组冷却时间配置, 单位秒
    :param user_cool_down_override: matcher 需要的用户冷却时间倍增系数, 对 cool_down 乘算
    :param echo_processor_result: 是否需要通知用户权限/冷却等处理结果
    """
    extra_auth_node = set() if extra_auth_node is None else extra_auth_node
    state_model = OmegaProcessorState(
        name=name,
        enable_processor=enable_processor,
        level=level,
        auth_node=auth_node,
        extra_auth_node=extra_auth_node,
        cool_down=cool_down,
        user_cool_down_override=user_cool_down_override,
        echo_processor_result=echo_processor_result
    )

    return {OMEGA_STATE_KEY: state_model.dict()}


def parse_processor_state(state: T_State) -> OmegaProcessorState:
    """从 state 中解析 processor 配置信息"""
    state_data = state.get(OMEGA_STATE_KEY, None)
    if state_data is None:
        processor_state = OmegaProcessorState(
            name='', enable_processor=False, level=0, auth_node='', extra_auth_node=set(), cool_down=0,
            user_cool_down_override=0, echo_processor_result=False)
    else:
        processor_state = OmegaProcessorState.parse_obj(state_data)
    return processor_state


__all__ = [
    'OMEGA_STATE_KEY',
    'init_processor_state',
    'parse_processor_state'
]
