"""
@Author         : Ailitonia
@Date           : 2026/11/2 10:00
@FileName       : test_002_omega_email
@Project        : omega-miya
@Description    : omega_email 插件单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import random
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from nonebug import App

from tests.test_006_plugins.helpers import expected_reply, obv11_user_entity
from tests.utils import (
    create_real_obv11_bot,
    make_obv11_group_message_event,
    make_obv11_private_message_event,
    preserve_plugin_row,
    rebind_module_namespace,
    seed_entity_permissions,
    unique_test_id,
)


@pytest.fixture(scope='class')
async def email_plugin_enabled_guard() -> AsyncGenerator[None, None]:
    """保证本插件启用并在测试后恢复原状态"""
    async with preserve_plugin_row('omega_email', 'src.plugins.omega_email', ensure_enabled=True):
        yield


@pytest.fixture
async def mailbox_settings_cleanup() -> AsyncGenerator[list[str], None]:
    """登记并精确清理本测试写入的邮箱账号配置"""
    addresses: list[str] = []
    yield addresses

    from src.database.internal.system_setting import SystemSettingDAL
    from src.plugins.omega_email.consts import DB_MAILBOX_ACCOUNT_SETTING_NAME

    async with SystemSettingDAL.create() as dal:
        for address in addresses:
            await dal.delete(setting_name=DB_MAILBOX_ACCOUNT_SETTING_NAME, setting_key=address)


class _FakeImapConnection:
    """组合式 IMAP 替身, 模拟 imaplib 的返回值与连接状态"""

    def __init__(self) -> None:
        self.state = 'NONAUTH'
        self.calls: list[tuple[Any, ...]] = []
        self.responses: dict[str, Any] = {}
        self.errors: dict[str, Exception] = {}

    def _respond(self, name: str, default: Any) -> Any:
        if name in self.errors:
            raise self.errors[name]
        return self.responses.get(name, default)

    def login(self, address: str, password: str) -> tuple[str, list[bytes]]:
        self.calls.append(('login', address, password))
        result = self._respond('login', ('OK', [b'LOGIN completed']))
        if result[0] == 'OK':
            self.state = 'AUTH'
        return result

    def select(self) -> tuple[str, list[bytes]]:
        self.calls.append(('select',))
        result = self._respond('select', ('OK', [b'1']))
        if result[0] == 'OK':
            self.state = 'SELECTED'
        return result

    def search(self, charset: str | None, *criteria: str) -> tuple[str, list[bytes]]:
        self.calls.append(('search', charset, *criteria))
        return self._respond('search', ('OK', [b'']))

    def fetch(self, num: str, parts: str) -> tuple[str, list[Any] | None]:
        self.calls.append(('fetch', num, parts))
        message_key = f'fetch:{num}'
        if message_key in self.errors or message_key in self.responses:
            return self._respond(message_key, ('OK', [None]))
        return self._respond('fetch', ('OK', [None]))

    def store(self, num: str, flags: str, value: str) -> tuple[str, list[bytes]]:
        self.calls.append(('store', num, flags, value))
        return self._respond('store', ('OK', [b'1 FLAGS (\\Seen)']))

    def uid(self, command: str, *args: Any) -> tuple[str, list[Any]]:
        self.calls.append(('uid', command, *args))
        match command:
            case 'SEARCH':
                return self._respond('search', ('OK', [b'']))
            case 'FETCH':
                uid = args[0]
                message_key = f'fetch:{uid}'
                if message_key in self.errors or message_key in self.responses:
                    return self._respond(message_key, ('OK', [None]))
                return self._respond('fetch', ('OK', [None]))
            case 'STORE':
                return self._respond('store', ('OK', [b'1 FLAGS (\\Seen)']))
            case _:
                raise AssertionError(f'unexpected UID command: {command}')

    def close(self) -> tuple[str, list[bytes]]:
        self.calls.append(('close',))
        result = self._respond('close', ('OK', [b'CLOSE completed']))
        if result[0] == 'OK':
            self.state = 'AUTH'
        return result

    def logout(self) -> tuple[str, list[bytes]]:
        self.calls.append(('logout',))
        self.state = 'LOGOUT'
        return self._respond('logout', ('OK', [b'LOGOUT completed']))

    def _simple_command(self, name: str, *args: str) -> tuple[str, list[bytes]]:
        self.calls.append(('_simple_command', name, *args))
        return self._respond(name, ('OK', [b'ID completed']))

    def _untagged_response(self, typ: str, dat: list[bytes], name: str) -> tuple[str, list[bytes]]:
        self.calls.append(('_untagged_response', typ, dat, name))
        return typ, dat


def _install_fake_imap(
        monkeypatch: pytest.MonkeyPatch,
        connection: _FakeImapConnection,
) -> dict[str, Any]:
    """仅在 mailbox 模块命名空间替换 IMAP 工厂, 不修改共享 imaplib 属性"""
    import imaplib

    import src.plugins.omega_email.mailbox as mailbox_module

    constructor_kwargs: dict[str, Any] = {}

    def fake_imap_factory(**kwargs: Any) -> _FakeImapConnection:
        constructor_kwargs.update(kwargs)
        return connection

    rebind_module_namespace(
        monkeypatch,
        mailbox_module,
        'imaplib',
        IMAP4_SSL=fake_imap_factory,
        Commands=dict(imaplib.Commands),
    )
    return constructor_kwargs


def _seen_store_calls(connection: _FakeImapConnection) -> list[tuple[Any, ...]]:
    return [
        call for call in connection.calls
        if call[0] == 'store' or (call[0] == 'uid' and call[1] == 'STORE')
    ]


def _random_user_id(bot_self_id: str) -> int:
    user_id = random.randint(10_000_000, 99_999_999)
    while str(user_id) == bot_self_id:
        user_id = random.randint(10_000_000, 99_999_999)
    return user_id


def _random_message_id() -> int:
    return random.randint(1, 2 ** 31 - 1)


def _private_event(**kwargs: Any) -> Any:
    event = make_obv11_private_message_event(**kwargs)
    event.to_me = True
    return event


def _group_event(**kwargs: Any) -> Any:
    event = make_obv11_group_message_event(**kwargs)
    event.to_me = True
    return event


def _expected_image_reply(event: Any, url: str) -> Any:
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    return Message([MessageSegment.reply(event.message_id), MessageSegment.image(file=url)])


def _test_address() -> str:
    return f'{unique_test_id("mail")}@example.com'


def _make_account(address: str, *, port: int | None = None) -> Any:
    from src.plugins.omega_email.consts import EMAIL_IMAP_PORT
    from src.plugins.omega_email.helpers import MailboxAccount, MailboxServer

    return MailboxAccount(
        address=address,
        server=MailboxServer(
            server_host='imap.example.com',
            password='secret',
            protocol='imap',
            port=EMAIL_IMAP_PORT if port is None else port,
        ),
    )


def _make_mail(header: str, *, body: str = 'plain', html: str = '', uid: str | None = '1001') -> Any:
    from src.plugins.omega_email.mailbox import Email

    return Email(
        date='Mon, 02 Nov 2026 10:00:00 +0800',
        header=header,
        sender='Sender <sender@example.com>',
        to='receiver@example.com',
        body=body,
        html=html,
        uid=uid,
    )


async def _seed_user_permissions(bot: Any, user_id: int) -> None:
    await seed_entity_permissions(
        bot, 'onebot_v11_user', str(user_id), enable_global=True, permission_level=30,
    )


async def _seed_group_permissions(bot: Any, group_id: int) -> None:
    await seed_entity_permissions(
        bot, 'onebot_v11_group', str(group_id), enable_global=True, permission_level=30,
    )


def _make_email_bytes(
        *,
        subject: Any = '测试主题',
        date: str | None = 'Mon, 02 Nov 2026 10:00:00 +0800',
        sender: str | None = 'Sender <sender@example.com>',
        recipient: str | None = 'receiver@example.com',
        body: str = '纯文本正文',
        html: str | None = None,
        with_attachment: bool = False,
) -> bytes:
    """使用标准库生成真实 RFC 邮件字节"""
    from email.message import EmailMessage

    message = EmailMessage()
    if date is not None:
        message['Date'] = date
    if subject is not None:
        message['Subject'] = str(subject)
    if sender is not None:
        message['From'] = sender
    if recipient is not None:
        message['To'] = recipient
    if html is None:
        message.set_content(body)
    else:
        message.set_content(body)
        message.add_alternative(html, subtype='html')
    if with_attachment:
        message.add_attachment(b'attachment', maintype='application', subtype='octet-stream', filename='test.bin')
    return message.as_bytes()


class _MailboxEntityInterface:
    """将 helper 的实体会话边界组合到真实测试实体"""

    def __init__(self, bot: Any, user_id: int) -> None:
        self.bot = bot
        self.user_id = user_id

    def create_current_entity_session(self) -> Any:
        return obv11_user_entity(self.bot, str(self.user_id))


class TestPluginMetadata:

    def test_plugin_metadata_loaded(self) -> None:
        from nonebot.plugin import get_plugin

        plugin = get_plugin('omega_email')
        assert plugin is not None
        assert plugin.metadata is not None
        assert plugin.metadata.name == '收邮件'
        assert plugin.metadata.usage is not None


class TestCommandParsing:

    @pytest.mark.parametrize(('command_text', 'expected'), [
        pytest.param('mailbox', {}, id='main'),
        pytest.param(
            'mailbox add --server imap.example.com --address test@example.com --password secret',
            {'server': 'imap.example.com', 'address': 'test@example.com', 'password': 'secret'},
            id='add_long_options',
        ),
        pytest.param(
            'mailbox 添加 -s imap.example.com -a test@example.com -p secret',
            {'server': 'imap.example.com', 'address': 'test@example.com', 'password': 'secret'},
            id='add_alias_short_options',
        ),
        pytest.param('mailbox bind --address test@example.com', {'address': 'test@example.com'}, id='bind'),
        pytest.param('mailbox 绑定 -a test@example.com', {'address': 'test@example.com'}, id='bind_alias'),
        pytest.param('mailbox unbind --address test@example.com', {'address': 'test@example.com'}, id='unbind'),
        pytest.param('mailbox 解绑 -a test@example.com', {'address': 'test@example.com'}, id='unbind_alias'),
        pytest.param('mailbox 取消绑定 -a test@example.com', {'address': 'test@example.com'}, id='unbind_alias_2'),
        pytest.param('mailbox receive', {}, id='receive'),
        pytest.param('mailbox 收件', {}, id='receive_alias'),
        pytest.param('mailbox 收邮件', {}, id='receive_alias_2'),
    ])
    def test_command_variants(self, command_text: str, expected: dict[str, str]) -> None:
        from nonebot_plugin_alconna.uniseg import UniMessage

        from src.plugins.omega_email.command import mailbox_manager

        result = mailbox_manager.command().parse(UniMessage(f'/{command_text}'))

        assert result.matched
        for name, value in expected.items():
            assert result.query(name) == value

    def test_option_without_value_matches_for_prompt(self) -> None:
        from nonebot_plugin_alconna.uniseg import UniMessage

        from src.plugins.omega_email.command import mailbox_manager

        result = mailbox_manager.command().parse(UniMessage('/mailbox add -s'))

        assert result.matched
        assert 'add' in result.subcommands
        assert result.query('server') is None

    def test_declarative_self_checks_cover_subcommands(self) -> None:
        from src.plugins.omega_email.command import mailbox_manager

        registered = [message.extract_plain_text() for message, _, _ in mailbox_manager._tests]

        assert {
                   'mailbox',
                   'mailbox add -s imap.example.com -a test@example.com -p test-password',
                   'mailbox bind --address test@example.com',
                   'mailbox unbind --address test@example.com',
                   'mailbox receive',
               } <= set(registered)


class TestImapConnection:

    def test_constructor_uses_verified_tls_and_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import ssl

        from src.plugins.omega_email.mailbox import ImapMailbox

        connection = _FakeImapConnection()
        constructor_kwargs = _install_fake_imap(monkeypatch, connection)

        ImapMailbox(host='imap.example.com', address='test@example.com', password='secret')

        assert constructor_kwargs['host'] == 'imap.example.com'
        assert constructor_kwargs['port'] == 993
        assert constructor_kwargs['timeout'] == 30.0
        ssl_context = constructor_kwargs['ssl_context']
        assert ssl_context.check_hostname is True
        assert ssl_context.verify_mode == ssl.CERT_REQUIRED

    def test_check_success_closes_and_logs_out(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.plugins.omega_email.mailbox import ImapMailbox

        connection = _FakeImapConnection()
        _install_fake_imap(monkeypatch, connection)

        ImapMailbox(host='imap.example.com', address='test@example.com', password='secret').check()

        assert [call[0] for call in connection.calls] == ['login', 'select', 'close', 'logout']

    def test_check_rejects_unselected_mailbox(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import imaplib

        from src.plugins.omega_email.mailbox import ImapMailbox

        connection = _FakeImapConnection()
        connection.responses['select'] = ('NO', [b'cannot select'])
        _install_fake_imap(monkeypatch, connection)

        with pytest.raises(imaplib.IMAP4.error, match='SELECT'):
            ImapMailbox(host='imap.example.com', address='test@example.com', password='secret').check()

        assert [call[0] for call in connection.calls] == ['login', 'select', 'logout']

    def test_login_error_is_not_masked_by_logout_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.plugins.omega_email.mailbox import ImapMailbox

        connection = _FakeImapConnection()
        login_error = RuntimeError('login failed')
        connection.errors['login'] = login_error
        connection.errors['logout'] = RuntimeError('logout failed')
        _install_fake_imap(monkeypatch, connection)

        with pytest.raises(RuntimeError) as exc_info:
            ImapMailbox(host='imap.example.com', address='test@example.com', password='secret').check()

        assert exc_info.value is login_error
        assert [call[0] for call in connection.calls] == ['login', 'logout']

    def test_163_check_sends_id_before_select_and_restores_commands(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """163 账号 check 与 fetch/ack 路径行为一致: login 后先发送 ID 再 select, 且恢复注册表"""
        import src.plugins.omega_email.mailbox as mailbox_module
        from src.plugins.omega_email.mailbox import ImapMailbox

        connection = _FakeImapConnection()
        _install_fake_imap(monkeypatch, connection)
        mailbox_module.imaplib.Commands.pop('ID', None)

        ImapMailbox(host='imap.163.com', address='test@163.com', password='secret').check()

        call_names = [call[0] for call in connection.calls]
        assert call_names.index('_simple_command') < call_names.index('select')
        assert 'ID' not in mailbox_module.imaplib.Commands
        assert call_names[-1] == 'logout'

    @pytest.mark.parametrize(('failing_method', 'should_close'), [
        pytest.param('login', False, id='login'),
        pytest.param('select', False, id='select'),
        pytest.param('search', True, id='search'),
        pytest.param('fetch', True, id='fetch'),
    ])
    def test_get_mail_list_always_cleans_up(
            self,
            monkeypatch: pytest.MonkeyPatch,
            failing_method: str,
            should_close: bool,
    ) -> None:
        from src.plugins.omega_email.mailbox import ImapMailbox

        connection = _FakeImapConnection()
        connection.responses['search'] = ('OK', [b'1'])
        error = RuntimeError(f'{failing_method} failed')
        connection.errors[failing_method] = error
        _install_fake_imap(monkeypatch, connection)

        with pytest.raises(RuntimeError) as exc_info:
            ImapMailbox(host='imap.example.com', address='test@example.com', password='secret').get_mail_list(
                None, 'UNSEEN',
            )

        assert exc_info.value is error
        call_names = [call[0] for call in connection.calls]
        assert call_names[-1] == 'logout'
        assert ('close' in call_names) is should_close

    def test_get_mail_list_empty_closes_without_extra_select(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.plugins.omega_email.mailbox import ImapMailbox

        connection = _FakeImapConnection()
        _install_fake_imap(monkeypatch, connection)

        result = ImapMailbox(
            host='imap.example.com', address='test@example.com', password='secret',
        ).get_mail_list(None, 'UNSEEN')

        assert result == []
        assert [call[0] for call in connection.calls] == ['login', 'select', 'uid', 'close', 'logout']
        assert connection.calls[2] == ('uid', 'SEARCH', None, 'UNSEEN')

    @pytest.mark.parametrize('failing_method', ['search', 'fetch'])
    def test_get_mail_list_rejects_protocol_error_status(
            self,
            monkeypatch: pytest.MonkeyPatch,
            failing_method: str,
    ) -> None:
        import imaplib

        from src.plugins.omega_email.mailbox import ImapMailbox

        connection = _FakeImapConnection()
        connection.responses['search'] = ('OK', [b'1'])
        connection.responses[failing_method] = ('NO', [b'not allowed'])
        _install_fake_imap(monkeypatch, connection)

        with pytest.raises(imaplib.IMAP4.error, match=failing_method.upper()):
            ImapMailbox(host='imap.example.com', address='test@example.com', password='secret').get_mail_list(
                None, 'UNSEEN',
            )

        assert connection.calls[-1] == ('logout',)


class TestMarkMailAsSeen:

    def test_mark_as_seen_uses_uid_store_and_cleans_up(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.plugins.omega_email.mailbox import ImapMailbox

        connection = _FakeImapConnection()
        _install_fake_imap(monkeypatch, connection)
        mailbox = ImapMailbox(host='imap.example.com', address='test@example.com', password='secret')

        mailbox.mark_as_seen('101')

        assert [call[0] for call in connection.calls] == ['login', 'select', 'uid', 'close', 'logout']
        assert connection.calls[2] == ('uid', 'STORE', '101', '+FLAGS', '\\Seen')

    @pytest.mark.parametrize('failure_mode', ['status', 'exception'])
    def test_mark_as_seen_failure_preserves_error_and_cleans_up(
            self,
            monkeypatch: pytest.MonkeyPatch,
            failure_mode: str,
    ) -> None:
        import imaplib

        from src.plugins.omega_email.mailbox import ImapMailbox

        connection = _FakeImapConnection()
        error = RuntimeError('store failed')
        if failure_mode == 'status':
            connection.responses['store'] = ('NO', [b'not allowed'])
        else:
            connection.errors['store'] = error
        _install_fake_imap(monkeypatch, connection)
        mailbox = ImapMailbox(host='imap.example.com', address='test@example.com', password='secret')

        with pytest.raises((imaplib.IMAP4.error, RuntimeError)) as exc_info:
            mailbox.mark_as_seen('101')

        if failure_mode == 'exception':
            assert exc_info.value is error
        else:
            assert 'STORE' in str(exc_info.value)
        assert connection.calls[-1] == ('logout',)

    @pytest.mark.parametrize('uid', ['', 'abc', '0', '-1'])
    def test_mark_as_seen_rejects_invalid_uid_before_login(
            self,
            monkeypatch: pytest.MonkeyPatch,
            uid: str,
    ) -> None:
        from src.plugins.omega_email.mailbox import ImapMailbox

        connection = _FakeImapConnection()
        _install_fake_imap(monkeypatch, connection)
        mailbox = ImapMailbox(host='imap.example.com', address='test@example.com', password='secret')

        with pytest.raises(ValueError, match='Invalid IMAP UID'):
            mailbox.mark_as_seen(uid)

        assert connection.calls == []
        mailbox._disconnect()

    async def test_helper_forwards_uid_and_custom_port(self, app: App, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import Mock

        import src.plugins.omega_email.helpers as helpers_module

        mailbox = Mock()
        factory = Mock(return_value=mailbox)
        monkeypatch.setattr(helpers_module, 'ImapMailbox', factory)

        result = await helpers_module.mark_mail_as_seen(
            address='test@example.com',
            server_host='imap.example.com',
            password='secret',
            uid='101',
            port=1993,
        )

        assert result is None
        factory.assert_called_once_with(
            host='imap.example.com', address='test@example.com', password='secret', port=1993,
        )
        mailbox.mark_as_seen.assert_called_once_with('101')

    async def test_helper_propagates_ack_failure(self, app: App, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import Mock

        import src.plugins.omega_email.helpers as helpers_module

        error = RuntimeError('ack failed')
        mailbox = Mock()
        mailbox.mark_as_seen.side_effect = error
        monkeypatch.setattr(helpers_module, 'ImapMailbox', Mock(return_value=mailbox))

        with pytest.raises(RuntimeError) as exc_info:
            await helpers_module.mark_mail_as_seen('test@example.com', 'imap.example.com', 'secret', '101')

        assert exc_info.value is error

    def test_163_ack_sends_id_and_restores_commands(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import src.plugins.omega_email.mailbox as mailbox_module
        from src.plugins.omega_email.mailbox import ImapMailbox

        connection = _FakeImapConnection()
        _install_fake_imap(monkeypatch, connection)
        mailbox_module.imaplib.Commands.pop('ID', None)
        mailbox = ImapMailbox(host='imap.163.com', address='test@163.com', password='secret')

        mailbox.mark_as_seen('101')

        assert any(call[:2] == ('_simple_command', 'ID') for call in connection.calls)
        assert ('uid', 'STORE', '101', '+FLAGS', '\\Seen') in connection.calls
        assert 'ID' not in mailbox_module.imaplib.Commands
        assert connection.calls[-1] == ('logout',)


class TestEmailParsing:

    @pytest.mark.parametrize(('raw_header', 'expected'), [
        pytest.param(None, '', id='none'),
        pytest.param('plain text', 'plain text', id='plain'),
        pytest.param('=?utf-8?b?/w==?=', '\ufffd', id='invalid_utf8'),
        pytest.param('=?x-unknown?b?5L2g5aW9?=', '你好', id='unknown_charset'),
    ])
    def test_decode_header_fallbacks(self, raw_header: str | None, expected: str) -> None:
        from src.plugins.omega_email.mailbox import ImapMailbox

        assert ImapMailbox._decode_header(raw_header) == expected

    def test_decode_header_encoded_and_mixed_text(self) -> None:
        from email.header import Header

        from src.plugins.omega_email.mailbox import ImapMailbox

        for charset in ('utf-8', 'gbk'):
            assert ImapMailbox._decode_header(str(Header('中文主题', charset))) == '中文主题'
        assert ImapMailbox._decode_header(f'{Header("你好", "utf-8")} suffix') == '你好 suffix'

    def test_get_mail_list_uses_uid_without_marking_seen(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from email.header import Header

        from src.plugins.omega_email.mailbox import ImapMailbox

        raw_message = _make_email_bytes(
            subject=Header('验证码通知', 'utf-8'), body='line 1&nbsp;line 2\n', with_attachment=True,
        )
        connection = _FakeImapConnection()
        connection.responses['search'] = ('OK', [b'1'])
        connection.responses['fetch'] = ('OK', [(b'1 (BODY.PEEK[] {123}', raw_message)])
        _install_fake_imap(monkeypatch, connection)

        result = ImapMailbox(
            host='imap.example.com', address='test@example.com', password='secret',
        ).get_mail_list(None, 'UNSEEN')

        assert len(result) == 1
        mail = result[0]
        assert mail.uid == '1'
        assert mail.date == 'Mon, 02 Nov 2026 10:00:00 +0800'
        assert mail.header == '验证码通知'
        assert mail.sender == 'Sender <sender@example.com>'
        assert mail.to == 'receiver@example.com'
        assert mail.body == 'line 1\nline 2\n'
        assert mail.html == ''
        assert ('uid', 'FETCH', '1', '(BODY.PEEK[])') in connection.calls
        assert _seen_store_calls(connection) == []
        assert connection.calls[-1] == ('logout',)

    def test_missing_headers_default_to_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.plugins.omega_email.mailbox import ImapMailbox

        raw_message = _make_email_bytes(subject=None, date=None, sender=None, recipient=None, body='body')
        connection = _FakeImapConnection()
        connection.responses['search'] = ('OK', [b'1'])
        connection.responses['fetch'] = ('OK', [(b'1 (BODY.PEEK[] {10}', raw_message)])
        _install_fake_imap(monkeypatch, connection)

        result = ImapMailbox(
            host='imap.example.com', address='test@example.com', password='secret',
        ).get_mail_list(None, 'UNSEEN')

        assert len(result) == 1
        assert result[0].date == ''
        assert result[0].header == ''
        assert result[0].sender == ''
        assert result[0].to == ''
        assert result[0].body == 'body\n'

    def test_parse_multipart_plain_html_and_attachment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.plugins.omega_email.mailbox import ImapMailbox

        raw_message = _make_email_bytes(
            body='plain body', html='<p>Hello<br>world<br/>!<br  />end&amp;</p>', with_attachment=True,
        )
        connection = _FakeImapConnection()
        connection.responses['search'] = ('OK', [b'1'])
        connection.responses['fetch'] = ('OK', [(b'1 (BODY.PEEK[] {123}', raw_message)])
        _install_fake_imap(monkeypatch, connection)

        result = ImapMailbox(
            host='imap.example.com', address='test@example.com', password='secret',
        ).get_mail_list(None, 'UNSEEN')

        assert result[0].body == 'plain body\n'
        assert result[0].html == 'Hello\nworld\n!\nend&\n'

    @pytest.mark.parametrize(('charset', 'payload', 'expected'), [
        pytest.param('x-unknown', '你好'.encode(), '你好', id='unknown_charset'),
        pytest.param('utf-8', b'\xff', '\ufffd', id='invalid_utf8'),
    ])
    def test_body_charset_fallbacks(
            self,
            monkeypatch: pytest.MonkeyPatch,
            charset: str,
            payload: bytes,
            expected: str,
    ) -> None:
        from src.plugins.omega_email.mailbox import ImapMailbox

        headers = (
            'Date: Mon, 02 Nov 2026 10:00:00 +0800\r\n'
            'Subject: test\r\nFrom: sender@example.com\r\nTo: receiver@example.com\r\n'
            f'Content-Type: text/plain; charset="{charset}"\r\n'
            'Content-Transfer-Encoding: 8bit\r\n\r\n'
        ).encode('ascii')
        connection = _FakeImapConnection()
        connection.responses['search'] = ('OK', [b'1'])
        connection.responses['fetch'] = ('OK', [(b'1 (BODY.PEEK[] {123}', headers + payload)])
        _install_fake_imap(monkeypatch, connection)

        result = ImapMailbox(
            host='imap.example.com', address='test@example.com', password='secret',
        ).get_mail_list(None, 'UNSEEN')

        assert result[0].body == expected
        assert connection.calls[-1] == ('logout',)

    def test_whitespace_html_is_empty_instead_of_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.plugins.omega_email.mailbox import ImapMailbox

        connection = _FakeImapConnection()
        connection.responses['search'] = ('OK', [b'1'])
        connection.responses['fetch'] = (
            'OK', [(b'1 (BODY.PEEK[] {123}', _make_email_bytes(body='plain', html=' '))],
        )
        _install_fake_imap(monkeypatch, connection)

        result = ImapMailbox(
            host='imap.example.com', address='test@example.com', password='secret',
        ).get_mail_list(None, 'UNSEEN')

        assert result[0].body == 'plain\n'
        assert result[0].html == ''
        assert connection.calls[-1] == ('logout',)

    def test_empty_search_response_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.plugins.omega_email.mailbox import ImapMailbox

        connection = _FakeImapConnection()
        connection.responses['search'] = ('OK', [])
        _install_fake_imap(monkeypatch, connection)

        result = ImapMailbox(
            host='imap.example.com', address='test@example.com', password='secret',
        ).get_mail_list(None, 'UNSEEN')

        assert result == []
        assert connection.calls[-1] == ('logout',)

    @pytest.mark.parametrize('fetch_data', [
        pytest.param(None, id='none_data'),
        pytest.param([], id='empty_data'),
        pytest.param([None], id='none_content'),
        pytest.param([b'unexpected'], id='bytes_content'),
        pytest.param([(b'incomplete',)], id='short_tuple'),
        pytest.param([(b'header', 'not bytes')], id='non_bytes_payload'),
    ])
    def test_invalid_fetch_entries_are_skipped(
            self,
            monkeypatch: pytest.MonkeyPatch,
            fetch_data: list[Any] | None,
    ) -> None:
        from src.plugins.omega_email.mailbox import ImapMailbox

        connection = _FakeImapConnection()
        connection.responses['search'] = ('OK', [b'1'])
        connection.responses['fetch'] = ('OK', fetch_data)
        _install_fake_imap(monkeypatch, connection)

        result = ImapMailbox(
            host='imap.example.com', address='test@example.com', password='secret',
        ).get_mail_list(None, 'UNSEEN')

        assert result == []
        assert connection.calls[-1] == ('logout',)

    def test_bad_message_does_not_block_following_message(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import email as std_email

        import src.plugins.omega_email.mailbox as mailbox_module
        from src.plugins.omega_email.mailbox import ImapMailbox

        good_message = _make_email_bytes(subject='good', body='valid')
        connection = _FakeImapConnection()
        connection.responses['search'] = ('OK', [b'1 2'])
        connection.responses['fetch:1'] = ('OK', [(b'1 (BODY.PEEK[] {3}', b'bad')])
        connection.responses['fetch:2'] = ('OK', [(b'2 (BODY.PEEK[] {123}', good_message)])
        _install_fake_imap(monkeypatch, connection)

        real_message_from_bytes = std_email.message_from_bytes

        def message_from_bytes(data: bytes):
            if data == b'bad':
                raise ValueError('bad message')
            return real_message_from_bytes(data)

        rebind_module_namespace(monkeypatch, mailbox_module, 'email', message_from_bytes=message_from_bytes)

        result = ImapMailbox(
            host='imap.example.com', address='test@example.com', password='secret',
        ).get_mail_list(None, 'UNSEEN')

        assert [mail.header for mail in result] == ['good']
        assert [mail.uid for mail in result] == ['2']
        assert ('uid', 'FETCH', '2', '(BODY.PEEK[])') in connection.calls
        assert _seen_store_calls(connection) == []
        assert connection.calls[-1] == ('logout',)

    def test_get_mail_list_never_calls_store(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.plugins.omega_email.mailbox import ImapMailbox

        raw_message = _make_email_bytes(subject='good', body='valid')
        connection = _FakeImapConnection()
        connection.responses['search'] = ('OK', [b'1'])
        connection.responses['fetch'] = ('OK', [(b'1 (BODY.PEEK[] {123}', raw_message)])
        connection.errors['store'] = RuntimeError('store must not be called')
        _install_fake_imap(monkeypatch, connection)

        result = ImapMailbox(
            host='imap.example.com', address='test@example.com', password='secret',
        ).get_mail_list(None, 'UNSEEN')

        assert [mail.header for mail in result] == ['good']
        assert _seen_store_calls(connection) == []
        assert connection.calls[-1] == ('logout',)

    def test_later_fetch_failure_leaves_all_messages_unread(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.plugins.omega_email.mailbox import ImapMailbox

        connection = _FakeImapConnection()
        connection.responses['search'] = ('OK', [b'101 102'])
        connection.responses['fetch:101'] = (
            'OK', [(b'101 (BODY.PEEK[] {123}', _make_email_bytes(subject='first'))],
        )
        error = RuntimeError('second fetch failed')
        connection.errors['fetch:102'] = error
        _install_fake_imap(monkeypatch, connection)

        with pytest.raises(RuntimeError) as exc_info:
            ImapMailbox(
                host='imap.example.com', address='test@example.com', password='secret',
            ).get_mail_list(None, 'UNSEEN')

        assert exc_info.value is error
        assert _seen_store_calls(connection) == []
        assert connection.calls[-1] == ('logout',)

    def test_invalid_uid_entries_are_skipped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.plugins.omega_email.mailbox import ImapMailbox

        connection = _FakeImapConnection()
        connection.responses['search'] = ('OK', [b'0 abc 101'])
        _install_fake_imap(monkeypatch, connection)

        result = ImapMailbox(
            host='imap.example.com', address='test@example.com', password='secret',
        ).get_mail_list(None, 'UNSEEN')

        assert result == []
        uid_fetch_calls = [call for call in connection.calls if call[:2] == ('uid', 'FETCH')]
        assert uid_fetch_calls == [('uid', 'FETCH', '101', '(BODY.PEEK[])')]
        assert _seen_store_calls(connection) == []

    def test_parse_html_decodes_nbsp_into_character(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """真实解析路径: html 中的 &nbsp; 实体经 lxml 解析后解码为 U+00A0 字符(而非字面 '&nbsp;')"""
        from src.plugins.omega_email.mailbox import ImapMailbox

        raw_message = _make_email_bytes(body='plain', html='<p>a&nbsp;&nbsp;b</p>')
        connection = _FakeImapConnection()
        connection.responses['search'] = ('OK', [b'1'])
        connection.responses['fetch'] = ('OK', [(b'1 (BODY.PEEK[] {123}', raw_message)])
        _install_fake_imap(monkeypatch, connection)

        result = ImapMailbox(
            host='imap.example.com', address='test@example.com', password='secret',
        ).get_mail_list(None, 'UNSEEN')

        assert result[0].html == 'a\xa0\xa0b\n'
        assert connection.calls[-1] == ('logout',)


class TestImap163Extension:

    def test_id_command_registration_is_restored_when_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import imaplib as real_imaplib

        import src.plugins.omega_email.mailbox as mailbox_module
        from src.plugins.omega_email.mailbox import ImapMailbox

        real_commands_snapshot = dict(real_imaplib.Commands)
        connection = _FakeImapConnection()
        _install_fake_imap(monkeypatch, connection)
        mailbox_module.imaplib.Commands.pop('ID', None)

        result = ImapMailbox(
            host='imap.163.com', address='test@163.com', password='secret',
        ).get_mail_list(None, 'UNSEEN')

        assert result == []
        assert 'ID' not in mailbox_module.imaplib.Commands
        assert real_imaplib.Commands == real_commands_snapshot
        assert connection.calls[-1] == ('logout',)

    def test_existing_id_command_registration_is_restored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import src.plugins.omega_email.mailbox as mailbox_module
        from src.plugins.omega_email.mailbox import ImapMailbox

        connection = _FakeImapConnection()
        _install_fake_imap(monkeypatch, connection)
        mailbox_module.imaplib.Commands['ID'] = ('CUSTOM',)

        ImapMailbox(host='imap.163.com', address='test@163.com', password='secret').get_mail_list(None, 'UNSEEN')

        assert mailbox_module.imaplib.Commands['ID'] == ('CUSTOM',)

    def test_id_error_status_is_rejected_and_registration_restored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import imaplib

        import src.plugins.omega_email.mailbox as mailbox_module
        from src.plugins.omega_email.mailbox import ImapMailbox

        connection = _FakeImapConnection()
        connection.responses['ID'] = ('NO', [b'ID rejected'])
        _install_fake_imap(monkeypatch, connection)
        mailbox_module.imaplib.Commands.pop('ID', None)

        with pytest.raises(imaplib.IMAP4.error, match='ID'):
            ImapMailbox(host='imap.163.com', address='test@163.com', password='secret').get_mail_list(None, 'UNSEEN')

        assert 'ID' not in mailbox_module.imaplib.Commands
        assert connection.calls[-1] == ('logout',)

    def test_id_exception_preserves_error_and_restores_registration(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import src.plugins.omega_email.mailbox as mailbox_module
        from src.plugins.omega_email.mailbox import ImapMailbox

        connection = _FakeImapConnection()
        error = RuntimeError('ID failed')
        connection.errors['ID'] = error
        _install_fake_imap(monkeypatch, connection)
        mailbox_module.imaplib.Commands.pop('ID', None)

        with pytest.raises(RuntimeError) as exc_info:
            ImapMailbox(host='imap.163.com', address='test@163.com', password='secret').get_mail_list(None, 'UNSEEN')

        assert exc_info.value is error
        assert 'ID' not in mailbox_module.imaplib.Commands
        assert connection.calls[-1] == ('logout',)

    def test_non_163_account_does_not_send_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import src.plugins.omega_email.mailbox as mailbox_module
        from src.plugins.omega_email.mailbox import ImapMailbox

        connection = _FakeImapConnection()
        _install_fake_imap(monkeypatch, connection)
        commands_snapshot = dict(mailbox_module.imaplib.Commands)

        ImapMailbox(host='imap.example.com', address='test@example.com', password='secret').get_mail_list(
            None, 'UNSEEN',
        )

        assert not any(call[0] == '_simple_command' for call in connection.calls)
        assert mailbox_module.imaplib.Commands == commands_snapshot


class TestEmailAddressValidation:

    @pytest.mark.parametrize('address', [
        pytest.param('a@x.io', id='short_local'),
        pytest.param('user.name+tag@example-mail.com', id='plus_and_hyphen'),
        pytest.param(f'{"a" * (64 - len("@example.com"))}@example.com', id='database_max_length'),
    ])
    def test_valid_addresses(self, address: str) -> None:
        from src.plugins.omega_email.helpers import is_valid_email_address

        assert len(address) <= 64
        assert is_valid_email_address(address) is True

    @pytest.mark.parametrize('address', [
        pytest.param('', id='empty'),
        pytest.param(' ', id='whitespace'),
        pytest.param('userexample.com', id='missing_at'),
        pytest.param('user@@example.com', id='multiple_at'),
        pytest.param('.user@example.com', id='local_leading_dot'),
        pytest.param('user.@example.com', id='local_trailing_dot'),
        pytest.param('user..name@example.com', id='local_consecutive_dots'),
        pytest.param('user@example..com', id='domain_empty_label'),
        pytest.param('user@-example.com', id='domain_leading_hyphen'),
        pytest.param('user@example-.com', id='domain_trailing_hyphen'),
        pytest.param('user@example.c', id='short_tld'),
        pytest.param('user@example', id='missing_tld'),
        pytest.param('用户@example.com', id='non_ascii'),
        pytest.param('user@example.com\n', id='trailing_newline'),
        pytest.param(f'{"a" * (65 - len("@example.com"))}@example.com', id='over_database_limit'),
    ])
    def test_invalid_addresses(self, address: str) -> None:
        from src.plugins.omega_email.helpers import is_valid_email_address

        assert is_valid_email_address(address) is False


class TestMailboxHelpers:

    async def test_database_roundtrip_and_update(
            self,
            app: App,
            mailbox_settings_cleanup: list[str],
    ) -> None:
        from src.database.internal.system_setting import SystemSettingDAL
        from src.plugins.omega_email.consts import DB_MAILBOX_ACCOUNT_SETTING_NAME
        from src.plugins.omega_email.helpers import (
            MailboxServer,
            load_mailbox_from_database,
            query_available_mailbox_address,
            save_mailbox_into_database,
        )

        address = _test_address()
        mailbox_settings_cleanup.append(address)
        await save_mailbox_into_database(address, 'imap.example.com', 'first-password', 'imap', 993)
        await save_mailbox_into_database(address, 'imap.example.com', 'second-password', 'imap', 993)

        account = await load_mailbox_from_database(address)
        available = await query_available_mailbox_address()
        async with SystemSettingDAL.create() as dal:
            row = await dal.query_unique(setting_name=DB_MAILBOX_ACCOUNT_SETTING_NAME, setting_key=address)
        stored_server = MailboxServer.model_validate_json(row.setting_value)

        assert account is not None
        assert account.address == address
        assert account.server.server_host == 'imap.example.com'
        assert account.server.password == 'second-password'
        assert account.server.protocol == 'imap'
        assert account.server.port == 993
        assert available.count(address) == 1
        assert stored_server.password.startswith('v2:')
        assert stored_server.password not in {'first-password', 'second-password'}
        assert 'second-password' not in row.setting_value

    async def test_save_invalid_address_before_encryption(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import AsyncMock

        import src.plugins.omega_email.helpers as helpers_module

        encrypt = AsyncMock()
        monkeypatch.setattr(helpers_module, '_encrypt_password', encrypt)

        with pytest.raises(ValueError, match='Invalid email address'):
            await helpers_module.save_mailbox_into_database('invalid', 'imap.example.com', 'secret', 'imap', 993)

        encrypt.assert_not_awaited()

    async def test_load_missing_account(self, app: App) -> None:
        """记录不存在: 返回 None 且仅记录 WARNING(不产生误导性 ERROR)"""
        from loguru import logger

        from src.plugins.omega_email.helpers import load_mailbox_from_database

        log_levels: list[str] = []
        sink_id = logger.add(lambda message: log_levels.append(message.record['level'].name), level='DEBUG')
        try:
            assert await load_mailbox_from_database(_test_address()) is None
        finally:
            logger.remove(sink_id)

        assert 'WARNING' in log_levels
        assert 'ERROR' not in log_levels

    @pytest.mark.parametrize('setting_value', [
        pytest.param('not-json', id='invalid_json'),
        pytest.param('{}', id='missing_fields'),
        pytest.param(
            '{"server_host":"imap.example.com","password":"tampered","protocol":"imap","port":993}',
            id='invalid_ciphertext',
        ),
    ])
    async def test_load_corrupt_account_returns_none(
            self,
            app: App,
            mailbox_settings_cleanup: list[str],
            setting_value: str,
    ) -> None:
        from src.database.internal.system_setting import SystemSettingDAL
        from src.plugins.omega_email.consts import DB_MAILBOX_ACCOUNT_SETTING_NAME
        from src.plugins.omega_email.helpers import load_mailbox_from_database

        address = _test_address()
        mailbox_settings_cleanup.append(address)
        async with SystemSettingDAL.create() as dal:
            await dal.add_update_exist(
                setting_name=DB_MAILBOX_ACCOUNT_SETTING_NAME,
                setting_key=address,
                setting_value=setting_value,
            )

        assert await load_mailbox_from_database(address) is None

    async def test_load_database_error_returns_none(self, app: App, monkeypatch: pytest.MonkeyPatch) -> None:
        """数据库故障: 返回 None 且记录 ERROR"""
        from loguru import logger

        import src.plugins.omega_email.helpers as helpers_module

        class BrokenDAL:
            @classmethod
            def create(cls) -> Any:
                raise RuntimeError('database unavailable')

        monkeypatch.setattr(helpers_module, 'SystemSettingDAL', BrokenDAL)

        log_levels: list[str] = []
        sink_id = logger.add(lambda message: log_levels.append(message.record['level'].name), level='DEBUG')
        try:
            assert await helpers_module.load_mailbox_from_database('test@example.com') is None
        finally:
            logger.remove(sink_id)

        assert 'ERROR' in log_levels

    async def test_check_mailbox_success_and_failure(self, app: App, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import Mock

        import src.plugins.omega_email.helpers as helpers_module

        mailbox = Mock()
        factory = Mock(return_value=mailbox)
        monkeypatch.setattr(helpers_module, 'ImapMailbox', factory)

        assert await helpers_module.check_mailbox('test@example.com', 'imap.example.com', 'secret') is True
        factory.assert_called_once_with(host='imap.example.com', address='test@example.com', password='secret')

        mailbox.check.side_effect = RuntimeError('login failed')
        assert await helpers_module.check_mailbox('test@example.com', 'imap.example.com', 'secret') is False

    @pytest.mark.parametrize(('port', 'expected_port'), [
        pytest.param(None, 993, id='default_port'),
        pytest.param(1993, 1993, id='custom_port'),
    ])
    async def test_get_unseen_mail_data_uses_unseen_criterion(
            self,
            app: App,
            monkeypatch: pytest.MonkeyPatch,
            port: int | None,
            expected_port: int,
    ) -> None:
        from unittest.mock import Mock

        import src.plugins.omega_email.helpers as helpers_module
        from src.plugins.omega_email.mailbox import Email

        mail = Email(date='date', header='header', sender='sender', to='to', body='body')
        mailbox = Mock()
        mailbox.get_mail_list.return_value = [mail]
        factory = Mock(return_value=mailbox)
        monkeypatch.setattr(helpers_module, 'ImapMailbox', factory)

        kwargs = {} if port is None else {'port': port}
        result = await helpers_module.get_unseen_mail_data('test@example.com', 'imap.example.com', 'secret', **kwargs)

        assert result == [mail]
        factory.assert_called_once_with(
            host='imap.example.com', address='test@example.com', password='secret', port=expected_port,
        )
        mailbox.get_mail_list.assert_called_once_with(None, 'UNSEEN')

    @pytest.mark.parametrize('content', ['中文邮件\n\n正文', ''])
    async def test_generate_mail_snapshot(self, app: App, content: str) -> None:
        from pathlib import Path

        from src.plugins.omega_email.helpers import generate_mail_snapshot

        resource = await generate_mail_snapshot(content)
        image_path = Path(resource.resolve_path)
        try:
            assert image_path.is_file()
            assert image_path.suffix == '.jpg'
            assert image_path.read_bytes().startswith(b'\xff\xd8')
        finally:
            image_path.unlink(missing_ok=True)


class TestMailboxEntityBinding:

    async def test_bind_query_unbind_and_repeat(self, app: App, numeric_bot: Any) -> None:
        from src.plugins.omega_email.consts import DB_ENTITY_SETTING_MODULE_NAME, DB_ENTITY_SETTING_PLUGIN_NAME
        from src.plugins.omega_email.helpers import (
            bind_entity_mailbox,
            query_entity_bound_mailbox,
            unbind_entity_mailbox,
        )

        user_id = _random_user_id(numeric_bot.self_id)
        interface = _MailboxEntityInterface(numeric_bot, user_id)
        enabled_address = _test_address()
        disabled_address = _test_address()

        await bind_entity_mailbox(interface, enabled_address)
        await bind_entity_mailbox(interface, enabled_address)
        await bind_entity_mailbox(interface, disabled_address)
        await unbind_entity_mailbox(interface, disabled_address)

        assert await query_entity_bound_mailbox(interface) == [enabled_address]

        await unbind_entity_mailbox(interface, enabled_address)
        await unbind_entity_mailbox(interface, enabled_address)
        assert await query_entity_bound_mailbox(interface) == []

        async with obv11_user_entity(numeric_bot, str(user_id)) as entity:
            disabled_setting = await entity.query_auth_setting(
                module=DB_ENTITY_SETTING_MODULE_NAME,
                plugin=DB_ENTITY_SETTING_PLUGIN_NAME,
                node=disabled_address,
            )
            enabled_setting = await entity.query_auth_setting(
                module=DB_ENTITY_SETTING_MODULE_NAME,
                plugin=DB_ENTITY_SETTING_PLUGIN_NAME,
                node=enabled_address,
            )
        assert disabled_setting.available == 0
        assert disabled_setting.value == {}
        assert enabled_setting.available == 0
        assert enabled_setting.value == {}


@pytest.mark.usefixtures('email_plugin_enabled_guard')
class TestMailboxManagerCommands:

    async def test_main_default_reply(self, app: App, numeric_bot: Any) -> None:
        from src.plugins.omega_email.command import mailbox_manager

        user_id = _random_user_id(numeric_bot.self_id)
        await _seed_user_permissions(numeric_bot, user_id)
        event = _private_event(
            user_id=user_id, text='/邮箱', self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(mailbox_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_pass_rule(matcher=mailbox_manager)
            ctx.should_pass_permission(matcher=mailbox_manager)
            ctx.should_call_send(
                event, expected_reply(event, '邮箱插件, 可用子命令：<添加|绑定|解绑|收件>, 使用帮助查看详细使用方法'),
            )

    async def test_add_with_all_options_success(
            self,
            app: App,
            numeric_bot: Any,
            superuser_int_id: int,
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from unittest.mock import AsyncMock

        import src.plugins.omega_email.command as command_module

        check = AsyncMock(return_value=True)
        save = AsyncMock()
        monkeypatch.setattr(command_module, 'check_mailbox', check)
        monkeypatch.setattr(command_module, 'save_mailbox_into_database', save)
        event = _private_event(
            user_id=superuser_int_id,
            text='/邮箱 添加 -s imap.example.com -a test@example.com -p secret',
            self_id=int(numeric_bot.self_id),
            message_id=_random_message_id(),
        )

        async with app.test_matcher(command_module.mailbox_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, '添加邮箱 test@example.com 成功'))

        check.assert_awaited_once_with(address='test@example.com', server_host='imap.example.com', password='secret')
        save.assert_awaited_once_with(
            address='test@example.com', server_host='imap.example.com', password='secret', protocol='imap', port=993,
        )

    async def test_add_invalid_address_skips_network_and_database(
            self,
            app: App,
            numeric_bot: Any,
            superuser_int_id: int,
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from unittest.mock import AsyncMock

        import src.plugins.omega_email.command as command_module

        check = AsyncMock()
        save = AsyncMock()
        monkeypatch.setattr(command_module, 'check_mailbox', check)
        monkeypatch.setattr(command_module, 'save_mailbox_into_database', save)
        event = _private_event(
            user_id=superuser_int_id, text='/邮箱 添加 -s imap.example.com -a invalid -p secret',
            self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(command_module.mailbox_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, '输入的不是有效的邮箱地址, 请确认后重试'))

        check.assert_not_awaited()
        save.assert_not_awaited()

    @pytest.mark.parametrize(('check_succeeds', 'save_error', 'expected_text'), [
        pytest.param(False, None, '验证邮箱信息失败, 请检查邮箱信息或稍后再试', id='check_failed'),
        pytest.param(True, RuntimeError('db failed'), '添加邮箱失败, 数据库写入失败, 详情请查看日志', id='save_failed'),
    ])
    async def test_add_failures(
            self,
            app: App,
            numeric_bot: Any,
            superuser_int_id: int,
            monkeypatch: pytest.MonkeyPatch,
            check_succeeds: bool,
            save_error: Exception | None,
            expected_text: str,
    ) -> None:
        from unittest.mock import AsyncMock

        import src.plugins.omega_email.command as command_module

        save = AsyncMock(side_effect=save_error)
        monkeypatch.setattr(command_module, 'check_mailbox', AsyncMock(return_value=check_succeeds))
        monkeypatch.setattr(command_module, 'save_mailbox_into_database', save)
        event = _private_event(
            user_id=superuser_int_id, text='/邮箱 添加 -s imap.example.com -a test@example.com -p secret',
            self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(command_module.mailbox_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, expected_text))

        assert save.await_count == int(check_succeeds)

    async def test_add_full_prompt_flow(
            self,
            app: App,
            numeric_bot: Any,
            superuser_int_id: int,
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from unittest.mock import AsyncMock

        import src.plugins.omega_email.command as command_module

        answers = iter(['imap.example.com', 'test@example.com', 'secret'])
        prompts: list[tuple[str, float]] = []

        async def fake_ensure_arg_text(*, prompt_text: str, timeout: float, **_kwargs) -> str:
            prompts.append((prompt_text, timeout))
            return next(answers)

        monkeypatch.setattr(command_module, 'ensure_arg_text', fake_ensure_arg_text)
        monkeypatch.setattr(command_module, 'check_mailbox', AsyncMock(return_value=True))
        monkeypatch.setattr(command_module, 'save_mailbox_into_database', AsyncMock())
        event = _private_event(
            user_id=superuser_int_id, text='/邮箱 添加', self_id=int(numeric_bot.self_id),
            message_id=_random_message_id(),
        )

        async with app.test_matcher(command_module.mailbox_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, '添加邮箱 test@example.com 成功'))

        assert prompts == [
            ('请输入邮箱IMAP服务器地址:', 60),
            ('请输入邮箱地址:', 60),
            ('【警告】在会话中添加邮箱可能导致账号信息泄露, 强烈建议使用内置工具在命令行导入\n\n请输入邮箱密码:', 60),
        ]

    async def test_add_by_non_superuser_silenced(self, app: App, numeric_bot: Any) -> None:
        from src.plugins.omega_email.command import mailbox_manager

        user_id = _random_user_id(numeric_bot.self_id)
        await _seed_user_permissions(numeric_bot, user_id)
        event = _private_event(
            user_id=user_id, text='/邮箱 添加 -s imap.example.com -a test@example.com -p secret',
            self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(mailbox_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)

    @pytest.mark.parametrize(('query_result', 'expected_text'), [
        pytest.param([], '无可绑定邮箱, 请联系管理员添加邮箱后再试', id='empty'),
        pytest.param(RuntimeError('db failed'), '查询可用邮箱失败, 详情请查看日志', id='query_error'),
    ])
    async def test_bind_query_empty_or_error(
            self,
            app: App,
            numeric_bot: Any,
            monkeypatch: pytest.MonkeyPatch,
            query_result: list[str] | Exception,
            expected_text: str,
    ) -> None:
        from unittest.mock import AsyncMock

        import src.plugins.omega_email.command as command_module

        monkeypatch.setattr(command_module, 'query_available_mailbox_address', AsyncMock(return_value=query_result))
        if isinstance(query_result, Exception):
            monkeypatch.setattr(
                command_module, 'query_available_mailbox_address', AsyncMock(side_effect=query_result),
            )
        user_id = _random_user_id(numeric_bot.self_id)
        await _seed_user_permissions(numeric_bot, user_id)
        event = _private_event(
            user_id=user_id, text='/邮箱 绑定', self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(command_module.mailbox_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, expected_text))

    @pytest.mark.parametrize(('address', 'expected_text'), [
        pytest.param('invalid', '输入的不是有效的邮箱地址, 请确认后重试', id='invalid'),
        pytest.param(
            'other@example.com',
            'other@example.com 不是可用的邮箱地址, 请确认后重试或请管理员添加该邮箱',
            id='unavailable',
        ),
    ])
    async def test_bind_rejects_invalid_or_unavailable_address(
            self,
            app: App,
            numeric_bot: Any,
            monkeypatch: pytest.MonkeyPatch,
            address: str,
            expected_text: str,
    ) -> None:
        from unittest.mock import AsyncMock

        import src.plugins.omega_email.command as command_module

        bind = AsyncMock()
        monkeypatch.setattr(
            command_module, 'query_available_mailbox_address', AsyncMock(return_value=['test@example.com']),
        )
        monkeypatch.setattr(command_module, 'bind_entity_mailbox', bind)
        user_id = _random_user_id(numeric_bot.self_id)
        await _seed_user_permissions(numeric_bot, user_id)
        event = _private_event(
            user_id=user_id, text=f'/邮箱 绑定 -a {address}', self_id=int(numeric_bot.self_id),
            message_id=_random_message_id(),
        )

        async with app.test_matcher(command_module.mailbox_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, expected_text))

        bind.assert_not_awaited()

    async def test_bind_operation_failure(self, app: App, numeric_bot: Any, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import AsyncMock

        import src.plugins.omega_email.command as command_module

        monkeypatch.setattr(
            command_module, 'query_available_mailbox_address', AsyncMock(return_value=['test@example.com']),
        )
        monkeypatch.setattr(command_module, 'bind_entity_mailbox', AsyncMock(side_effect=RuntimeError('db failed')))
        user_id = _random_user_id(numeric_bot.self_id)
        await _seed_user_permissions(numeric_bot, user_id)
        event = _private_event(
            user_id=user_id, text='/邮箱 绑定 -a test@example.com', self_id=int(numeric_bot.self_id),
            message_id=_random_message_id(),
        )

        async with app.test_matcher(command_module.mailbox_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event, expected_reply(event, '绑定邮箱 test@example.com 失败, 请稍后再试或联系管理员处理'),
            )

    async def test_bind_prompt_success_updates_real_entity(
            self,
            app: App,
            numeric_bot: Any,
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from unittest.mock import AsyncMock

        import src.plugins.omega_email.command as command_module
        from src.plugins.omega_email.consts import DB_ENTITY_SETTING_MODULE_NAME, DB_ENTITY_SETTING_PLUGIN_NAME

        address = _test_address()
        monkeypatch.setattr(command_module, 'query_available_mailbox_address', AsyncMock(return_value=[address]))

        async def fake_ensure_arg_text(*, prompt_text: str, timeout: float, **_kwargs) -> str:
            assert prompt_text == f'请输入需要绑定的邮箱地址:\n\n{address}'
            assert timeout == 60
            return address

        monkeypatch.setattr(command_module, 'ensure_arg_text', fake_ensure_arg_text)
        user_id = _random_user_id(numeric_bot.self_id)
        await _seed_user_permissions(numeric_bot, user_id)
        event = _private_event(
            user_id=user_id, text='/邮箱 绑定', self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(command_module.mailbox_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, f'绑定邮箱 {address} 成功'))

        async with obv11_user_entity(numeric_bot, str(user_id)) as entity:
            setting = await entity.query_auth_setting(
                module=DB_ENTITY_SETTING_MODULE_NAME, plugin=DB_ENTITY_SETTING_PLUGIN_NAME, node=address,
            )
        assert setting.available == 1
        assert setting.value == {'bound_email': address}

    @pytest.mark.parametrize(('query_result', 'expected_text'), [
        pytest.param([], '无已绑定邮箱, 无需解绑', id='empty'),
        pytest.param(RuntimeError('db failed'), '查询已绑定邮箱失败, 详情请查看日志', id='query_error'),
    ])
    async def test_unbind_query_empty_or_error(
            self,
            app: App,
            numeric_bot: Any,
            monkeypatch: pytest.MonkeyPatch,
            query_result: list[str] | Exception,
            expected_text: str,
    ) -> None:
        from unittest.mock import AsyncMock

        import src.plugins.omega_email.command as command_module

        query = AsyncMock(return_value=query_result)
        if isinstance(query_result, Exception):
            query = AsyncMock(side_effect=query_result)
        monkeypatch.setattr(command_module, 'query_entity_bound_mailbox', query)
        user_id = _random_user_id(numeric_bot.self_id)
        await _seed_user_permissions(numeric_bot, user_id)
        event = _private_event(
            user_id=user_id, text='/邮箱 解绑', self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(command_module.mailbox_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, expected_text))

    @pytest.mark.parametrize(('address', 'expected_text'), [
        pytest.param('invalid', '输入的不是有效的邮箱地址, 请确认后重试', id='invalid'),
        pytest.param('other@example.com', 'other@example.com 不是已绑定的邮箱地址, 请确认后重试', id='not_bound'),
    ])
    async def test_unbind_rejects_invalid_or_unbound_address(
            self,
            app: App,
            numeric_bot: Any,
            monkeypatch: pytest.MonkeyPatch,
            address: str,
            expected_text: str,
    ) -> None:
        from unittest.mock import AsyncMock

        import src.plugins.omega_email.command as command_module

        unbind = AsyncMock()
        monkeypatch.setattr(command_module, 'query_entity_bound_mailbox', AsyncMock(return_value=['test@example.com']))
        monkeypatch.setattr(command_module, 'unbind_entity_mailbox', unbind)
        user_id = _random_user_id(numeric_bot.self_id)
        await _seed_user_permissions(numeric_bot, user_id)
        event = _private_event(
            user_id=user_id, text=f'/邮箱 解绑 -a {address}', self_id=int(numeric_bot.self_id),
            message_id=_random_message_id(),
        )

        async with app.test_matcher(command_module.mailbox_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, expected_text))

        unbind.assert_not_awaited()

    async def test_unbind_operation_failure(self, app: App, numeric_bot: Any, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import AsyncMock

        import src.plugins.omega_email.command as command_module

        monkeypatch.setattr(command_module, 'query_entity_bound_mailbox', AsyncMock(return_value=['test@example.com']))
        monkeypatch.setattr(command_module, 'unbind_entity_mailbox', AsyncMock(side_effect=RuntimeError('db failed')))
        user_id = _random_user_id(numeric_bot.self_id)
        await _seed_user_permissions(numeric_bot, user_id)
        event = _private_event(
            user_id=user_id, text='/邮箱 解绑 -a test@example.com', self_id=int(numeric_bot.self_id),
            message_id=_random_message_id(),
        )

        async with app.test_matcher(command_module.mailbox_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event, expected_reply(event, '解绑邮箱 test@example.com 失败, 请稍后再试或联系管理员处理'),
            )

    async def test_unbind_prompt_success_updates_real_entity(
            self,
            app: App,
            numeric_bot: Any,
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import src.plugins.omega_email.command as command_module
        from src.plugins.omega_email.consts import DB_ENTITY_SETTING_MODULE_NAME, DB_ENTITY_SETTING_PLUGIN_NAME
        from src.plugins.omega_email.helpers import bind_entity_mailbox

        address = _test_address()
        user_id = _random_user_id(numeric_bot.self_id)
        await _seed_user_permissions(numeric_bot, user_id)
        await bind_entity_mailbox(_MailboxEntityInterface(numeric_bot, user_id), address)

        async def fake_ensure_arg_text(*, prompt_text: str, timeout: float, **_kwargs) -> str:
            assert prompt_text == f'请输入需要解绑的邮箱地址:\n\n{address}'
            assert timeout == 60
            return address

        monkeypatch.setattr(command_module, 'ensure_arg_text', fake_ensure_arg_text)
        event = _private_event(
            user_id=user_id, text='/邮箱 解绑', self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

        async with app.test_matcher(command_module.mailbox_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, f'解绑邮箱 {address} 成功'))

        async with obv11_user_entity(numeric_bot, str(user_id)) as entity:
            setting = await entity.query_auth_setting(
                module=DB_ENTITY_SETTING_MODULE_NAME, plugin=DB_ENTITY_SETTING_PLUGIN_NAME, node=address,
            )
        assert setting.available == 0
        assert setting.value == {}

    @pytest.mark.parametrize('subcommand', ['绑定', '解绑'])
    async def test_bind_unbind_by_group_member_silenced(
            self,
            app: App,
            numeric_bot: Any,
            subcommand: str,
    ) -> None:
        from src.plugins.omega_email.command import mailbox_manager

        group_id = random.randint(10_000_000, 99_999_999)
        await _seed_group_permissions(numeric_bot, group_id)
        event = _group_event(
            group_id=group_id,
            user_id=_random_user_id(numeric_bot.self_id),
            text=f'/邮箱 {subcommand} -a test@example.com',
            self_id=int(numeric_bot.self_id),
            message_id=_random_message_id(),
            role='member',
        )

        async with app.test_matcher(mailbox_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)


@pytest.mark.usefixtures('email_plugin_enabled_guard')
class TestReceiveEmailCommand:

    @staticmethod
    async def _make_event(numeric_bot: Any) -> Any:
        user_id = _random_user_id(numeric_bot.self_id)
        await _seed_user_permissions(numeric_bot, user_id)
        return _private_event(
            user_id=user_id, text='/邮箱 收件', self_id=int(numeric_bot.self_id), message_id=_random_message_id(),
        )

    async def test_receive_bound_query_error(self, app: App, numeric_bot: Any, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import AsyncMock

        import src.plugins.omega_email.command as command_module

        monkeypatch.setattr(
            command_module, 'query_entity_bound_mailbox', AsyncMock(side_effect=RuntimeError('db failed')),
        )
        event = await self._make_event(numeric_bot)

        async with app.test_matcher(command_module.mailbox_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, '查询已绑定邮箱失败, 请稍后重试或联系管理员处理'))

    async def test_receive_without_bound_mailbox(
            self,
            app: App,
            numeric_bot: Any,
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from unittest.mock import AsyncMock

        import src.plugins.omega_email.command as command_module

        monkeypatch.setattr(command_module, 'query_entity_bound_mailbox', AsyncMock(return_value=[]))
        event = await self._make_event(numeric_bot)

        async with app.test_matcher(command_module.mailbox_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected_reply(event, '没有绑定的邮箱, 请先联系管理员绑定邮箱后再收件'))

    async def test_receive_account_read_failure(
            self,
            app: App,
            numeric_bot: Any,
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from unittest.mock import AsyncMock

        import src.plugins.omega_email.command as command_module

        address = _test_address()
        monkeypatch.setattr(command_module, 'query_entity_bound_mailbox', AsyncMock(return_value=[address]))
        monkeypatch.setattr(command_module, 'load_mailbox_from_database', AsyncMock(return_value=None))
        event = await self._make_event(numeric_bot)

        async with app.test_matcher(command_module.mailbox_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event,
                expected_reply(event, f'已绑定邮箱:\n\n{address}\n\n正在连接到邮箱服务器, 请稍候~'),
            )
            ctx.should_call_send(
                event,
                expected_reply(event, f'邮箱: {address}\n账号读取失败, 可能需管理员重新导入, 已跳过'),
            )

    @pytest.mark.parametrize(('fetch_result', 'expected_text'), [
        pytest.param([], '收件完成, 没有新的邮件', id='no_unseen'),
        pytest.param(RuntimeError('imap failed'), '收件失败, 请稍后重试或联系管理员处理', id='fetch_error'),
    ])
    async def test_receive_empty_or_fetch_failure(
            self,
            app: App,
            numeric_bot: Any,
            monkeypatch: pytest.MonkeyPatch,
            fetch_result: list[Any] | Exception,
            expected_text: str,
    ) -> None:
        from unittest.mock import AsyncMock

        import src.plugins.omega_email.command as command_module

        address = _test_address()
        get_unseen = AsyncMock(return_value=fetch_result)
        if isinstance(fetch_result, Exception):
            get_unseen = AsyncMock(side_effect=fetch_result)
        monkeypatch.setattr(command_module, 'query_entity_bound_mailbox', AsyncMock(return_value=[address]))
        monkeypatch.setattr(
            command_module, 'load_mailbox_from_database', AsyncMock(return_value=_make_account(address)),
        )
        monkeypatch.setattr(command_module, 'get_unseen_mail_data', get_unseen)
        event = await self._make_event(numeric_bot)

        async with app.test_matcher(command_module.mailbox_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event, expected_reply(event, f'已绑定邮箱:\n\n{address}\n\n正在连接到邮箱服务器, 请稍候~'),
            )
            ctx.should_call_send(event, expected_reply(event, f'邮箱: {address}\n{expected_text}'))

        get_unseen.assert_awaited_once_with(
            address=address, server_host='imap.example.com', password='secret', port=993,
        )

    async def test_receive_multiple_mailboxes_continue_after_failure(
            self,
            app: App,
            numeric_bot: Any,
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from unittest.mock import AsyncMock

        import src.plugins.omega_email.command as command_module

        failed_address = _test_address()
        good_address = _test_address()
        get_unseen = AsyncMock(side_effect=[RuntimeError('imap failed'), []])
        monkeypatch.setattr(
            command_module,
            'query_entity_bound_mailbox',
            AsyncMock(return_value=[failed_address, good_address]),
        )
        monkeypatch.setattr(
            command_module,
            'load_mailbox_from_database',
            AsyncMock(side_effect=[_make_account(failed_address), _make_account(good_address)]),
        )
        monkeypatch.setattr(command_module, 'get_unseen_mail_data', get_unseen)
        event = await self._make_event(numeric_bot)

        async with app.test_matcher(command_module.mailbox_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event,
                expected_reply(
                    event,
                    f'已绑定邮箱:\n\n{failed_address}\n{good_address}\n\n正在连接到邮箱服务器, 请稍候~',
                ),
            )
            ctx.should_call_send(
                event, expected_reply(event, f'邮箱: {failed_address}\n收件失败, 请稍后重试或联系管理员处理'),
            )
            ctx.should_call_send(
                event, expected_reply(event, f'邮箱: {good_address}\n收件完成, 没有新的邮件'),
            )

        assert get_unseen.await_count == 2

    async def test_receive_marks_seen_only_after_send(
            self,
            app: App,
            numeric_bot: Any,
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from unittest.mock import AsyncMock, Mock

        import src.plugins.omega_email.command as command_module

        address = _test_address()
        image_url = 'https://example.test/mail-success.jpg'
        resource = Mock()
        resource.get_hosting_path = AsyncMock(return_value=('url', image_url))
        generate = AsyncMock(return_value=resource)
        mark_seen = AsyncMock()
        mail = _make_mail('通知', body='plain body', html='HTML正文\n\n\xa0\xa0第二行', uid='101')
        monkeypatch.setattr(command_module, 'query_entity_bound_mailbox', AsyncMock(return_value=[address]))
        monkeypatch.setattr(
            command_module, 'load_mailbox_from_database', AsyncMock(return_value=_make_account(address)),
        )
        monkeypatch.setattr(command_module, 'get_unseen_mail_data', AsyncMock(return_value=[mail]))
        monkeypatch.setattr(command_module, 'generate_mail_snapshot', generate)
        monkeypatch.setattr(command_module, 'mark_mail_as_seen', mark_seen, raising=False)
        event = await self._make_event(numeric_bot)

        async with app.test_matcher(command_module.mailbox_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event, expected_reply(event, f'已绑定邮箱:\n\n{address}\n\n正在连接到邮箱服务器, 请稍候~'),
            )
            ctx.should_call_send(event, _expected_image_reply(event, image_url))
            ctx.should_call_send(event, expected_reply(event, f'邮箱 {address}\n收件完成, 共1封新的邮件'))

        generate.assert_awaited_once_with(
            mail_content=(
                '【通知】\n时间: Mon, 02 Nov 2026 10:00:00 +0800\n'
                '发件人: Sender <sender@example.com>\n================\nHTML正文\n第二行'
            ),
        )
        resource.get_hosting_path.assert_awaited_once_with()
        mark_seen.assert_awaited_once_with(
            address=address, server_host='imap.example.com', password='secret', uid='101', port=993,
        )

    async def test_receive_plain_mail_falls_back_to_body(
            self,
            app: App,
            numeric_bot: Any,
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from unittest.mock import AsyncMock, Mock

        import src.plugins.omega_email.command as command_module

        address = _test_address()
        image_url = 'https://example.test/mail-plain.jpg'
        resource = Mock()
        resource.get_hosting_path = AsyncMock(return_value=('url', image_url))
        generate = AsyncMock(return_value=resource)
        mark_seen = AsyncMock()
        mail = _make_mail('纯文本通知', body='纯文本\n\n正文', html='', uid='102')
        monkeypatch.setattr(command_module, 'query_entity_bound_mailbox', AsyncMock(return_value=[address]))
        monkeypatch.setattr(
            command_module, 'load_mailbox_from_database', AsyncMock(return_value=_make_account(address)),
        )
        monkeypatch.setattr(command_module, 'get_unseen_mail_data', AsyncMock(return_value=[mail]))
        monkeypatch.setattr(command_module, 'generate_mail_snapshot', generate)
        monkeypatch.setattr(command_module, 'mark_mail_as_seen', mark_seen, raising=False)
        event = await self._make_event(numeric_bot)

        async with app.test_matcher(command_module.mailbox_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event, expected_reply(event, f'已绑定邮箱:\n\n{address}\n\n正在连接到邮箱服务器, 请稍候~'),
            )
            ctx.should_call_send(event, _expected_image_reply(event, image_url))
            ctx.should_call_send(event, expected_reply(event, f'邮箱 {address}\n收件完成, 共1封新的邮件'))

        generate.assert_awaited_once_with(
            mail_content=(
                '【纯文本通知】\n时间: Mon, 02 Nov 2026 10:00:00 +0800\n'
                '发件人: Sender <sender@example.com>\n================\n纯文本\n正文'
            ),
        )
        mark_seen.assert_awaited_once_with(
            address=address, server_host='imap.example.com', password='secret', uid='102', port=993,
        )

    async def test_receive_partial_failure_reports_actual_counts(
            self,
            app: App,
            numeric_bot: Any,
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from unittest.mock import AsyncMock, Mock

        import src.plugins.omega_email.command as command_module

        address = _test_address()
        image_url = 'https://example.test/mail-second.jpg'
        resource = Mock()
        resource.get_hosting_path = AsyncMock(return_value=('url', image_url))
        generate = AsyncMock(side_effect=[RuntimeError('render failed'), resource])
        mark_seen = AsyncMock()
        monkeypatch.setattr(command_module, 'query_entity_bound_mailbox', AsyncMock(return_value=[address]))
        monkeypatch.setattr(
            command_module, 'load_mailbox_from_database', AsyncMock(return_value=_make_account(address)),
        )
        monkeypatch.setattr(
            command_module,
            'get_unseen_mail_data',
            AsyncMock(return_value=[
                _make_mail('坏邮件', uid='201'),
                _make_mail('正常邮件', body='第二封正文', uid='202'),
            ]),
        )
        monkeypatch.setattr(command_module, 'generate_mail_snapshot', generate)
        monkeypatch.setattr(command_module, 'mark_mail_as_seen', mark_seen, raising=False)
        event = await self._make_event(numeric_bot)

        async with app.test_matcher(command_module.mailbox_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event, expected_reply(event, f'已绑定邮箱:\n\n{address}\n\n正在连接到邮箱服务器, 请稍候~'),
            )
            ctx.should_call_send(event, _expected_image_reply(event, image_url))
            ctx.should_call_send(
                event,
                expected_reply(
                    event,
                    f'邮箱 {address}\n收件完成, 共2封新的邮件, 发送消息成功1封, 发送消息失败1封',
                ),
            )

        assert generate.await_count == 2
        assert '第二封正文' in generate.await_args_list[1].kwargs['mail_content']
        mark_seen.assert_awaited_once_with(
            address=address, server_host='imap.example.com', password='secret', uid='202', port=993,
        )

    async def test_receive_render_failure_does_not_mark_seen(
            self,
            app: App,
            numeric_bot: Any,
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from unittest.mock import AsyncMock

        import src.plugins.omega_email.command as command_module

        address = _test_address()
        generate = AsyncMock(side_effect=RuntimeError('render failed'))
        mark_seen = AsyncMock()
        monkeypatch.setattr(command_module, 'query_entity_bound_mailbox', AsyncMock(return_value=[address]))
        monkeypatch.setattr(
            command_module, 'load_mailbox_from_database', AsyncMock(return_value=_make_account(address)),
        )
        monkeypatch.setattr(
            command_module, 'get_unseen_mail_data', AsyncMock(return_value=[_make_mail('坏邮件', uid='201')]),
        )
        monkeypatch.setattr(command_module, 'generate_mail_snapshot', generate)
        monkeypatch.setattr(command_module, 'mark_mail_as_seen', mark_seen, raising=False)
        event = await self._make_event(numeric_bot)

        async with app.test_matcher(command_module.mailbox_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event, expected_reply(event, f'已绑定邮箱:\n\n{address}\n\n正在连接到邮箱服务器, 请稍候~'),
            )
            ctx.should_call_send(
                event,
                expected_reply(
                    event,
                    f'邮箱 {address}\n收件完成, 共1封新的邮件, 发送消息成功0封, 发送消息失败1封',
                ),
            )

        mark_seen.assert_not_awaited()

    async def test_receive_send_failure_does_not_mark_seen(
            self,
            app: App,
            numeric_bot: Any,
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from unittest.mock import AsyncMock, Mock

        import src.plugins.omega_email.command as command_module

        address = _test_address()
        image_url = 'https://example.test/mail-send-failed.jpg'
        resource = Mock()
        resource.get_hosting_path = AsyncMock(return_value=('url', image_url))
        generate = AsyncMock(return_value=resource)
        mark_seen = AsyncMock()
        monkeypatch.setattr(command_module, 'query_entity_bound_mailbox', AsyncMock(return_value=[address]))
        monkeypatch.setattr(
            command_module, 'load_mailbox_from_database', AsyncMock(return_value=_make_account(address)),
        )
        monkeypatch.setattr(
            command_module, 'get_unseen_mail_data', AsyncMock(return_value=[_make_mail('发送失败邮件', uid='201')]),
        )
        monkeypatch.setattr(command_module, 'generate_mail_snapshot', generate)
        monkeypatch.setattr(command_module, 'mark_mail_as_seen', mark_seen)
        event = await self._make_event(numeric_bot)

        async with app.test_matcher(command_module.mailbox_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event, expected_reply(event, f'已绑定邮箱:\n\n{address}\n\n正在连接到邮箱服务器, 请稍候~'),
            )
            ctx.should_call_send(
                event,
                _expected_image_reply(event, image_url),
                exception=RuntimeError('send failed'),
            )
            ctx.should_call_send(
                event,
                expected_reply(
                    event,
                    f'邮箱 {address}\n收件完成, 共1封新的邮件, 发送消息成功0封, 发送消息失败1封',
                ),
            )

        generate.assert_awaited_once()
        resource.get_hosting_path.assert_awaited_once_with()
        mark_seen.assert_not_awaited()

    async def test_receive_ack_failure_still_counts_as_sent(
            self,
            app: App,
            numeric_bot: Any,
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from unittest.mock import AsyncMock, Mock

        import src.plugins.omega_email.command as command_module

        address = _test_address()
        image_url = 'https://example.test/mail-ack-failed.jpg'
        resource = Mock()
        resource.get_hosting_path = AsyncMock(return_value=('url', image_url))
        mark_seen = AsyncMock(side_effect=RuntimeError('ack failed'))
        monkeypatch.setattr(command_module, 'query_entity_bound_mailbox', AsyncMock(return_value=[address]))
        monkeypatch.setattr(
            command_module, 'load_mailbox_from_database', AsyncMock(return_value=_make_account(address)),
        )
        monkeypatch.setattr(
            command_module,
            'get_unseen_mail_data',
            AsyncMock(return_value=[_make_mail('已发送邮件', uid='301')]),
        )
        monkeypatch.setattr(command_module, 'generate_mail_snapshot', AsyncMock(return_value=resource))
        monkeypatch.setattr(command_module, 'mark_mail_as_seen', mark_seen, raising=False)
        event = await self._make_event(numeric_bot)

        async with app.test_matcher(command_module.mailbox_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event, expected_reply(event, f'已绑定邮箱:\n\n{address}\n\n正在连接到邮箱服务器, 请稍候~'),
            )
            ctx.should_call_send(event, _expected_image_reply(event, image_url))
            ctx.should_call_send(event, expected_reply(event, f'邮箱 {address}\n收件完成, 共1封新的邮件'))

        mark_seen.assert_awaited_once_with(
            address=address, server_host='imap.example.com', password='secret', uid='301', port=993,
        )

    async def test_receive_custom_port_used_for_fetch_and_ack(
            self,
            app: App,
            numeric_bot: Any,
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from unittest.mock import AsyncMock, Mock

        import src.plugins.omega_email.command as command_module

        address = _test_address()
        image_url = 'https://example.test/mail-custom-port.jpg'
        resource = Mock()
        resource.get_hosting_path = AsyncMock(return_value=('url', image_url))
        get_unseen = AsyncMock(return_value=[_make_mail('自定义端口', uid='401')])
        mark_seen = AsyncMock()
        monkeypatch.setattr(command_module, 'query_entity_bound_mailbox', AsyncMock(return_value=[address]))
        monkeypatch.setattr(
            command_module,
            'load_mailbox_from_database',
            AsyncMock(return_value=_make_account(address, port=1993)),
        )
        monkeypatch.setattr(command_module, 'get_unseen_mail_data', get_unseen)
        monkeypatch.setattr(command_module, 'generate_mail_snapshot', AsyncMock(return_value=resource))
        monkeypatch.setattr(command_module, 'mark_mail_as_seen', mark_seen)
        event = await self._make_event(numeric_bot)

        async with app.test_matcher(command_module.mailbox_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event, expected_reply(event, f'已绑定邮箱:\n\n{address}\n\n正在连接到邮箱服务器, 请稍候~'),
            )
            ctx.should_call_send(event, _expected_image_reply(event, image_url))
            ctx.should_call_send(event, expected_reply(event, f'邮箱 {address}\n收件完成, 共1封新的邮件'))

        get_unseen.assert_awaited_once_with(
            address=address, server_host='imap.example.com', password='secret', port=1993,
        )
        mark_seen.assert_awaited_once_with(
            address=address, server_host='imap.example.com', password='secret', uid='401', port=1993,
        )

    @pytest.mark.parametrize('uid', [None, '', '0', 'abc'])
    async def test_receive_invalid_uid_is_not_sent_or_marked(
            self,
            app: App,
            numeric_bot: Any,
            monkeypatch: pytest.MonkeyPatch,
            uid: str | None,
    ) -> None:
        from unittest.mock import AsyncMock

        import src.plugins.omega_email.command as command_module

        address = _test_address()
        generate = AsyncMock()
        mark_seen = AsyncMock()
        monkeypatch.setattr(command_module, 'query_entity_bound_mailbox', AsyncMock(return_value=[address]))
        monkeypatch.setattr(
            command_module, 'load_mailbox_from_database', AsyncMock(return_value=_make_account(address)),
        )
        monkeypatch.setattr(
            command_module, 'get_unseen_mail_data', AsyncMock(return_value=[_make_mail('无效 UID', uid=uid)]),
        )
        monkeypatch.setattr(command_module, 'generate_mail_snapshot', generate)
        monkeypatch.setattr(command_module, 'mark_mail_as_seen', mark_seen, raising=False)
        event = await self._make_event(numeric_bot)

        async with app.test_matcher(command_module.mailbox_manager) as ctx:
            bot = create_real_obv11_bot(ctx, numeric_bot.self_id)
            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event, expected_reply(event, f'已绑定邮箱:\n\n{address}\n\n正在连接到邮箱服务器, 请稍候~'),
            )
            ctx.should_call_send(
                event,
                expected_reply(
                    event,
                    f'邮箱 {address}\n收件完成, 共1封新的邮件, 发送消息成功0封, 发送消息失败1封',
                ),
            )

        generate.assert_not_awaited()
        mark_seen.assert_not_awaited()


__all__ = []
