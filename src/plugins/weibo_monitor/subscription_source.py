"""
@Author         : Ailitonia
@Date           : 2025/6/5 22:42
@FileName       : subscription_source.py
@Project        : omega-miya
@Description    : 微博订阅源实现
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import TYPE_CHECKING, Self

from nonebot.log import logger

from src.database.internal.social_media_content import SocialMediaContent
from src.database.internal.subscription_source import SubscriptionSource, SubscriptionSourceType
from src.service import OmegaMessage, OmegaMessageSegment
from src.service.omega_subscription_service import BaseSubscriptionManager
from src.utils import semaphore_gather
from src.utils.weibo_api import Weibo

if TYPE_CHECKING:
    from src.utils.weibo_api.model import WeiboCard

    type SMC_T = WeiboCard


class WeiboUserSubscriptionManager(BaseSubscriptionManager['SMC_T']):
    """微博用户动态订阅服务管理"""

    def __init__(self, uid: str | int) -> None:
        self.sub_id = str(uid)

    @classmethod
    def init_from_sub_id(cls, sub_id: str | int) -> Self:
        return cls(uid=sub_id)

    @classmethod
    def get_sub_type(cls) -> str:
        return SubscriptionSourceType.weibo_user.value

    @staticmethod
    def _get_smc_item_mid(smc_item: 'SMC_T') -> str:
        return str(smc_item.mblog.id)

    @classmethod
    def _parse_smc_item(cls, smc_item: 'SMC_T') -> 'SocialMediaContent':
        retweeted_content = (
            smc_item.mblog.retweeted_status.text
            if smc_item.mblog.is_retweeted and smc_item.mblog.retweeted_status is not None
            else ''
        )
        return SocialMediaContent.model_validate({
            'source': cls.get_sub_type(),
            'm_id': str(smc_item.mblog.id),
            'm_type': smc_item.card_type,
            'm_uid': str(smc_item.mblog.user.id),
            'title': f'{smc_item.mblog.user.screen_name}的微博',
            'content': smc_item.mblog.text,
            'ref_content': retweeted_content,
        })

    async def _query_sub_source_smc_items(self) -> 'list[SMC_T]':
        return await Weibo.query_user_weibo_cards(uid=self.sub_id)

    async def query_sub_source_data(self) -> 'SubscriptionSource':
        user_data = await Weibo.query_user_data(uid=self.sub_id)
        return SubscriptionSource.model_validate({
            'id': -1,
            'sub_type': self.get_sub_type(),
            'sub_id': self.sub_id,
            'sub_user_name': user_data.screen_name,
            'sub_info': '微博用户订阅',
        })

    @classmethod
    async def _format_smc_item_message(cls, smc_item: 'SMC_T') -> str | OmegaMessage:
        send_message = f'【微博】{smc_item.mblog.user.screen_name}'
        img_urls = []

        # 检测转发
        if smc_item.mblog.is_retweeted and smc_item.mblog.retweeted_status is not None:
            retweeted_username = smc_item.mblog.retweeted_status.user.screen_name
            send_message += f'转发了{retweeted_username}的微博!\n'
            # 获取转发微博全文
            try:
                retweeted_content = await Weibo.query_weibo_extend_text(mid=smc_item.mblog.retweeted_status.mid)
            except Exception as e:
                logger.debug(f'WeiboMonitor | Query retweeted origin content failed, '
                             f'maybe deleted, mid: {smc_item.mblog.retweeted_status.mid}, {e}')
                retweeted_content = smc_item.mblog.retweeted_status.text
            text = f'“{smc_item.mblog.text}”\n{"=" * 16}\n@{retweeted_username}:\n“{retweeted_content}”\n'
            if smc_item.mblog.retweeted_status.pics is not None:
                img_urls.extend(x.large.url for x in smc_item.mblog.retweeted_status.pics)
            if smc_item.mblog.retweeted_status.page_info is not None:
                img_urls.append(smc_item.mblog.retweeted_status.page_info.pic_url)
        else:
            send_message += '发布了新微博!\n'
            text = f'“{smc_item.mblog.text}”\n'
            if smc_item.mblog.pics is not None:
                img_urls.extend(x.large.url for x in smc_item.mblog.pics)
            if smc_item.mblog.page_info is not None:
                img_urls.append(smc_item.mblog.page_info.pic_url)

        # 添加发布来源和内容
        send_message += f'{smc_item.mblog.format_created_at} 来自{smc_item.mblog.source}\n'
        if smc_item.mblog.region_name is not None:
            send_message += f'{smc_item.mblog.region_name}\n\n'
        else:
            send_message += '\n'
        send_message += text

        # 下载微博中包含的图片
        if img_urls:
            img_download_tasks = [Weibo.download_resource(url=url) for url in img_urls]
            img_download_res = await semaphore_gather(tasks=img_download_tasks, semaphore_num=9, filter_exception=True)
            for img in img_download_res:
                send_message += OmegaMessageSegment.image(await img.get_hosting_path())
            send_message += '\n'

        send_message += f'\n微博链接: https://weibo.com/detail/{smc_item.mblog.mid}'
        return send_message


__all__ = [
    'WeiboUserSubscriptionManager',
]
