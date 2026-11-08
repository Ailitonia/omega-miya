"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : mailbox.py
@Project        : nonebot2_miya
@Description    : imap 协议处理模块
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import email
import imaplib
import re
import ssl
from email.header import Header
from threading import Lock

from lxml import etree
from nonebot.log import logger
from pydantic import BaseModel

from .consts import EMAIL_IMAP_PORT, EMAIL_IMAP_TIMEOUT

_IMAP_ID_LOCK = Lock()
"""串行化 163 邮箱 ID 命令对进程级全局 imaplib.Commands 注册表的"变更-执行-恢复"过程, 仅在工作线程内使用"""


class Email(BaseModel):
    date: str
    header: str
    sender: str
    to: str
    body: str = ''
    html: str = ''
    uid: str | None = None


class ImapMailbox:
    """IMAP 邮箱客户端封装

    本类全部方法均为阻塞同步调用, 仅允许经 run_sync 包装在工作线程中执行;
    禁止在事件循环线程中直接调用, 否则阻塞 socket I/O 将卡住整个事件循环
    """

    def __init__(self, host: str, address: str, password: str, *, port: int = EMAIL_IMAP_PORT):
        self.__mail = imaplib.IMAP4_SSL(
            host=host,
            port=port,
            ssl_context=ssl.create_default_context(),
            timeout=EMAIL_IMAP_TIMEOUT,
        )
        self.__address = address
        self.__password = password

    @staticmethod
    def _decode_bytes(content: bytes, charset: str | None = None) -> str:
        try:
            return content.decode(charset or 'utf-8', errors='replace')
        except LookupError:
            return content.decode('utf-8', errors='replace')

    @classmethod
    def _decode_header(cls, header: Header | str | None) -> str:
        """解析邮件 header 为文本"""
        header_content = email.header.decode_header(header or '')
        output_text = ''
        for content, charset in header_content:
            if isinstance(content, bytes):
                output_text += cls._decode_bytes(content, charset)
            else:
                output_text += content
        return output_text

    @staticmethod
    def _ensure_ok(typ: str, command: str) -> None:
        if typ != 'OK':
            raise imaplib.IMAP4.error(f'{command} failed with IMAP status {typ}')

    @staticmethod
    def _validate_uid(uid: str) -> None:
        if not uid.isdecimal() or int(uid) <= 0:
            raise ValueError(f'Invalid IMAP UID: {uid!r}')

    def _disconnect(self) -> None:
        try:
            if self.__mail.state == 'SELECTED':
                self.__mail.close()
        except Exception as e:
            logger.warning(f'OmegaEmail | Close IMAP mailbox failed, {e}')
        try:
            self.__mail.logout()
        except Exception as e:
            logger.warning(f'OmegaEmail | IMAP logout failed, {e}')

    def check(self) -> None:
        try:
            self.__mail.login(self.__address, self.__password)
            if self.__address.endswith('@163.com'):
                self._send_163_id()
            typ, _ = self.__mail.select()
            self._ensure_ok(typ, 'SELECT')
        finally:
            self._disconnect()

    def mark_as_seen(self, uid: str) -> None:
        self._validate_uid(uid)
        try:
            self.__mail.login(self.__address, self.__password)
            if self.__address.endswith('@163.com'):
                self._send_163_id()
            typ, _ = self.__mail.select()
            self._ensure_ok(typ, 'SELECT')
            typ, _ = self.__mail.uid('STORE', uid, '+FLAGS', '\\Seen')
            self._ensure_ok(typ, 'STORE')
        finally:
            self._disconnect()

    def _send_163_id(self) -> None:
        args = ('name', 'omega', 'contact', 'omega_miya@163.com', 'version', '1.0.2', 'vendor', 'pyimaplibclient')
        with _IMAP_ID_LOCK:
            had_id = 'ID' in imaplib.Commands
            previous_id = imaplib.Commands.get('ID')
            try:
                imaplib.Commands['ID'] = ('AUTH',)
                typ, dat = self.__mail._simple_command('ID', '("' + '" "'.join(args) + '")')
                typ, _ = self.__mail._untagged_response(typ, dat, 'ID')
                self._ensure_ok(typ, 'ID')
            finally:
                if had_id:
                    imaplib.Commands['ID'] = previous_id
                else:
                    imaplib.Commands.pop('ID', None)

    @classmethod
    def _parse_message(cls, raw_message: bytes, uid: str) -> Email:
        msg = email.message_from_bytes(raw_message)

        date = cls._decode_header(msg.get('Date'))
        header = cls._decode_header(msg.get('subject'))
        sender = cls._decode_header(msg.get('from'))
        receiver = cls._decode_header(msg.get('to'))

        body_list = []
        html_list = []
        for part in msg.walk():
            charset = part.get_content_charset()
            part_content = part.get_payload(decode=True)
            if not part_content:
                continue
            if isinstance(part_content, bytes):
                content_text = cls._decode_bytes(part_content, charset)
            else:
                content_text = str(part_content)

            if part.get_content_type() == 'text/plain':
                body_list.append(content_text.replace('&nbsp;', '\n'))
            elif part.get_content_type() == 'text/html':
                content_text = re.sub(r'<br\s*/?>', '\n', content_text, flags=re.IGNORECASE)
                try:
                    html_ = etree.HTML(content_text)
                except (etree.ParserError, ValueError):
                    html_ = None
                if html_ is not None:
                    html_list.append(''.join(html_.itertext()))

        return Email(
            date=date,
            header=header,
            sender=sender,
            to=receiver,
            body='\n'.join(body_list),
            html='\n'.join(html_list),
            uid=uid,
        )

    @staticmethod
    def _extract_message_bytes(data: list | None) -> bytes | None:
        if not data:
            return None
        for item in data:
            if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], bytes):
                return item[1]
        return None

    def _get_mail_list(self, charset, *criteria) -> list[Email]:
        self.__mail.login(self.__address, self.__password)

        if self.__address.endswith('@163.com'):
            self._send_163_id()

        typ, _ = self.__mail.select()
        self._ensure_ok(typ, 'SELECT')
        typ, msg_uids = self.__mail.uid('SEARCH', charset, *criteria)
        self._ensure_ok(typ, 'SEARCH')

        if not msg_uids or msg_uids[0] is None:
            return []

        msg_uids_text = self._decode_bytes(msg_uids[0], 'utf-8')
        result_list = []
        for uid in msg_uids_text.split():
            try:
                self._validate_uid(uid)
            except ValueError:
                logger.warning(f'OmegaEmail | Skip invalid IMAP UID: {uid!r}')
                continue

            typ, data = self.__mail.uid('FETCH', uid, '(BODY.PEEK[])')
            self._ensure_ok(typ, 'FETCH')

            raw_message = self._extract_message_bytes(data)
            if raw_message is None:
                logger.warning(f'OmegaEmail | Skip message UID {uid}: missing BODY[] payload')
                continue
            try:
                result_list.append(self._parse_message(raw_message, uid))
            except Exception as e:
                logger.warning(f'OmegaEmail | Skip malformed message UID {uid}: {e}')

        return result_list

    def get_mail_list(self, charset, *criteria) -> list[Email]:
        try:
            return self._get_mail_list(charset, *criteria)
        finally:
            self._disconnect()


__all__ = [
    'Email',
    'ImapMailbox',
]
