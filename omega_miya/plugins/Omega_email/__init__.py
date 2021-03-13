import re
from nonebot import MatcherGroup, export, logger
from nonebot.rule import to_me
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent, GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP
from omega_miya.utils.Omega_Base import DBEmailBox, DBGroup
from omega_miya.utils.Omega_plugin_utils import init_export, init_permission_state
from .utils import check_mailbox, get_unseen_mail_info, encrypt_password, decrypt_password


# Custom plugin usage text
__plugin_name__ = 'OmegaEmail'
__plugin_usage__ = r'''【OmegaEmail 邮箱插件】
主要是用来收验证码OvO

**Permission**
Command
with AuthNode

**Usage**
/收邮件

**SuperUser Only**
/添加邮箱
/绑定邮箱'''

# 声明本插件可配置的权限节点
__plugin_auth_node__ = [
    'basic'
]

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__, __plugin_auth_node__)


# 注册事件响应器
OmegaEmail_admin = MatcherGroup(type='message', rule=to_me(), priority=20, permission=SUPERUSER, block=True)

admin_mail_add = OmegaEmail_admin.on_command('添加邮箱')


# 修改默认参数处理
@admin_mail_add.args_parser
async def parse(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().split()
    if not args:
        await admin_mail_add.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await admin_mail_add.finish('操作已取消')


@admin_mail_add.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().split()
    if args:
        await admin_mail_add.finish('该命令不支持参数QAQ')
    await admin_mail_add.send('您正在添加邮箱, 请按提示操作, 注意: 当前只支持接收IMAP邮箱邮件!')


@admin_mail_add.got('address', prompt='请输入邮箱地址:')
@admin_mail_add.got('server_host', prompt='请输入IMAP服务器地址:')
@admin_mail_add.got('password', prompt='请输入邮箱密码:')
async def handle_admin_mail_add(bot: Bot, event: MessageEvent, state: T_State):
    address = state['address']
    server_host = state['server_host']
    password = state['password']

    check_result = await check_mailbox(address=address, server_host=server_host, password=password)
    if not check_result.success():
        logger.warning(f'{event.user_id} 添加邮箱: {address} 失败, 邮箱验证不通过, error: {check_result.info}')
        await admin_mail_add.finish('验证邮箱失败了QAQ, 请检查邮箱信息或稍后再试')

    # 对密码加密保存
    password = encrypt_password(plaintext=password)
    add_result = DBEmailBox(address=address).add(server_host=server_host, password=password)

    if add_result.success():
        logger.info(f'{event.user_id} 添加邮箱: {address} 成功')
        await admin_mail_add.finish('Success! 邮箱添加成功')
    else:
        logger.error(f'{event.user_id} 添加邮箱: {address} 失败, 数据库写入失败, error: {add_result.info}')
        await admin_mail_add.finish('邮箱添加失败QAQ, 请检联系管理员处理')


admin_mail_bind = OmegaEmail_admin.on_command('绑定邮箱')


# 修改默认参数处理
@admin_mail_bind.args_parser
async def parse(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().split()
    if not args:
        await admin_mail_bind.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await admin_mail_bind.finish('操作已取消')


@admin_mail_bind.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().split()
    if args:
        await admin_mail_bind.finish('该命令不支持参数QAQ')

    # 发送已有邮箱列表
    mailbox_list_res = DBEmailBox.list()
    mailbox_list = mailbox_list_res.result
    if not mailbox_list_res.success() or not mailbox_list:
        await admin_mail_bind.finish('无可绑定邮箱, 请先添加邮箱!')

    state['mailbox_list'] = mailbox_list
    mailbox_msg = '】\n【'.join(mailbox_list)
    msg = f'当前可绑定邮箱:\n【{mailbox_msg}】'
    await admin_mail_bind.send(msg)


@admin_mail_bind.got('email_address', prompt='请输入需要绑定的邮箱地址:')
async def handle_admin_mail_bind(bot: Bot, event: GroupMessageEvent, state: T_State):
    mailbox_list = state['mailbox_list']
    email_address = state['email_address']

    if email_address not in mailbox_list:
        logger.warning(f'Group:{event.group_id}/User:{event.user_id} 绑定邮箱: {email_address} 失败, 不在可绑定邮箱中的邮箱')
        await admin_mail_bind.finish('该邮箱不在可绑定邮箱中!')

    group_id = event.group_id
    res = DBGroup(group_id=group_id).mailbox_add(mailbox=DBEmailBox(address=email_address))

    if res.success():
        logger.info(f'Group:{event.group_id}/User:{event.user_id} 绑定邮箱: {email_address} 成功')
        await admin_mail_bind.finish('Success! 绑定成功')
    else:
        logger.error(f'Group:{event.group_id}/User:{event.user_id} 绑定邮箱: {email_address} 失败, error: {res.info}')
        await admin_mail_bind.finish('绑定邮箱失败QAQ, 请检联系管理员处理')


admin_mail_clear = OmegaEmail_admin.on_command('清空绑定邮箱')


@admin_mail_clear.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().split()
    if args:
        await mail_receive.finish('该命令不支持参数QAQ')

    group_id = event.group_id
    group = DBGroup(group_id=group_id)
    res = group.mailbox_clear()

    if res.success():
        logger.info(f'Group:{event.group_id}/User:{event.user_id} 清空绑定邮箱成功')
        await admin_mail_bind.finish('Success! 已清空本群组的绑定邮箱')
    else:
        logger.info(f'Group:{event.group_id}/User:{event.user_id} 清空绑定邮箱失败, error: {res.info}')
        await admin_mail_bind.finish('清空本群组的绑定邮箱失败QAQ, 请检联系管理员处理')


# 注册事件响应器
OmegaEmail_group = MatcherGroup(
    type='message',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_permission_state(
        name='OmegaEmail_group',
        command=True,
        auth_node='basic'),
    permission=GROUP,
    priority=20,
    block=True)

mail_receive = OmegaEmail_group.on_command('收邮件')


@mail_receive.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().split()
    if args:
        await mail_receive.finish('该命令不支持参数QAQ')

    group_id = event.group_id
    group = DBGroup(group_id=group_id)
    group_bind_mailbox = group.mailbox_list()
    if not group_bind_mailbox.success() or not group_bind_mailbox.result:
        logger.info(f'{group_id} 收邮件失败: 没有绑定的邮箱')
        await mail_receive.finish('本群组没有绑定的邮箱, 请先绑定邮箱后再收件!')

    mail_box_list_msg = '\n'.join([x for x in group_bind_mailbox.result])
    await mail_receive.send(f'本群组已绑定邮箱:\n{mail_box_list_msg}\n\n正在连接到邮箱服务器, 请稍后...')

    for mailbox_address in group_bind_mailbox.result:
        mailbox = DBEmailBox(address=mailbox_address).get_info()
        if not mailbox.success():
            logger.error(f'邮箱 {mailbox_address} 信息获取失败, 请检查数据库, error: {mailbox.info}')
            await mail_receive.send(f'邮箱: {mailbox_address} 收件失败QAQ, 请联系管理员处理')
            continue

        host = mailbox.result.get('server_host')
        password = mailbox.result.get('password')
        # 解密密码
        password = decrypt_password(ciphertext=password)
        if not password.success():
            logger.error(f'邮箱 {mailbox_address} 密码验证失败')
            await mail_receive.send(f'邮箱: {mailbox_address}\n密码验证失败QAQ, 请联系管理员处理')
            continue
        password = password.result
        unseen_mail_res = await get_unseen_mail_info(address=mailbox_address, server_host=host, password=password)
        if not unseen_mail_res.success():
            logger.error(f'邮箱 {mailbox_address} 收件失败, error: {unseen_mail_res.info}')
            await mail_receive.send(f'邮箱: {mailbox_address}\n收件失败QAQ, 请稍后再试')
            continue
        elif not unseen_mail_res.result:
            logger.info(f'邮箱 {mailbox_address} 收件完成, 没有新的邮件')
            await mail_receive.send(f'邮箱: {mailbox_address}\n收件完成, 没有新的邮件~')
            continue
        else:
            for mail in unseen_mail_res.result:
                html = mail.html
                content = re.sub(r'<[^>]*>', '', html)
                content = re.sub(r'\s', '', content)
                content = content.replace('&nbsp;', '').replace('\n', '').replace(' ', '')
                msg = f"【{mail.header}】\n时间: {mail.date}\n发件人: {mail.sender}\n{'='*16}\n{content}"
                await mail_receive.send(msg)
            logger.info(f'邮箱 {mailbox_address} 收件完成, 共{len(unseen_mail_res.result)}封新的邮件')
            await mail_receive.send(f'邮箱: {mailbox_address}\n收件完成, 共{len(unseen_mail_res.result)}封新的邮件~')
