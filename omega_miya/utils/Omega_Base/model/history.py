from omega_miya.utils.Omega_Base.database import NBdb, DBResult
from omega_miya.utils.Omega_Base.tables import History
from datetime import datetime


class DBHistory(object):
    def __init__(self, time: int, self_id: int, post_type: str, detail_type: str):
        self.time = time
        self.self_id = self_id
        self.post_type = post_type
        self.detail_type = detail_type

    def add(self, sub_type: str = None, group_id: int = None, user_id: int = None, user_name: str = None,
            raw_data: str = None, msg_data: str = None) -> DBResult:
        session = NBdb().get_session()
        try:
            new_event = History(time=self.time, self_id=self.self_id,
                                post_type=self.post_type, detail_type=self.detail_type, sub_type=sub_type,
                                group_id=group_id, user_id=user_id, user_name=user_name,
                                raw_data=raw_data, msg_data=msg_data, created_at=datetime.now())
            session.add(new_event)
            session.commit()
            result = DBResult(error=False, info='Success added', result=0)
        except Exception as e:
            session.rollback()
            result = DBResult(error=True, info=repr(e), result=-1)
        finally:
            session.close()
        return result
