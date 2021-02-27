import asyncio
from omega_miya.utils.Omega_Base import DBEmail, Result
from .imap import EmailImap


async def check_mailbox(address: str, server_host: str, password: str) -> Result:
    def __check_mailbox() -> Result:
        try:
            with EmailImap(host=server_host, address=address, password=password) as m:
                m.select()
            __result = Result(error=False, info='Success', result=0)
        except Exception as e:
            __result = Result(error=True, info=f'Login Failed: {repr(e)}', result=-1)

        return __result

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, __check_mailbox)

    return result


async def get_unseen_mail_info(address: str, server_host: str, password: str) -> Result:
    def __get_unseen_mail_info() -> Result:
        try:
            mail = EmailImap(host=server_host, address=address, password=password)
            unseen_mails = mail.get_mail_info(None, 'UNSEEN')
            res = []
            for email in unseen_mails:
                DBEmail(mail_hash=email.hash).add(date=email.date, header=email.header, sender=email.sender,
                                                  to=email.to, body=email.body, html=email.html)

                res.append(email)
            __result = Result(error=False, info='Success', result=res)
        except Exception as e:
            __result = Result(error=True, info=repr(e), result=[])
        return __result

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, __get_unseen_mail_info)

    return result
