import imaplib
import email
import hashlib
from email.header import Header
from typing import List


class Email(object):
    def __init__(self, date: str, header: str, sender: str, to: str, body: str = '', html: str = ''):
        self.date = date
        self.header = header
        self.sender = sender
        self.to = to
        self.body = body
        self.html = html

        hash_str = str([date, header, sender, to])
        md5 = hashlib.md5()
        md5.update(hash_str.encode('utf-8'))
        _hash = md5.hexdigest()
        self.hash = _hash

    def __repr__(self):
        return f'<Email(header={self.header}, _from={self.sender}, to={self.to}' \
               f"\n\nbody={self.body}\n\nhtml={self.html})>"


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

    def get_mail_info(self, charset, *criteria) -> List[Email]:
        self.__mail.login(self.__address, self.__password)

        if self.__address.endswith('163.com'):
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
            header, charset = email.header.decode_header(msg.get('subject'))[0]
            header = str(header, encoding=charset)

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

            body = None
            html = None
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    charset = part.get_content_charset()
                    body = part.get_payload(decode=True)
                    if not body:
                        continue
                    if charset and type(body) == bytes:
                        body = str(body, encoding=charset)
                    elif type(body) == bytes:
                        body = str(body, encoding='utf8')
                    else:
                        body = str(body)
                    body = body.replace(r'&nbsp;', '\n')
                elif part.get_content_type() == "text/html":
                    charset = part.get_content_charset()
                    html = part.get_payload(decode=True)
                    if not html:
                        continue
                    if charset and type(html) == bytes:
                        html = str(html, encoding=charset)
                    elif type(html) == bytes:
                        html = str(html, encoding='utf8')
                    else:
                        html = str(html)
                    html = html.replace('&nbsp;', '')
                else:
                    pass

            result_list.append(Email(date=date, header=header, sender=sender, to=receiver, body=body, html=html))

        return result_list
