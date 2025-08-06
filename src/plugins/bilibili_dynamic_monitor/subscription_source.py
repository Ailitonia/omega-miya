"""
@Author         : Ailitonia
@Date           : 2025/6/5 22:45
@FileName       : subscription_source.py
@Project        : omega-miya
@Description    : 哔哩哔哩动态订阅源实现
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import TYPE_CHECKING, ClassVar, Self

from src.database.internal.social_media_content import SocialMediaContent
from src.database.internal.subscription_source import SubscriptionSource, SubscriptionSourceType
from src.exception import WebSourceException
from src.service import OmegaMessage, OmegaMessageSegment
from src.service.omega_subscription_service import BaseSubscriptionManager
from src.utils import semaphore_gather
from src.utils.bilibili_api import BilibiliDynamic, BilibiliUser
from src.utils.bilibili_api.models.dynamic import DynamicType

if TYPE_CHECKING:
    from src.utils.bilibili_api.models.dynamic import DynItem

    type SMC_T = DynItem


class BilibiliDynamicSubscriptionManager(BaseSubscriptionManager['SMC_T']):
    """Bilibili 动态订阅服务管理"""

    _IGNORE_NOTICE_DYNAMIC_TYPES: ClassVar[list[DynamicType]] = [
        DynamicType.live_rcmd,
        DynamicType.ad,
        DynamicType.applet,
    ]
    """在通知时忽略的动态类型"""

    def __init__(self, uid: str | int) -> None:
        self.sub_id = str(uid)

    @classmethod
    def init_from_sub_id(cls, sub_id: str | int) -> Self:
        return cls(uid=sub_id)

    @classmethod
    def get_sub_type(cls) -> str:
        return SubscriptionSourceType.bili_dynamic.value

    @staticmethod
    def _get_smc_item_mid(smc_item: 'SMC_T') -> str:
        return smc_item.id_str

    @classmethod
    def _parse_smc_item(cls, smc_item: 'SMC_T') -> 'SocialMediaContent':
        return SocialMediaContent.model_validate({
            'source': cls.get_sub_type(),
            'm_id': smc_item.id_str,
            'm_type': str(smc_item.type),
            'm_uid': str(smc_item.modules.module_author.mid),
            'title': f'{smc_item.modules.module_author.name}的动态',
            'content': smc_item.dyn_text,
            'ref_content': '',
        })

    async def _query_sub_source_smc_items(self) -> 'list[SMC_T]':
        dynamics = await BilibiliDynamic.query_user_space_dynamics(host_mid=self.sub_id)
        return dynamics.data.items

    async def query_sub_source_data(self) -> 'SubscriptionSource':
        user_data = await BilibiliUser.query_user_info(mid=self.sub_id)
        if user_data.error:
            raise WebSourceException(404, f'query user({self.sub_id}) info failed, {user_data.message}')

        return SubscriptionSource.model_validate({
            'id': -1,
            'sub_type': self.get_sub_type(),
            'sub_id': self.sub_id,
            'sub_user_name': user_data.uname,
            'sub_info': 'Bilibili用户动态订阅',
        })

    @classmethod
    async def _format_smc_item_message(cls, smc_item: 'SMC_T') -> str | OmegaMessage | None:
        if smc_item.type in cls._IGNORE_NOTICE_DYNAMIC_TYPES:
            return None

        send_message = f'【bilibili】{smc_item.dyn_text}\n'

        # 下载动态中包含的图片
        if smc_item.dyn_image_urls:
            img_download_tasks = [BilibiliDynamic.download_resource(url=url) for url in smc_item.dyn_image_urls]
            img_download_res = await semaphore_gather(tasks=img_download_tasks, semaphore_num=9, filter_exception=True)
            for img in img_download_res:
                send_message += OmegaMessageSegment.image(await img.get_hosting_path())
            send_message += '\n'

        send_message += f'\n动态链接: https://t.bilibili.com/{smc_item.id_str}'
        return send_message


__all__ = [
    'BilibiliDynamicSubscriptionManager',
]
