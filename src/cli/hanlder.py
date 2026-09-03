"""
@Author         : Ailitonia
@Date           : 2026/8/21 22:20
@FileName       : hanlder
@Project        : omega-miya
@Description    : 命令分发及处理函数
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .command import CliQueryArguments


def _parse_tool_target(target: str) -> tuple[str, str]:
    """解析工具执行目标, 格式为 ``module[:func]``, 模块名支持点分层级, 函数名省略时默认为 ``main``

    返回限定在 tools 包命名空间内的完整模块路径与入口函数名
    """
    module_part, sep, func_name = target.rpartition(':')
    if not sep:
        module_part, func_name = target, 'main'

    if not module_part or any(not segment.isidentifier() for segment in module_part.split('.')):
        raise ValueError(f'invalid tool target module name: {target!r}')
    if not func_name.isidentifier():
        raise ValueError(f'invalid tool target function name: {target!r}')

    return f'tools.{module_part}', func_name


def run_bot(_: 'CliQueryArguments') -> None:
    """启动入口"""
    import nonebot
    from nonebot.log import default_format, logger

    from src.resource import LogFileResource

    # Config log file
    log_params = {
        'rotation': '00:00',
        'diagnose': False,
        'format': default_format,
        'encoding': 'utf-8',
    }
    log_path = LogFileResource()
    logger.add(log_path.info, level='INFO', **log_params)
    logger.add(log_path.error, level='ERROR', **log_params)

    # Initialize nonebot
    nonebot.init()
    driver = nonebot.get_driver()

    # 按需注册 OneBot V11 Adapter
    if driver.config.model_dump().get('onebot_access_token'):
        from nonebot.adapters.onebot.v11.adapter import Adapter as OneBotAdapter
        driver.register_adapter(OneBotAdapter)

    # 按需注册 QQ Adapter
    if driver.config.model_dump().get('qq_bots'):
        from nonebot.adapters.qq.adapter import Adapter as QQAdapter
        driver.register_adapter(QQAdapter)

    # 按需注册 Telegram Adapter
    if driver.config.model_dump().get('telegram_bots'):
        from nonebot.adapters.telegram.adapter import Adapter as TelegramAdapter
        driver.register_adapter(TelegramAdapter)

    # 按需注册 Console Adapter
    if driver.config.model_dump().get('enable_console'):
        from nonebot.adapters.console import Adapter as ConsoleAdapter
        driver.register_adapter(ConsoleAdapter)

    # 加载插件
    nonebot.load_plugins('src/service')
    nonebot.load_plugins('src/plugins')

    # 拉起驱动, 开始启动流程
    nonebot.run()


def run_tool_execute(args: 'CliQueryArguments') -> None:
    """执行 tools/ 下的工具模块入口函数"""
    if not args.tool_execute:
        raise ValueError('not provide tool target argument')

    module_path, func_name = _parse_tool_target(args.tool_execute)

    import asyncio
    import importlib
    import inspect

    import nonebot
    from nonebot.log import default_format, logger
    from nonebot.utils import run_sync

    from src.resource import LogFileResource

    log_path = LogFileResource()
    logger.add(log_path.debug, level='DEBUG', format=default_format, encoding='utf-8')

    # Initialize nonebot
    nonebot.init()

    # 导入目标工具模块, 仅当目标模块本身缺失时转换为友好的错误提示, 工具内部的依赖缺失则原样抛出
    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as e:
        if e.name is not None and (e.name == module_path or module_path.startswith(f'{e.name}.')):
            raise ValueError(f'tool module not found: {module_path}') from e
        raise

    func = getattr(module, func_name, None)
    if func is None:
        raise ValueError(f'tool function not found: {module_path}:{func_name}')
    if not inspect.isfunction(func):
        raise TypeError(f'tool target is not function: {module_path}:{func_name}')

    logger.info(f'Executing tool: {module_path}:{func_name}')

    # 执行入口函数, 兼容同步与异步入口
    if inspect.iscoroutinefunction(func):
        asyncio.run(func())
    else:
        @run_sync
        def _wrapped_func():
            func()

        asyncio.run(_wrapped_func())


def run_database_check(_: 'CliQueryArguments') -> None:
    """执行检查数据库版本"""
    import nonebot
    from nonebot.log import default_format, logger

    from src.resource import LogFileResource

    log_path = LogFileResource()
    logger.add(log_path.debug, level='DEBUG', format=default_format, encoding='utf-8')

    # Initialize nonebot
    nonebot.init()

    # 执行 alembic current/check
    from src.database.migrate import run_check_current
    run_check_current()


def run_database_upgrade_to_head(_: 'CliQueryArguments') -> None:
    """执行升级数据库到最新"""
    import nonebot
    from nonebot.log import default_format, logger

    from src.resource import LogFileResource

    log_path = LogFileResource()
    logger.add(log_path.debug, level='DEBUG', format=default_format, encoding='utf-8')

    # Initialize nonebot
    nonebot.init()

    # 执行数据库升级
    from src.database.migrate import run_upgrade_migrations
    run_upgrade_migrations(revision='head')


def run_database_upgrade(args: 'CliQueryArguments') -> None:
    """执行升级数据库到目标版本"""
    if not args.database_upgrade:
        raise ValueError('not provide upgrade target version argument')

    import nonebot
    from nonebot.log import default_format, logger

    from src.resource import LogFileResource

    log_path = LogFileResource()
    logger.add(log_path.debug, level='DEBUG', format=default_format, encoding='utf-8')

    # Initialize nonebot
    nonebot.init()

    # 执行数据库升级
    from src.database.migrate import run_upgrade_migrations
    run_upgrade_migrations(revision=args.database_upgrade)


def run_database_downgrade(args: 'CliQueryArguments') -> None:
    """执行降级数据库到目标版本"""
    if not args.database_downgrade:
        raise ValueError('not provide downgrade target version argument')

    import nonebot
    from nonebot.log import default_format, logger

    from src.resource import LogFileResource

    log_path = LogFileResource()
    logger.add(log_path.debug, level='DEBUG', format=default_format, encoding='utf-8')

    # Initialize nonebot
    nonebot.init()

    # 执行数据库降级
    from src.database.migrate import run_downgrade_migrations
    run_downgrade_migrations(revision=args.database_downgrade)


def run_database_revision(args: 'CliQueryArguments') -> None:
    """执行生成数据库迁移版本"""
    if not args.database_revision:
        raise ValueError('not provide version message')

    import nonebot
    from nonebot.log import default_format, logger

    from src.resource import LogFileResource

    log_path = LogFileResource()
    logger.add(log_path.debug, level='DEBUG', format=default_format, encoding='utf-8')

    # Initialize nonebot
    nonebot.init()

    # 执行生成数据库迁移版本
    from src.database.migrate import run_revision
    run_revision(message=args.database_revision)


def run_database_stamp(args: 'CliQueryArguments') -> None:
    """执行标记数据库版本"""
    if not args.database_stamp:
        raise ValueError('not provide revision_id')

    import nonebot
    from nonebot.log import default_format, logger

    from src.resource import LogFileResource

    log_path = LogFileResource()
    logger.add(log_path.debug, level='DEBUG', format=default_format, encoding='utf-8')

    # Initialize nonebot
    nonebot.init()

    # 执行标记数据库版本
    from src.database.migrate import run_stamp
    run_stamp(revision_id=args.database_stamp)


__all__ = [
    'run_bot',
    'run_database_check',
    'run_database_downgrade',
    'run_database_revision',
    'run_database_stamp',
    'run_database_upgrade',
    'run_database_upgrade_to_head',
    'run_tool_execute',
]
