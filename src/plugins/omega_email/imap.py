"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : imap.py
@Project        : nonebot2_miya
@Description    : imap 协议处理模块
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import abc
import email
import imaplib
import re
from email.header import Header

from lxml import etree
from pydantic import BaseModel


class Email(BaseModel):
    date: str
    header: str
    sender: str
    to: str
    body: str = ''
    html: str = ''


class BaseMailbox(abc.ABC):
    """邮箱客户端基类"""

    @abc.abstractmethod
    def check(self) -> None | Exception:
        """检查邮箱状态"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_mail_list(self, charset, *criteria) -> list[Email]:
        """获取邮件列表"""
        raise NotImplementedError

    @abc.abstractmethod
    def send_mail(self, *args, **kwargs) -> None:
        """发送邮件"""
        raise NotImplementedError


class ImapMailbox(BaseMailbox):
    """Imap 邮箱客户端封装"""

    def __init__(self, host: str, address: str, password: str, port: int = 993):
        self.__mail = imaplib.IMAP4_SSL(host=host, port=port)
        self.__address = address
        self.__password = password

    @staticmethod
    def _decode_header(header: Header | str) -> str:
        """解析邮件 header 为文本"""
        header_content = email.header.decode_header(header)
        output_text = ''
        for content, charset in header_content:
            if charset and isinstance(content, bytes):
                content = str(content, encoding=charset)
                output_text += content
            elif isinstance(content, bytes):
                content = str(content, encoding='utf8')
                output_text += content
            else:
                output_text += content
        return output_text

    def check(self) -> None:
        self.__mail.login(self.__address, self.__password)
        self.__mail.select()
        if self.__mail.state == 'SELECTED':
            self.__mail.close()
            self.__mail.logout()

    def get_mail_list(self, charset, *criteria) -> list[Email]:
        self.__mail.login(self.__address, self.__password)

        if self.__address.endswith('@163.com'):
            # 添加163邮箱 IMAP ID 验证
            imaplib.Commands['ID'] = ('AUTH',)
            args = ("name", "omega", "contact", "omega_miya@163.com", "version", "1.0.2", "vendor", "pyimaplibclient")
            typ, dat = self.__mail._simple_command('ID', '("' + '" "'.join(args) + '")')
            self.__mail._untagged_response(typ, dat, 'ID')

        self.__mail.select()
        typ, msg_nums = self.__mail.search(charset, *criteria)
        msg_nums = str(msg_nums[0], encoding='utf8')

        result_list = []

        # 遍历所有邮件
        for num in msg_nums.split(' '):
            if num == '':
                continue

            stat_code, data = self.__mail.fetch(num, 'RFC822')
            msg_content: bytes | tuple[bytes, bytes] | None = data[0]
            if msg_content is None:
                continue
            else:
                msg = email.message_from_bytes(msg_content[1])

            # 解析邮件
            # 日期
            date = email.header.decode_header(msg.get('Date'))[0][0]
            date = str(date)
            # 标题
            header = self._decode_header(msg.get('subject'))
            # 发件人
            sender = self._decode_header(msg.get('from'))
            # 收件人
            receiver = self._decode_header(msg.get('to'))

            body_list = []
            html_list = []
            for part in msg.walk():
                charset = part.get_content_charset()
                part_content = part.get_payload(decode=True)
                if not part_content:
                    continue
                if charset and isinstance(part_content, bytes):
                    content_text = str(part_content, encoding=charset)
                elif isinstance(part_content, bytes):
                    content_text = str(part_content, encoding='utf8')
                else:
                    content_text = str(part_content)

                # 根据内容形式进一步解析处理
                if part.get_content_type() == "text/plain":
                    content_text = content_text.replace(r'&nbsp;', '\n')
                    body_list.append(content_text)
                elif part.get_content_type() == "text/html":
                    content_text = re.sub(re.compile(r'<br\s?/?>', re.IGNORECASE), '\n', content_text)
                    html_ = etree.HTML(content_text)
                    html_list.append(''.join(text for text in html_.itertext()))
                else:
                    pass

            body = '\n'.join(body_list) if body_list else ''
            html = '\n'.join(html_list) if html_list else ''

            result_list.append(Email(date=date, header=header, sender=sender, to=receiver, body=body, html=html))

        # 断开邮箱连接
        self.__mail.select()
        if self.__mail.state == 'SELECTED':
            self.__mail.close()
            self.__mail.logout()

        return result_list

    def send_mail(self, *args, **kwargs) -> None:
        raise NotImplementedError


__all__ = [
    'Email',
    'ImapMailbox'
]
