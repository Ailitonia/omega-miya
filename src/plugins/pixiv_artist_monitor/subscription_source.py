"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : subscription_source.py
@Project        : nonebot2_miya
@Description    : 作品图片预处理及插件流程控制工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from asyncio import sleep as async_sleep
from collections.abc import Callable, Coroutine, Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal, Self

from nonebot.log import logger

from src.database.internal.subscription_source import SubscriptionSource, SubscriptionSourceType
from src.service import OmegaMessage, OmegaMessageSegment
from src.service.artwork_collection import PixivArtworkCollection
from src.service.artwork_proxy import PixivArtworkProxy
from src.service.omega_message_context.custom_depends import ARTWORK_CONTEXT_MANAGER
from src.service.omega_subscription_service import BaseSubscriptionManager
from src.utils import semaphore_gather
from src.utils.pixiv_api import PixivUser

if TYPE_CHECKING:
    from src.database.internal.social_media_content import SocialMediaContent
    from src.resource import TemporaryResource
    from src.service.omega_base.middlewares.models import SentMessageResponse
    from src.utils.pixiv_api.model.ranking import PixivRankingModel

    type SMC_T = str


class PixivUserSubscriptionManager(BaseSubscriptionManager['SMC_T']):
    """Pixiv 用户订阅服务管理"""

    _LIMIT_SMC_PROCESSING_NUMBER = 8

    def __init__(self, uid: str | int) -> None:
        if isinstance(uid, str) and not uid.isdigit():
            raise ValueError('uid must be a number')
        self.sub_id = str(uid)

    @property
    def uid(self) -> int:
        return int(self.sub_id)

    @classmethod
    def init_from_sub_id(cls, sub_id: str | int) -> Self:
        return cls(uid=sub_id)

    @classmethod
    def get_sub_type(cls) -> str:
        return SubscriptionSourceType.pixiv_user.value

    @staticmethod
    def _get_smc_item_mid(smc_item: 'SMC_T') -> str:
        return smc_item

    @classmethod
    def _parse_smc_item(cls, smc_item: 'SMC_T') -> 'SocialMediaContent':
        raise NotImplementedError

    @classmethod
    async def _check_new_smc_item(cls, smc_items: 'Sequence[SMC_T]') -> 'list[SMC_T]':
        return await PixivArtworkCollection.query_not_exists_aids(aids=smc_items)

    async def _query_sub_source_smc_items(self) -> 'list[SMC_T]':
        user_data = await PixivUser(uid=self.uid).query_user_data()
        return [str(pid) for pid in user_data.manga_illusts]

    @classmethod
    async def _add_upgrade_smc_item(cls, smc_item: 'SMC_T') -> None:
        return await PixivArtworkCollection(smc_item).add_artwork_into_database_ignore_exists()

    async def _add_sub_source_new_smc_content(self) -> None:
        new_smc_items = await self._query_sub_source_new_smc_items()

        # 应对 pixiv 流控, 对获取作品信息进行分段处理
        handle_pids = new_smc_items[:20]
        remain_pids = new_smc_items[20:]
        while handle_pids:

            tasks = [self._add_upgrade_smc_item(smc_item=smc_item) for smc_item in handle_pids]
            await semaphore_gather(
                tasks=tasks,
                semaphore_num=self._LIMIT_SMC_PROCESSING_NUMBER,
                return_exceptions=False,
            )

            handle_pids.clear()
            handle_pids = remain_pids[:20]
            remain_pids = remain_pids[20:]

            if remain_pids:
                logger.debug(f'{self} | Adding user({self.uid}) artworks, {len(remain_pids)} remaining')
                await async_sleep(int((len(remain_pids) if len(remain_pids) < 20 else 20) * 1.5))

        logger.info(f'{self} | Adding user({self.uid}) artworks completed')

    async def query_sub_source_data(self) -> 'SubscriptionSource':
        user_data = await PixivUser(uid=self.uid).query_user_data()
        return SubscriptionSource.model_validate({
            'id': -1,
            'sub_type': self.get_sub_type(),
            'sub_id': self.sub_id,
            'sub_user_name': user_data.name,
            'sub_info': 'Pixiv用户订阅',
        })

    @classmethod
    async def format_pixiv_artwork_message(
            cls,
            pid: str,
            *,
            message_prefix: str | None = None,
            show_page_limiting: int = 10,
    ) -> OmegaMessage:
        """预处理用户作品预览消息"""
        artwork_ap = PixivArtworkCollection(artwork_id=pid).artwork_proxy

        artwork_data = await artwork_ap.query()
        artwork_desc = await artwork_ap.get_std_desc()

        # 处理作品预览
        process_mode: Literal['mark', 'blur'] = 'mark' if artwork_data.rating <= 1 else 'blur'
        show_page_num = min(len(artwork_data.pages), show_page_limiting)
        if len(artwork_data.pages) > show_page_num:
            artwork_desc = f'({show_page_limiting} of {len(artwork_data.pages)} pages)\n{"-" * 16}\n{artwork_desc}'

        tasks = [
            artwork_ap.get_custom_proceed_page_file(page_index=page_index, process_mode=process_mode)
            for page_index in range(show_page_num)
        ]
        proceed_pages = await semaphore_gather(tasks=tasks, semaphore_num=10, return_exceptions=False)

        pages_url_tasks = [
            x.get_hosting_path()
            for x in proceed_pages
        ]
        pages_hosting_urls = await semaphore_gather(tasks=pages_url_tasks, semaphore_num=10, return_exceptions=False)

        # 拼接待发送消息
        send_msg = OmegaMessage(OmegaMessageSegment.image(url) for url in pages_hosting_urls)
        if message_prefix is not None:
            send_msg = message_prefix + send_msg + f'\n{artwork_desc}'
        else:
            send_msg = send_msg + f'\n{artwork_desc}'
        return send_msg

    @classmethod
    async def _format_smc_item_message(cls, smc_item: 'SMC_T') -> str | OmegaMessage:
        return await cls.format_pixiv_artwork_message(pid=smc_item, message_prefix='【Pixiv】新作品发布!\n')

    async def _entity_message_send_postprocessor(self, response: 'SentMessageResponse', smc_item: 'SMC_T') -> None:
        artwork_data = await PixivArtworkProxy(artwork_id=smc_item).query(use_cache=True)
        await ARTWORK_CONTEXT_MANAGER.set_message_context(response=response, **artwork_data.model_dump())

    """作品预览图生成工具"""

    @classmethod
    async def generate_artworks_preview(
            cls,
            title: str,
            pids: Sequence[int],
            *,
            no_blur_rating: int = 1,
    ) -> 'TemporaryResource':
        """生成多个作品的预览图"""
        return await PixivArtworkProxy.generate_artworks_preview(
            preview_name=title,
            artworks=[PixivArtworkProxy(pid) for pid in pids],
            no_blur_rating=no_blur_rating,
            preview_size=(360, 360),
            num_of_line=6,
        )

    @classmethod
    async def _generate_ranking_preview(
            cls,
            title: str,
            ranking_data: 'PixivRankingModel',
    ) -> 'TemporaryResource':
        """根据榜单数据生成预览图"""
        return await PixivArtworkProxy.generate_artworks_preview(
            preview_name=title,
            artworks=[PixivArtworkProxy(x.illust_id) for x in ranking_data.contents],
            preview_size=(512, 512),
            num_of_line=6,
        )

    @classmethod
    def get_ranking_preview_factory(
            cls,
            mode: Literal['daily', 'weekly', 'monthly'],
    ) -> Callable[[int], Coroutine[Any, Any, 'TemporaryResource']]:
        """获取榜单预览图生成器"""

        async def _factor(page: int) -> 'TemporaryResource':
            ranking_data = await PixivUser.query_ranking(mode=mode, page=page, content='illust')

            title = f'Pixiv {mode.title()} Ranking {datetime.now().strftime("%Y-%m-%d")}'
            return await cls._generate_ranking_preview(title=title, ranking_data=ranking_data)

        return _factor


__all__ = [
    'PixivUserSubscriptionManager',
]
