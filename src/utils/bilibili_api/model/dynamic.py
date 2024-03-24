"""
@Author         : Ailitonia
@Date           : 2022/04/11 22:53
@FileName       : dynamic.py
@Project        : nonebot2_miya 
@Description    : Bilibili Dynamic Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pydantic import AnyHttpUrl, Json, field_validator
from typing import Any, Literal, Optional

from .base_model import BaseBilibiliModel


class BilibiliDynamicCardDescUserProfile(BaseBilibiliModel):
    """Bilibili 动态 Card Desc 用户信息"""

    class _UserInfo(BaseBilibiliModel):
        """内部用户信息字段"""
        uid: int
        uname: str
        face: AnyHttpUrl

    info: _UserInfo
    sign: str


class BilibiliDynamicCardDescOrigin(BaseBilibiliModel):
    """Bilibili 动态 Card Desc 转发来源"""
    uid: int
    type: int
    rid: int
    dynamic_id: int
    timestamp: int
    orig_dy_id: int = 0
    pre_dy_id: int = 0


class BilibiliDynamicCardDesc(BaseBilibiliModel):
    """Bilibili 动态 Card Desc"""
    uid: int
    type: int
    rid: int
    view: int
    dynamic_id: int
    timestamp: int
    user_profile: BilibiliDynamicCardDescUserProfile
    orig_type: int
    pre_dy_id: int = 0
    orig_dy_id: int = 0
    origin: Optional[BilibiliDynamicCardDescOrigin] = None


class _StdCardOutputData(BaseBilibiliModel):
    """用于外部模块使用的标准化动态 Card 导出数据"""
    content: str  # 动态主体文本内容
    text: str  # 输出文本内容
    img_urls: list[AnyHttpUrl] = []


class _BaseCardType(BaseBilibiliModel):
    """Bilibili 动态 Card 基类"""
    verify_type: int

    @property
    def user_name(self) -> str:
        """动态发布者的名称"""
        raise NotImplementedError

    def output_std_model(self) -> _StdCardOutputData:
        """导出标准化数据"""
        raise NotImplementedError


class CardType2OriginalWithImage(_BaseCardType):
    """Bilibili 动态 Card Type 2 原创带图动态"""

    class _UserInfo(BaseBilibiliModel):
        """内部用户信息字段"""
        uid: int
        name: str
        head_url: AnyHttpUrl

    class _Item(BaseBilibiliModel):
        """内部内容信息字段"""
        class _Picture(BaseBilibiliModel):
            img_width: int
            img_height: int
            img_size: float
            img_src: AnyHttpUrl

        id: int
        category: Optional[str] = None  # Deactivated
        description: str  # 为文字内容
        pictures: list[_Picture]  # 图片内容
        pictures_count: int
        title: Optional[str] = None  # Deactivated

    verify_type: int = 2
    user: _UserInfo
    item: _Item

    @property
    def user_name(self) -> str:
        return self.user.name

    def output_std_model(self) -> _StdCardOutputData:
        text = f'{self.user_name}发布了新动态!\n\n“{self.item.description}”\n'
        return _StdCardOutputData.parse_obj({
            'content': self.item.description,
            'text': text,
            'img_urls': [x.img_src for x in self.item.pictures]
        })


class CardType4OriginalWithoutImage(_BaseCardType):
    """Bilibili 动态 Card Type 4 原创不带图动态"""

    class _UserInfo(BaseBilibiliModel):
        """内部用户信息字段"""
        uid: int
        uname: str
        face: AnyHttpUrl

    class _Item(BaseBilibiliModel):
        """内部内容信息字段"""
        rp_id: int
        uid: int
        content: str
        timestamp: Optional[int] = None  # Deactivated
        ctrl: Any
        reply: Any

    verify_type: int = 4
    user: _UserInfo
    item: _Item

    @property
    def user_name(self) -> str:
        return self.user.uname

    def output_std_model(self) -> _StdCardOutputData:
        text = f'{self.user_name}发布了新动态!\n\n“{self.item.content}”'
        return _StdCardOutputData.parse_obj({'content': self.item.content, 'text': text})


class CardType8Video(_BaseCardType):
    """Bilibili 动态 Card Type 8 视频投稿动态"""

    class _Owner(BaseBilibiliModel):
        """内部用户信息字段"""
        mid: int
        name: str
        face: AnyHttpUrl

    verify_type: int = 8
    aid: int  # 视频avid
    cid: int  # 视频cid
    copyright: Optional[int] = None  # [Deactivated] 原创信息, 1为原创, 2为转载
    dynamic: str  # 动态文字内容
    title: str  # 视频标题
    tname: str  # 视频分区名称
    desc: str  # 视频简介
    owner: _Owner
    first_frame: Optional[AnyHttpUrl | str] = None  # 视频第一帧图片
    pic: AnyHttpUrl  # 视频封面
    videos: int  # 视频数

    @property
    def user_name(self) -> str:
        return self.owner.name

    def output_std_model(self) -> _StdCardOutputData:
        text = f'{self.user_name}发布了新的视频!\n\n《{self.title}》\n\n' \
               f'{self.dynamic if self.dynamic else ""}\n{self.desc}\n'
        return _StdCardOutputData.parse_obj({'content': self.dynamic, 'text': text, 'img_urls': [self.pic]})


class CardType16ShortVideo(_BaseCardType):
    """Bilibili 动态 Card Type 16 小视频动态 (可能已废弃)"""

    class _Item(BaseBilibiliModel):
        """内部内容信息字段"""
        description: str

    verify_type: int = 16
    item: _Item

    @property
    def user_name(self) -> str:
        return ''

    def output_std_model(self) -> _StdCardOutputData:
        text = f'{self.user_name}发布了新的小视频动态!\n\n“{self.item.description}”\n'
        return _StdCardOutputData.parse_obj({'content': self.item.description, 'text': text})


class CardType32Anime(_BaseCardType):
    """Bilibili 动态 Card Type 32 番剧动态 (可能已废弃)"""
    verify_type: int = 32
    title: str
    dynamic: str
    pic: AnyHttpUrl

    @property
    def user_name(self) -> str:
        return '哔哩哔哩番剧'

    def output_std_model(self) -> _StdCardOutputData:
        text = f'{self.user_name}发布了新的番剧!\n\n《{self.title}》\n\n' \
               f'{self.dynamic if self.dynamic else ""}\n'
        return _StdCardOutputData.parse_obj({'content': self.dynamic, 'text': text, 'img_urls': [self.pic]})


class CardType64Article(_BaseCardType):
    """Bilibili 动态 Card Type 64 专栏投稿动态"""

    class _Category(BaseBilibiliModel):
        """分类信息"""
        id: int
        parent_id: int
        name: str

    class _Author(BaseBilibiliModel):
        """作者信息"""
        mid: int
        name: str
        face: AnyHttpUrl

    verify_type: int = 64
    id: int
    category: Optional[_Category] = None  # Deactivated
    categories: Optional[list[_Category]] = None  # Deactivated
    title: str
    summary: str
    banner_url: Optional[AnyHttpUrl | str] = None  # [Deactivated] 是否原创
    author: _Author
    image_urls: list[AnyHttpUrl]
    publish_time: int
    origin_image_urls: list[AnyHttpUrl]  # 源图片地址(这里才是真·头图)
    original: Optional[int] = None  # [Deactivated] 是否原创

    @property
    def user_name(self) -> str:
        return self.author.name

    def output_std_model(self) -> _StdCardOutputData:
        text = f'{self.user_name}发布了新的文章!\n\n《{self.title}》\n\n{self.summary}......\n'
        return _StdCardOutputData.parse_obj({'content': self.summary, 'text': text, 'img_urls': self.origin_image_urls})


class CardType256Music(_BaseCardType):
    """Bilibili 动态 Card Type 256 音频投稿动态"""
    verify_type: int = 256
    id: int  # 投稿编号, 即au号
    upId: int  # 音乐人id, 与用户uid不同
    title: str  # 音频标题
    upper: str  # 上传者名称
    cover: AnyHttpUrl  # 封面图链接
    author: str  # 作者名称
    intro: str  # 音频介绍
    typeInfo: str  # 分区信息
    upperAvatar: AnyHttpUrl  # 上传者的头像链接

    @property
    def user_name(self) -> str:
        return self.upper

    def output_std_model(self) -> _StdCardOutputData:
        text = f'{self.user_name}发布了新的音乐!\n\n《{self.title}》\n\n{self.intro}\n'
        return _StdCardOutputData.parse_obj({'content': self.intro, 'text': text, 'img_urls': [self.cover]})


class CardType512Anime(_BaseCardType):
    """Bilibili 动态 Card Type 512 番剧更新动态 (可能已废弃)"""

    class _ApiSeasonInfo(BaseBilibiliModel):
        title: str

    verify_type: int = 512
    index_title: str
    cover: AnyHttpUrl
    apiSeasonInfo: _ApiSeasonInfo

    @property
    def user_name(self) -> str:
        return '哔哩哔哩番剧'

    def output_std_model(self) -> _StdCardOutputData:
        text = f'{self.user_name}发布了新的番剧!\n\n《{self.apiSeasonInfo.title}》\n\n' \
               f'{self.index_title if self.index_title else ""}\n'
        return _StdCardOutputData.parse_obj({'content': self.index_title, 'text': text, 'img_urls': [self.cover]})


class CardType2048Active(_BaseCardType):
    """Bilibili 动态 Card Type 2048 活动相关动态"""

    class _Sketch(BaseBilibiliModel):
        title: str
        desc_text: Optional[str] = None

    class _Vest(BaseBilibiliModel):
        content: str

    verify_type: int = 2048
    vest: _Vest
    sketch: _Sketch

    @property
    def user_name(self) -> str:
        return ''

    def output_std_model(self) -> _StdCardOutputData:
        text = f'{self.user_name}发布了一条活动相关动态!\n\n' \
               f'【{self.sketch.title}{(" - " + self.sketch.desc_text) if self.sketch.desc_text else ""}】\n\n' \
               f'“{self.vest.content}”\n'
        return _StdCardOutputData.parse_obj({'content': self.vest.content, 'text': text})


class CardType4200LiveRoom(_BaseCardType):
    """Bilibili 动态 Card Type 4200 直播间动态 (可能已废弃)"""
    verify_type: int = 4200
    uname: str
    title: str
    cover: AnyHttpUrl  # 直播间封面

    @property
    def user_name(self) -> str:
        return self.uname

    def output_std_model(self) -> _StdCardOutputData:
        content = f'{self.uname}的直播间 - {self.title}'
        text = f'{self.user_name}发布了一条直播间动态!\n\n{content}\n'
        return _StdCardOutputData.parse_obj({'content': content, 'text': text, 'img_urls': [self.cover]})


class CardType4300MediaListShare(_BaseCardType):
    """Bilibili 动态 Card Type 4300 收藏夹/播放列表分享"""

    class _Upper(BaseBilibiliModel):
        """内部上传用户信息字段"""
        mid: int
        name: str
        face: AnyHttpUrl

    verify_type: int = 4300
    cover: AnyHttpUrl
    cover_type: int
    fid: int
    id: int
    intro: str
    media_count: int
    mid: int
    sharable: bool
    title: str
    type: int
    upper: _Upper

    @property
    def user_name(self) -> str:
        return self.upper.name

    def output_std_model(self) -> _StdCardOutputData:
        content = f'《{self.title}》\n{self.intro}\n- 共{self.media_count}个内容'
        text = f'{self.user_name}分享了收藏夹和播放列表!\n\n{content}\n'
        return _StdCardOutputData.parse_obj({'content': content, 'text': text, 'img_urls': [self.cover]})


class CardType4308LiveRoom(_BaseCardType):
    """Bilibili 动态 Card Type 4308 直播间动态"""

    class _LivePlayInfo(BaseBilibiliModel):
        area_id: int
        area_name: str
        cover: AnyHttpUrl
        link: AnyHttpUrl
        live_id: int
        live_start_time: int
        live_status: int
        room_id: int
        room_type: int
        title: str
        uid: int

    verify_type: int = 4308
    live_play_info: _LivePlayInfo
    live_record_info: Optional[str] = None
    style: int
    type: int

    @property
    def user_name(self) -> str:
        return f'bilibili直播间({self.live_play_info.room_id})'

    def output_std_model(self) -> _StdCardOutputData:
        content = f'bilibili直播间(房间号: {self.live_play_info.room_id})直播了!\n\n【{self.live_play_info.title}】'
        return _StdCardOutputData.parse_obj({'content': content, 'text': content,
                                             'img_urls': [self.live_play_info.cover]})


class CardType1Forward(_BaseCardType):
    """Bilibili 动态 Card Type 1 转发动态"""

    class _UserInfo(BaseBilibiliModel):
        """内部用户信息字段"""
        uid: int
        uname: str
        face: AnyHttpUrl

    class _Item(BaseBilibiliModel):
        """内部内容信息字段"""
        rp_id: int
        uid: int
        content: str
        orig_dy_id: int
        pre_dy_id: int
        orig_type: int
        timestamp: Optional[int] = None  # Deactivated
        ctrl: Any
        reply: Any

    verify_type: int = 1
    user: _UserInfo  # 转发者用户信息
    item: _Item  # 转发相关信息
    # 被转发动态信息, 套娃, (注意多次转发后原动态一直是最开始的那个, 所以源动态类型不可能也是转发)
    origin: Optional[
        Json[CardType2OriginalWithImage]
        | Json[CardType4OriginalWithoutImage]
        | Json[CardType8Video]
        | Json[CardType16ShortVideo]
        | Json[CardType32Anime]
        | Json[CardType64Article]
        | Json[CardType256Music]
        | Json[CardType512Anime]
        | Json[CardType2048Active]
        | Json[CardType4200LiveRoom]
        | Json[CardType4300MediaListShare]
        | Json[CardType4308LiveRoom]
        | Literal['源动态已被作者删除', '源动态不见了', '直播结束了']
        ]  # 原动态被删 origin 字段返回 message 是谁整出来的傻逼玩意儿
    origin_user: Optional[BilibiliDynamicCardDescUserProfile] = None  # 被转发用户信息

    @property
    def user_name(self) -> str:
        return self.user.uname

    def output_std_model(self) -> _StdCardOutputData:
        if self.origin is None:
            text = f'{self.user_name}转发了一条动态!\n\n“{self.item.content}”\n{"=" * 16}\n@源动态已被作者删除'
            img_urls = []
        elif self.origin and isinstance(self.origin, str):
            text = f'{self.user_name}转发了一条动态!\n\n“{self.item.content}”\n{"=" * 16}\n@{self.origin}'
            img_urls = []
        else:
            text = f'{self.user_name}转发了{self.origin.user_name}的动态!\n\n“{self.item.content}”\n' \
                   f'{"=" * 16}\n@{self.origin.output_std_model().text}'
            img_urls = self.origin.output_std_model().img_urls
        return _StdCardOutputData.parse_obj({'content': self.item.content, 'text': text, 'img_urls': img_urls})


class BilibiliDynamicCard(BaseBilibiliModel):
    """Bilibili 动态 Card"""
    desc: BilibiliDynamicCardDesc
    card: (
        Json[CardType1Forward]
        | Json[CardType2OriginalWithImage]
        | Json[CardType4OriginalWithoutImage]
        | Json[CardType8Video]
        | Json[CardType16ShortVideo]
        | Json[CardType32Anime]
        | Json[CardType64Article]
        | Json[CardType256Music]
        | Json[CardType512Anime]
        | Json[CardType2048Active]
        | Json[CardType4200LiveRoom]
        | Json[CardType4300MediaListShare]
        | Json[CardType4308LiveRoom]
    )

    @property
    def output_text(self) -> str:
        return self.card.output_std_model().text

    @property
    def output_img_urls(self) -> list[AnyHttpUrl]:
        return self.card.output_std_model().img_urls


class BilibiliUserDynamicData(BaseBilibiliModel):
    """Bilibili 用户动态 Data"""
    has_more: int
    cards: list[BilibiliDynamicCard] = []
    next_offset: int

    @field_validator('cards')
    @classmethod
    def desc_type_must_equal_card_type(cls, v):
        """校验解析的 Card 类型与动态类型是否匹配"""
        for i, card in enumerate(v):
            desc_type = card.desc.type
            card_type = card.card.verify_type
            if desc_type != card_type:
                raise ValueError(f'Parsed dynamic card({i}, id={card.desc.dynamic_id}) '
                                 f'verify type={card_type} not matched description type={desc_type}')
        return v


class BilibiliUserDynamicModel(BaseBilibiliModel):
    """Bilibili 用户动态 Model"""
    code: int
    data: Optional[BilibiliUserDynamicData] = None
    message: str = ''
    msg: str = ''

    @property
    def all_cards(self) -> list[BilibiliDynamicCard]:
        if self.data is None:
            return []
        return [x for x in self.data.cards]


class BilibiliDynamicData(BaseBilibiliModel):
    """Bilibili 单个动态 Data"""
    card: BilibiliDynamicCard
    result: int = -1

    @field_validator('card')
    @classmethod
    def desc_type_must_equal_card_type(cls, v):
        """校验解析的 Card 类型与动态类型是否匹配"""
        desc_type = v.desc.type
        card_type = v.card.verify_type
        if desc_type != card_type:
            raise ValueError(f'Parsed dynamic card(id={v.desc.dynamic_id}) '
                             f'verify type={card_type} not matched description type={desc_type}')
        return v


class BilibiliDynamicModel(BaseBilibiliModel):
    """Bilibili 单个动态 Model"""
    code: int
    data: Optional[BilibiliDynamicData] = None
    message: str = ''
    msg: str = ''

    @property
    def card(self) -> BilibiliDynamicCard:
        return self.data.card


__all__ = [
    'BilibiliDynamicCard',
    'BilibiliUserDynamicModel',
    'BilibiliDynamicModel'
]
