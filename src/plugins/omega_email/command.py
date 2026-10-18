"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : omega_email.py
@Project        : nonebot2_miya
@Description    : Omega 邮箱插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import re

from arclet.alconna import Alconna, Args, CommandMeta, Option, Subcommand
from nonebot.log import logger
from nonebot.rule import to_me
from nonebot_plugin_alconna import AlconnaMatcher, Match, on_alconna
from nonebot_plugin_alconna.uniseg import UniMessage

from src.params.depends import EVENT_M_IFACE
from src.params.handler import ensure_arg_text
from src.params.message_builder import build_sendable_image
from src.params.permission import check_event_is_admin, check_event_is_superuser
from src.service import enable_processor_state
from .helpers import (
    bind_entity_mailbox,
    check_mailbox,
    generate_mail_snapshot,
    get_unseen_mail_data,
    is_valid_email_address,
    load_mailbox_from_database,
    query_available_mailbox_address,
    query_entity_bound_mailbox,
    save_mailbox_into_database,
    unbind_entity_mailbox,
)

_HANDLER_PROMPT_TIMEOUT: float = 60
"""交互流程等待用户响应超时时间"""


mailbox_manager = on_alconna(
    Alconna(
        'mailbox',
        Subcommand(
            'add',
            Option('--server|-s', Args['server#服务器地址', str], help_text='邮箱IMAP服务器地址'),
            Option('--address|-a', Args['address#邮箱地址', str], help_text='邮箱地址'),
            Option('--password|-p', Args['password#邮箱密码', str], help_text='邮箱密码'),
            alias=['新增', '添加'],
            help_text='新增邮箱账号',
        ),
        Subcommand(
            'bind',
            Option('--address|-a', Args['address#邮箱地址', str], help_text='邮箱地址'),
            alias=['绑定'],
            help_text='为当前会话绑定已有邮箱账号',
        ),
        Subcommand(
            'unbind',
            Option('--address|-a', Args['address#邮箱地址', str], help_text='邮箱地址'),
            alias=['解绑', '取消绑定'],
            help_text='为当前会话解绑已绑定的邮箱账号',
        ),
        Subcommand(
            'receive',
            alias=['收件', '收邮件'],
            help_text='检查当前会话已绑定的邮箱账号并收取未读邮件',
        ),
        meta=CommandMeta(
            description='邮箱管理与邮件收取',
            usage='mailbox <add|bind|unbind|receive> [参数] [选项]',
            example='mailbox bind --address test@example.com',
            compact=True,
        ),
    ),
    rule=to_me(),
    use_cmd_start=True,
    aliases={'邮箱'},
    priority=10,
    block=True,
    default_state=enable_processor_state(
        name='OmegaMailboxManager',
        level=10,
    ),
)


@mailbox_manager.assign('add', additional=check_event_is_superuser)
async def handle_add_mailbox(
        matcher: AlconnaMatcher,
        interface: EVENT_M_IFACE,
        server: Match[str],
        address: Match[str],
        password: Match[str],
) -> None:
    target_server = await ensure_arg_text(
        matcher=matcher,
        interface=interface,
        arg=server,
        prompt_text='请输入邮箱IMAP服务器地址:',
        timeout=_HANDLER_PROMPT_TIMEOUT,
    )

    target_address = await ensure_arg_text(
        matcher=matcher,
        interface=interface,
        arg=address,
        prompt_text='请输入邮箱地址:',
        timeout=_HANDLER_PROMPT_TIMEOUT,
    )
    if not is_valid_email_address(target_address):
        await interface.finish_reply('输入的不是有效的邮箱地址, 请确认后重试')

    target_password = await ensure_arg_text(
        matcher=matcher,
        interface=interface,
        arg=password,
        prompt_text='【警告】在会话中添加邮箱可能导致账号信息泄露, 强烈建议使用内置工具在命令行导入\n\n请输入邮箱密码:',
        timeout=_HANDLER_PROMPT_TIMEOUT,
    )

    if not await check_mailbox(address=target_address, server_host=target_server, password=target_password):
        logger.error(f'EmailBoxManager | 添加邮箱: {target_address} 失败, 邮箱验证未通过')
        await interface.finish_reply('验证邮箱信息失败, 请检查邮箱信息或稍后再试')

    try:
        await save_mailbox_into_database(
            address=target_address,
            server_host=target_server,
            password=target_password,
            protocol='imap',
            port=993,
        )
        logger.success(f'EmailBoxManager | 添加邮箱: {target_address} 成功')
        await interface.send_reply(f'添加邮箱 {target_address} 成功')
    except Exception as e:
        logger.error(f'EmailBoxManager | 添加邮箱: {target_address} 失败, 数据库写入失败, {e}')
        await interface.send_reply('添加邮箱失败, 数据库写入失败, 详情请查看日志')


@mailbox_manager.assign('bind', additional=check_event_is_admin)
async def handle_bind_mailbox(
        matcher: AlconnaMatcher,
        interface: EVENT_M_IFACE,
        address: Match[str],
) -> None:
    try:
        available_mailbox = await query_available_mailbox_address()
    except Exception as e:
        logger.error(f'EmailBoxManager | 查询可用邮箱失败, {e}')
        await interface.finish_reply('查询可用邮箱失败, 详情请查看日志')

    if not available_mailbox:
        await interface.finish_reply('无可绑定邮箱, 请联系管理员添加邮箱后再试')

    target_address = await ensure_arg_text(
        matcher=matcher,
        interface=interface,
        arg=address,
        prompt_text=f'请输入需要绑定的邮箱地址:\n\n{"\n".join(available_mailbox)}',
        timeout=_HANDLER_PROMPT_TIMEOUT,
    )

    if not is_valid_email_address(target_address):
        await interface.finish_reply('输入的不是有效的邮箱地址, 请确认后重试')

    if target_address not in available_mailbox:
        await interface.finish_reply(f'{target_address} 不是可用的邮箱地址, 请确认后重试或请管理员添加该邮箱')

    try:
        await bind_entity_mailbox(interface=interface, mailbox_address=target_address)
        logger.success(f'EmailBoxManager | 绑定邮箱: {target_address} 成功')
        await interface.send_reply(f'绑定邮箱 {target_address} 成功')
    except Exception as e:
        logger.error(f'EmailBoxManager | 绑定邮箱: {target_address} 失败, {e}')
        await interface.send_reply(f'绑定邮箱 {target_address} 失败, 请稍后再试或联系管理员处理')


@mailbox_manager.assign('unbind', additional=check_event_is_admin)
async def handle_unbind_mailbox(
        matcher: AlconnaMatcher,
        interface: EVENT_M_IFACE,
        address: Match[str],
) -> None:
    try:
        bound_mailbox = await query_entity_bound_mailbox(interface=interface)
    except Exception as e:
        logger.error(f'EmailBoxManager | 查询已绑定邮箱失败, {e}')
        await interface.finish_reply('查询已绑定邮箱失败, 详情请查看日志')

    if not bound_mailbox:
        await interface.finish_reply('无已绑定邮箱, 无需解绑')

    target_address = await ensure_arg_text(
        matcher=matcher,
        interface=interface,
        arg=address,
        prompt_text=f'请输入需要解绑的邮箱地址:\n\n{"\n".join(bound_mailbox)}',
        timeout=_HANDLER_PROMPT_TIMEOUT,
    )

    if not is_valid_email_address(target_address):
        await interface.finish_reply('输入的不是有效的邮箱地址, 请确认后重试')

    if target_address not in bound_mailbox:
        await interface.finish_reply(f'{target_address} 不是已绑定的邮箱地址, 请确认后重试')

    try:
        await unbind_entity_mailbox(interface=interface, mailbox_address=target_address)
        logger.success(f'EmailBoxManager | 解绑邮箱: {target_address} 成功')
        await interface.send_reply(f'解绑邮箱 {target_address} 成功')
    except Exception as e:
        logger.error(f'EmailBoxManager | 解绑邮箱: {target_address} 失败, {e}')
        await interface.send_reply(f'解绑邮箱 {target_address} 失败, 请稍后再试或联系管理员处理')


@mailbox_manager.assign('receive')
async def handle_receive_email(interface: EVENT_M_IFACE) -> None:
    try:
        bound_mailbox = await query_entity_bound_mailbox(interface=interface)
    except Exception as e:
        logger.error(f'ReceiveEmail | 查询已绑定邮箱失败, {e}')
        await interface.finish_reply('查询已绑定邮箱失败, 请稍后重试或联系管理员处理')

    if not bound_mailbox:
        logger.warning('ReceiveEmail | 收邮件结束, 没有绑定的邮箱')
        await interface.finish_reply('没有绑定的邮箱, 请先联系管理员绑定邮箱后再收件')

    await interface.send_reply(f'已绑定邮箱:\n\n{"\n".join(bound_mailbox)}\n\n正在连接到邮箱服务器, 请稍候~')

    for mailbox_address in bound_mailbox:
        # 读取并解密邮箱账号, 读取失败(含旧版本数据不可解)时返回 None
        mailbox_account = await load_mailbox_from_database(mailbox_address=mailbox_address)
        if mailbox_account is None:
            logger.error(f'ReceiveEmail | 邮箱 {mailbox_address} 账号读取失败, 已跳过')
            await interface.send_reply(f'邮箱: {mailbox_address}\n账号读取失败, 可能需管理员重新导入, 已跳过')
            continue

        # 接收邮件内容
        try:
            unseen_mail = await get_unseen_mail_data(
                address=mailbox_account.address,
                server_host=mailbox_account.server.server_host,
                password=mailbox_account.server.password,
            )
        except Exception as e:
            logger.error(f'ReceiveEmail | 邮箱 {mailbox_address} 收件失败, {e}')
            await interface.send_reply(f'邮箱: {mailbox_address}\n收件失败, 请稍后重试或联系管理员处理')
            continue

        if not unseen_mail:
            logger.success(f'ReceiveEmail | 邮箱 {mailbox_address} 收件完成, 没有新的邮件')
            await interface.send_reply(f'邮箱: {mailbox_address}\n收件完成, 没有新的邮件')
            continue

        for mail in unseen_mail:
            try:
                content = mail.html if mail.html else mail.body
                content = re.sub(r'(\n|&nbsp;){2,}', '\n', content)
                mail_content = f"【{mail.header}】\n时间: {mail.date}\n发件人: {mail.sender}\n{'=' * 16}\n{content}"
                mail_img = await generate_mail_snapshot(mail_content=mail_content)
                await interface.send_reply(UniMessage(build_sendable_image(await mail_img.get_hosting_path())))
            except Exception as e:
                logger.error(f'ReceiveEmail | 转换或发送已收邮件失败, {e}')
                continue

        logger.success(f'ReceiveEmail | 邮箱 {mailbox_address} 收件完成, 共{len(unseen_mail)}封新的邮件')
        await interface.send_reply(f'邮箱 {mailbox_address}\n收件完成, 共{len(unseen_mail)}封新的邮件')


__all__ = []
