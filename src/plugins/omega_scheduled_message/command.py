"""
@Author         : Ailitonia
@Date           : 2021/06/22 20:38
@FileName       : schedule_message.py
@Project        : nonebot2_miya
@Description    : 定时消息插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import Sequence

from apscheduler.triggers.cron import CronTrigger
from arclet.alconna import Alconna, AllParam, Args, CommandMeta, MultiVar, Option, Subcommand
from nonebot.log import logger
from nonebot_plugin_alconna import AlconnaMatcher, Match, on_alconna
from nonebot_plugin_alconna.uniseg import Text, UniMessage

from src.params.depends import EVENT_M_IFACE
from src.params.handler import ensure_arg_message, ensure_arg_text
from src.params.permission import check_event_is_admin
from src.service import enable_processor_state
from .helpers import (
    add_schedule_job,
    generate_schedule_job_data,
    get_schedule_message_job_list,
    query_schedule_message_job_value,
    remove_schedule_job_media,
    remove_schedule_message_job,
    restore_schedule_message_job_value,
    set_schedule_message_job,
)

_HANDLER_PROMPT_TIMEOUT: float = 60
"""交互流程等待用户响应超时时间"""
_MAX_READABLE_JOB_NAME_LENGTH: int = 50
"""任务名称最大长度"""


schedule_message_manager = on_alconna(
    Alconna(
        'schedule-message',
        Subcommand(
            'add',
            Option(
                '--name|-n', Args['name?#任务名称', str],
                help_text='为定时消息设置的任务名称',
            ),
            Option(
                '--crontab|-c', Args['crontab?#调度策略', MultiVar(str)],
                help_text='调度的定时任务的crontab表达式, 星期字段0代表周一(APScheduler 语义)',
            ),
            Option(
                '--message|-m', Args['message?#消息内容', AllParam],
                help_text='发送的定时消息内容, 该选项须放在最后, 其后的全部内容均作为消息内容',
            ),
            alias=['新增', '添加', '设置'],
            help_text='新增一个定时消息任务',
        ),
        Subcommand(
            'remove',
            Option('--name|-n', Args['name?#任务名称', str], help_text='将移除定时消息的任务名称'),
            alias=['移除', '删除'],
            help_text='移除一个定时消息任务',
        ),
        Subcommand(
            'list',
            alias=['清单', '列表'],
            help_text='列出当前会话已配置的定时消息任务',
        ),
        meta=CommandMeta(
            description='定时消息任务管理, crontab 星期字段 0 代表周一(APScheduler 语义)',
            usage='/定时消息 <新增|移除|清单> [选项]',
            example='/定时消息 新增 -n 任务名 -c 0 8 * * * -m 消息内容',
            compact=True,
        ),
    ),
    use_cmd_start=True,
    aliases={'定时消息'},
    priority=20,
    block=True,
    default_state=enable_processor_state(
        name='OmegaScheduleMessage',
        level=10,
    ),
)


@schedule_message_manager.assign('$main')
async def handle_default(interface: EVENT_M_IFACE) -> None:
    await interface.finish_reply('定时消息插件, 可用子命令：<新增|移除|清单>, 使用帮助查看详细使用方法')


@schedule_message_manager.assign('add', additional=check_event_is_admin)
async def handle_add_schedule_message(
        matcher: AlconnaMatcher,
        interface: EVENT_M_IFACE,
        name: Match[str],
        crontab: Match[Sequence[str]],
        message: Match,
) -> None:
    readable_job_name = await ensure_arg_text(
        matcher=matcher,
        interface=interface,
        arg=name,
        prompt_text='请输入为定时消息设置的任务名称:',
        timeout=_HANDLER_PROMPT_TIMEOUT,
    )
    if len(readable_job_name) > _MAX_READABLE_JOB_NAME_LENGTH:
        await interface.finish_reply(
            f'设置的定时消息任务名称过长(超过{_MAX_READABLE_JOB_NAME_LENGTH}字), 请修改后重新执行命令'
        )

    crontab_text = ' '.join(crontab.result) if crontab.available else ''
    crontab_arg: Match[str] = Match(crontab_text, bool(crontab_text))
    set_crontab = await ensure_arg_text(
        matcher=matcher,
        interface=interface,
        arg=crontab_arg,
        prompt_text='请输入调度的定时任务的crontab表达式:',
        timeout=_HANDLER_PROMPT_TIMEOUT,
    )
    try:
        CronTrigger.from_crontab(set_crontab)
    except (TypeError, ValueError):
        await interface.finish_reply(f'设置的crontab表达式{set_crontab!r}非法, 请修改后重新执行命令')

    # AllParam 的匹配结果为消息段列表, 包装为 ensure_arg_message 所需的 UniMessage 参数类型
    message_arg: Match[UniMessage] = (
        Match(UniMessage(message.result), True) if message.available else Match(UniMessage(), False)
    )
    set_message = await ensure_arg_message(
        matcher=matcher,
        interface=interface,
        arg=message_arg,
        prompt_text='请输入设置的定时消息内容:',
        timeout=_HANDLER_PROMPT_TIMEOUT,
    )

    try:
        job_data = await generate_schedule_job_data(
            interface=interface,
            readable_job_name=readable_job_name,
            crontab=set_crontab,
            message=set_message,
        )
    except Exception as e:
        logger.error(f'SetScheduleMessage | 处理定时消息数据错误, {e}')
        await interface.finish_reply('处理定时消息数据错误, 请稍后再试或联系管理员处理')

    # 快照覆盖更新前的配置, 供后续失败时回滚; 同名任务不存在时视为全新任务
    is_new_job = False
    previous_value = None
    try:
        previous_value = await query_schedule_message_job_value(
            interface=interface,
            job_unique_id=job_data.job_unique_id,
        )
        is_new_job = previous_value is None
        await set_schedule_message_job(interface=interface, job_data=job_data)
    except Exception as e:
        logger.error(f'SetScheduleMessage | 将定时消息任务({job_data.job_unique_id})写入数据库失败, {e}')
        # 确定为全新任务时清理已下载的媒体文件, 避免残留孤儿目录; 覆盖更新失败时保留旧任务媒体
        if is_new_job:
            remove_schedule_job_media(job_unique_id=job_data.job_unique_id)
        await interface.finish_reply('保存定时消息失败, 请稍后再试或联系管理员处理')

    try:
        add_schedule_job(job_data=job_data)
    except Exception as e:
        logger.error(f'SetScheduleMessage | 添加定时消息任务({job_data.job_unique_id})到调度器失败, {e}')
        # 回滚数据库中的任务配置: 全新任务停用并清理媒体; 覆盖更新恢复旧配置,
        # 此时旧调度任务仍在调度器中且媒体目录仍被旧任务引用, 均不做改动
        try:
            if is_new_job:
                await remove_schedule_message_job(interface=interface, readable_job_name=job_data.readable_job_name)
            else:
                await restore_schedule_message_job_value(
                    interface=interface,
                    job_unique_id=job_data.job_unique_id,
                    value=previous_value,
                )
        except Exception as rollback_e:
            logger.error(f'SetScheduleMessage | 回滚定时消息任务({job_data.job_unique_id})失败, {rollback_e}')
        await interface.finish_reply('设置消息定时任务失败, 请稍后再试或联系管理员处理')

    await interface.finish_reply(f'添加定时消息{job_data.readable_job_name!r}成功!')


@schedule_message_manager.assign('remove', additional=check_event_is_admin)
async def handle_remove_schedule_message(
        matcher: AlconnaMatcher,
        interface: EVENT_M_IFACE,
        name: Match[str],
) -> None:
    readable_job_name = await ensure_arg_text(
        matcher=matcher,
        interface=interface,
        arg=name,
        prompt_text='请输入将要删除的定时消息任务名称:',
        timeout=_HANDLER_PROMPT_TIMEOUT,
    )

    try:
        exist_jobs = await get_schedule_message_job_list(interface=interface)
    except Exception as e:
        logger.error(f'RemoveScheduleMessage | 获取{interface}已配置任务列表失败, {e}')
        await interface.finish_reply('获取已配置任务列表失败, 请稍后再试或联系管理员处理')

    if readable_job_name not in exist_jobs:
        exist_text = '\n'.join(exist_jobs) if exist_jobs else '无已配置的定时消息'
        await interface.finish_reply(
            f'没有名为{readable_job_name!r}定时消息任务, 请确认已配置的定时消息:\n\n{exist_text}')

    try:
        await remove_schedule_message_job(interface=interface, readable_job_name=readable_job_name)
    except Exception as e:
        logger.error(f'RemoveScheduleMessage | 移除定时消息任务({readable_job_name})失败, {e}')
        await interface.finish_reply('移除定时消息任务失败, 请稍后再试或联系管理员处理')

    await interface.finish_reply(f'移除定时消息{readable_job_name!r}成功!')


@schedule_message_manager.assign('list', additional=check_event_is_admin)
async def handle_list_schedule_message(interface: EVENT_M_IFACE) -> None:
    try:
        exist_jobs = await get_schedule_message_job_list(interface=interface)
    except Exception as e:
        logger.error(f'ListScheduleMessage | 获取{interface}已配置任务列表失败, {e}')
        await interface.finish_reply('获取已配置任务列表失败, 请稍后再试或联系管理员处理')

    exist_text = '\n'.join(exist_jobs) if exist_jobs else '无已配置的定时消息'
    await interface.finish_reply(f'当前已配置定时消息任务有:\n\n{exist_text}')


# 注册声明式自检, 启动时解析失败将输出 ERROR 日志
schedule_message_manager.test('schedule-message')
schedule_message_manager.test(
    'schedule-message add --name 测试任务 --crontab 0 8 * * * --message 早上好',
    # 真实运行环境中 AllParam 捕获 UniMessage 的 Text 段
    expected={'name': '测试任务', 'crontab': ('0', '8', '*', '*', '*'), 'message': [Text('早上好')]},
)
schedule_message_manager.test(
    'schedule-message add -n 测试任务 -c 0 8 * * * -m 早上好 各位',
    expected={'name': '测试任务', 'crontab': ('0', '8', '*', '*', '*'), 'message': [Text('早上好 各位')]},
)
schedule_message_manager.test(
    'schedule-message 新增 -n 测试任务 -m 定时消息内容',
    expected={'name': '测试任务', 'message': [Text('定时消息内容')]},
)
schedule_message_manager.test('schedule-message add -n')
schedule_message_manager.test('schedule-message remove --name 测试任务', expected={'name': '测试任务'})
schedule_message_manager.test('schedule-message remove -n 测试任务', expected={'name': '测试任务'})
schedule_message_manager.test('schedule-message 删除 -n 测试任务', expected={'name': '测试任务'})
schedule_message_manager.test('schedule-message list')
schedule_message_manager.test('schedule-message 清单')
schedule_message_manager.test('schedule-message 列表')


__all__ = []
