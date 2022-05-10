import imaplib
import email
from pydantic import BaseModel
from email.header import Header
from bs4 import BeautifulSoup


class Email(BaseModel):
    date: str
    header: str
    sender: str
    to: str
    body: str = ''
    html: str = ''


class EmailImap(object):
    def __init__(self, host: str, address: str, password: str, port: int = 993):
        self.__mail = imaplib.IMAP4_SSL(host=host, port=port)
        self.__address = address
        self.__password = password

    def __enter__(self):
        """enter方法，返回file_handler"""
        self.__mail.login(self.__address, self.__password)
        return self.__mail

    def __exit__(self, exc_type, exc_val, exc_tb):
        """exit方法，关闭文件并返回True"""
        self.__mail.select()
        if self.__mail.state == 'SELECTED':
            self.__mail.close()
            self.__mail.logout()
        return True

    def get_mail_data(self, charset, *criteria) -> list[Email]:
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
            msg = email.message_from_bytes(data[0][1])

            # 解析邮件
            # 日期
            date = email.header.decode_header(msg.get('Date'))[0][0]
            date = str(date)

            # 标题
            header, charset_header = email.header.decode_header(msg.get('subject'))[0]
            if charset_header and type(header) == bytes:
                header = str(header, encoding=charset_header)
            elif type(header) == bytes:
                header = str(header, encoding='utf8')
            else:
                pass

            # 发件人
            sender_info = email.header.decode_header(msg.get('from'))
            sender = ''
            for sender_text, charset in sender_info:
                if charset and type(sender_text) == bytes:
                    sender_text = str(sender_text, encoding=charset)
                    sender += sender_text
                elif type(sender_text) == bytes:
                    sender_text = str(sender_text, encoding='utf8')
                    sender += sender_text
                else:
                    sender += sender_text

            # 收件人
            receiver_info = email.header.decode_header(msg.get('to'))
            receiver = ''
            for receiver_text, charset in receiver_info:
                if charset and type(receiver_text) == bytes:
                    receiver_text = str(receiver_text, encoding=charset)
                    receiver += receiver_text
                elif type(receiver_text) == bytes:
                    receiver_text = str(receiver_text, encoding='utf8')
                    receiver += receiver_text
                else:
                    receiver += receiver_text

            body_list = []
            html_list = []
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    charset = part.get_content_charset()
                    _body = part.get_payload(decode=True)
                    if not _body:
                        continue
                    if charset and type(_body) == bytes:
                        body_text = str(_body, encoding=charset)
                    elif type(_body) == bytes:
                        body_text = str(_body, encoding='utf8')
                    else:
                        body_text = str(_body)
                    body_text = body_text.replace(r'&nbsp;', '\n')
                    body_list.append(body_text)
                elif part.get_content_type() == "text/html":
                    charset = part.get_content_charset()
                    _html = part.get_payload(decode=True)
                    if not _html:
                        continue
                    if charset and type(_html) == bytes:
                        html_text = str(_html, encoding=charset)
                    elif type(_html) == bytes:
                        html_text = str(_html, encoding='utf8')
                    else:
                        html_text = str(_html)
                    _bs = BeautifulSoup(html_text, 'lxml')
                    html_list.append(_bs.get_text(strip=False))
                else:
                    pass

            body = '\n'.join(body_list) if body_list else ''
            html = '\n'.join(html_list) if html_list else ''

            result_list.append(Email(date=date, header=header, sender=sender, to=receiver, body=body, html=html))

        return result_list


__all__ = [
    'Email',
    'EmailImap'
]
