from .database import NBdb, DBResult
from .tables import Email, EmailBox
from datetime import datetime
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBEmailBox(object):
    def __init__(self, address: str):
        self.address = address

    def id(self) -> DBResult:
        session = NBdb().get_session()
        try:
            email_box_table_id = session.query(EmailBox.id).filter(EmailBox.address == self.address).one()[0]
            result = DBResult(error=False, info='Success', result=email_box_table_id)
        except NoResultFound:
            result = DBResult(error=True, info='NoResultFound', result=-1)
        except MultipleResultsFound:
            result = DBResult(error=True, info='MultipleResultsFound', result=-1)
        except Exception as e:
            result = DBResult(error=True, info=repr(e), result=-1)
        finally:
            session.close()
        return result

    def exist(self) -> bool:
        result = self.id().success()
        return result

    @classmethod
    def list(cls) -> DBResult:
        session = NBdb().get_session()
        try:
            res = [x[0] for x in session.query(EmailBox.address).all()]
            result = DBResult(error=False, info='Success', result=res)
        except Exception as e:
            result = DBResult(error=True, info=repr(e), result=[])
        finally:
            session.close()
        return result

    def get_info(self) -> DBResult:
        session = NBdb().get_session()
        try:
            # 已存在则更新
            exist_box = session.query(EmailBox).filter(EmailBox.address == self.address).one()
            server_host = exist_box.server_host
            port = exist_box.port
            password = exist_box.password
            res_dict = {'server_host': server_host, 'port': port, 'password': password}
            result = DBResult(error=False, info='Success', result=res_dict)
        except NoResultFound:
            result = DBResult(error=True, info='NoResultFound', result={})
        except MultipleResultsFound:
            result = DBResult(error=True, info='MultipleResultsFound', result={})
        except Exception as e:
            result = DBResult(error=True, info=repr(e), result={})
        finally:
            session.close()
        return result

    def add(self, server_host: str, password: str, port: int = 993) -> DBResult:
        session = NBdb().get_session()
        try:
            # 已存在则更新
            exist_box = session.query(EmailBox).filter(EmailBox.address == self.address).one()
            exist_box.server_host = server_host
            exist_box.port = port
            exist_box.password = password
            exist_box.updated_at = datetime.now()
            session.commit()
            result = DBResult(error=False, info='Success upgraded', result=0)
        except NoResultFound:
            # 不存在则添加
            try:
                new_box = EmailBox(address=self.address, server_host=server_host, password=password,
                                   port=port, created_at=datetime.now())
                session.add(new_box)
                session.commit()
                result = DBResult(error=False, info='Success added', result=0)
            except Exception as e:
                session.rollback()
                result = DBResult(error=True, info=repr(e), result=-1)
        except MultipleResultsFound:
            result = DBResult(error=True, info='MultipleResultsFound', result=-1)
        except Exception as e:
            session.rollback()
            result = DBResult(error=True, info=repr(e), result=-1)
        finally:
            session.close()
        return result

    def delete(self) -> DBResult:
        session = NBdb().get_session()
        try:
            exist_box = session.query(EmailBox).filter(EmailBox.address == self.address).one()
            session.delete(exist_box)
            session.commit()
            result = DBResult(error=False, info='Success', result=0)
        except NoResultFound:
            result = DBResult(error=True, info='NoResultFound', result=-1)
        except MultipleResultsFound:
            result = DBResult(error=True, info='MultipleResultsFound', result=-1)
        except Exception as e:
            session.rollback()
            result = DBResult(error=True, info=repr(e), result=-1)
        finally:
            session.close()
        return result


class DBEmail(object):
    def __init__(self, mail_hash: str):
        self.mail_hash = mail_hash

    def add(self, date: str, header: str, sender: str, to: str = None, body: str = None, html: str = None) -> DBResult:
        session = NBdb().get_session()
        try:
            new_email = Email(mail_hash=self.mail_hash, date=date, header=header, sender=sender, to=to,
                              body=body, html=html, created_at=datetime.now())
            session.add(new_email)
            session.commit()
            result = DBResult(error=False, info='Success added', result=0)
        except Exception as e:
            session.rollback()
            result = DBResult(error=True, info=repr(e), result=-1)
        finally:
            session.close()
        return result
