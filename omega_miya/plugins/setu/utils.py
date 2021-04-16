from omega_miya.utils.Omega_Base import DBPixivillust, Result
from omega_miya.utils.pixiv_utils import PixivIllust


async def add_illust(pid: int, nsfw_tag: int) -> Result:
    illust_result = await PixivIllust(pid=pid).get_illust_data()

    if illust_result.success():
        illust_data = illust_result.result
        title = illust_data.get('title')
        uid = illust_data.get('uid')
        uname = illust_data.get('uname')
        url = illust_data.get('url')
        tags = illust_data.get('tags')
        is_r18 = illust_data.get('is_r18')

        if is_r18:
            nsfw_tag = 2

        illust = DBPixivillust(pid=pid)
        _res = await illust.add(uid=uid, title=title, uname=uname, nsfw_tag=nsfw_tag, tags=tags, url=url)
        return _res
    else:
        return illust_result
