"""
@Author         : Ailitonia
@Date           : 2022/04/30 18:11
@FileName       : subscription_source.py
@Project        : nonebot2_miya
@Description    : Pixivision 特辑作品图片预处理及插件工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import TYPE_CHECKING, Self

from nonebot import logger

from src.database import SocialMediaContentDAL, begin_db_session
from src.database.internal.subscription_source import SubscriptionSource, SubscriptionSourceType
from src.resource import TemporaryResource
from src.service import OmegaMessage, OmegaMessageSegment
from src.service.artwork_collection import PixivArtworkCollection
from src.service.artwork_proxy import PixivArtworkProxy
from src.service.omega_subscription_service import BaseSubscriptionManager
from src.utils import semaphore_gather
from src.utils.pixiv_api import Pixivision

if TYPE_CHECKING:
    from src.database.internal.social_media_content import SocialMediaContent
    from src.utils.pixiv_api.model.pixivision import PixivisionArticle, PixivisionIllustration

    type SMC_T = PixivisionIllustration


class PixivisionSubscriptionManager(BaseSubscriptionManager['SMC_T']):
    """Pixivision 订阅服务管理"""

    _LIMIT_SMC_PROCESSING_NUMBER = 2
    _LIMIT_SMC_ARTWORK_PROCESSING_NUMBER = 4

    def __init__(self) -> None:
        self.sub_id = 'pixivision'

    @classmethod
    def init_from_sub_id(cls, sub_id: str | int = '') -> Self:
        return cls()

    @classmethod
    def get_sub_type(cls) -> str:
        return SubscriptionSourceType.pixivision.value

    @classmethod
    def _get_tmp_folder(cls) -> 'TemporaryResource':
        """图片缓存文件夹"""
        return TemporaryResource(cls.get_sub_type())

    @staticmethod
    def _get_smc_item_mid(smc_item: 'SMC_T') -> str:
        return str(smc_item.aid)

    @classmethod
    def _parse_smc_item(cls, smc_item: 'SMC_T') -> 'SocialMediaContent':
        raise NotImplementedError

    async def _query_sub_source_smc_items(self) -> 'list[SMC_T]':
        articles_data = await Pixivision.query_illustration_list()
        return articles_data.illustrations[:8]

    @classmethod
    async def _add_pixivision_article_artworks_into_database(cls, article_data: 'PixivisionArticle') -> None:
        """向数据库中写入 Pixivision 特辑文章中的作品"""
        add_artwork_tasks = [
            PixivArtworkCollection(x.artwork_id).add_artwork_into_database_ignore_exists()
            for x in article_data.artwork_list
        ]
        await semaphore_gather(
            tasks=add_artwork_tasks,
            semaphore_num=cls._LIMIT_SMC_ARTWORK_PROCESSING_NUMBER,
            return_exceptions=False,
        )

    @classmethod
    async def _add_upgrade_smc_item(cls, smc_item: 'SMC_T') -> None:
        article = Pixivision(aid=smc_item.aid)
        article_data = await article.query_article()

        # 先写入特辑文章中的作品信息
        await cls._add_pixivision_article_artworks_into_database(article_data=article_data)

        # 写入特辑文章信息
        async with begin_db_session() as session:
            await SocialMediaContentDAL(session=session).upsert(
                source=cls.get_sub_type(),
                m_id=str(article.aid),
                m_type='pixivision_article',
                m_uid='-1',
                title=article_data.title_without_mark,
                content=f'{article_data.description}\n{",".join(x.tag_name for x in article_data.tags_list)}',
                ref_content=','.join(str(x.artwork_id) for x in article_data.artwork_list),
            )

    async def query_sub_source_data(self) -> 'SubscriptionSource':
        return SubscriptionSource.model_validate({
            'id': -1,
            'sub_type': self.get_sub_type(),
            'sub_id': self.sub_id,
            'sub_user_name': 'pixivision',
            'sub_info': 'Pixivision特辑订阅',
        })

    @classmethod
    async def format_pixivision_article_message(cls, aid: int) -> str | OmegaMessage:
        """处理 Pixivision 特辑更新为消息"""
        article = Pixivision(aid=aid)
        article_data = await article.query_article()
        send_message = f'《{article_data.title}》\n'
        try:
            if article_data.eyecatch_image is None:
                raise ValueError('article eyecatch image not found')

            eyecatch_image = await article.download_resource(
                url=article_data.eyecatch_image,
                save_folder=cls._get_tmp_folder()('eyecatch'),
                custom_file_name=f'eyecatch_{article.aid}.jpg'
            )
            send_message += OmegaMessageSegment.image(await eyecatch_image.get_hosting_path())
        except Exception as e:
            logger.warning(f'PixivisionArticleMonitor | Query {article} eye-catch image failed, {e!r}')

        send_message += f'\n{article_data.description}\n'

        try:
            title = f'Pixivision - {article_data.title_without_mark}'
            preview_image = await cls._generate_pixivision_article_preview(title=title, article_data=article_data)
            send_message += OmegaMessageSegment.image(await preview_image.get_hosting_path())
        except Exception as e:
            logger.warning(f'PixivisionArticleMonitor | Query {article} preview image failed, {e!r}')

        send_message += f'\n传送门: {article.url}'
        return send_message

    @classmethod
    async def _format_smc_item_message(cls, smc_item: 'SMC_T') -> str | OmegaMessage:
        return await cls.format_pixivision_article_message(aid=smc_item.aid)

    @staticmethod
    async def _generate_pixivision_article_preview(
            title: str,
            article_data: 'PixivisionArticle',
    ) -> 'TemporaryResource':
        """根据 Pixivision 特辑内容生成预览图"""
        if article_data.illustration_list:
            return await PixivArtworkProxy.generate_any_images_preview(
                preview_name=title,
                image_data=[
                    (x.thumbnail, f'ArticleID: {x.aid}\n{x.split_title_without_mark}')
                    for x in article_data.illustration_list
                ],
                preview_size=(480, 270),
                hold_ratio=True,
                num_of_line=4,
            )
        else:
            return await PixivArtworkProxy.generate_artworks_preview(
                preview_name=title,
                artworks=[PixivArtworkProxy(x.artwork_id) for x in article_data.artwork_list],
                preview_size=(512, 512),
                num_of_line=4,
            )

    @staticmethod
    async def generate_pixivision_illustration_list_preview(page: int = 1) -> 'TemporaryResource':
        """根据 Pixivision Illustration 导览页面内容生成预览图"""
        illustration_result = await Pixivision.query_illustration_list(page=page)
        title = f'Pixivision Illustration - Page {page}'

        return await PixivArtworkProxy.generate_any_images_preview(
            preview_name=title,
            image_data=[
                (x.thumbnail, f'ArticleID: {x.aid}\n{x.split_title_without_mark}')
                for x in illustration_result.illustrations
            ],
            preview_size=(480, 270),
            hold_ratio=True,
            num_of_line=4,
        )


__all__ = [
    'PixivisionSubscriptionManager',
]
