from nonebot import logger
from omega_miya.utils.omega_plugin_utils import HttpFetcher
from omega_miya.database import Result


API_URL = 'https://api.trace.moe/search'
# ANILIST_API_URL = 'https://graphql.anilist.co'    # Anilist API
ANILIST_API_URL = 'https://trace.moe/anilist/'    # 中文 Anilist API
ANILIST_API_QUERY = '''
query ($id: Int) { # Define which variables will be used in the query (id)
  Media (id: $id, type: ANIME) { # Insert our variables into the query arguments (id) (type: ANIME is hard-coded in the query)
    id # you must query the id field for it to search the translated database
    title {
      native # do not query chinese here, the official Anilist API doesn't recognize
      romaji
      english
    }
    isAdult
    synonyms # chinese titles will always be merged into this array
  }
}
'''

HEADERS = {'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
                     'application/signed-exchange;v=b3;q=0.9',
           'accept-encoding': 'gzip, deflate',
           'accept-language': 'zh-CN,zh;q=0.9',
           'cache-control': 'max-age=0',
           'dnt': '1',
           'upgrade-insecure-requests': '1',
           'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                         'Chrome/90.0.4430.212 Safari/537.36'}


# 获取识别结果
async def get_identify_result(img_url: str, *, sensitivity: float = 0.8) -> Result.ListResult:
    fetcher = HttpFetcher(timeout=10, flag='search_anime', headers=HEADERS)

    payload = {'url': img_url}
    result_json = await fetcher.get_json(url=API_URL, params=payload)
    if not result_json.success():
        return Result.ListResult(error=True, info=result_json.info, result=[])

    _result = []
    for item in result_json.result.get('result'):
        try:
            if item.get('similarity') < sensitivity:
                continue
            anilist = item.get('anilist')
            # 获取番剧信息
            payload = {'query': ANILIST_API_QUERY, 'variables': {'id': anilist}}
            anilist_result = await fetcher.post_json(url=ANILIST_API_URL, json=payload)
            if anilist_result.error:
                raise Exception(anilist_result.info)

            title_native = anilist_result.result['data']['Media']['title']['native']
            title_chinese = anilist_result.result['data']['Media']['title']['chinese']
            is_adult = anilist_result.result['data']['Media']['isAdult']

            _result.append({
                'anilist': anilist,
                'filename': item.get('filename'),
                'episode': item.get('episode'),
                'from': item.get('from'),
                'to': item.get('to'),
                'similarity': item.get('similarity'),
                'video': item.get('video'),
                'image': item.get('image'),
                'title_native': title_native,
                'title_chinese': title_chinese,
                'is_adult': is_adult,
            })
        except Exception as e:
            logger.warning(f'result parse failed: {repr(e)}, raw_json: {item}')
            continue

    return Result.ListResult(error=False, info='Success', result=_result)
