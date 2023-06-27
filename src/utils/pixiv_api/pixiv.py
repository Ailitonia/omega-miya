"""
@Author         : Ailitonia
@Date           : 2022/04/05 22:03
@FileName       : pixiv.py
@Project        : nonebot2_miya
@Description    : Pixiv Api
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import abc
import re
import zipfile
import imageio
import asyncio
from datetime import datetime
from typing import Literal, Optional, Any
from urllib.parse import quote
from io import BytesIO

from nonebot.utils import run_sync

from src.resource import TemporaryResource
from src.service.omega_requests import OmegaRequests
from src.utils.process_utils import semaphore_gather
from src.utils.image_utils import ImageUtils
from src.utils.image_utils.template import PreviewImageModel, PreviewImageThumbs

from .config import pixiv_config, pixiv_resource_config
from .exception import PixivApiError, PixivNetworkError
from .model import (PixivArtworkDataModel, PixivArtworkPageModel, PixivArtworkUgoiraMeta,
                    PixivArtworkCompleteDataModel, PixivArtworkRecommendModel,
                    PixivRankingModel, PixivSearchingResultModel,
                    PixivDiscoveryModel, PixivRecommendModel,
                    PixivUserDataModel, PixivUserArtworkDataModel, PixivUserModel, PixivUserSearchingModel)
from .helper import (parse_user_searching_result_page, generate_user_searching_result_image,
                     emit_preview_model_from_ranking_model, emit_preview_model_from_searching_model,
                     format_artwork_preview_desc, generate_artworks_preview_image)


class Pixiv(abc.ABC):
    """Pixiv 基类"""
    _root_url: str = 'https://www.pixiv.net'
    _ranking_url: str = 'https://www.pixiv.net/ranking.php'  # Pixiv 排行榜
    _search_url: str = 'https://www.pixiv.net/ajax/search/'  # Pixiv 搜索
    _recommend_artworks_url: str = 'https://www.pixiv.net/ajax/top/illust'  # Pixiv 推荐
    _discovery_artworks_url: str = 'https://www.pixiv.net/ajax/discovery/artworks'  # Pixiv 发现

    def __repr__(self):
        return f'<{self.__class__.__name__}>'

    @classmethod
    async def request_json(
            cls,
            url: str,
            params: Optional[dict[str, Any]] = None,
            headers: Optional[dict[str, Any]] = None
    ) -> Any:
        """请求 api 并返回 json 数据"""
        if headers is None:
            headers = OmegaRequests.get_default_headers()
            headers.update({'referer': 'https://www.pixiv.net/'})

        requests = OmegaRequests(timeout=10, headers=headers, cookies=pixiv_config.cookie_phpssid)
        response = await requests.get(url=url, params=params)
        if response.status_code != 200:
            raise PixivNetworkError(f'{response.request}, status code {response.status_code}')

        return OmegaRequests.parse_content_json(response)

    @classmethod
    async def request_resource(
            cls,
            url: str,
            params: Optional[dict[str, Any]] = None,
            headers: Optional[dict[str, Any]] = None,
            timeout: int = 45
    ) -> str | bytes | None:
        """请求原始资源内容"""
        if headers is None:
            headers = OmegaRequests.get_default_headers()
            headers.update({'referer': 'https://www.pixiv.net/'})

        requests = OmegaRequests(timeout=timeout, headers=headers, cookies=pixiv_config.cookie_phpssid)
        response = await requests.get(url=url, params=params)
        if response.status_code != 200:
            raise PixivNetworkError(f'{response.request}, status code {response.status_code}')

        return response.content

    @classmethod
    async def download_resource(
            cls,
            url: str,
            params: Optional[dict[str, Any]] = None,
            headers: Optional[dict[str, Any]] = None,
            timeout: int = 60
    ) -> TemporaryResource:
        """下载任意资源到本地, 保持原始文件名, 直接覆盖同名文件"""
        if headers is None:
            headers = OmegaRequests.get_default_headers()
            headers.update({'referer': 'https://www.pixiv.net/'})

        original_file_name = OmegaRequests.parse_url_file_name(url=url)
        file = pixiv_resource_config.default_download_folder(original_file_name)
        requests = OmegaRequests(timeout=timeout, headers=headers, cookies=pixiv_config.cookie_phpssid)

        return await requests.download(url=url, file=file, params=params)

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
        params = {'format': 'json', 'mode': mode, 'p': page}
        if content is not None:
            params.update({'content': content})

        ranking_data = await cls.request_json(url=cls._ranking_url, params=params)
        return PixivRankingModel.parse_obj(ranking_data)

    @classmethod
    async def query_daily_illust_ranking_with_preview(cls, page: int = 1) -> TemporaryResource:
        ranking_result = await cls.query_ranking(mode='daily', page=page, content='illust')
        name = f'Pixiv Daily Ranking {datetime.now().strftime("%Y-%m-%d")}'
        preview_request = await emit_preview_model_from_ranking_model(ranking_name=name, model=ranking_result)
        preview_img_file = await generate_artworks_preview_image(
            preview=preview_request, preview_size=(512, 512), hold_ratio=True, num_of_line=6)
        return preview_img_file

    @classmethod
    async def query_weekly_illust_ranking_with_preview(cls, page: int = 1) -> TemporaryResource:
        ranking_result = await cls.query_ranking(mode='weekly', page=page, content='illust')
        name = f'Pixiv Weekly Ranking {datetime.now().strftime("%Y-%m-%d")}'
        preview_request = await emit_preview_model_from_ranking_model(ranking_name=name, model=ranking_result)
        preview_img_file = await generate_artworks_preview_image(
            preview=preview_request, preview_size=(512, 512), hold_ratio=True, num_of_line=6)
        return preview_img_file

    @classmethod
    async def query_monthly_illust_ranking_with_preview(cls, page: int = 1) -> TemporaryResource:
        ranking_result = await cls.query_ranking(mode='monthly', page=page, content='illust')
        name = f'Pixiv Monthly Ranking {datetime.now().strftime("%Y-%m-%d")}'
        preview_request = await emit_preview_model_from_ranking_model(ranking_name=name, model=ranking_result)
        preview_img_file = await generate_artworks_preview_image(
            preview=preview_request, preview_size=(512, 512), hold_ratio=True, num_of_line=6)
        return preview_img_file

    @classmethod
    async def query_daily_r18_illust_ranking_with_preview(cls, page: int = 1) -> TemporaryResource:
        ranking_result = await cls.query_ranking(mode='daily_r18', page=page, content='illust')
        name = f'Pixiv R18 Daily Ranking {datetime.now().strftime("%Y-%m-%d")}'
        preview_request = await emit_preview_model_from_ranking_model(ranking_name=name, model=ranking_result)
        preview_img_file = await generate_artworks_preview_image(
            preview=preview_request, preview_size=(512, 512), hold_ratio=True, num_of_line=6)
        return preview_img_file

    @classmethod
    async def query_weekly_r18_illust_ranking_with_preview(cls, page: int = 1) -> TemporaryResource:
        ranking_result = await cls.query_ranking(mode='weekly_r18', page=page, content='illust')
        name = f'Pixiv R18 Weekly Ranking {datetime.now().strftime("%Y-%m-%d")}'
        preview_request = await emit_preview_model_from_ranking_model(ranking_name=name, model=ranking_result)
        preview_img_file = await generate_artworks_preview_image(
            preview=preview_request, preview_size=(512, 512), hold_ratio=True, num_of_line=6)
        return preview_img_file

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

        searching_url = f'{cls._search_url}{mode}/{word}'
        searching_data = await cls.request_json(url=searching_url, params=params)
        return PixivSearchingResultModel.parse_obj(searching_data)

    @classmethod
    async def search_by_default_popular_condition(cls, word: str) -> PixivSearchingResultModel:
        """Pixiv 搜索 (使用热度作为过滤条件筛选条件) (需要pixiv高级会员)"""
        return await cls.search(word=word, mode='illustrations', order='popular_d', mode_='safe', type_='illust')

    @classmethod
    async def search_with_preview(
            cls,
            word: str,
            mode: Literal['artworks', 'illustrations', 'manga'] = 'artworks',
            *,
            page: int = 1,
            order: Literal['date_d', 'date', 'popular_d', 'popular_male_d', 'popular_female_d'] = 'date_d',
            mode_: Literal['all', 'safe', 'r18'] = 'safe',
            s_mode_: Literal['s_tag', 's_tag_full', 's_tc'] = 's_tag',
            type_: Literal['all', 'illust_and_ugoira', 'illust', 'manga', 'ugoira'] = 'illust_and_ugoira',
            ratio_: Literal['0.5', '0', '-0.5'] | None = None,
            scd_: datetime | None = None,
            ecd_: datetime | None = None,
            blt_: int | None = None,
            bgt_: int | None = None,
            lang_: Literal['zh'] = 'zh'
    ) -> TemporaryResource:
        """搜索作品并生成预览图"""
        searching_result = await cls.search(
            word=word, mode=mode, page=page, order=order, mode_=mode_, s_mode_=s_mode_,
            type_=type_, ratio_=ratio_, scd_=scd_, ecd_=ecd_, blt_=blt_, bgt_=bgt_, lang_=lang_)
        name = f'Searching - {word}'
        preview_request = await emit_preview_model_from_searching_model(searching_name=name, model=searching_result)
        preview_img_file = await generate_artworks_preview_image(preview=preview_request)
        return preview_img_file

    @classmethod
    async def search_by_default_popular_condition_with_preview(cls, word: str) -> TemporaryResource:
        """搜索作品并生成预览图 (使用通用的好图筛选条件) (近三年的图) (会用到仅限pixiv高级会员可用的部分参数)"""
        searching_result = await cls.search_by_default_popular_condition(word=word)
        name = f'Searching - {word}'
        preview_request = await emit_preview_model_from_searching_model(searching_name=name, model=searching_result)
        preview_img_file = await generate_artworks_preview_image(preview=preview_request)
        return preview_img_file

    @classmethod
    async def query_discovery_artworks(
            cls,
            *,
            mode: Literal['all', 'safe', 'r18'] = 'safe',
            limit: int = 60,
            lang: Literal['zh'] = 'zh'
    ) -> PixivDiscoveryModel:
        """获取发现页内容"""
        params = {'mode': mode, 'limit': limit, 'lang': lang}

        discovery_data = await cls.request_json(url=cls._discovery_artworks_url, params=params)
        return PixivDiscoveryModel.parse_obj(discovery_data)

    @classmethod
    async def query_discovery_artworks_with_preview(cls) -> TemporaryResource:
        """获取发现页内容并生成预览图"""
        discovery_result = await cls.query_discovery_artworks(limit=60)
        # 获取缩略图内容
        name = 'Pixiv Discovery'
        preview_request = await _emit_preview_model_from_artwork_pids(preview_name=name,
                                                                      pids=discovery_result.recommend_pids)
        preview_img_file = await generate_artworks_preview_image(
            preview=preview_request, preview_size=(360, 360), hold_ratio=True, num_of_line=6)
        return preview_img_file

    @classmethod
    async def query_recommend_illust(
            cls,
            *,
            mode: Literal['all'] = 'all',
            lang: Literal['zh'] = 'zh'
    ) -> PixivRecommendModel:
        """获取首页推荐内容"""
        params = {'mode': mode, 'lang': lang}

        recommend_data = await cls.request_json(url=cls._recommend_artworks_url, params=params)
        return PixivRecommendModel.parse_obj(recommend_data)

    @classmethod
    async def query_recommend_artworks_with_preview(cls) -> TemporaryResource:
        """获取首页推荐内容并生成预览图"""
        recommend_result = await cls.query_recommend_illust()
        # 获取缩略图内容
        name = 'Pixiv Top Recommend'
        preview_request = await _emit_preview_model_from_artwork_pids(preview_name=name,
                                                                      pids=recommend_result.recommend_pids)
        preview_img_file = await generate_artworks_preview_image(
            preview=preview_request, preview_size=(512, 512), hold_ratio=True, num_of_line=3)
        return preview_img_file


class PixivArtwork(Pixiv):
    """Pixiv 作品"""
    _artwork_root: str = 'https://www.pixiv.net/artworks/'
    _artwork_data_url: str = 'https://www.pixiv.net/ajax/illust/'

    def __init__(self, pid: int):
        self.pid = pid
        self.artwork_url = f'{self._artwork_root}{pid}'
        self.data_url = f'{self._artwork_data_url}{pid}'
        self.page_data_url = f'{self.data_url}/pages'
        self.ugoira_meta_url = f'{self.data_url}/ugoira_meta'
        self.recommend_url = f'{self.data_url}/recommend/init'

        # 实例缓存
        self.artwork_model: Optional[PixivArtworkCompleteDataModel] = None

    def __repr__(self):
        return f'<{self.__class__.__name__}(pid={self.pid})>'

    async def _query_data(self) -> PixivArtworkDataModel:
        """获取作品信息"""
        artwork_data = await self.request_json(url=self.data_url)
        return PixivArtworkDataModel.parse_obj(artwork_data)

    async def _query_page_date(self) -> PixivArtworkPageModel:
        """获取多页信息"""
        page_data = await self.request_json(url=self.page_data_url)
        return PixivArtworkPageModel.parse_obj(page_data)

    async def _query_ugoira_meta(self) -> PixivArtworkUgoiraMeta:
        """获取动图信息"""
        ugoira_meta = await self.request_json(url=self.ugoira_meta_url)
        return PixivArtworkUgoiraMeta.parse_obj(ugoira_meta)

    async def get_artwork_model(self) -> PixivArtworkCompleteDataModel:
        """获取并初始化作品对应 PixivArtworkCompleteDataModel"""
        if not isinstance(self.artwork_model, PixivArtworkCompleteDataModel):
            query_data_task = asyncio.create_task(self._query_data())
            query_page_data_task = asyncio.create_task(self._query_page_date())

            _artwork_data = await query_data_task
            if _artwork_data.error:
                query_page_data_task.cancel()
                raise PixivApiError(f'Query artwork(pid={self.pid}) data failed, {_artwork_data.message}')

            _page_data = await query_page_data_task
            if _page_data.error:
                raise PixivApiError(f'Query artwork(pid={self.pid}) page failed, {_page_data.message}')

            # 处理作品tag
            _tags = _artwork_data.body.tags.all_tags

            # 判断 R-18
            _is_r18 = False
            for tag in _tags:
                if re.match(r'^[Rr]-18[Gg]?$', tag):
                    _is_r18 = True
                    break
            _sanity_level = _artwork_data.body.xRestrict
            if _sanity_level >= 1:
                _is_r18 = True

            # 判断是否 AI 生成
            _is_ai = False
            for tag in _tags:
                if re.match(r'^([Nn]ovel[Aa][Ii]([Dd]iffusion)?|[Ss]table[Dd]iffusion|AIイラスト)$', tag):
                    _is_ai = True
                    break
            _ai_level = _artwork_data.body.aiType
            if _ai_level >= 2:
                _is_ai = True

            # 导出多图列表
            _all_url = _page_data.type_page
            _all_page = _page_data.index_page

            # 如果是动图额外处理动图资源
            _illust_type = _artwork_data.body.illustType
            if _illust_type == 2:
                _ugoira_data = await self._query_ugoira_meta()
                if _ugoira_data.error:
                    raise PixivApiError(f'Query artwork(pid={self.pid}) ugoira meta failed, {_ugoira_data.message}')
                _ugoira_meta = _ugoira_data.body
            else:
                _ugoira_meta = None

            _data = {
                'illust_type': _illust_type,
                'pid': _artwork_data.body.illustId,
                'title': _artwork_data.body.illustTitle,
                'sanity_level': _sanity_level,
                'is_r18': _is_r18,
                'is_ai': _is_ai,
                'uid': _artwork_data.body.userId,
                'uname': _artwork_data.body.userName,
                'description': _artwork_data.body.parsed_description,
                'tags': _tags,
                'url': self.artwork_url,
                'width': _artwork_data.body.width,
                'height': _artwork_data.body.height,
                'like_count': _artwork_data.body.likeCount,
                'bookmark_count': _artwork_data.body.bookmarkCount,
                'view_count': _artwork_data.body.viewCount,
                'comment_count': _artwork_data.body.commentCount,
                'page_count': _artwork_data.body.pageCount,
                'orig_url': _artwork_data.body.urls.original,
                'regular_url': _artwork_data.body.urls.regular,
                'all_url': _all_url,
                'all_page': _all_page,
                'ugoira_meta': _ugoira_meta
            }
            self.artwork_model = PixivArtworkCompleteDataModel.parse_obj(_data)

        assert isinstance(self.artwork_model, PixivArtworkCompleteDataModel), 'Query artwork model failed'
        return self.artwork_model

    async def _load_page_resource(
            self,
            *,
            page: int = 0,
            url_type: Literal['original', 'regular', 'small', 'thumb_mini'] = 'regular'
    ) -> bytes:
        """内部方法, 加载作品图片资源

        :param page: 页码
        :param url_type: 类型, original: 原始图片, regular: 默认压缩大图, small: 小图, thumb_mini: 缩略图
        """
        _artwork_model = await self.get_artwork_model()
        if page > _artwork_model.page_count - 1:
            raise ValueError(f'request page({page}) exceeds the page count range({_artwork_model.page_count - 1})')

        _page_url = _artwork_model.all_page.get(page).dict().get(url_type)
        _page_resource = await self.request_resource(url=_page_url)
        return _page_resource

    async def _save_page_resource(
            self,
            *,
            page: int = 0,
            url_type: Literal['original', 'regular', 'small', 'thumb_mini'] = 'regular'
    ) -> TemporaryResource:
        """内部方法, 保存作品资源到本地

        :param page: 页码
        :param url_type: 类型, original: 原始图片, regular: 默认压缩大图, small: 小图, thumb_mini: 缩略图
        :return: 保存路径对象
        """
        _page_file_name = f'{self.pid}_{url_type}_p{page}'
        _page_file = pixiv_resource_config.default_artwork_folder(_page_file_name)

        # 如果已经存在则直接返回本地资源
        if _page_file.is_file:
            return _page_file

        # 没有的话再下载并保存文件
        _content = await self._load_page_resource(page=page, url_type=url_type)
        async with _page_file.async_open('wb') as af:
            await af.write(_content)
        return _page_file

    async def _get_page_resource(
            self,
            *,
            page: int = 0,
            url_type: Literal['original', 'regular', 'small', 'thumb_mini'] = 'regular'
    ) -> bytes:
        """内部方法, 获取作品资源, 优先从本地缓存资源加载

        :param page: 页码
        :param url_type: 类型, original: 原始图片, regular: 默认压缩大图, small: 小图, thumb_mini: 缩略图
        """
        _page_file_path = await self._save_page_resource(page=page, url_type=url_type)
        async with _page_file_path.async_open('rb') as af:
            _page_content = await af.read()
        return _page_content

    async def get_page_file(
            self,
            *,
            page: int = 0,
            url_type: Literal['original', 'regular', 'small', 'thumb_mini'] = 'regular'
    ) -> TemporaryResource:
        """获取作品文件资源对象, 使用本地缓存"""
        return await self._save_page_resource(page=page, url_type=url_type)

    async def get_page_bytes(
            self,
            *,
            page: int = 0,
            url_type: Literal['original', 'regular', 'small', 'thumb_mini'] = 'regular'
    ) -> bytes:
        """获取作品文件 bytes, 使用本地缓存

        :param page: 页码
        :param url_type: 类型, original: 原始图片, regular: 默认压缩大图, small: 小图, thumb_mini: 缩略图
        """
        return await self._get_page_resource(page=page, url_type=url_type)

    async def get_all_page_file(
            self,
            *,
            page_limit: int | None = 8,
            url_type: Literal['original', 'regular', 'small', 'thumb_mini'] = 'regular'
    ) -> list[TemporaryResource]:
        """获取作品所有页文件资源列表, 使用本地缓存

        :param page_limit: 返回作品图片最大数量限制, 从第一张图开始计算, 避免漫画作品等单作品图片数量过多出现问题, 0 或 None 为无限制
        :param url_type: 类型, original: 原始图片, regular: 默认压缩大图, small: 小图, thumb_mini: 缩略图
        """
        artwork_model = await self.get_artwork_model()

        # 创建获取作品页资源文件的 Task
        if page_limit <= 0 or page_limit is None:
            tasks = [self.get_page_file(page=page, url_type=url_type) for page in range(artwork_model.page_count)]
        else:
            tasks = [self.get_page_file(page=page, url_type=url_type) for page in range(artwork_model.page_count)
                     if page < page_limit]

        all_page_file = await semaphore_gather(tasks=tasks, semaphore_num=10)
        if any([isinstance(x, BaseException) for x in all_page_file]):
            raise PixivApiError(f'Query artwork(pid={self.pid}) all page files failed')
        return list(all_page_file)

    async def download_page(self, page: int = 0) -> TemporaryResource:
        """下载作品原图到本地

        :param page: 页码
        """
        artwork_model = await self.get_artwork_model()
        if page > artwork_model.page_count - 1:
            raise ValueError(f'request page({page}) exceeds the page count range({artwork_model.page_count - 1})')
        page_file_url = artwork_model.all_page.get(page).dict().get('original')
        return await self.download_resource(url=page_file_url)

    async def download_all_page(self) -> list[TemporaryResource]:
        """下载作品全部原图到本地"""
        artwork_model = await self.get_artwork_model()
        tasks = [self.download_page(page=page) for page in range(artwork_model.page_count)]
        all_page_file = await semaphore_gather(tasks=tasks, semaphore_num=10)
        if any([isinstance(x, BaseException) for x in all_page_file]):
            raise PixivApiError(f'Download artwork(pid={self.pid}) all pages failed')
        return list(all_page_file)

    async def download_ugoira(self, *, original: bool = True) -> TemporaryResource:
        """下载动图资源

        :param original: 是否下载原图
        """
        artwork_model = await self.get_artwork_model()
        if artwork_model.illust_type != 2:
            raise ValueError(f'Artwork {self.pid} is not ugoira')
        if original:
            ugoira_url = artwork_model.ugoira_meta.originalSrc
        else:
            ugoira_url = artwork_model.ugoira_meta.src
        return await self.download_resource(url=ugoira_url)

    async def generate_ugoira_gif(self, *, original: bool = False) -> TemporaryResource:
        """下载动图资源并生成 gif (非常吃 CPU 性能)

        :param original: 是否下载原图
        """

        def _generate_frames_sequence(
                ugoira_path: TemporaryResource,
                data_model: PixivArtworkCompleteDataModel
        ) -> bytes:
            """构造动图生成的帧序列"""
            _frames_list = []
            _sum_delay = []
            # 读取动图资源文件内容
            with zipfile.ZipFile(ugoira_path.resolve_path, 'r') as _zf:
                for frame in data_model.ugoira_meta.frames:
                    with _zf.open(frame.file, 'r') as _ff:
                        with BytesIO(_ff.read()) as _fbf:
                            _frames_list.append(imageio.v2.imread(_fbf))
                    _sum_delay.append(frame.delay)
            # 均值化处理动图帧时间
            _avg_delay = sum(_sum_delay) / len(_sum_delay)
            _avg_duration = _avg_delay / 1000
            # 生成 gif
            with BytesIO() as _bf:
                imageio.mimsave(_bf, _frames_list, format='GIF-PIL', duration=_avg_duration, quantizer=2)
                _content = _bf.getvalue()
            return _content

        # 读取并解析动图帧信息, 生成 gif 文件
        artwork_model = await self.get_artwork_model()
        ugoira_file = await self.download_ugoira(original=original)
        ugoira_content = await run_sync(_generate_frames_sequence)(ugoira_path=ugoira_file, data_model=artwork_model)
        # 写入文件
        gif_file_name = f'{self.pid}_ugoira_{"original" if original else "small"}.gif'
        gif_file = pixiv_resource_config.default_ugoira_gif_folder(gif_file_name)
        async with gif_file.async_open('wb') as af:
            await af.write(ugoira_content)
        return gif_file

    async def format_desc_msg(self, desc_len: int = 64) -> str:
        """获取格式化作品描述文本

        :param desc_len: 描述文本长度限制
        """
        artwork_model = await self.get_artwork_model()

        tag_t = f'#{"  #".join(artwork_model.tags)}'
        if not artwork_model.description:
            desc_t = f'「{artwork_model.title}」/「{artwork_model.uname}」\n{tag_t}\n{artwork_model.url}'
        else:
            desc_t = (
                f'「{artwork_model.title}」/「{artwork_model.uname}」\n{tag_t}\n{artwork_model.url}\n{"-"*16}\n'
                f'{artwork_model.description[:desc_len]}'
                f'{"."*6 if len(artwork_model.description) > desc_len else ""}'
            )
        return desc_t

    async def query_recommend(self, *, init_limit: int = 18, lang: Literal['zh'] = 'zh') -> PixivArtworkRecommendModel:
        """获取本作品对应的相关作品推荐

        :param init_limit: 初始化作品推荐时首次加载的作品数量, 默认 18, 最大 180
        :param lang: 语言
        """
        params = {'limit': init_limit, 'lang': lang}
        recommend_data = await self.request_json(url=self.recommend_url, params=params)

        # 清理返回数据中的 isAdContainer 字段
        illusts = [illust for illust in recommend_data.get('body', {}).get('illusts', [])
                   if not illust.get('isAdContainer')]
        next_ids = recommend_data.get('nextIds', [])
        return PixivArtworkRecommendModel(illusts=illusts, nextIds=next_ids)

    async def query_recommend_with_preview(
            self,
            *,
            init_limit: int = 18,
            lang: Literal['zh'] = 'zh'
    ) -> TemporaryResource:
        """获取本作品对应的相关作品推荐并生成预览图

        :param init_limit: 初始化作品推荐时首次加载的作品数量, 默认 18, 最大 180
        :param lang: 语言
        """
        recommend_result = await self.query_recommend(init_limit=init_limit, lang=lang)
        # 获取缩略图内容
        name = 'Pixiv Artwork Recommend'
        preview_request = await _emit_preview_model_from_artwork_pids(preview_name=name,
                                                                      pids=[x.id for x in recommend_result.illusts])
        preview_img_file = await generate_artworks_preview_image(
            preview=preview_request, preview_size=(512, 512), hold_ratio=True, num_of_line=3)
        return preview_img_file


class PixivUser(Pixiv):
    """Pixiv 用户"""
    _user_root: str = 'https://www.pixiv.net/users/'
    _user_data_url: str = 'https://www.pixiv.net/ajax/user/'
    _user_search_url: str = 'https://www.pixiv.net/search_user.php'

    def __init__(self, uid: int):
        self.uid = uid
        self.user_url = f'{self._user_root}{uid}'
        self.data_url = f'{self._user_data_url}{uid}'
        self.profile_url = f'{self._user_data_url}{uid}/profile/all'

        # 实例缓存
        self.user_model: Optional[PixivUserModel] = None

    def __repr__(self):
        return f'<{self.__class__.__name__}(uid={self.uid})>'

    @classmethod
    async def search_user(cls, nick: str) -> PixivUserSearchingModel:
        """搜索用户"""
        params = {'s_mode': 's_usr', 'nick': nick}
        searching_data = await cls.request_resource(url=cls._user_search_url, params=params)

        # p站唯独画师搜索没有做前后端分离 只能解析页面了
        searching_result = await run_sync(parse_user_searching_result_page)(content=searching_data)
        return searching_result

    @classmethod
    async def search_user_with_preview(cls, nick: str) -> TemporaryResource:
        """搜索用户并生成预览图"""
        searching_model = await cls.search_user(nick=nick)
        preview_img_file = await generate_user_searching_result_image(searching=searching_model)
        return preview_img_file

    async def _query_user_data(self) -> PixivUserDataModel:
        """获取用户基本信息"""
        params = {'lang': 'zh'}

        user_data = await self.request_json(url=self.data_url, params=params)
        return PixivUserDataModel.parse_obj(user_data)

    async def _query_user_artwork_data(self) -> PixivUserArtworkDataModel:
        """获取用户作品信息"""
        params = {'lang': 'zh'}

        user_artwork_data = await self.request_json(url=self.profile_url, params=params)
        return PixivUserArtworkDataModel.parse_obj(user_artwork_data)

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
            self.user_model = PixivUserModel.parse_obj(_data)

        assert isinstance(self.user_model, PixivUserModel), 'Query user model failed'
        return self.user_model

    async def query_user_artworks_with_preview(self, num_limit: int = 120) -> TemporaryResource:
        """获取用户作品并生成预览图"""
        user_data_result = await self.query_user_data()
        # 获取缩略图内容
        name = f'Pixiv User Artwork  - {user_data_result.name}'
        preview_request = await _emit_preview_model_from_artwork_pids(preview_name=name,
                                                                      pids=user_data_result.manga_illusts[:num_limit])
        preview_img_file = await generate_artworks_preview_image(
            preview=preview_request, preview_size=(360, 360), hold_ratio=True, num_of_line=6)
        return preview_img_file


async def _request_artwork_preview_body(pid: int, *, blur_r18: bool = True) -> PreviewImageThumbs:
    """生成多个作品的预览图, 获取生成预览图中每个作品的缩略图的数据

    :param pid: 作品 PID
    :param blur_r18: 是否模糊处理 r18 作品
    """

    def _handle_r18_blur(image: bytes) -> bytes:
        """模糊处理 r18 图"""
        return ImageUtils.init_from_bytes(image=image).gaussian_blur().get_bytes()

    _artwork = PixivArtwork(pid=pid)
    _artwork_model = await _artwork.get_artwork_model()
    _artwork_thumb = await _artwork.get_page_bytes(url_type='small')

    if blur_r18 and _artwork_model.is_r18:
        _artwork_thumb = await run_sync(_handle_r18_blur)(image=_artwork_thumb)

    desc_text = format_artwork_preview_desc(
        pid=_artwork_model.pid, title=_artwork_model.title, uname=_artwork_model.uname)
    return PreviewImageThumbs(desc_text=desc_text, preview_thumb=_artwork_thumb)


async def _emit_preview_model_from_artwork_pids(preview_name: str, pids: list[int]) -> PreviewImageModel:
    """从作品信息中获取生成预览图所需要的数据模型"""
    _tasks = [_request_artwork_preview_body(pid=pid) for pid in pids]
    _requests_data = await semaphore_gather(tasks=_tasks, semaphore_num=30, filter_exception=True)
    _requests_data = list(_requests_data)
    count = len(_requests_data)
    return PreviewImageModel(preview_name=preview_name, count=count, previews=_requests_data)


__all__ = [
    'PixivArtwork',
    'PixivUser'
]
