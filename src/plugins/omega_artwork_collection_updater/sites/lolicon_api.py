"""
@Author         : Ailitonia
@Date           : 2024/8/17 下午7:11
@FileName       : lolicon_api
@Project        : nonebot2_miya
@Description    : lolicon API 自动更新工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING, Literal, Optional

from pydantic import BaseModel, ConfigDict

from src.service.artwork_collection import PixivArtworkCollection
from src.utils.common_api import BaseCommonAPI
from src.utils.process_utils import semaphore_gather

if TYPE_CHECKING:
    from nonebot.internal.driver import CookieTypes, HeaderTypes


class BaseLoliconModel(BaseModel):
    model_config = ConfigDict(extra='ignore', frozen=True, coerce_numbers_to_str=True)


class LoliconSetu(BaseLoliconModel):
    pid: int
    p: int
    uid: int
    title: str
    author: str
    r18: bool
    width: int
    height: int
    tags: list[str]
    ext: str
    aiType: int
    uploadDate: int
    urls: dict[str, str]


class LoliconAPIReturn(BaseLoliconModel):
    error: Optional[str] = None
    data: list[LoliconSetu]


class LoliconAPI(BaseCommonAPI):
    """lolicon API"""

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'https://api.lolicon.app'

    @classmethod
    async def _async_get_root_url(cls, *args, **kwargs) -> str:
        return cls._get_root_url(*args, **kwargs)

    @classmethod
    def _load_cloudflare_clearance(cls) -> bool:
        return False

    @classmethod
    def _get_default_headers(cls) -> "HeaderTypes":
        return {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0'}

    @classmethod
    def _get_default_cookies(cls) -> "CookieTypes":
        return None

    @classmethod
    def _get_setu_api_url(cls) -> str:
        return f'{cls._get_root_url()}/setu/v2'

    @classmethod
    async def _query_setu(cls, r18: Literal[0, 1, 2] = 2, num: int = 20) -> LoliconAPIReturn:
        json = {'r18': str(r18), 'num': str(num)}
        return LoliconAPIReturn.model_validate(await cls._post_json(url=cls._get_setu_api_url(), json=json))

    @classmethod
    async def _add_lolicon_setu_into_database(cls, pixiv_ac: PixivArtworkCollection) -> None:
        """在数据库中添加作品信息"""
        artwork_data = await pixiv_ac.artwork_proxy.query()

        classification = 1 if artwork_data.classification == 1 else 2
        rating = 3 if artwork_data.rating == 3 else 1

        await pixiv_ac.add_artwork_into_database_ignore_exists(classification=classification, rating=rating)

    @classmethod
    async def update_lolicon_setu(cls) -> None:
        """从 lolicon API 获取涩图数据并导入数据库"""
        setu_data = await cls._query_setu(r18=2, num=20)
        tasks = [cls._add_lolicon_setu_into_database(PixivArtworkCollection(artwork_id=x.pid)) for x in setu_data.data]
        await semaphore_gather(tasks=tasks, semaphore_num=8, return_exceptions=False)


__all__ = [
    'LoliconAPI',
]
