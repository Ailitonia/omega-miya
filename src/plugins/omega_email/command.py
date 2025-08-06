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
from typing import Annotated

from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.params import ArgStr, Depends
from nonebot.permission import SUPERUSER
from nonebot.plugin import CommandGroup
from nonebot.rule import to_me

from src.params.handler import get_command_str_multi_args_parser_handler, get_command_str_single_arg_parser_handler
from src.service import OmegaMatcherInterface as OmMI
from src.service import OmegaMessageSegment, enable_processor_state
from .helpers import (
    bind_entity_mailbox,
    check_mailbox,
    decrypt_password,
    encrypt_password,
    generate_mail_snapshot,
    get_entity_bound_mailbox,
    get_unseen_mail_data,
    query_available_mailbox,
    save_mailbox,
    unbind_entity_mailbox,
)

mailbox_manager = CommandGroup(
    'mailbox-manager',
    rule=to_me(),
    permission=SUPERUSER,
    priority=10,
    block=True,
    state=enable_processor_state(name='MailboxManager', enable_processor=False),
)

add_mail_box = mailbox_manager.command(
    'add',
    aliases={'添加邮箱', '新增邮箱'},
    handlers=[get_command_str_multi_args_parser_handler('add_mailbox_arg')]
)


@add_mail_box.got('add_mailbox_arg_0', prompt='请输入邮箱IMAP服务器地址:')
@add_mail_box.got('add_mailbox_arg_1', prompt='请输入邮箱地址:')
@add_mail_box.got('add_mailbox_arg_2', prompt='请输入邮箱密码:')
async def handle_add_mailbox(
        matcher: Matcher,
        server_host: Annotated[str, ArgStr('add_mailbox_arg_0')],
        address: Annotated[str, ArgStr('add_mailbox_arg_1')],
        password: Annotated[str, ArgStr('add_mailbox_arg_2')],
) -> None:
    server_host = server_host.strip()
    address = address.strip()
    password = password.strip()

    if not await check_mailbox(address=address, server_host=server_host, password=password):
        logger.error(f'EmailBoxManager | 添加邮箱: {address} 失败, 邮箱验证不通过')
        await matcher.finish('验证邮箱信息失败, 请检查邮箱信息或稍后再试')

    try:
        password = await encrypt_password(plaintext=password)
        await save_mailbox(address=address, server_host=server_host, password=password, protocol='imap', port=993)
        logger.success(f'EmailBoxManager | 添加邮箱: {address} 成功')
        await matcher.send(f'添加邮箱 {address} 成功')
    except Exception as e:
        logger.error(f'EmailBoxManager | 添加邮箱: {address} 失败, 数据库写入失败, {e}')
        await matcher.send('添加邮箱失败, 数据库写入失败, 详情请查看日志')


@mailbox_manager.command(
    'bind',
    aliases={'绑定邮箱'},
    handlers=[get_command_str_single_arg_parser_handler('mailbox_address', ensure_key=True)]
).got('mailbox_address', prompt='请输入需要绑定的邮箱地址:')
async def handle_bind_mailbox(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        mailbox_address: Annotated[str | None, ArgStr('mailbox_address')],
) -> None:
    try:
        available_mailbox = await query_available_mailbox()
    except Exception as e:
        logger.error(f'EmailBoxManager | 查询可用邮箱失败, {e}')
        await interface.finish_reply('查询可用邮箱失败, 详情请查看日志')

    if not available_mailbox:
        await interface.finish_reply('无可绑定邮箱, 请联系管理员添加邮箱后再试')

    if mailbox_address is None or not mailbox_address.strip():
        mailbox_msg = '\n'.join(x.address for x in available_mailbox)
        await interface.reject_reply(f'请输入需要绑定的邮箱地址:\n\n{mailbox_msg}')

    available_mailbox_map = {x.address: x for x in available_mailbox}
    mailbox_address = mailbox_address.strip()
    if mailbox_address not in available_mailbox_map.keys():
        await interface.finish_reply(f'{mailbox_address} 不是可用的邮箱地址, 请确认后重试或请管理员添加该邮箱')

    try:
        await bind_entity_mailbox(interface=interface, mailbox_account=available_mailbox_map[mailbox_address])
        await interface.entity.commit_session()
        logger.success(f'EmailBoxManager | 绑定邮箱: {mailbox_address} 成功')
        await interface.send_reply(f'绑定邮箱 {mailbox_address} 成功')
    except Exception as e:
        logger.error(f'EmailBoxManager | 绑定邮箱: {mailbox_address} 失败, {e}')
        await interface.send_reply(f'绑定邮箱 {mailbox_address} 失败, 详情请查看日志')


@mailbox_manager.command(
    'unbind',
    aliases={'解绑邮箱'},
    handlers=[get_command_str_single_arg_parser_handler('mailbox_address', ensure_key=True)]
).got('mailbox_address', prompt='请输入需要解绑的邮箱地址:')
async def handle_unbind_mailbox(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        mailbox_address: Annotated[str | None, ArgStr('mailbox_address')],
) -> None:
    try:
        bound_mailbox = await get_entity_bound_mailbox(interface=interface)
    except Exception as e:
        logger.error(f'EmailBoxManager | 查询已绑定邮箱失败, {e}')
        await interface.finish_reply('查询已绑定邮箱失败, 详情请查看日志')

    if not bound_mailbox:
        await interface.finish_reply('无已绑定邮箱, 无需解绑')

    if mailbox_address is None or not mailbox_address.strip():
        mailbox_msg = '\n'.join(x.address for x in bound_mailbox)
        await interface.reject_reply(f'请输入需要解绑的邮箱地址:\n\n{mailbox_msg}')

    bound_mailbox_map = {x.address: x for x in bound_mailbox}
    mailbox_address = mailbox_address.strip()
    if mailbox_address not in bound_mailbox_map.keys():
        await interface.finish_reply(f'{mailbox_address} 不是已绑定的邮箱地址, 请确认后重试')

    try:
        await unbind_entity_mailbox(interface=interface, mailbox_address=mailbox_address)
        await interface.entity.commit_session()
        logger.success(f'EmailBoxManager | 解绑邮箱: {mailbox_address} 成功')
        await interface.send_reply(f'解绑邮箱 {mailbox_address} 成功')
    except Exception as e:
        logger.error(f'EmailBoxManager | 解绑邮箱: {mailbox_address} 失败, {e}')
        await interface.send_reply(f'解绑邮箱 {mailbox_address} 失败, 详情请查看日志')


@mailbox_manager.command(
    'receive',
    aliases={'收邮件'},
    rule=None,
    permission=None,
    state=enable_processor_state(name='ReceiveEmail', level=10),
).handle()
async def handle_receive_email(interface: Annotated[OmMI, Depends(OmMI.depend())]) -> None:
    try:
        bound_mailbox = await get_entity_bound_mailbox(interface=interface)
    except Exception as e:
        logger.error(f'ReceiveEmail | 查询已绑定邮箱失败, {e}')
        await interface.finish_reply('查询已绑定邮箱失败, 请稍后重试或联系管理员处理')

    if not bound_mailbox:
        logger.warning('ReceiveEmail | 收邮件结束, 没有绑定的邮箱')
        await interface.finish_reply('没有绑定的邮箱, 请先联系管理员绑定邮箱后再收件')

    bound_mailbox_msg = '\n'.join(x.address for x in bound_mailbox)
    await interface.send_reply(f'已绑定邮箱:\n\n{bound_mailbox_msg}\n\n正在连接到邮箱服务器, 请稍候~')

    for mailbox in bound_mailbox:
        # 解密密码
        try:
            password = await decrypt_password(ciphertext=mailbox.server.password)
        except Exception as e:
            logger.error(f'ReceiveEmail | 邮箱 {mailbox.address} 密码验证失败, {e}')
            await interface.send_reply(f'邮箱: {mailbox.address}\n密码验证失败, 请联系管理员处理')
            continue

        # 接收邮件内容
        try:
            unseen_mail = await get_unseen_mail_data(
                address=mailbox.address, server_host=mailbox.server.server_host, password=password
            )
        except Exception as e:
            logger.error(f'ReceiveEmail | 邮箱 {mailbox.address} 收件失败, {e}')
            await interface.send_reply(f'邮箱: {mailbox.address}\n收件失败, 请稍后重试或联系管理员处理')
            continue

        if not unseen_mail:
            logger.success(f'ReceiveEmail | 邮箱 {mailbox.address} 收件完成, 没有新的邮件')
            await interface.send_reply(f'邮箱: {mailbox.address}\n收件完成, 没有新的邮件')
            continue

        for mail in unseen_mail:
            try:
                content = mail.html if mail.html else mail.body
                content = re.sub(r'(\n|&nbsp;){2,}', '\n', content)
                mail_content = f"【{mail.header}】\n时间: {mail.date}\n发件人: {mail.sender}\n{'=' * 16}\n{content}"
                mail_img = await generate_mail_snapshot(mail_content=mail_content)
                await interface.send_reply(OmegaMessageSegment.image(await mail_img.get_hosting_path()))
            except Exception as e:
                logger.error(f'ReceiveEmail | 转换或发送已收邮件失败, {e}')
                continue

        logger.success(f'ReceiveEmail | 邮箱 {mailbox.address} 收件完成, 共{len(unseen_mail)}封新的邮件')
        await interface.send_reply(f'邮箱 {mailbox.address}\n收件完成, 共{len(unseen_mail)}封新的邮件')


__all__ = []
