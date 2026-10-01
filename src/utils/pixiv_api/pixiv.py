"""
@Author         : Ailitonia
@Date           : 2022/04/05 22:03
@FileName       : pixiv.py
@Project        : nonebot2_miya
@Description    : Pixiv API
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import re
from datetime import datetime
from typing import Literal, Self
from urllib.parse import quote

from pydantic import ValidationError

from src.exception import WebSourceException
from .api_base import BasePixivAPI
from .helper import PixivParser
from .model import (
    PixivBookmark,
    PixivDiscovery,
    PixivFollowLatestIllust,
    PixivFollowUser,
    PixivIllustData,
    PixivIllustFull,
    PixivIllustPages,
    PixivIllustRecommend,
    PixivIllustUgoiraMeta,
    PixivRanking,
    PixivSearchingResult,
    PixivTop,
    PixivUserData,
    PixivUserFull,
    PixivUserProfile,
    PixivUserSearchingResult,
)


class PixivCommon(BasePixivAPI):
    """Pixiv 主站通用接口"""

    @classmethod
    async def query_ranking(
            cls,
            mode: Literal[
                'daily',
                'weekly',
                'monthly',
                'rookie',
                'original',
                'male',
                'female',
                'daily_r18',
                'weekly_r18',
                'male_r18',
                'female_r18',
            ],
            *,
            content: Literal['illust', 'ugoira', 'manga'] | None = None,
            date: str | None = None,
            page: int = 1,
    ) -> PixivRanking:
        """获取 Pixiv 排行榜

        :param mode: 排行榜类型
        :param page: 页数
        :param date: 指定日期的排行榜
        :param content: 作品类型, None 为全部
        """
        url = f'{cls._get_root_url()}/ranking.php'  # Pixiv 排行榜
        params = {'format': 'json', 'mode': mode, 'p': page}
        if content is not None:
            params.update({'content': content})
        if date is not None:
            params.update({'date': date})

        # 排行榜接口返回数据没有 error/message 标记, 仅依赖响应状态码与数据校验
        ranking_data = await cls._get_resource_as_json(url=url, params=params)
        return PixivRanking.model_validate(ranking_data)

    @classmethod
    async def search(
            cls,
            word: str,
            domain: Literal['top', 'artworks', 'illustrations', 'manga', 'novels'] = 'top',
            *,
            page: int = 1,
            order: Literal['date_d', 'date', 'popular_d', 'popular_male_d', 'popular_female_d'] = 'date_d',
            mode: Literal['all', 'safe', 'r18'] = 'safe',
            s_mode: Literal['s_tag', 's_tag_full', 's_tc', 's_tag_tc'] = 's_tag',
            type_: Literal['illust_and_ugoira', 'illust', 'ugoira'] | None = None,
            ai_type: int | None = None,
            ratio: Literal['0.5', '0', '-0.5'] | None = None,
            scd: datetime | None = None,
            ecd: datetime | None = None,
            blt: int | None = None,
            bgt: int | None = None,
            wlt: int | None = None,
            wgt: int | None = None,
            hlt: int | None = None,
            hgt: int | None = None,
            wib: int | None = None,
            sbd: datetime | None = None,
            ebd: datetime | None = None,
            csw: bool = False,
            dgw: bool = False,
            lang_: Literal['zh'] = 'zh'
    ) -> PixivSearchingResult:
        """Pixiv 搜索 (部分参数仅限pixiv高级会员可用)

        :param word: 搜索内容
        :param domain: 搜索类型, top: 全部作品, artworks: 插画漫画, illustrations: 插画, manga: 漫画, novels: 小说
        :param page: 搜索结果页码
        :param order: 排序模式, date_d: 按最新排序, date: 按旧排序,
            popular_d: 受全站欢迎, popular_male_d: 受男性欢迎, popular_female_d: 受女性欢迎
        :param mode: 分类模式, all: 全部, safe: 全年龄, r18: R-18
        :param s_mode: 检索标签模式, s_tag: 标签（部分一致）, s_tag_full: 标签（完全一致）,
            s_tc: 标题、说明文字, s_tag_tc: 标签、标题、说明文字
        :param type_: 筛选检索范围, 只有当 domain=illustrations 时才生效,
            illust_and_ugoira: 插画和动图, illust: 插画, ugoira: 动图
        :param ai_type: 筛选是否显示 ai 图, None: 根据用户设置决定(若用户设置不显示则该项不会生效),
            0: 显示 ai 图, 1: 隐藏 ai 图
        :param ratio: 筛选纵横比, 0.5: 横图, -0.5: 纵图, 0: 正方形图
        :param scd: 筛选作品发布时间起点
        :param ecd: 筛选作品发布时间终点
        :param blt: 筛选收藏数下限
        :param bgt: 筛选收藏数上限
        :param wlt: 筛选宽度像素下限
        :param wgt: 筛选宽度像素上限
        :param hlt: 筛选长度像素下限
        :param hgt: 筛选长度像素上限
        :param wib: 筛选已收藏的作品, 1: 所有收藏, 2: 仅限公开收藏, 3: 仅限匿名收藏
        :param sbd: 仅当使用 wib 时有效, 筛选添加收藏的时间起点
        :param ebd: 仅当使用 wib 时有效, 筛选添加收藏的时间终点
        :param csw: 开启后, 可在搜索结果中, 整合显示相同作者投稿的作品
        :param dgw: 开启后, 可以显示有较大可能违反本站方针的作品
        :param lang_: 搜索语言
        :return: 搜索结果数据
        """
        encoded_word = quote(word, safe='', encoding='utf-8')
        params: dict[str, str] = {
            'order': order,
            'mode': mode,
            'p': str(page),
            's_mode': s_mode,
            'lang': lang_,
        }
        if (domain == 'illustrations') and (type_ is not None):
            params.update({'type': str(type_)})
        if ai_type is not None:
            params.update({'ai_type': str(ai_type)})
        if ratio is not None:
            params.update({'ratio': ratio})
        if scd is not None:
            params.update({'scd': scd.strftime('%Y-%m-%d')})
        if ecd is not None:
            params.update({'ecd': ecd.strftime('%Y-%m-%d')})
        if blt is not None:
            params.update({'blt': str(blt)})
        if bgt is not None:
            params.update({'bgt': str(bgt)})
        if wlt is not None:
            params.update({'wlt': str(wlt)})
        if wgt is not None:
            params.update({'wgt': str(wgt)})
        if hlt is not None:
            params.update({'hlt': str(hlt)})
        if hgt is not None:
            params.update({'hgt': str(hgt)})
        if wib is not None:
            params.update({'wib': str(wib)})
        if (wib is not None) and (sbd is not None):
            params.update({'sbd': sbd.strftime('%Y-%m-%d')})
        if (wib is not None) and (ebd is not None):
            params.update({'ebd': ebd.strftime('%Y-%m-%d')})
        if csw:
            params.update({'csw': '1'})
        if dgw:
            params.update({'dgw': '1'})

        searching_url = f'{cls._get_root_url()}/ajax/search/{domain}/{encoded_word}'
        searching_response = await cls._get_resource_as_json(url=searching_url, params=params)
        searching_data = PixivSearchingResult.model_validate(searching_response)
        if searching_data.error:
            raise WebSourceException(400, f'Searching failed, {searching_data.message}')
        return searching_data

    @classmethod
    async def search_by_default_popular_condition(cls, word: str, *, page: int = 1) -> PixivSearchingResult:
        """Pixiv 搜索 (默认使用 illust/safe 作为过滤条件, 匹配标签标题及说明文字, 按热度排序) (需要pixiv高级会员)"""
        return await cls.search(
            word=word,
            domain='illustrations',
            page=page,
            order='popular_d',
            mode='safe',
            s_mode='s_tag_tc',
            type_='illust',
            ai_type=1,
        )

    @classmethod
    async def query_discovery_artworks(
            cls,
            *,
            mode: Literal['all', 'safe', 'r18'] = 'safe',
            limit: int = 60,
            lang: str = 'zh'
    ) -> PixivDiscovery:
        """获取发现页内容"""
        url = f'{cls._get_root_url()}/ajax/discovery/artworks'  # Pixiv 发现
        params = {'mode': mode, 'limit': limit, 'lang': lang}

        discovery_response = await cls._get_resource_as_json(url=url, params=params)
        discovery_data = PixivDiscovery.model_validate(discovery_response)
        if discovery_data.error:
            raise WebSourceException(400, f'Query discovery failed, {discovery_data.message}')
        return discovery_data

    @classmethod
    async def query_top_illust(
            cls,
            *,
            mode: Literal['all'] = 'all',
            lang: str = 'zh'
    ) -> PixivTop:
        """获取首页推荐内容"""
        url = f'{cls._get_root_url()}/ajax/top/illust'
        params = {'mode': mode, 'lang': lang}

        recommend_response = await cls._get_resource_as_json(url=url, params=params)
        recommend_data = PixivTop.model_validate(recommend_response)
        if recommend_data.error:
            raise WebSourceException(400, f'Query top illust failed, {recommend_data.message}')
        return recommend_data

    @classmethod
    async def query_following_user_latest_illust(
            cls,
            page: int,
            *,
            tag: str | None = None,
            mode: Literal['all', 'r18'] = 'all',
            lang: str = 'zh'
    ) -> PixivFollowLatestIllust:
        """获取已关注用户最新作品(需要 cookies)"""
        url = f'{cls._get_root_url()}/ajax/follow_latest/illust'
        params = {'mode': mode, 'lang': lang, 'p': page}
        if tag is not None:
            params.update({'tag': tag})

        following_response = await cls._get_resource_as_json(url=url, params=params)
        following_data = PixivFollowLatestIllust.model_validate(following_response)
        if following_data.error:
            raise WebSourceException(400, f'Query following failed, {following_data.message}')
        return following_data

    @classmethod
    async def query_bookmarks(
            cls,
            uid: int | str | None = None,
            tag: str = '',
            offset: int = 0,
            limit: int = 48,
            rest: Literal['show', 'hide'] = 'show',
            *,
            lang: str = 'zh',
            version: str | None = None
    ) -> PixivBookmark:
        """获取收藏(需要 cookies)"""
        uid = cls._get_default_user_id() if uid is None else uid
        url = f'{cls._get_root_url()}/ajax/user/{uid}/illusts/bookmarks'
        params = {'tag': tag, 'offset': offset, 'limit': limit, 'rest': rest, 'lang': lang}
        if version is not None:
            params.update({'version': version})

        bookmark_response = await cls._get_resource_as_json(url=url, params=params)
        bookmark_data = PixivBookmark.model_validate(bookmark_response)
        if bookmark_data.error:
            raise WebSourceException(400, f'Query bookmarks failed, {bookmark_data.message}')
        return bookmark_data


class PixivArtwork(PixivCommon):
    """Pixiv 作品接口集成"""

    def __init__(self, pid: int | str):
        self.pid = str(pid)
        self.artwork_url = f'{self._get_root_url()}/artworks/{self.pid}'
        self.data_url = f'{self._get_root_url()}/ajax/illust/{self.pid}'
        self.page_data_url = f'{self.data_url}/pages'
        self.ugoira_meta_url = f'{self.data_url}/ugoira_meta'
        self.recommend_url = f'{self.data_url}/recommend/init'

        # 实例缓存
        self.artwork_data: PixivIllustFull | None = None

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(pid={self.pid})'

    async def _query_data(self) -> PixivIllustData:
        """获取作品信息"""
        artwork_data = await self._get_resource_as_json(url=self.data_url)
        return PixivIllustData.model_validate(artwork_data)

    async def _query_page_data(self) -> PixivIllustPages:
        """获取多页信息"""
        page_data = await self._get_resource_as_json(url=self.page_data_url)
        return PixivIllustPages.model_validate(page_data)

    async def _query_ugoira_meta(self) -> PixivIllustUgoiraMeta:
        """获取动图信息"""
        ugoira_meta = await self._get_resource_as_json(url=self.ugoira_meta_url)
        return PixivIllustUgoiraMeta.model_validate(ugoira_meta)

    async def query_artwork(self) -> PixivIllustFull:
        """获取并初始化作品对应缓存数据"""
        if not isinstance(self.artwork_data, PixivIllustFull):
            try:
                artwork_data = await self._query_data()
            except ValidationError:
                raise
            except WebSourceException as e:
                raise WebSourceException(e.status_code, f'Query {self!r} data failed') from e
            except Exception as e:
                raise WebSourceException(500, f'Query {self!r} data failed, {e!r}') from e
            if artwork_data.error:
                raise WebSourceException(400, f'Query {self!r} data failed, {artwork_data.message}')

            try:
                page_data = await self._query_page_data()
            except ValidationError:
                raise
            except WebSourceException as e:
                raise WebSourceException(e.status_code, f'Query {self!r} data failed') from e
            except Exception as e:
                raise WebSourceException(500, f'Query {self!r} page failed, {e!r}') from e
            if page_data.error:
                raise WebSourceException(400, f'Query {self!r} page failed, {page_data.message}')

            # 处理作品tag
            tags = artwork_data.body.tag_info.all_tags

            # 判断 R-18
            is_r18 = False
            for tag in tags:
                if re.match(r'^[Rr]-18[Gg]?$', tag):
                    is_r18 = True
                    break
            sanity_level = artwork_data.body.xRestrict
            if sanity_level >= 1:
                is_r18 = True

            # 判断是否 AI 生成
            is_ai = False
            for tag in tags:
                if re.match(r'^([Nn]ovel[Aa][Ii]([Dd]iffusion)?|[Ss]table[Dd]iffusion)$', tag):
                    is_ai = True
                    break
            for tag in tags.copy():
                if re.match(r'^(AI|ai)(生成|-[Gg]enerated|イラスト|绘图)$', tag):
                    is_ai = True
                    tags.remove(tag)  # remove AI tag
            ai_level = artwork_data.body.aiType
            if ai_level >= 2:
                is_ai = True
            if is_ai:
                tags.insert(0, 'AI生成')

            # 如果是动图额外处理动图资源
            illust_type = artwork_data.body.illustType
            if illust_type == 2:
                ugoira_data = await self._query_ugoira_meta()
                if ugoira_data.error:
                    raise WebSourceException(400, f'Query {self!r} ugoira meta failed, {ugoira_data.message}')
                ugoira_meta = ugoira_data.body
            else:
                ugoira_meta = None

            # 获取发布日期
            published_at = datetime.fromisoformat(artwork_data.body.reuploadDate or artwork_data.body.uploadDate)

            _data = {
                'pid': artwork_data.body.illustId,
                'illust_type': illust_type,
                'is_ai': is_ai,
                'ai_level': ai_level,
                'is_r18': is_r18,
                'sanity_level': sanity_level,
                'title': artwork_data.body.illustTitle,
                'description': artwork_data.body.parsed_description,
                'tags': tags,
                'uid': artwork_data.body.userId,
                'uname': artwork_data.body.userName,
                'width': artwork_data.body.width,
                'height': artwork_data.body.height,
                'bookmark_count': artwork_data.body.bookmarkCount,
                'like_count': artwork_data.body.likeCount,
                'comment_count': artwork_data.body.commentCount,
                'response_count': artwork_data.body.responseCount,
                'view_count': artwork_data.body.viewCount,
                'page_count': artwork_data.body.pageCount,
                'url': self.artwork_url,
                'orig_url': artwork_data.body.urls.original,
                'regular_url': artwork_data.body.urls.regular,
                'type_pages': page_data.type_pages,
                'index_pages': page_data.index_pages,
                'ugoira_meta': ugoira_meta,
                'published_at': published_at.astimezone(),
            }
            self.artwork_data = PixivIllustFull.model_validate(_data)

        if not isinstance(self.artwork_data, PixivIllustFull):
            raise TypeError('Query artwork model failed')
        return self.artwork_data

    async def query_recommend(self, *, init_limit: int = 18, lang: str = 'zh') -> PixivIllustRecommend:
        """获取本作品对应的相关作品推荐

        :param init_limit: 初始化作品推荐时首次加载的作品数量, 默认 18, 最大 180
        :param lang: 语言
        """
        params = {'limit': init_limit, 'lang': lang}
        recommend_response = await self._get_resource_as_json(url=self.recommend_url, params=params)
        recommend_data = PixivIllustRecommend.model_validate(recommend_response)
        if recommend_data.error:
            raise WebSourceException(400, f'Query recommend failed, {recommend_data.message}')
        return recommend_data


class PixivUser(PixivCommon):
    """Pixiv 用户接口集成"""

    def __init__(self, uid: int | str):
        self.uid = str(uid)
        self.user_url = f'{self._get_root_url()}/users/{self.uid}'
        self.data_url = f'{self._get_root_url()}/ajax/user/{self.uid}'
        self.profile_url = f'{self._get_root_url()}/ajax/user/{self.uid}/profile/all'
        self.follow_user_url = f'{self._get_root_url()}/ajax/user/{self.uid}/following'

        # 实例缓存
        self.user_data: PixivUserFull | None = None

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(uid={self.uid})'

    @classmethod
    def init_default_user(cls) -> Self:
        return cls(uid=cls._get_default_user_id())

    @classmethod
    async def search_user(
            cls,
            nick: str,
            *,
            mode: Literal['s_usr', 's_usr_full'] = 's_usr',
            page: int = 1,
    ) -> PixivUserSearchingResult:
        """搜索用户"""
        url = f'{cls._get_root_url()}/search/users'
        params = {'nick': nick, 's_mode': mode, 'p': page}
        searching_data = await cls.get_resource_as_text(url=url, params=params)

        # p站唯独画师搜索没有做前后端分离, 只能解析页面
        return await PixivParser.parse_user_searching_result_page(content=searching_data)

    async def _query_user_data(self) -> PixivUserData:
        """获取用户基本信息"""
        params = {'lang': 'zh'}

        user_data = await self._get_resource_as_json(url=self.data_url, params=params)
        return PixivUserData.model_validate(user_data)

    async def _query_user_artwork_data(self) -> PixivUserProfile:
        """获取用户作品信息"""
        params = {'lang': 'zh'}

        user_artwork_data = await self._get_resource_as_json(url=self.profile_url, params=params)
        return PixivUserProfile.model_validate(user_artwork_data)

    async def query_user(self) -> PixivUserFull:
        """获取并初始化用户对应缓存数据"""
        if not isinstance(self.user_data, PixivUserFull):
            try:
                user_data = await self._query_user_data()
            except ValidationError:
                raise
            except WebSourceException as e:
                raise WebSourceException(e.status_code, f'Query {self!r} data failed') from e
            except Exception as e:
                raise WebSourceException(500, f'Query {self!r} data failed, {e!r}') from e
            if user_data.error:
                raise WebSourceException(400, f'Query {self!r} data failed, {user_data.message}')

            try:
                user_artwork_data = await self._query_user_artwork_data()
            except ValidationError:
                raise
            except WebSourceException as e:
                raise WebSourceException(e.status_code, f'Query {self!r} data failed') from e
            except Exception as e:
                raise WebSourceException(500, f'Query {self!r} data failed, {e!r}') from e
            if user_artwork_data.error:
                raise WebSourceException(400, f'Query {self!r} artwork data failed, {user_artwork_data.message}')

            full_data = {
                'user_id': user_data.body.userId,
                'name': user_data.body.name,
                'image': user_data.body.image,
                'image_big': user_data.body.imageBig,
                'illusts': user_artwork_data.body.illust_list,
                'manga': user_artwork_data.body.manga_list,
                'novels': user_artwork_data.body.novel_list
            }
            self.user_data = PixivUserFull.model_validate(full_data)

        if not isinstance(self.user_data, PixivUserFull):
            raise TypeError('Query user model failed')
        return self.user_data

    async def query_user_bookmarks(self, page: int = 1, *, limit: int = 48) -> PixivBookmark:
        """获取该用户的收藏, 默认每页 48 张作品"""
        page = 1 if page < 1 else page
        return await self.query_bookmarks(uid=self.uid, offset=limit * (page - 1), limit=limit)

    async def query_user_following_users(
            self,
            offset: int = 0,
            limit: int = 24,
            *,
            rest: Literal['show', 'hide'] = 'show',
            tag: str | None = None,
            accepting_requests: int = 0,
            lang: str = 'zh',
    ) -> PixivFollowUser:
        """获取已关注用户列表"""
        params = {
            'offset': offset,
            'limit': limit,
            'rest': rest,
            'acceptingRequests': accepting_requests,
            'lang': lang,
        }
        if tag is not None:
            params.update({'tag': tag})

        following_user_response = await self._get_resource_as_json(url=self.follow_user_url, params=params)
        following_user_data = PixivFollowUser.model_validate(following_user_response)
        if following_user_data.error:
            raise WebSourceException(400, f'Query following failed, {following_user_data.message}')
        return following_user_data


__all__ = [
    'PixivArtwork',
    'PixivCommon',
    'PixivUser',
]
