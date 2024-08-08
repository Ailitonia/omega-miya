"""
@Author         : Ailitonia
@Date           : 2024/8/5 16:14:50
@FileName       : pixiv.py
@Project        : omega-miya
@Description    : Pixiv 图库统一接口实现
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime
from io import BytesIO
from typing import TYPE_CHECKING, Literal

from PIL import Image, ImageDraw, ImageFont
from nonebot.utils import run_sync

from src.utils.image_utils import ImageUtils
from src.utils.image_utils.template import generate_thumbs_preview_image, PreviewImageThumbs, PreviewImageModel
from src.utils.pixiv_api import PixivArtwork, PixivUser, Pixivision
from src.utils.pixiv_api.api_base import BasePixivAPI
from src.utils.pixiv_api.model.artwork import PixivArtworkPreviewRequestModel
from src.utils.pixiv_api.model.pixivision import PixivisionArticle, PixivisionIllustrationList
from src.utils.pixiv_api.model.ranking import PixivRankingModel
from src.utils.pixiv_api.model.searching import PixivSearchingResultModel
from src.utils.pixiv_api.model.user import PixivUserSearchingBody, PixivUserSearchingModel
from src.utils.process_utils import semaphore_gather
from ..add_ons import ImageOpsMixin
from ..internal import BaseArtworkProxy
from ..models import ArtworkData

if TYPE_CHECKING:
    from src.resource import StaticResource, TemporaryResource


class PixivArtworkProxy(BaseArtworkProxy, ImageOpsMixin):
    """Pixiv 图库统一接口实现"""

    @classmethod
    def _get_base_origin_name(cls) -> str:
        return 'pixiv'

    @classmethod
    async def _get_resource(cls, url: str, *, timeout: int = 30) -> str | bytes | None:
        return await PixivArtwork.get_resource(url=url, timeout=timeout)

    async def _query(self) -> ArtworkData:
        artwork_data = await PixivArtwork(pid=self.i_aid).query_artwork()

        """Pixiv 主站作品默认分类分级
        (classification, rating)
                    is_ai     not_ai
        is_r18     (1,  3)    (0,  3)
        not_r18    (1, -1)    (0, -1)
        """

        return ArtworkData.model_validate({
            'origin': self._get_base_origin_name(),
            'aid': artwork_data.pid,
            'title': artwork_data.title,
            'uid': artwork_data.uid,
            'uname': artwork_data.uname,
            'classification': 1 if artwork_data.is_ai else 0,
            'rating': 3 if artwork_data.is_r18 else -1,
            'width': artwork_data.width,
            'height': artwork_data.height,
            'tags': artwork_data.tags,
            'description': artwork_data.description,
            'source': artwork_data.url,
            'pages': [
                {
                    'preview_file': {
                        'url': page.small,
                        'file_ext': self.parse_url_file_suffix(page.small),
                        'width': None,
                        'height': None,
                    },
                    'regular_file': {
                        'url': page.regular,
                        'file_ext': self.parse_url_file_suffix(page.regular),
                        'width': None,
                        'height': None,
                    },
                    'original_file': {
                        'url': page.original,
                        'file_ext': self.parse_url_file_suffix(page.original),
                        'width': artwork_data.width,
                        'height': artwork_data.height,
                    }
                }
                for _, page in artwork_data.all_page.items()
            ]
        })

    async def get_std_desc(self, *, desc_len_limit: int = 128) -> str:
        artwork_data = await self.query()

        tag_t = ' '.join(f'#{x.strip()}' for x in artwork_data.tags)

        if not artwork_data.description:
            desc_t = f'「{artwork_data.title}」/「{artwork_data.uname}」\n{tag_t}\n{artwork_data.source}'
        else:
            desc_t = (
                f'「{artwork_data.title}」/「{artwork_data.uname}」\n{tag_t}\n{artwork_data.source}\n{"-" * 16}\n'
                f'{artwork_data.description[:desc_len_limit]}'
                f'{"." * 6 if len(artwork_data.description) > desc_len_limit else ""}'
            )
        return desc_t.strip()

    """Pixiv 作品相关各类预览图生成"""

    @classmethod
    async def query_search_result_with_preview(
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
    ) -> "TemporaryResource":
        """搜索作品并生成预览图"""
        searching_result = await PixivArtwork.search(
            word=word, mode=mode, page=page, order=order, mode_=mode_, s_mode_=s_mode_,
            type_=type_, ai_type=ai_type, ratio_=ratio_, scd_=scd_, ecd_=ecd_, blt_=blt_, bgt_=bgt_, lang_=lang_
        )
        name = f'Searching - {word}'
        path_config = cls._generate_path_config()

        preview_request = await PixivPreviewGenerator.emit_preview_model_from_searching_model(
            searching_name=name, model=searching_result
        )
        preview_img_file = await PixivPreviewGenerator.generate_artworks_preview_image(
            preview=preview_request, output_folder=path_config.preview_path, preview_font_file=path_config.theme_font
        )
        return preview_img_file

    @classmethod
    async def query_search_result_by_default_popular_condition_with_preview(cls, word: str) -> "TemporaryResource":
        """搜索作品并生成预览图 (使用通用的好图筛选条件) (近三年的图) (会用到仅限pixiv高级会员可用的部分参数)"""
        searching_result = await PixivArtwork.search_by_default_popular_condition(word=word)
        name = f'Searching - {word}'
        path_config = cls._generate_path_config()

        preview_request = await PixivPreviewGenerator.emit_preview_model_from_searching_model(
            searching_name=name, model=searching_result
        )
        preview_img_file = await PixivPreviewGenerator.generate_artworks_preview_image(
            preview=preview_request, output_folder=path_config.preview_path, preview_font_file=path_config.theme_font
        )
        return preview_img_file

    @classmethod
    async def query_daily_illust_ranking_with_preview(cls, page: int = 1) -> "TemporaryResource":
        ranking_result = await PixivArtwork.query_ranking(mode='daily', page=page, content='illust')
        name = f'Pixiv Daily Ranking {datetime.now().strftime("%Y-%m-%d")}'
        path_config = cls._generate_path_config()

        preview_request = await PixivPreviewGenerator.emit_preview_model_from_ranking_model(
            ranking_name=name, model=ranking_result
        )
        preview_img_file = await PixivPreviewGenerator.generate_artworks_preview_image(
            preview=preview_request, output_folder=path_config.preview_path,
            preview_font_file=path_config.theme_font, preview_size=(512, 512), hold_ratio=True, num_of_line=6
        )
        return preview_img_file

    @classmethod
    async def query_weekly_illust_ranking_with_preview(cls, page: int = 1) -> "TemporaryResource":
        ranking_result = await PixivArtwork.query_ranking(mode='weekly', page=page, content='illust')
        name = f'Pixiv Weekly Ranking {datetime.now().strftime("%Y-%m-%d")}'
        path_config = cls._generate_path_config()

        preview_request = await PixivPreviewGenerator.emit_preview_model_from_ranking_model(
            ranking_name=name, model=ranking_result
        )
        preview_img_file = await PixivPreviewGenerator.generate_artworks_preview_image(
            preview=preview_request, output_folder=path_config.preview_path,
            preview_font_file=path_config.theme_font, preview_size=(512, 512), hold_ratio=True, num_of_line=6
        )
        return preview_img_file

    @classmethod
    async def query_monthly_illust_ranking_with_preview(cls, page: int = 1) -> "TemporaryResource":
        ranking_result = await PixivArtwork.query_ranking(mode='monthly', page=page, content='illust')
        name = f'Pixiv Monthly Ranking {datetime.now().strftime("%Y-%m-%d")}'
        path_config = cls._generate_path_config()

        preview_request = await PixivPreviewGenerator.emit_preview_model_from_ranking_model(
            ranking_name=name, model=ranking_result
        )
        preview_img_file = await PixivPreviewGenerator.generate_artworks_preview_image(
            preview=preview_request, output_folder=path_config.preview_path,
            preview_font_file=path_config.theme_font, preview_size=(512, 512), hold_ratio=True, num_of_line=6
        )
        return preview_img_file

    @classmethod
    async def query_discovery_artworks_with_preview(cls) -> "TemporaryResource":
        """获取发现页内容并生成预览图"""
        discovery_result = await PixivArtwork.query_discovery_artworks(limit=60)
        name = 'Pixiv Discovery'
        path_config = cls._generate_path_config()

        preview_request = await PixivPreviewGenerator.emit_preview_model_from_artworks(
            preview_name=name, artworks=[PixivArtworkProxy(pid) for pid in discovery_result.recommend_pids]
        )
        preview_img_file = await PixivPreviewGenerator.generate_artworks_preview_image(
            preview=preview_request, output_folder=path_config.preview_path,
            preview_font_file=path_config.theme_font, preview_size=(360, 360), hold_ratio=True, num_of_line=6
        )
        return preview_img_file

    @classmethod
    async def query_top_artworks_with_preview(cls) -> "TemporaryResource":
        """获取首页推荐内容并生成预览图"""
        recommend_result = await PixivArtwork.query_top_illust()
        name = 'Pixiv Top Recommend'
        path_config = cls._generate_path_config()

        preview_request = await PixivPreviewGenerator.emit_preview_model_from_artworks(
            preview_name=name, artworks=[PixivArtworkProxy(pid) for pid in recommend_result.recommend_pids]
        )
        preview_img_file = await PixivPreviewGenerator.generate_artworks_preview_image(
            preview=preview_request, output_folder=path_config.preview_path,
            preview_font_file=path_config.theme_font, preview_size=(512, 512), hold_ratio=True, num_of_line=3
        )
        return preview_img_file

    async def query_recommend_with_preview(
            self,
            *,
            init_limit: int = 18,
            lang: Literal['zh'] = 'zh'
    ) -> "TemporaryResource":
        """获取本作品对应的相关作品推荐并生成预览图

        :param init_limit: 初始化作品推荐时首次加载的作品数量, 默认 18, 最大 180
        :param lang: 语言
        """
        recommend_result = await PixivArtwork(pid=self.i_aid).query_recommend(init_limit=init_limit, lang=lang)
        name = 'Pixiv Artwork Recommend'

        preview_request = await PixivPreviewGenerator.emit_preview_model_from_artworks(
            preview_name=name, artworks=[PixivArtworkProxy(x.id) for x in recommend_result.illusts]
        )
        preview_img_file = await PixivPreviewGenerator.generate_artworks_preview_image(
            preview=preview_request,
            output_folder=self._get_path_config().preview_path,
            preview_font_file=self._get_path_config().theme_font,
            preview_size=(512, 512), hold_ratio=True, num_of_line=3
        )
        return preview_img_file

    """Pixiv 用户相关各类预览图生成"""

    @classmethod
    async def query_user_search_result_with_preview(cls, nick: str) -> "TemporaryResource":
        """搜索用户并生成预览图"""
        searching_model = await PixivUser.search_user(nick=nick)
        path_config = cls._generate_path_config()
        preview_img_file = await PixivPreviewGenerator.generate_user_searching_result_image(
            searching=searching_model, save_folder=path_config.preview_path, font_file=path_config.text_font
        )
        return preview_img_file

    @classmethod
    async def query_user_artworks_with_preview(cls, uid: int, page: int = 1) -> "TemporaryResource":
        """获取用户作品并生成预览图, 默认每页 48 张作品"""
        user_data_result = await PixivUser(uid).query_user_data()
        index_start = 48 * (page - 1)
        index_end = 48 * page

        name = f'Pixiv User Artwork  - {user_data_result.name}'
        path_config = cls._generate_path_config()

        preview_request = await PixivPreviewGenerator.emit_preview_model_from_artworks(
            preview_name=name,
            artworks=[PixivArtworkProxy(pid) for pid in user_data_result.manga_illusts[index_start:index_end]]
        )
        preview_img_file = await PixivPreviewGenerator.generate_artworks_preview_image(
            preview=preview_request, output_folder=path_config.preview_path,
            preview_font_file=path_config.theme_font, preview_size=(360, 360), hold_ratio=True, num_of_line=6
        )
        return preview_img_file

    @classmethod
    async def query_user_bookmarks_with_preview(cls, uid: int, page: int = 1) -> "TemporaryResource":
        """获取用户的收藏并生成预览图, 默认每页 48 张作品"""
        user_bookmark_result = await PixivUser(uid).query_user_bookmarks(page=page)
        name = f'Pixiv User Bookmark  - {uid}'
        path_config = cls._generate_path_config()

        preview_request = await PixivPreviewGenerator.emit_preview_model_from_artworks(
            preview_name=name,
            artworks=[PixivArtworkProxy(pid) for pid in user_bookmark_result.illust_ids]
        )
        preview_img_file = await PixivPreviewGenerator.generate_artworks_preview_image(
            preview=preview_request, output_folder=path_config.preview_path,
            preview_font_file=path_config.theme_font, preview_size=(360, 360), hold_ratio=True, num_of_line=6
        )
        return preview_img_file

    """Pixivision 特辑相关各类预览图生成"""

    @classmethod
    async def query_pixivision_illustration_list_with_preview(cls, page: int = 1) -> "TemporaryResource":
        """获取并解析 Pixivision Illustration 导览页面内容并生成预览图"""
        illustration_result = await Pixivision.query_illustration_list(page=page)
        name = f'Pixivision Illustration - Page {page}'
        path_config = cls._generate_path_config()

        preview_request = await PixivPreviewGenerator.emit_preview_model_from_pixivision_illustration_model(
            preview_name=name, model=illustration_result
        )
        preview_img_file = await PixivPreviewGenerator.generate_artworks_preview_image(
            preview=preview_request, output_folder=path_config.preview_path,
            preview_font_file=path_config.theme_font, preview_size=(480, 270), hold_ratio=True, num_of_line=4
        )
        return preview_img_file

    @classmethod
    async def query_pixivision_eyecatch_image(cls, aid: int) -> "TemporaryResource":
        """获取 Pixivision 文章头图"""
        file = cls._generate_path_config().download_path('pixivision', 'eyecatch', f'eyecatch_{aid}.jpg')
        if file.is_file:
            return file

        article_data = await Pixivision(aid=aid).query_article()
        image_content = await Pixivision.get_resource(url=article_data.eyecatch_image)
        async with file.async_open('wb') as af:
            await af.write(image_content)
        return file

    @classmethod
    async def query_pixivision_article_with_preview(cls, aid: int) -> "TemporaryResource":
        """获取并解析 Pixivision 文章页面内容并生成预览图"""
        article_result = await Pixivision(aid=aid).query_article()
        name = f'Pixivision - {article_result.title_without_mark}'
        path_config = cls._generate_path_config()

        preview_request = await PixivPreviewGenerator.emit_preview_model_from_pixivision_article_model(
            preview_name=name, model=article_result
        )
        preview_img_file = await PixivPreviewGenerator.generate_artworks_preview_image(
            preview=preview_request, output_folder=path_config.preview_path,
            preview_font_file=path_config.theme_font, preview_size=(512, 512), hold_ratio=True, num_of_line=4
        )
        return preview_img_file


class PixivPreviewGenerator(BasePixivAPI):
    """Pixiv 预览图生成工具集"""

    @classmethod
    async def _generate_user_searching_result_card(
            cls,
            user: PixivUserSearchingBody,
            *,
            font_file: "StaticResource",
            width: int = 1600,
            card_ratio: float = 6.75,  # 注意这里的图片长宽比会直接影响到排版 不要随便改
    ) -> Image.Image:
        """根据用户搜索结果页面解析内容, 生成单独一个用户的结果 card 图片"""
        # 首先获取用户相关图片资源
        user_head = await cls.get_resource(url=user.user_head_url)
        user_illusts_thumb = await semaphore_gather(
            tasks=[cls.get_resource(url=url) for url in user.illusts_thumb_urls],
            semaphore_num=4
        )

        @run_sync
        def _handle_generate_card() -> Image.Image:
            """用于图像生成处理的内部函数"""
            # 整体图片大小
            _height = int(width / card_ratio)
            # 字体
            _font_main_size = int(_height / 8)
            _font_desc_size = int(_height / 12)
            _font_main = ImageFont.truetype(font_file.resolve_path, _font_main_size)
            _font_desc = ImageFont.truetype(font_file.resolve_path, _font_desc_size)
            # 创建背景图层
            _background = Image.new(mode="RGB", size=(width, _height), color=(255, 255, 255))
            # 头像及预览图大小
            _user_head_w = int(_height * 5 / 6)
            _thumb_img_w = _user_head_w
            # 根据头像计算标准间距
            _spacing_w = int((_height - _user_head_w) / 2)
            # 绘制背景框
            ImageDraw.Draw(_background).rounded_rectangle(
                xy=(
                    int(_spacing_w / 4), int(_spacing_w / 4),
                    int(width - _spacing_w / 4), int(_height - _spacing_w / 4)
                ),
                radius=int(_height / 12),
                fill=(228, 250, 255)
            )
            # 读取头像
            with BytesIO(user_head) as bf:
                _user_head_img: Image.Image = Image.open(bf)
                _user_head_img.load()
            _user_head_img = _user_head_img.resize((_user_head_w, _user_head_w))
            _user_head_img = _user_head_img.convert(mode="RGBA")
            # 新建头像蒙版
            _user_head_mask = Image.new(mode="RGBA", size=(_user_head_w, _user_head_w), color=(255, 255, 255, 0))
            _user_head_mask_draw = ImageDraw.Draw(_user_head_mask)
            _user_head_mask_draw.ellipse((0, 0, _user_head_w, _user_head_w), fill=(0, 0, 0, 255))
            # 处理头像蒙版并粘贴
            _background.paste(im=_user_head_img, box=(_spacing_w * 2, _spacing_w), mask=_user_head_mask)
            # 绘制用户名称
            ImageDraw.Draw(_background).text(
                xy=(_spacing_w * 4 + _user_head_w, int(_spacing_w * 1.5)),
                font=_font_main,
                text=user.user_name,
                fill=(0, 0, 0))
            # 绘制用户 uid
            _name_text_w, _name_text_h = ImageUtils.get_text_size(user.user_name, font=_font_main)
            _uid_text = f'UID：{user.user_id}'
            _uid_text_w, _uid_text_h = ImageUtils.get_text_size(_uid_text, font=_font_desc)
            ImageDraw.Draw(_background).text(
                xy=(_spacing_w * 4 + _user_head_w, _name_text_h + int(_spacing_w * 2)),
                font=_font_desc,
                text=_uid_text,
                fill=(37, 143, 184))
            # 投稿作品数
            _count_text = f'插画投稿数：{user.user_illust_count}'
            _count_text_w, _count_text_h = ImageUtils.get_text_size(_count_text, font=_font_desc)
            ImageDraw.Draw(_background).text(
                xy=(_spacing_w * 4 + _user_head_w, _name_text_h + _uid_text_h + int(_spacing_w * 2.5)),
                font=_font_desc,
                text=_count_text,
                fill=(37, 143, 184))
            # 绘制用户简介
            # 按长度切分文本
            _desc_text = ImageUtils.split_multiline_text(text=user.user_desc, width=int(_height * 1.5), font=_font_desc)
            ImageDraw.Draw(_background).multiline_text(
                xy=(_spacing_w * 4 + _user_head_w,
                    _name_text_h + _uid_text_h + _count_text_h + int(_spacing_w * 3)),
                font=_font_desc,
                text=_desc_text,
                fill=(0, 0, 0))

            # 一般页面只有四张预览图 这里也只贴四张
            for _index, _illusts_thumb in enumerate(user_illusts_thumb[:4]):
                # 检查缩略图加载情况
                if isinstance(_illusts_thumb, Exception):
                    # 获取失败或小说等作品没有预览图
                    _thumb_img = Image.new(mode="RGB", size=(_thumb_img_w, _thumb_img_w), color=(127, 127, 127))
                else:
                    # 正常获取的预览图
                    with BytesIO(_illusts_thumb) as bf:
                        _thumb_img: Image.Image = Image.open(bf)
                        _thumb_img.load()
                    _thumb_img = _thumb_img.resize((_thumb_img_w, _thumb_img_w))
                    _thumb_img = _thumb_img.convert(mode="RGB")
                # 预览图外边框
                ImageDraw.Draw(_background).rectangle(
                    xy=((_spacing_w * 6 + _user_head_w + int(_height * 1.5)  # 前面文字的宽度
                         + _index * (_thumb_img_w + _spacing_w)  # 根据缩略图序列增加的位置宽度
                         - int(_thumb_img_w / 80),  # 边框预留的宽度
                         _spacing_w - int(_thumb_img_w / 80)),  # 高度及边框预留宽度
                        (_spacing_w * 6 + _user_head_w + int(_height * 1.5)
                         + _index * (_thumb_img_w + _spacing_w) + _thumb_img_w
                         + int(_thumb_img_w / 96),
                         _spacing_w + _thumb_img_w + int(_thumb_img_w / 96))),
                    fill=(224, 224, 224),
                    width=0
                )
                # 依次粘贴预览图
                _background.paste(
                    im=_thumb_img,
                    box=(_spacing_w * 6 + _user_head_w + int(_height * 1.5) +  # 前面头像及介绍文本的宽度
                         _index * (_thumb_img_w + _spacing_w),  # 预览图加间隔的宽度
                         _spacing_w)  # 预览图高度
                )
            return _background

        return await _handle_generate_card()

    @classmethod
    async def generate_user_searching_result_image(
            cls,
            searching: PixivUserSearchingModel,
            save_folder: "TemporaryResource",
            *,
            font_file: "StaticResource",
            width: int = 1600,
            card_ratio: float = 6.75,
            searching_card_limit: int = 8,  # 图中绘制的画师搜索结果数量限制
    ) -> "TemporaryResource":
        """根据用户搜索结果页面解析内容, 生成结果预览图片"""
        tasks = [
            cls._generate_user_searching_result_card(user=user, font_file=font_file, width=width)
            for user in searching.users[:searching_card_limit]
        ]
        cards = await semaphore_gather(tasks=tasks, semaphore_num=8, filter_exception=True)

        @run_sync
        def _handle_generate_image() -> bytes:
            """用于图像生成处理的内部函数"""
            _card_height = int(width / card_ratio)
            # 根据卡片计算标准间距
            _spacing_width = int(_card_height / 12)
            # 字体
            _font_title_size = int(_card_height / 6)
            _font_title = ImageFont.truetype(font_file.resolve_path, _font_title_size)
            # 标题
            _title_text = f'Pixiv 用户搜索：{searching.search_name} - 共{searching.count}'
            _title_text_w, _title_text_h = ImageUtils.get_text_size(_title_text, font=_font_title)
            # 整体图片高度
            _height = (_card_height + _spacing_width) * len(cards) + _title_text_h + 3 * _spacing_width
            # 创建背景图层
            _background = Image.new(mode="RGB", size=(width + _spacing_width * 2, _height), color=(255, 255, 255))
            # 绘制标题
            ImageDraw.Draw(_background).text(
                xy=(_spacing_width * 2, _spacing_width),
                font=_font_title,
                text=_title_text,
                fill=(37, 143, 184)
            )
            # 依次粘贴各结果卡片
            for _index, _card in enumerate(cards):
                _background.paste(
                    im=_card,
                    box=(_spacing_width, _spacing_width * 2 + _title_text_h + (_card_height + _spacing_width) * _index)
                )
            # 生成结果图片
            with BytesIO() as _bf:
                _background.save(_bf, 'JPEG')
                _content = _bf.getvalue()
            return _content

        image_content = await _handle_generate_image()
        image_file_name = f"preview_search_user_{searching.search_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        save_file = save_folder(image_file_name)
        async with save_file.async_open('wb') as af:
            await af.write(image_content)

        return save_file

    @classmethod
    async def _request_preview_body(cls, request: PixivArtworkPreviewRequestModel) -> PreviewImageThumbs:
        """获取生成预览图中每个缩略图的数据"""
        _request_data = await cls.get_resource(url=request.request_url)
        return PreviewImageThumbs(desc_text=request.desc_text, preview_thumb=_request_data)

    @classmethod
    async def _request_artwork_preview_body(
            cls,
            artwork: "PixivArtworkProxy",
            *,
            blur_r18: bool = True
    ) -> PreviewImageThumbs:
        """生成多个作品的预览图, 获取生成预览图中每个作品的缩略图的数据

        :param artwork: 作品
        :param blur_r18: 是否模糊处理 r18 作品
        """

        @run_sync
        def _handle_r18_blur(image: bytes) -> bytes:
            """模糊处理 r18 图"""
            return ImageUtils.init_from_bytes(image=image).gaussian_blur().get_bytes()

        _artwork_data = await artwork.query()
        _artwork_thumb = await artwork.get_page_bytes(page_type='preview')

        if blur_r18 and _artwork_data.rating.value >= 3:
            _artwork_thumb = await _handle_r18_blur(image=_artwork_thumb)

        desc_text = cls.format_artwork_preview_desc(
            pid=artwork.i_aid, title=_artwork_data.title, uname=_artwork_data.uname
        )
        return PreviewImageThumbs(desc_text=desc_text, preview_thumb=_artwork_thumb)

    @classmethod
    async def _request_preview_model(
            cls,
            preview_name: str,
            requests: list[PixivArtworkPreviewRequestModel]
    ) -> PreviewImageModel:
        """获取生成预览图所需要的数据模型"""
        _tasks = [cls._request_preview_body(request) for request in requests]
        _requests_data = await semaphore_gather(tasks=_tasks, semaphore_num=30, filter_exception=True)
        _requests_data = list(_requests_data)
        count = len(_requests_data)
        return PreviewImageModel(preview_name=preview_name, count=count, previews=_requests_data)

    @staticmethod
    def format_artwork_preview_desc(pid: int | str, title: str, uname: str, *, num_lmt: int = 13) -> str:
        """格式化预览图的作品描述信息"""
        pid_text = f"Pid: {pid}"
        title_text = f"{title[:num_lmt]}..." if len(title) > num_lmt else title
        author_text = f"Author: {uname}"
        author_text = f"{author_text[:num_lmt]}..." if len(author_text) > num_lmt else author_text
        return f'{pid_text}\n{title_text}\n{author_text}'

    @classmethod
    async def emit_preview_model_from_artworks(
            cls,
            preview_name: str,
            artworks: list["PixivArtworkProxy"]
    ) -> PreviewImageModel:
        """从作品信息中获取生成预览图所需要的数据模型"""
        _tasks = [cls._request_artwork_preview_body(artwork=artwork) for artwork in artworks]
        _requests_data = await semaphore_gather(tasks=_tasks, semaphore_num=30, filter_exception=True)
        _requests_data = list(_requests_data)
        count = len(_requests_data)
        return PreviewImageModel(preview_name=preview_name, count=count, previews=_requests_data)

    @classmethod
    async def emit_preview_model_from_ranking_model(
            cls,
            ranking_name: str,
            model: PixivRankingModel
    ) -> PreviewImageModel:
        """从排行榜结果中获取生成预览图所需要的数据模型"""
        request_list = [
            PixivArtworkPreviewRequestModel(
                desc_text=cls.format_artwork_preview_desc(
                    pid=data.illust_id,
                    title=f'【No.{(model.page - 1) * len(model.contents) + index + 1}】{data.title}',
                    uname=data.user_name
                ),
                request_url=data.url
            )
            for index, data in enumerate(model.contents)
        ]
        preview_model = await cls._request_preview_model(preview_name=ranking_name, requests=request_list)
        return preview_model

    @classmethod
    async def emit_preview_model_from_searching_model(
            cls,
            searching_name: str,
            model: PixivSearchingResultModel
    ) -> PreviewImageModel:
        """从搜索结果中获取生成预览图所需要的数据模型"""
        request_list = [
            PixivArtworkPreviewRequestModel(
                desc_text=cls.format_artwork_preview_desc(pid=data.id, title=data.title, uname=data.userName),
                request_url=data.url
            )
            for data in model.searching_result
        ]
        preview_model = await cls._request_preview_model(preview_name=searching_name, requests=request_list)
        return preview_model

    @classmethod
    async def emit_preview_model_from_pixivision_illustration_model(
            cls,
            preview_name: str,
            model: PixivisionIllustrationList
    ) -> PreviewImageModel:
        """从 pixivision illustration 内容中获取生成预览图所需要的数据模型"""
        request_list = [
            PixivArtworkPreviewRequestModel(
                desc_text=f'ArticleID: {data.aid}\n{data.split_title_without_mark}',
                request_url=data.thumbnail
            )
            for data in model.illustrations
        ]
        preview_model = await cls._request_preview_model(preview_name=preview_name, requests=request_list)
        return preview_model

    @classmethod
    async def emit_preview_model_from_pixivision_article_model(
            cls,
            preview_name: str,
            model: PixivisionArticle
    ) -> PreviewImageModel:
        """从 pixivision article 内容中获取生成预览图所需要的数据模型"""
        request_list = [
            PixivArtworkPreviewRequestModel(
                desc_text=cls.format_artwork_preview_desc(
                    pid=data.artwork_id, title=data.artwork_title, uname=data.artwork_user
                ),
                request_url=data.image_url
            )
            for data in model.artwork_list
        ]
        preview_model = await cls._request_preview_model(preview_name=preview_name, requests=request_list)
        return preview_model

    @staticmethod
    async def generate_artworks_preview_image(
            preview: PreviewImageModel,
            output_folder: "TemporaryResource",
            *,
            preview_font_file: "StaticResource",
            preview_size: tuple[int, int] = (250, 250),  # 默认预览图缩略图大小
            hold_ratio: bool = False,
            edge_scale: float = 1 / 32,
            num_of_line: int = 6,
            limit: int = 1000
    ) -> "TemporaryResource":
        """生成多个作品的预览图

        :param output_folder: 预览图输出路径
        :param preview_font_file: 绘制预览图中使用的字体
        :param preview: 经过预处理的生成预览的数据
        :param preview_size: 单个小缩略图的尺寸
        :param hold_ratio: 是否保持缩略图原图比例
        :param edge_scale: 缩略图添加白边的比例, 范围 0~1
        :param num_of_line: 生成预览每一行的预览图数
        :param limit: 限制生成时加载 preview 中图片的最大值
        """
        return await generate_thumbs_preview_image(
            preview=preview,
            preview_size=preview_size,
            font_path=preview_font_file,
            header_color=(0, 150, 250),
            hold_ratio=hold_ratio,
            edge_scale=edge_scale,
            num_of_line=num_of_line,
            limit=limit,
            output_folder=output_folder
        )


__all__ = [
    'PixivArtworkProxy'
]
