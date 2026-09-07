"""
@Author         : Ailitonia
@Date           : 2021/07/09 19:49
@FileName       : omega_processor
@Project        : nonebot2_miya
@Description    : Omega 基础服务, 统一流程处理, 包括插件、冷却、权限、统计等
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from . import universal as universal  # noqa: F401, I001 通用处理模块优先导入

enable_processor_state = universal.enable_processor_state


__all__ = [
    'enable_processor_state',
]
