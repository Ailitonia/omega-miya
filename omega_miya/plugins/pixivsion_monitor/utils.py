from omega_miya.database import DBPixivision, Result
from omega_miya.utils.pixiv_utils import PixivisionArticle


async def pixivsion_article_parse(aid: int, tags: list) -> Result.DictResult:
    article_result = await PixivisionArticle(aid=aid).get_article_info()
    if article_result.error:
        return Result.DictResult(error=True, info=article_result.info, result={})

    try:
        if not tags:
            tags = [x.get('tag_name') for x in article_result.result.get('tags_list')]

        article_info = dict(article_result.result)

        title = str(article_info['article_title'])
        description = str(article_info['article_description'])
        url = f'https://www.pixivision.net/zh/a/{aid}'
        illusts_list = []

        for illust in article_info['illusts_list']:
            illusts_list.append(int(illust['illusts_id']))

        pixivision = DBPixivision(aid=aid)
        db_res = await pixivision.add(title=title, description=description,
                                      tags=repr(tags), illust_id=repr(illusts_list), url=url)
        if db_res.success():
            __res = {
                'title': title,
                'description': description,
                'url': url,
                'image:': article_info['article_eyecatch_image'],
                'illusts_list': illusts_list
            }
            result = Result.DictResult(error=False, info='Success', result=__res)
        else:
            result = Result.DictResult(error=True, info=db_res.info, result={})
    except Exception as e:
        result = Result.DictResult(error=True, info=repr(e), result={})
    return result
