"""
@Author         : Ailitonia
@Date           : 2022/04/14 21:39
@FileName       : message.py
@Project        : nonebot2_miya 
@Description    : Onebot Message Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal, Optional
from pydantic import AnyHttpUrl
from .base_model import BaseOnebotModel


class _MessageSegment(BaseOnebotModel):
    """数组消息段"""
    type: str
    data: dict


class TextMessageSegment(_MessageSegment):
    """纯文本"""
    class _TextData(BaseOnebotModel):
        text: str

    type: Literal['text']
    data: _TextData


class FaceMessageSegment(_MessageSegment):
    """QQ 表情"""
    class _FaceData(BaseOnebotModel):
        id: int

    type: Literal['face']
    data: _FaceData


class ImageMessageSegment(_MessageSegment):
    """图片"""
    class _ImageData(BaseOnebotModel):
        file: str
        type: Optional[Literal['flash']]
        url: Optional[AnyHttpUrl]

    type: Literal['image']
    data: _ImageData


class RecordMessageSegment(_MessageSegment):
    """语音"""
    class _RecordData(BaseOnebotModel):
        file: str
        magic: Optional[Literal['0', '1']]
        url: Optional[AnyHttpUrl]

    type: Literal['record']
    data: _RecordData


class VideoMessageSegment(_MessageSegment):
    """短视频"""
    class _VideoData(BaseOnebotModel):
        file: str
        url: Optional[AnyHttpUrl]

    type: Literal['video']
    data: _VideoData


class AtMessageSegment(_MessageSegment):
    """@某人"""
    class _AtData(BaseOnebotModel):
        qq: int | Literal['all']

    type: Literal['at']
    data: _AtData


class RpsMessageSegment(_MessageSegment):
    """猜拳魔法表情"""
    type: Literal['rps']
    data: dict = {}


class DiceMessageSegment(_MessageSegment):
    """掷骰子魔法表情"""
    type: Literal['dice']
    data: dict = {}


class ShakeMessageSegment(_MessageSegment):
    """窗口抖动（戳一戳）"""
    type: Literal['shake']
    data: dict = {}


class PokeMessageSegment(_MessageSegment):
    """戳一戳"""
    class _PokeData(BaseOnebotModel):
        type: str
        id: str
        name: Optional[str]

    type: Literal['poke']
    data: _PokeData


class AnonymousMessageSegment(_MessageSegment):
    """匿名发消息(当收到匿名消息时，需要通过 消息事件的群消息 的 anonymous 字段判断。)"""
    type: Literal['anonymous']
    data: dict = {}


class ShareMessageSegment(_MessageSegment):
    """链接分享"""
    class _ShareData(BaseOnebotModel):
        url: AnyHttpUrl
        title: str
        content: Optional[str]
        image: Optional[AnyHttpUrl]

    type: Literal['share']
    data: _ShareData


class ContactUserMessageSegment(_MessageSegment):
    """推荐好友"""
    class _ContactData(BaseOnebotModel):
        type: Literal['qq']
        id: str

    type: Literal['contact']
    data: _ContactData


class ContactGroupMessageSegment(_MessageSegment):
    """推荐群"""
    class _ContactData(BaseOnebotModel):
        type: Literal['group']
        id: str

    type: Literal['contact']
    data: _ContactData


class LocationMessageSegment(_MessageSegment):
    """位置"""
    class _LocationData(BaseOnebotModel):
        lat: float
        lon: float
        title: Optional[str]
        content: Optional[str]

    type: Literal['location']
    data: _LocationData


class MusicMessageSegment(_MessageSegment):
    """音乐分享"""
    class _MusicData(BaseOnebotModel):
        type: Literal['qq', '163', 'xm']
        id: str

    type: Literal['music']
    data: _MusicData


class MusicCustomMessageSegment(_MessageSegment):
    """音乐自定义分享"""
    class _MusicData(BaseOnebotModel):
        type: Literal['custom']
        url: AnyHttpUrl
        audio: AnyHttpUrl
        title: str
        content: Optional[str]
        image: Optional[AnyHttpUrl]

    type: Literal['music']
    data: _MusicData


class ReplyMessageSegment(_MessageSegment):
    """回复"""
    class _ReplyData(BaseOnebotModel):
        id: str

    type: Literal['reply']
    data: _ReplyData


class ForwardMessageSegment(_MessageSegment):
    """合并转发"""
    class _ForwardData(BaseOnebotModel):
        id: str

    type: Literal['forward']
    data: _ForwardData


class NodeMessageSegment(_MessageSegment):
    """合并转发节点"""
    class _NodeData(BaseOnebotModel):
        id: str

    type: Literal['node']
    data: _NodeData


class NodeCustomMessageSegment(_MessageSegment):
    """合并转发自定义节点"""
    class _NodeData(BaseOnebotModel):
        user_id: str
        nickname: str
        content: type("T_Message")

    type: Literal['node']
    data: _NodeData


class NodesCustomMessageSegment(_MessageSegment):
    """合并转发自定义节点"""
    class _NodeData(BaseOnebotModel):
        user_id: str
        nickname: str
        content: list[type("T_Message")]

    type: Literal['node']
    data: _NodeData


T_Message = (
        TextMessageSegment |
        FaceMessageSegment |
        ImageMessageSegment |
        RecordMessageSegment |
        VideoMessageSegment |
        AtMessageSegment |
        RpsMessageSegment |
        DiceMessageSegment |
        ShakeMessageSegment |
        PokeMessageSegment |
        AnonymousMessageSegment |
        ShareMessageSegment |
        ContactUserMessageSegment |
        ContactGroupMessageSegment |
        LocationMessageSegment |
        MusicMessageSegment |
        MusicCustomMessageSegment |
        ReplyMessageSegment |
        ForwardMessageSegment |
        NodeMessageSegment |
        NodeCustomMessageSegment |
        NodesCustomMessageSegment
)


class SentMessage(BaseOnebotModel):
    """已发送的消息"""
    message_id: int


class Sender(BaseOnebotModel):
    """消息发送人"""
    user_id: str
    nickname: str
    sex: Optional[str]
    age: Optional[int]


class ReceiveMessage(BaseOnebotModel):
    """收到的消息"""
    time: int
    message_type: str
    message_id: int
    real_id: int
    sender: Sender
    message: list[T_Message]


class CustomNodeMessage(BaseOnebotModel):
    """收到的合并转发消息"""
    message: list[T_Message]


__all__ = [
    'SentMessage',
    'ReceiveMessage',
    'CustomNodeMessage'
]
