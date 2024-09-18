"""
@Author         : Ailitonia
@Date           : 2024/8/17 下午7:53
@FileName       : local_collected_artwork
@Project        : nonebot2_miya
@Description    : 本地图片自动更新工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from src.service.artwork_collection import LocalCollectedArtworkCollection
from src.service.artwork_proxy import LocalCollectedArtworkProxy
from src.utils import semaphore_gather


class LocalCollectedArtworkUpdater:
    """本地图片更新工具"""

    @classmethod
    async def update_local_collected_artwork(cls) -> None:
        """导入本地图片到数据库

        注意: 自动更新会将所有本地图片的分级 (rating) 视为 General (rating=0) 处理, 请自行确认存放于 local_collected_artwork 中的图片
        """
        local_now_artworks = await LocalCollectedArtworkProxy.list_all_artwork()

        # 删除本地已不存在的作品信息
        exists_aids = await LocalCollectedArtworkCollection.query_user_all_aids(uid='Unknown', uname='Unknown')
        delete_aids = (aid for aid in exists_aids if aid not in (x.s_aid for x in local_now_artworks))

        delete_tasks = [LocalCollectedArtworkCollection(aid).delete_artwork_from_database() for aid in delete_aids]
        await semaphore_gather(tasks=delete_tasks, semaphore_num=10, return_exceptions=False)

        # 重新根据现有文件导入作品
        add_aids = (x.s_aid for x in local_now_artworks if x.s_aid not in exists_aids)
        add_tasks = [
            LocalCollectedArtworkCollection(aid).add_artwork_into_database_ignore_exists(classification=3, rating=0)
            for aid in add_aids
        ]
        await semaphore_gather(tasks=add_tasks, semaphore_num=10, return_exceptions=False)


__all__ = [
    'LocalCollectedArtworkUpdater',
]
