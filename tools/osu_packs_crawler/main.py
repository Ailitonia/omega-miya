"""
@Author         : Ailitonia
@Date           : 2025/5/18 16:22
@FileName       : main
@Project        : omega-miya
@Description    : osu! 网页端 API
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import TYPE_CHECKING, Literal

from lxml import etree
from nonebot.utils import run_sync

from src.utils import BaseCommonAPI
from .config import osu_web_config
from .model import BeatMap, BeatmapsPack

if TYPE_CHECKING:
    from src.utils.omega_common_api.types import CookieTypes, HeaderTypes

type BeatmapsPacksType = Literal[
    'standard',
    'featured',
    'tournament',
    'loved',
    'chart',
    'theme',
    'artist',
]


class OsuWeb(BaseCommonAPI):
    """osu! web"""

    @staticmethod
    @run_sync
    def _parse_beatmaps_packs(content: str) -> list[str]:
        html = etree.HTML(content)
        beatmap_containers = html.xpath(
            '/html/body/div/div[@class="osu-page"]/'
            'div[@class="beatmap-packs js-accordion"]/'
            'div[@class="beatmap-pack js-beatmap-pack js-accordion__item"]'
        )
        return [
            str(data_pack_tag)
            for x in beatmap_containers
            if x.attrib is not None and (data_pack_tag := x.attrib.get('data-pack-tag')) is not None
        ]

    @staticmethod
    @run_sync
    def _parse_beatmap_pack(id_: str, content: str) -> BeatmapsPack:
        html = etree.HTML(content)
        download_url = html.xpath(
            '//div[@class="beatmap-pack-description"]/'
            'a[@class="beatmap-pack-download__link"]'
        ).pop(0).attrib.get('href')

        beatmaps = html.xpath(
            '//ul[@class="beatmap-pack-items"]/'
            'li[@class="beatmap-pack-items__set"]/'
            'a[@class="beatmap-pack-items__link"]'
        )

        maps = [
            BeatMap.model_validate({
                'id': x.attrib.get('href').split('/')[-1],
                'url': x.attrib.get('href'),
                'name': ''.join(s.text if s.text else '' for s in x.xpath('span'))
            })
            for x in beatmaps
        ]
        return BeatmapsPack.model_validate({'id': id_, 'download_url': download_url, 'beatmaps': maps})

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'https://osu.ppy.sh'

    @classmethod
    def _get_default_headers(cls) -> 'HeaderTypes':
        return cls._get_omega_requests_default_headers()

    @classmethod
    def _get_default_cookies(cls) -> 'CookieTypes':
        return osu_web_config.osu_session

    @classmethod
    async def query_beatmaps_packs_list(cls, type_: BeatmapsPacksType = 'standard', page: int = 1) -> list[str]:
        url = f'{cls._get_root_url()}/beatmaps/packs'
        params = {
            'type': type_,
            'page': page,
        }
        packs_content = await cls._get_resource_as_text(url=url, params=params)
        return await cls._parse_beatmaps_packs(packs_content)

    @classmethod
    async def query_beatmap_pack(cls, beatmap_pack_id: str) -> BeatmapsPack:
        url = f'{cls._get_root_url()}/beatmaps/packs/{beatmap_pack_id}'
        params = {
            'format': 'raw',
        }
        pack_content = await cls._get_resource_as_text(url=url, params=params)
        return await cls._parse_beatmap_pack(beatmap_pack_id, pack_content)


__all__ = [
    'BeatmapsPacksType',
    'OsuWeb',
]
