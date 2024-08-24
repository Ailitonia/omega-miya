"""
@Author         : Ailitonia
@Date           : 2022/04/05 22:03
@FileName       : pixiv.py
@Project        : nonebot2_miya
@Description    : Pixiv Api
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import re
from datetime import datetime
from typing import Literal, Optional
from urllib.parse import quote

from pydantic import ValidationError

from src.exception import WebSourceException
from .api_base import BasePixivAPI
from .exception import PixivApiError
from .helper import PixivParser
from .model import (
    PixivArtworkDataModel,
    PixivArtworkPageModel,
    PixivArtworkUgoiraMeta,
    PixivArtworkCompleteDataModel,
    PixivArtworkRecommendModel,
    PixivRankingModel,
    PixivSearchingResultModel,
    PixivDiscoveryModel,
    PixivTopModel,
    PixivGlobalData,
    PixivUserDataModel,
    PixivUserArtworkDataModel,
    PixivUserModel,
    PixivUserSearchingModel,
    PixivFollowLatestIllust,
    PixivBookmark
)


class PixivCommon(BasePixivAPI):
    """Pixiv 主站通用接口"""

    @classmethod
    async def query_global_data(cls) -> PixivGlobalData:
        """获取全局信息(需要 cookies)"""
        root_page_content = await cls.get_resource_as_text(url=cls._get_root_url())
        return await PixivParser.parse_global_data(content=root_page_content)

    @classmethod
    async def query_ranking(
            cls,
            mode: Literal['daily', 'weekly', 'monthly', 'rookie', 'original', 'male', 'female',
                          'daily_r18', 'weekly_r18', 'male_r18', 'female_r18'],
            *,
            page: int = 1,
            content: Literal['illust', 'ugoira', 'manga'] | None = None
    ) -> PixivRankingModel:
        """获取 Pixiv 排行榜

        :param mode: 排行榜类型
        :param page: 页数
        :param content: 作品类型, None 为全部
        """
        url = f'{cls._get_root_url()}/ranking.php'  # Pixiv 排行榜
        params = {'format': 'json', 'mode': mode, 'p': page}
        if content is not None:
            params.update({'content': content})

        ranking_data = await cls._get_json(url=url, params=params)
        return PixivRankingModel.model_validate(ranking_data)

    @classmethod
    async def search(
            cls,
            word: str,
            mode: Literal['artworks', 'illustrations', 'manga'] = 'artworks',
            *,
            page: int = 1,
            order: Literal['date_d', 'date', 'popular_d', 'popular_male_d', 'popular_female_d'] = 'date_d',
            mode_: Literal['all', 'safe', 'r18'] = 'safe',
            s_mode_: Literal['s_tag', 's_tag_full', 's_tc'] = 's_tag',
            type_: Literal['all', 'illust_and_ugoira', 'illust', 'manga', 'ugoira'] = 'illust_and_ugoira',
            ai_type: int | None = None,
            ratio_: Literal['0.5', '0', '-0.5'] | None = None,
            scd_: datetime | None = None,
            ecd_: datetime | None = None,
            blt_: int | None = None,
            bgt_: int | None = None,
            lang_: Literal['zh'] = 'zh'
    ) -> PixivSearchingResultModel:
        """Pixiv 搜索 (部分参数仅限pixiv高级会员可用)

        :param word: 搜索内容
        :param mode: 作品类型, artworks: 插画·漫画, top: 全部作品, illustrations: 插画, manga: 漫画, novels: 小说
        :param page: 搜索结果页码
        :param order: 排序模式, date_d: 按最新排序, date: 按旧排序, popular_d: 受全站欢迎, popular_male_d: 受男性欢迎, popular_female_d: 受女性欢迎
        :param mode_: 搜索参数, all: 全部, safe: 全年龄, r18: R-18
        :param s_mode_: 检索标签模式, s_tag: 标签（部分一致）, s_tag_full: 标签（完全一致）, s_tc: 标题、说明文字
        :param type_: 筛选检索范围, all: 插画、漫画、动图（动态插画）, illust_and_ugoira: 插画、动图, illust: 插画, manga: 漫画. ugoira: 动图
        :param ai_type: 筛选是否显示 ai 图, None: 根据用户设置决定(若用户设置不显示则该项不会生效), 0: 显示 ai 图, 1: 隐藏 ai 图
        :param ratio_: 筛选纵横比, 0.5: 横图, -0.5: 纵图, 0: 正方形图
        :param scd_: 筛选时间起点, 从什么时候开始
        :param ecd_: 筛选时间终点, 从什么时候开始
        :param blt_: 筛选收藏数下限(参数仅限pixiv高级会员可用)
        :param bgt_: 筛选收藏数上限(参数仅限pixiv高级会员可用)
        :param lang_: 搜索语言
        :return: dict, 原始返回数据
        """
        word = quote(word, encoding='utf-8')
        params = {
            'word': word, 'order': order, 'mode': mode_, 'p': page, 's_mode': s_mode_, 'type': type_, 'lang': lang_}
        if ai_type:
            params.update({'ai_type': ai_type})
        if ratio_:
            params.update({'ratio': ratio_})
        if scd_:
            params.update({'scd': scd_.strftime('%Y-%m-%d')})
        if ecd_:
            params.update({'ecd': ecd_.strftime('%Y-%m-%d')})
        if blt_:
            params.update({'blt': blt_})
        if bgt_:
            params.update({'bgt': bgt_})

        searching_url = f'{cls._get_root_url()}/ajax/search/{mode}/{word}'
        searching_data = await cls._get_json(url=searching_url, params=params)
        return PixivSearchingResultModel.model_validate(searching_data)

    @classmethod
    async def search_by_default_popular_condition(cls, word: str) -> PixivSearchingResultModel:
        """Pixiv 搜索 (使用热度作为过滤条件筛选条件) (需要pixiv高级会员)"""
        return await cls.search(
            word=word, mode='illustrations', order='popular_d', mode_='safe', type_='illust', ai_type=1
        )

    @classmethod
    async def query_discovery_artworks(
            cls,
            *,
            mode: Literal['all', 'safe', 'r18'] = 'safe',
            limit: int = 60,
            lang: Literal['zh'] = 'zh'
    ) -> PixivDiscoveryModel:
        """获取发现页内容"""
        url = f'{cls._get_root_url()}/ajax/discovery/artworks'  # Pixiv 发现
        params = {'mode': mode, 'limit': limit, 'lang': lang}

        discovery_data = await cls._get_json(url=url, params=params)
        return PixivDiscoveryModel.model_validate(discovery_data)

    @classmethod
    async def query_top_illust(
            cls,
            *,
            mode: Literal['all'] = 'all',
            lang: Literal['zh'] = 'zh'
    ) -> PixivTopModel:
        """获取首页推荐内容"""
        url = f'{cls._get_root_url()}/ajax/top/illust'
        params = {'mode': mode, 'lang': lang}

        recommend_data = await cls._get_json(url=url, params=params)
        return PixivTopModel.model_validate(recommend_data)

    @classmethod
    async def query_following_user_latest_illust(
            cls,
            page: int,
            *,
            mode: Literal['all', 'r18'] = 'all',
            lang: str = 'zh'
    ) -> PixivFollowLatestIllust:
        """获取已关注用户最新作品(需要 cookies)"""
        url = f'{cls._get_root_url()}/ajax/follow_latest/illust'
        params = {'mode': mode, 'lang': lang, 'p': page}

        following_data = await cls._get_json(url=url, params=params)
        return PixivFollowLatestIllust.model_validate(following_data)

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
        if uid is None:
            global_data = await cls.query_global_data()
            uid = global_data.uid

        url = f'https://www.pixiv.net/ajax/user/{uid}/illusts/bookmarks'
        params = {'tag': tag, 'offset': offset, 'limit': limit, 'rest': rest, 'lang': lang}
        if version is not None:
            params.update({'version': version})

        bookmark_data = await cls._get_json(url=url, params=params)
        return PixivBookmark.model_validate(bookmark_data)


class PixivArtwork(PixivCommon):
    """Pixiv 作品接口集成"""

    def __init__(self, pid: int):
        self.pid = pid
        self.artwork_url = f'{self._get_root_url()}/artworks/{pid}'
        self.data_url = f'{self._get_root_url()}/ajax/illust/{pid}'
        self.page_data_url = f'{self.data_url}/pages'
        self.ugoira_meta_url = f'{self.data_url}/ugoira_meta'
        self.recommend_url = f'{self.data_url}/recommend/init'

        # 实例缓存
        self.artwork_model: Optional[PixivArtworkCompleteDataModel] = None

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(pid={self.pid})'

    async def _query_data(self) -> PixivArtworkDataModel:
        """获取作品信息"""
        artwork_data = await self._get_json(url=self.data_url)
        return PixivArtworkDataModel.model_validate(artwork_data)

    async def _query_page_date(self) -> PixivArtworkPageModel:
        """获取多页信息"""
        page_data = await self._get_json(url=self.page_data_url)
        return PixivArtworkPageModel.model_validate(page_data)

    async def _query_ugoira_meta(self) -> PixivArtworkUgoiraMeta:
        """获取动图信息"""
        ugoira_meta = await self._get_json(url=self.ugoira_meta_url)
        return PixivArtworkUgoiraMeta.model_validate(ugoira_meta)

    async def query_artwork(self) -> PixivArtworkCompleteDataModel:
        """获取并初始化作品对应 PixivArtworkCompleteDataModel"""
        if not isinstance(self.artwork_model, PixivArtworkCompleteDataModel):
            try:
                artwork_data = await self._query_data()
            except ValidationError:
                raise
            except Exception as e:
                raise WebSourceException(f'Query artwork(pid={self.pid}) data failed, {e}') from e
            if artwork_data.error:
                raise PixivApiError(f'Query artwork(pid={self.pid}) data failed, {artwork_data.message}')

            try:
                page_data = await self._query_page_date()
            except ValidationError:
                raise
            except Exception as e:
                raise WebSourceException(f'Query artwork(pid={self.pid}) page failed, {e}') from e
            if page_data.error:
                raise PixivApiError(f'Query artwork(pid={self.pid}) page failed, {page_data.message}')

            # 处理作品tag
            tags = artwork_data.body.tags.all_tags

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
                    tags.remove(tag)
            ai_level = artwork_data.body.aiType
            if ai_level >= 2:
                is_ai = True
            if is_ai:
                tags.insert(0, 'AI生成')

            # 如果是动图额外处理动图资源
            illust_type = artwork_data.body.illustType
            if illust_type == 2:
                try:
                    ugoira_data = await self._query_ugoira_meta()
                    if ugoira_data.error:
                        raise PixivApiError(f'Query artwork(pid={self.pid}) ugoira meta failed, {ugoira_data.message}')
                except Exception as e:
                    raise WebSourceException(f'Query artwork(pid={self.pid}) ugoira meta failed, {e}') from e
                ugoira_meta = ugoira_data.body
            else:
                ugoira_meta = None

            _data = {
                'illust_type': illust_type,
                'pid': artwork_data.body.illustId,
                'title': artwork_data.body.illustTitle,
                'sanity_level': sanity_level,
                'is_r18': is_r18,
                'ai_level': ai_level,
                'is_ai': is_ai,
                'uid': artwork_data.body.userId,
                'uname': artwork_data.body.userName,
                'description': artwork_data.body.parsed_description,
                'tags': tags,
                'url': self.artwork_url,
                'width': artwork_data.body.width,
                'height': artwork_data.body.height,
                'like_count': artwork_data.body.likeCount,
                'bookmark_count': artwork_data.body.bookmarkCount,
                'view_count': artwork_data.body.viewCount,
                'comment_count': artwork_data.body.commentCount,
                'page_count': artwork_data.body.pageCount,
                'orig_url': artwork_data.body.urls.original,
                'regular_url': artwork_data.body.urls.regular,
                'all_url': page_data.type_page,
                'all_page': page_data.index_page,
                'ugoira_meta': ugoira_meta
            }
            self.artwork_model = PixivArtworkCompleteDataModel.model_validate(_data)

        assert isinstance(self.artwork_model, PixivArtworkCompleteDataModel), 'Query artwork model failed'
        return self.artwork_model

    async def query_recommend(self, *, init_limit: int = 18, lang: Literal['zh'] = 'zh') -> PixivArtworkRecommendModel:
        """获取本作品对应的相关作品推荐

        :param init_limit: 初始化作品推荐时首次加载的作品数量, 默认 18, 最大 180
        :param lang: 语言
        """
        params = {'limit': init_limit, 'lang': lang}
        recommend_data = await self._get_json(url=self.recommend_url, params=params)

        # 清理返回数据中的 isAdContainer 字段
        illusts = [illust for illust in recommend_data.get('body', {}).get('illusts', [])
                   if not illust.get('isAdContainer')]
        next_ids = recommend_data.get('nextIds', [])
        return PixivArtworkRecommendModel(illusts=illusts, nextIds=next_ids)


class PixivUser(PixivCommon):
    """Pixiv 用户接口集成"""

    def __init__(self, uid: int):
        self.uid = uid
        self.user_url = f'{self._get_root_url()}/users/{uid}'
        self.data_url = f'{self._get_root_url()}/ajax/user/{uid}'
        self.profile_url = f'{self._get_root_url()}/ajax/user/{uid}/profile/all'

        # 实例缓存
        self.user_model: Optional[PixivUserModel] = None

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(uid={self.uid})'

    @classmethod
    async def search_user(cls, nick: str) -> PixivUserSearchingModel:
        """搜索用户"""
        url = f'{cls._get_root_url()}/search_user.php'
        params = {'s_mode': 's_usr', 'nick': nick}
        searching_data = await cls.get_resource_as_text(url=url, params=params)

        # p站唯独画师搜索没有做前后端分离 只能解析页面了
        return await PixivParser.parse_user_searching_result_page(content=searching_data)

    async def _query_user_data(self) -> PixivUserDataModel:
        """获取用户基本信息"""
        params = {'lang': 'zh'}

        user_data = await self._get_json(url=self.data_url, params=params)
        return PixivUserDataModel.model_validate(user_data)

    async def _query_user_artwork_data(self) -> PixivUserArtworkDataModel:
        """获取用户作品信息"""
        params = {'lang': 'zh'}

        user_artwork_data = await self._get_json(url=self.profile_url, params=params)
        return PixivUserArtworkDataModel.model_validate(user_artwork_data)

    async def query_user_data(self) -> PixivUserModel:
        """获取并初始化用户对应 PixivUserModel"""
        if not isinstance(self.user_model, PixivUserModel):
            _user_data = await self._query_user_data()
            if _user_data.error:
                raise PixivApiError(f'Query user(uid={self.uid}) data failed, {_user_data.message}')

            _user_artwork_data = await self._query_user_artwork_data()
            if _user_artwork_data.error:
                raise PixivApiError(f'Query user(uid={self.uid}) artwork data failed, {_user_artwork_data.message}')

            _data = {
                'user_id': _user_data.body.userId,
                'name': _user_data.body.name,
                'image': _user_data.body.image,
                'image_big': _user_data.body.imageBig,
                'illusts': _user_artwork_data.body.illust_list,
                'manga': _user_artwork_data.body.manga_list,
                'novels': _user_artwork_data.body.novel_list
            }
            self.user_model = PixivUserModel.model_validate(_data)

        assert isinstance(self.user_model, PixivUserModel), 'Query user model failed'
        return self.user_model

    async def query_user_bookmarks(self, page: int = 1) -> PixivBookmark:
        """获取该用户的收藏, 默认每页 48 张作品"""
        return await self.query_bookmarks(uid=self.uid, offset=48 * (page - 1))


__all__ = [
    'PixivArtwork',
    'PixivCommon',
    'PixivUser',
]
