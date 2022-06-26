"""
@Author         : Ailitonia
@Date           : 2022/04/17 14:20
@FileName       : model.py
@Project        : nonebot2_miya 
@Description    : Processor Tools Models
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pydantic import BaseModel


class OmegaServiceBaseModel(BaseModel):
    """Omega Service Model 基类"""

    class Config:
        extra = 'ignore'
        allow_mutation = False


class OmegaProcessorState(OmegaServiceBaseModel):
    """在插件注册 matcher 时初始化 state, 写入权限、冷却等配置, 用于后续相关 processor 进行处理

    - name: matcher 的自定义名称
    - enable_processor: 是否启用 processor 处理流程
    - level: matcher 需要的权限等级
    - auth_node: matcher 需要的权限节点
    - extra_auth_node: matcher 在运行中可能需要的权限节点, 供授权管理插件配置, 一般作为运行时判断, 不在 processor 阶段进行处理
    - cool_down: matcher 的群组冷却时间, 单位秒
    - user_cool_down_override: matcher 的用户冷却时间倍增系数, 对 cool_down 乘算
    - echo_processor_result: 是否通知用户 processor 权限/冷却等处理结果
    """
    name: str
    enable_processor: bool
    level: int
    auth_node: str | None
    extra_auth_node: set[str]
    cool_down: int
    user_cool_down_override: int
    echo_processor_result: bool


__all__ = [
    'OmegaProcessorState'
]
