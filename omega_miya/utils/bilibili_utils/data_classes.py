from dataclasses import dataclass
from typing import Optional, Dict, List
from omega_miya.utils.Omega_Base import Result


class BiliInfo(object):
    @dataclass
    class UserInfo:
        user_id: int
        name: str
        sex: str
        face: str
        sign: str
        level: int

        @property
        def uid(self):
            return self.user_id

        @property
        def mid(self):
            return str(self.user_id)

    @dataclass
    class LiveRoomInfo:
        room_id: int
        short_id: int
        user_id: int
        status: int
        url: str
        title: str
        live_time: str
        cover_img: str

        @property
        def uid(self):
            return self.user_id

        @property
        def mid(self):
            return str(self.user_id)

    @dataclass
    class DynamicInfo:

        @dataclass
        class DynamicCard:
            content: str
            pictures: List[str]
            title: Optional[str]
            description: Optional[str]

        dynamic_id: int
        user_id: int
        user_name: str
        type: int
        desc: str
        url: str
        orig_dy_id: int
        orig_type: int
        data: DynamicCard

        @property
        def uid(self):
            return self.user_id

        @property
        def mid(self):
            return str(self.user_id)


class BiliResult(object):
    @dataclass
    class UserInfoInfoResult(Result.AnyResult):
        result: Optional[BiliInfo.UserInfo]

        def __repr__(self):
            return f'<UserInfoInfoResult(error={self.error}, info={self.info}, result={self.result})>'

    @dataclass
    class LiveRoomInfoResult(Result.AnyResult):
        result: Optional[BiliInfo.LiveRoomInfo]

        def __repr__(self):
            return f'<LiveRoomInfoResult(error={self.error}, info={self.info}, result={self.result})>'

    @dataclass
    class LiveRoomDictInfoResult(Result.AnyResult):
        result: Optional[Dict[int, BiliInfo.LiveRoomInfo]]

        def __repr__(self):
            return f'<LiveRoomInfoDictResult(error={self.error}, info={self.info}, result={self.result})>'

    @dataclass
    class DynamicInfoResult(Result.AnyResult):
        result: Optional[BiliInfo.DynamicInfo]

        def __repr__(self):
            return f'<DynamicInfoResult(error={self.error}, info={self.info}, result={self.result})>'
