from omega_miya.utils.Omega_Base.database import NBdb
from omega_miya.utils.Omega_Base.class_result import Result
from omega_miya.utils.Omega_Base.tables import History
from datetime import datetime


class DBHistory(object):
    def __init__(self, time: int, self_id: int, post_type: str, detail_type: str):
        self.time = time
        self.self_id = self_id
        self.post_type = post_type
        self.detail_type = detail_type

    async def add(self, sub_type: str = None, event_id: int = None, group_id: int = None,
                  user_id: int = None, user_name: str = None,
                  raw_data: str = None, msg_data: str = None) -> Result.IntResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    new_event = History(time=self.time, self_id=self.self_id,
                                        post_type=self.post_type, detail_type=self.detail_type, sub_type=sub_type,
                                        event_id=event_id, group_id=group_id, user_id=user_id, user_name=user_name,
                                        raw_data=raw_data, msg_data=msg_data, created_at=datetime.now())
                    session.add(new_event)
                    result = Result.IntResult(error=False, info='Success added', result=0)
                await session.commit()
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result
