import re
from nonebot import CommandGroup, logger
from nonebot.rule import to_me
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.params import CommandArg, ArgStr

from omega_miya.database import EventEntityHelper, EmailBox
from omega_miya.service import init_processor_state
from omega_miya.service.gocqhttp_guild_patch.permission import GUILD
from omega_miya.utils.process_utils import run_async_catching_exception
from omega_miya.utils.text_utils import TextUtils

from .utils import check_mailbox, get_unseen_mail_data, encrypt_password, decrypt_password


# Custom plugin usage text
__plugin_custom_name__ = '收邮件'
__plugin_usage__ = r'''【OmegaEmail 邮箱插件】
主要是用来收验证码OvO
仅限群聊使用

用法:
/收邮件

管理员命令:
/添加邮箱
/绑定邮箱
/解绑邮箱'''


# 注册事件响应器
EmailBoxManager = CommandGroup(
    'EmailBoxManager',
    rule=to_me(),
    state=init_processor_state(name='EmailBoxManager', enable_processor=False),
    permission=SUPERUSER,
    priority=10,
    block=True
)

add_mail_box = EmailBoxManager.command('add', aliases={'添加邮箱'})


@add_mail_box.got('server_host', prompt='请输入IMAP服务器地址:')
@add_mail_box.got('address', prompt='请输入邮箱地址:')
@add_mail_box.got('password', prompt='请输入邮箱密码:')
async def handle_admin_mail_add(
        matcher: Matcher,
        address: str = ArgStr('address'),
        server_host: str = ArgStr('server_host'),
        password: str = ArgStr('password')
):
    address = address.strip()
    server_host = server_host.strip()
    password = password.strip()

    check_result = await check_mailbox(address=address, server_host=server_host, password=password)
    if isinstance(check_result, Exception) or not check_result:
        logger.warning(f'EmailBoxManager | 添加邮箱: {address} 失败, 邮箱验证不通过, {check_result}')
        await matcher.finish('验证邮箱失败了QAQ, 请检查邮箱信息或稍后再试')

    # 对密码加密保存
    password = encrypt_password(plaintext=password)
    add_result = await run_async_catching_exception(EmailBox(address=address).add_upgrade_unique_self)(
        server_host=server_host, password=password)

    if isinstance(add_result, Exception) or add_result.error:
        logger.error(f'EmailBoxManager | 添加邮箱: {address} 失败, 数据库写入失败, {add_result}')
        await matcher.finish('添加邮箱失败, 详情请查看日志')
    else:
        logger.success(f'EmailBoxManager | 添加邮箱: {address} 成功')
        await matcher.finish('添加邮箱成功')


bind_mail_box = EmailBoxManager.command('bind', aliases={'绑定邮箱'})


@bind_mail_box.handle()
async def handle_parse_email_address(matcher: Matcher, state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    address = cmd_arg.extract_plain_text().strip()
    if address:
        state.update({'address': address})
    else:
        mail_box_result = await run_async_catching_exception(EmailBox.query_all)()
        if isinstance(mail_box_result, Exception) or mail_box_result.error:
            logger.error(f'EmailBoxManager | 查询可用邮箱失败, {mail_box_result}')
            await matcher.finish('查询可用邮箱失败, 详情请查看日志')
        elif not mail_box_result.result:
            await matcher.finish('无可绑定邮箱, 请先添加邮箱!')
        else:
            mailbox_msg = '\n'.join(x.address for x in mail_box_result.result)
            msg = f'当前可绑定邮箱:\n\n{mailbox_msg}'
            await matcher.send(msg)


@bind_mail_box.got('address', prompt='请输入需要绑定的邮箱地址:')
async def handle_bind_mail(bot: Bot, matcher: Matcher, event: MessageEvent, address: str = ArgStr('address')):
    address = address.strip()

    entity = EventEntityHelper(bot=bot, event=event).get_event_entity()

    bind_result = await run_async_catching_exception(entity.bind_email_box)(address=address, bind_info=address)
    if isinstance(bind_result, Exception) or bind_result.error:
        logger.error(f'EmailBoxManager | 绑定邮箱: {address} 失败, {bind_result}')
        await matcher.finish(f'绑定邮箱{address}失败QAQ, 详情请查看日志')
    else:
        logger.success(f'EmailBoxManager | 绑定邮箱: {address} 成功')
        await matcher.finish(f'绑定邮箱{address}成功')


unbind_mail_box = EmailBoxManager.command('unbind', aliases={'解绑邮箱'})


@unbind_mail_box.handle()
async def handle_parse_email_address(bot: Bot, event: MessageEvent, state: T_State, matcher: Matcher,
                                     cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    address = cmd_arg.extract_plain_text().strip()
    if address:
        state.update({'address': address})
    else:
        entity = EventEntityHelper(bot=bot, event=event).get_event_entity()

        mail_box_result = await run_async_catching_exception(entity.query_bound_email_box)()
        if isinstance(mail_box_result, Exception):
            logger.error(f'EmailBoxManager | 查询已绑定邮箱失败, {mail_box_result}')
            await matcher.finish('查询已绑定邮箱失败, 详情请查看日志')
        elif not mail_box_result:
            await matcher.finish('无已绑定邮箱, 无需解绑!')
        else:
            mailbox_msg = '\n'.join(x.address for x in mail_box_result)
            msg = f'当前已绑定邮箱:\n\n{mailbox_msg}'
            await matcher.send(msg)


@unbind_mail_box.got('address', prompt='请输入需要解绑的邮箱地址:')
async def handle_bind_mail(bot: Bot, matcher: Matcher, event: MessageEvent, address: str = ArgStr('address')):
    address = address.strip()

    entity = EventEntityHelper(bot=bot, event=event).get_event_entity()

    bind_result = await run_async_catching_exception(entity.unbind_email_box)(address=address)
    if isinstance(bind_result, Exception) or bind_result.error:
        logger.error(f'EmailBoxManager | 解绑邮箱: {address} 失败, {bind_result}')
        await matcher.finish(f'解绑邮箱{address}失败QAQ, 详情请查看日志')
    else:
        logger.success(f'EmailBoxManager | 解绑邮箱: {address} 成功')
        await matcher.finish(f'解绑邮箱{address}成功')


receive_email = EmailBoxManager.command(
    'receive',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='ReceiveEmail', level=10),
    rule=None,
    aliases={'收邮件'},
    permission=GROUP | GUILD | SUPERUSER,
    priority=10,
    block=True
)


@receive_email.handle()
async def handle_receive_email(bot: Bot, event: MessageEvent, matcher: Matcher):
    entity = EventEntityHelper(bot=bot, event=event).get_event_entity()

    bind_mailbox = await run_async_catching_exception(entity.query_bound_email_box)()

    if isinstance(bind_mailbox, Exception):
        logger.error(f'ReceiveEmail | 查询已绑定邮箱失败, {bind_mailbox}')
        await matcher.finish('查询已绑定邮箱失败QAQ, 请联系管理员处理')
    elif not bind_mailbox:
        logger.warning('ReceiveEmail | 收邮件失败, 没有绑定的邮箱')
        await matcher.finish('没有绑定的邮箱, 请先绑定邮箱后再收件')

    mail_box_list_msg = '\n'.join(x.address for x in bind_mailbox)
    await matcher.send(f'已绑定邮箱:\n\n{mail_box_list_msg}\n\n正在连接到邮箱服务器, 请稍候~')

    for mailbox_result in bind_mailbox:
        address = mailbox_result.address
        host = mailbox_result.server_host
        mailbox = await run_async_catching_exception(EmailBox(address=address).query)()
        if isinstance(mailbox, Exception) or mailbox.error:
            logger.error(f'ReceiveEmail | 邮箱 {address} 数据库查询失败, {mailbox}')
            await matcher.send(f'邮箱: {address}\n收件失败QAQ, 请联系管理员处理')
            continue

        # 解密密码
        password = decrypt_password(ciphertext=mailbox.result.password)
        if isinstance(password, Exception):
            logger.error(f'ReceiveEmail | 邮箱 {address} 密码验证失败')
            await matcher.send(f'邮箱: {address}\n密码验证失败QAQ, 请联系管理员处理')
            continue

        # 接受邮件内容
        unseen_mail_result = await get_unseen_mail_data(address=address, server_host=host, password=password)
        if isinstance(unseen_mail_result, Exception):
            logger.error(f'ReceiveEmail | 邮箱 {address} 收件失败, {unseen_mail_result}')
            await matcher.send(f'邮箱: {address}\n收件失败QAQ, 请稍后再试')
            continue
        elif not unseen_mail_result:
            logger.success(f'ReceiveEmail | 邮箱 {address} 收件完成, 没有新的邮件')
            await matcher.send(f'邮箱: {address}\n收件完成, 没有新的邮件~')
            continue
        else:
            for mail in unseen_mail_result:
                content = mail.html if mail.html else mail.body
                content = re.sub(r'(\n|&nbsp;){2,}', '\n', content)
                msg = f"【{mail.header}】\n时间: {mail.date}\n发件人: {mail.sender}\n{'=' * 16}\n{content}"
                mail_img = await run_async_catching_exception(TextUtils(text=msg).text_to_img)()
                if isinstance(mail_img, Exception):
                    logger.error(f'ReceiveEmail | Convert email to image failed, {mail_img}')
                    continue
                await matcher.send(MessageSegment.image(file=mail_img.file_uri))

            logger.success(f'ReceiveEmail | 邮箱 {address} 收件完成, 共{len(unseen_mail_result)}封新的邮件')
            await matcher.send(f'邮箱 {address}\n收件完成, 共{len(unseen_mail_result)}封新的邮件~')
