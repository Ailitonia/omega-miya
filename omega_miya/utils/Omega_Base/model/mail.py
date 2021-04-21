from omega_miya.utils.Omega_Base.database import NBdb
from omega_miya.utils.Omega_Base.class_result import Result
from omega_miya.utils.Omega_Base.tables import Email, EmailBox, GroupEmailBox
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBEmailBox(object):
    def __init__(self, address: str):
        self.address = address

    async def id(self) -> Result.IntResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(EmailBox.id).
                        where(EmailBox.address == self.address)
                    )
                    email_box_table_id = session_result.scalar_one()
                    result = Result.IntResult(error=False, info='Success', result=email_box_table_id)
                except NoResultFound:
                    result = Result.IntResult(error=True, info='NoResultFound', result=-1)
                except MultipleResultsFound:
                    result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
                except Exception as e:
                    result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def exist(self) -> bool:
        result = await self.id()
        return result.success()

    @classmethod
    async def list(cls) -> Result.ListResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(EmailBox.address).order_by(EmailBox.id)
                    )
                    res = [x for x in session_result.scalars().all()]
                    result = Result.ListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.ListResult(error=True, info=repr(e), result=[])
        return result

    async def get_info(self) -> Result.DictResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(EmailBox).
                        where(EmailBox.address == self.address)
                    )
                    exist_box = session_result.scalar_one()
                    server_host = exist_box.server_host
                    port = exist_box.port
                    password = exist_box.password
                    res_dict = {'server_host': server_host, 'port': port, 'password': password}
                    result = Result.DictResult(error=False, info='Success', result=res_dict)
                except NoResultFound:
                    result = Result.DictResult(error=True, info='NoResultFound', result={})
                except MultipleResultsFound:
                    result = Result.DictResult(error=True, info='MultipleResultsFound', result={})
                except Exception as e:
                    result = Result.DictResult(error=True, info=repr(e), result={})
        return result

    async def add(self, server_host: str, password: str, port: int = 993) -> Result.IntResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        # 已存在则更新
                        session_result = await session.execute(
                            select(EmailBox).
                            where(EmailBox.address == self.address)
                        )
                        exist_box = session_result.scalar_one()
                        exist_box.server_host = server_host
                        exist_box.port = port
                        exist_box.password = password
                        exist_box.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        new_box = EmailBox(address=self.address, server_host=server_host, password=password,
                                           port=port, created_at=datetime.now())
                        session.add(new_box)
                        result = Result.IntResult(error=False, info='Success added', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def delete(self) -> Result.IntResult:
        id_result = await self.id()
        if id_result.error:
            return Result.IntResult(error=True, info='EmailBox not exist', result=-1)

        # 清空持已绑定这个邮箱的群组
        await self.mailbox_group_clear()

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(EmailBox).
                        where(EmailBox.address == self.address)
                    )
                    exist_box = session_result.scalar_one()
                    await session.delete(exist_box)
                await session.commit()
                result = Result.IntResult(error=False, info='Success', result=0)
            except NoResultFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='NoResultFound', result=-1)
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def mailbox_group_clear(self) -> Result.IntResult:
        id_result = await self.id()
        if id_result.error:
            return Result.IntResult(error=True, info='EmailBox not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(GroupEmailBox).where(GroupEmailBox.email_box_id == id_result.result)
                    )
                    for exist_group_mailbox in session_result.scalars().all():
                        await session.delete(exist_group_mailbox)
                await session.commit()
                result = Result.IntResult(error=False, info='Success', result=0)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result


class DBEmail(object):
    def __init__(self, mail_hash: str):
        self.mail_hash = mail_hash

    async def add(
            self, date: str, header: str, sender: str, to: str, body: str = None, html: str = None
    ) -> Result.IntResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    new_email = Email(mail_hash=self.mail_hash, date=date, header=header, sender=sender, to=to,
                                      body=body, html=html, created_at=datetime.now())
                    session.add(new_email)
                await session.commit()
                result = Result.IntResult(error=False, info='Success added', result=0)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result
