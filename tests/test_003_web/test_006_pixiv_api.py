"""
@Author         : Ailitonia
@Date           : 2026/9/23 20:48
@FileName       : test_006_pixiv_api
@Project        : omega-miya
@Description    : pixiv api 单元测试

真实请求的核验分三层: 原始响应(raw json/html)断言 -> 数据模型交叉核验 -> 公开方法结果一致性
页面解析的核验基准由测试内独立的 xpath/正则从同一份原始 HTML 提取, 不复用 PixivParser 实现

真实请求用例默认跳过, 需用户手动设置 PIXIV_API_REAL_TEST=1 环境变量后发起;
发起前须确保 .env.test 中已配置有效的 PIXIV_PHPSESSID

真实请求用例不使用固化样本 id, 样本动态取自 Session 上下文:
用户为 Session 用户及其关注列表前 5 个用户; 作品为最新收藏与关注动态(最新发布)中首个可用作品;
动图与合集型特辑从候选池有界扫描, 取样失败时相关用例跳过而非失败
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import asyncio
import re
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest
from lxml import etree

from tests.test_003_web.helpers import require_env_flag

if TYPE_CHECKING:
    from src.utils.pixiv_api import PixivArtwork, PixivUser

require_real_test = require_env_flag('PIXIV_API_REAL_TEST')
"""真实请求验证类门禁: 日常运行 (含全量套件) 一律跳过, 由用户手动设置环境变量后发起"""


@pytest.fixture
async def _throttle_requests():
    """pixiv 真实接口请求节流(仅真实请求用例, 每个用例结束后等待 1s)"""
    yield
    await asyncio.sleep(1)


async def throttled_get_json(url: str, params: Any = None) -> Any:
    """请求 pixiv 接口 JSON 并等待 1s(请求节流)"""
    from src.utils.pixiv_api import PixivCommon

    result = await PixivCommon._get_resource_as_json(url=url, params=params)
    await asyncio.sleep(1)
    return result


async def _fetch_user_raw(api: 'PixivUser') -> SimpleNamespace:
    """抓取指定用户的 data/profile 原始响应(请求间 1s 节流)"""
    raw_user = await throttled_get_json(url=api.data_url, params={'lang': 'zh'})
    raw_profile = await throttled_get_json(url=api.profile_url, params={'lang': 'zh'})
    return SimpleNamespace(api=api, raw_user=raw_user, raw_profile=raw_profile)


async def _fetch_artwork_sample(candidates: list[str], *, with_ugoira: bool = False) -> SimpleNamespace | None:
    """按候选序抓取首个可用作品样本(data + pages, with_ugoira 时含 ugoira_meta)

    候选作品可能已被删除/转私密(error=True), 最多尝试前 5 个候选, 全部不可用返回 None
    """
    from src.utils.pixiv_api import PixivArtwork

    for pid in candidates[:5]:
        api = PixivArtwork(pid=pid)
        raw_data = await throttled_get_json(url=api.data_url)
        if raw_data.get('error'):
            continue
        raw_pages = await throttled_get_json(url=api.page_data_url)
        if raw_pages.get('error'):
            continue
        raw_ugoira = None
        if with_ugoira and raw_data['body']['illustType'] == 2:
            raw_ugoira = await throttled_get_json(url=api.ugoira_meta_url)
        return SimpleNamespace(api=api, raw_data=raw_data, raw_pages=raw_pages, raw_ugoira=raw_ugoira)
    return None


@pytest.fixture(scope='module')
async def session_user_sample() -> SimpleNamespace:
    """Session 用户样本(cookie 对应的默认用户)"""
    from src.utils.pixiv_api import PixivUser

    try:
        api = PixivUser.init_default_user()
    except ValueError as e:
        pytest.skip(f'未配置 Pixiv Cookie, 跳过 Session 用户样本测试: {e}')
    return await _fetch_user_raw(api)


@pytest.fixture(scope='module')
async def following_users_samples(session_user_sample: SimpleNamespace) -> SimpleNamespace:
    """Session 用户关注列表前 5 个用户样本(含关注列表原始响应)"""
    from src.utils.pixiv_api import PixivUser

    api: PixivUser = session_user_sample.api
    raw_following = await throttled_get_json(
        url=api.follow_user_url,
        params={'offset': 0, 'limit': 24, 'rest': 'show', 'acceptingRequests': 0, 'lang': 'zh'},
    )

    samples = []
    for item in (raw_following.get('body', {}).get('users') or [])[:5]:
        samples.append(await _fetch_user_raw(PixivUser(uid=item['userId'])))
    return SimpleNamespace(raw_following=raw_following, samples=samples)


@pytest.fixture(scope='module')
async def artwork_pool_sample() -> SimpleNamespace:
    """作品候选池: 最新收藏(默认用户收藏第 1 页) + 最新发布(关注动态第 1 页)

    候选序列按来源顺序排列并优先 xRestrict=0 的作品; 动图候选取自两池前 10 条中的 illustType=2
    """
    from src.utils.pixiv_api import PixivCommon

    try:
        uid = PixivCommon._get_default_user_id()
    except ValueError as e:
        pytest.skip(f'未配置 Pixiv Cookie, 跳过作品取样: {e}')

    raw_bookmarks = await throttled_get_json(
        url=f'{PixivCommon._get_root_url()}/ajax/user/{uid}/illusts/bookmarks',
        params={'tag': '', 'offset': 0, 'limit': 48, 'rest': 'show', 'lang': 'zh'},
    )
    raw_follow_latest = await throttled_get_json(
        url=f'{PixivCommon._get_root_url()}/ajax/follow_latest/illust',
        params={'mode': 'all', 'lang': 'zh', 'p': 1},
    )

    bookmark_works = raw_bookmarks.get('body', {}).get('works') or []
    follow_body = raw_follow_latest.get('body', {})
    latest_thumbs = {str(x['id']): x for x in follow_body.get('thumbnails', {}).get('illust', [])}
    latest_ids = [str(x) for x in follow_body.get('page', {}).get('ids', [])]

    bookmark_safe = [str(x['id']) for x in bookmark_works if not x.get('xRestrict')]
    latest_safe = [x for x in latest_ids if not latest_thumbs.get(x, {}).get('xRestrict')]
    pool_items = [*bookmark_works[:10], *list(latest_thumbs.values())[:10]]
    return SimpleNamespace(
        raw_bookmarks=raw_bookmarks,
        raw_follow_latest=raw_follow_latest,
        bookmark_candidates=bookmark_safe or [str(x['id']) for x in bookmark_works],
        latest_candidates=latest_safe or latest_ids,
        ugoira_candidates=[str(x['id']) for x in pool_items if x.get('illustType') == 2],
    )


@pytest.fixture(scope='module')
async def bookmark_artwork_sample(artwork_pool_sample: SimpleNamespace) -> SimpleNamespace | None:
    """最新收藏作品样本(候选池中首个可用作品)"""
    return await _fetch_artwork_sample(artwork_pool_sample.bookmark_candidates)


@pytest.fixture(scope='module')
async def latest_artwork_sample(artwork_pool_sample: SimpleNamespace) -> SimpleNamespace | None:
    """最新发布作品样本(关注动态第 1 页中首个可用作品)"""
    return await _fetch_artwork_sample(artwork_pool_sample.latest_candidates)


@pytest.fixture(scope='module')
async def ugoira_artwork_sample(artwork_pool_sample: SimpleNamespace) -> SimpleNamespace | None:
    """动图作品样本(候选池前 10 条中首个动图, 无则 None)"""
    return await _fetch_artwork_sample(artwork_pool_sample.ugoira_candidates, with_ugoira=True)


@pytest.fixture(scope='module')
async def show_page() -> SimpleNamespace:
    """pixivision 导览页样本(页面内容 + 解析结果)"""
    from src.utils.pixiv_api import Pixivision
    from src.utils.pixiv_api.helper import PixivParser

    content = await Pixivision.get_resource_as_text(
        url=Pixivision._get_illustration_url(), params={'p': 1, 'lang': 'zh'}
    )
    parsed = await PixivParser.parse_pixivision_show_page(
        content=content, root_url=Pixivision._get_root_url()
    )
    return SimpleNamespace(content=content, parsed=parsed, root_url=Pixivision._get_root_url())


@pytest.fixture(scope='module')
async def article_pages_sample(show_page: SimpleNamespace) -> list[SimpleNamespace]:
    """pixivision 文章页样本: 导览页前 10 篇特辑的页面内容与解析结果(请求间 1s 节流)"""
    from src.utils.pixiv_api import Pixivision
    from src.utils.pixiv_api.helper import PixivParser

    pages = []
    for item in show_page.parsed.illustrations[:10]:
        content = await Pixivision.get_resource_as_text(url=f'{Pixivision._get_articles_url()}/{item.aid}')
        parsed = await PixivParser.parse_pixivision_article_page(
            content=content, root_url=Pixivision._get_root_url()
        )
        pages.append(SimpleNamespace(aid=item.aid, content=content, parsed=parsed))
        await asyncio.sleep(1)
    return pages


def assert_no_error(raw: Any, label: str, *, hint: str = '') -> None:
    """接口原始响应 error 标记核验(应为 False), hint 为附加排查提示"""
    suffix = f' ({hint})' if hint else ''
    assert raw.get('error') is False, f'{label} error: {raw.get("message")}{suffix}'


def assert_numeric(value: Any, label: str = 'value') -> None:
    """纯数字字段核验(字符串化后应整体匹配 \\d+)"""
    assert re.fullmatch(r'\d+', str(value)), f'illegal {label}: {value!r}'


def _content_keys(content: Any) -> list[str]:
    """profile 接口作品索引的键集合(无内容时接口返回空列表, 按空字典处理)"""
    return list(content.keys()) if isinstance(content, dict) else []


def _gt_user_search_page(content: str) -> dict[str, Any]:
    """独立基准提取: pixiv 用户搜索结果页(不复用 PixivParser 实现)"""
    html = etree.HTML(content)

    users: dict[str, str] = {}
    thumbs: dict[str, list[str]] = {}
    for li in html.xpath('//li[contains(@class, "list-none")]'):
        uid = None
        for a in li.xpath('.//a[@data-ga4-label="user_name_link"]'):
            matched = re.search(r'/users/(\d+)', a.attrib.get('href') or '')
            if matched is not None:
                uid = matched.group(1)
                users[uid] = ''.join(a.itertext()).strip()
        if uid is not None:
            thumbs[uid] = [
                img.attrib['src']
                for img in li.xpath('.//div[@type="illust"]//img')
                if img.attrib.get('src')
            ]

    h1 = html.xpath('//h1')
    title = h1[0].text if h1 else None
    count_spans = html.xpath('//h1/following-sibling::div/span[1]')
    count = count_spans[0].text if count_spans else None
    return {'title': title, 'count': count, 'users': users, 'thumbs': thumbs}


def _extract_cards(context: Any, xpath: str) -> list[dict[str, Any]]:
    """独立基准提取: 特辑卡片条目(导览页卡片与文章页合集卡片共用提取逻辑)"""
    items = []
    for card in context.xpath(xpath):
        link = card.xpath('.//h2/a')
        thumb_div = card.xpath('.//div[@class="_thumbnail"]')
        if not link or not thumb_div:
            continue
        href = link[0].attrib.get('href') or ''
        aid_matched = re.search(r'/a/(\d+)', href)
        thumb_matched = re.search(r'url\((.*?)\)', thumb_div[0].attrib.get('style') or '')
        if aid_matched is None or thumb_matched is None:
            continue
        tags = []
        for tag_a in card.xpath('.//ul/li/a[contains(@href, "/t/")]'):
            tid_matched = re.search(r'/t/(\d+)', tag_a.attrib.get('href') or '')
            if tid_matched is not None:
                tags.append({'id': tid_matched.group(1), 'name': ''.join(tag_a.itertext()).strip()})
        items.append({
            'aid': aid_matched.group(1),
            'title': ''.join(link[0].itertext()).strip(),
            'href': href,
            'thumbnail': thumb_matched.group(1).strip('\'" '),
            'tags': tags,
        })
    return items


def _gt_pixivision_show_page(content: str) -> list[dict[str, Any]]:
    """独立基准提取: pixivision 导览页特辑卡片(不复用 PixivParser 实现)"""
    html = etree.HTML(content)
    return _extract_cards(html, '//li[@class="article-card-container"]')


def _gt_pixivision_article_page(content: str) -> dict[str, Any]:
    """独立基准提取: pixivision 文章页(不复用 PixivParser 实现)"""
    html = etree.HTML(content)
    main = html.xpath('//div[@class="_article-main"]')[0]

    title = ''.join(main.xpath('.//h1[@class="am__title"]')[0].itertext()).strip()
    eyecatch_nodes = main.xpath('.//div[@class="_article-illust-eyecatch"]//img')
    eyecatch = eyecatch_nodes[0].attrib.get('src') if eyecatch_nodes else None
    desc_nodes = main.xpath('.//div[@class="am__body"]/div//div[contains(@class, "_medium-editor-text")]')
    description = ' '.join(''.join(desc_nodes[0].itertext()).split()) if desc_nodes else ''

    artworks = []
    for work in main.xpath('.//div[@class="am__work"]'):
        link = work.xpath('.//div[@class="am__work__main"]/a[@class="inner-link"]')
        if not link:
            continue
        href = link[0].attrib.get('href') or ''
        pid_matched = re.search(r'pixiv\.net/(?:artworks|i)/(\d+)', href) or re.search(r'illust_id=(\d+)', href)
        title_nodes = work.xpath('.//h3[@class="am__work__title"]/a')
        user_nodes = work.xpath('.//p[@class="am__work__user-name"]/a')
        img_nodes = link[0].xpath('.//img')
        artworks.append({
            'pid': pid_matched.group(1) if pid_matched is not None else None,
            'url': href,
            'title': ''.join(title_nodes[0].itertext()).strip() if title_nodes else None,
            'user': ''.join(user_nodes[0].itertext()).strip() if user_nodes else None,
            'image': img_nodes[0].attrib.get('src') if img_nodes else None,
        })

    collections = _extract_cards(main, './/article[contains(@class, "spotlight")]')

    article_tags = []
    for tag_a in main.xpath('./div//ul[@class="_tag-list"]/a'):
        tid_matched = re.search(r'/t/(\d+)', tag_a.attrib.get('href') or '')
        if tid_matched is not None:
            article_tags.append({'id': tid_matched.group(1), 'name': ''.join(tag_a.itertext()).strip()})

    return {
        'title': title,
        'eyecatch': eyecatch,
        'description': description,
        'artworks': artworks,
        'collections': collections,
        'tags': article_tags,
    }


def _assert_artwork_raw(sample: SimpleNamespace) -> None:
    """作品样本核验: data/pages 原始响应断言 + 模型交叉核验"""
    from src.utils.pixiv_api.model import PixivIllustData, PixivIllustPages

    raw = sample.raw_data
    assert raw.get('error') is False, f'illust data error: {raw.get("message")}'
    body = raw['body']

    # raw 核验: 关键字段存在性/类型/取值
    assert str(body['illustId']) == sample.api.pid
    assert isinstance(body['illustTitle'], str)
    assert body['illustTitle'], 'illustTitle is empty'
    assert isinstance(body['tags'], dict)
    assert isinstance(body['tags']['tags'], list)
    for tag in body['tags']['tags']:
        assert isinstance(tag['tag'], str)
        assert isinstance(tag['locked'], bool)
    assert re.fullmatch(r'\d+', str(body['userId']))
    for key in ('mini', 'thumb', 'small', 'regular', 'original'):
        assert body['urls'][key].startswith('https://i.pximg.net/'), f'illegal {key} url'
    for key in ('bookmarkCount', 'likeCount', 'commentCount', 'responseCount', 'viewCount', 'pageCount'):
        assert isinstance(body[key], int), f'illegal {key}'
        assert body[key] >= 0, f'illegal {key}'
    assert isinstance(body['xRestrict'], int)
    assert isinstance(body['aiType'], int)

    # 模型交叉核验
    data = PixivIllustData.model_validate(raw)
    assert data.body.illustId == str(body['illustId'])
    assert data.body.illustTitle == body['illustTitle']
    assert data.body.userId == str(body['userId'])
    assert data.body.bookmarkCount == body['bookmarkCount']
    assert data.body.pageCount == body['pageCount']
    # tag_info 迁移核验: 原始 tags 对象迁入 tag_info, 父类列表字段保持默认空
    assert data.body.tags == []
    assert data.body.tag_info.all_tags == list(dict.fromkeys(
        [x['tag'] for x in body['tags']['tags']]
        + [t for x in body['tags']['tags'] for t in x.get('translation', {}).values()]
    ))
    # parsed_description 不应残留 HTML 标签
    assert '<br' not in data.body.parsed_description
    assert '<a ' not in data.body.parsed_description

    # raw pages 核验: 多页列表长度与作品 pageCount 一致, 每页四档 url 与尺寸
    raw_pages = sample.raw_pages
    assert raw_pages.get('error') is False, f'illust pages error: {raw_pages.get("message")}'
    pages_body = raw_pages['body']
    assert isinstance(pages_body, list)
    assert len(pages_body) == body['pageCount']
    for item in pages_body:
        for key in ('thumb_mini', 'small', 'regular', 'original'):
            assert item['urls'][key].startswith('https://i.pximg.net/')
        assert item['width'] > 0
        assert item['height'] > 0

    # 模型交叉核验
    pages = PixivIllustPages.model_validate(raw_pages)
    assert sorted(pages.index_pages.keys()) == list(range(len(pages_body)))
    assert pages.index_pages[0].original == pages_body[0]['urls']['original']
    assert len(pages.type_pages.original) == len(pages_body)
    assert len(pages.type_pages.regular) == len(pages_body)
    assert len(pages.type_pages.small) == len(pages_body)
    assert len(pages.type_pages.thumb_mini) == len(pages_body)


async def _assert_artwork_full(sample: SimpleNamespace) -> None:
    """作品样本方法层核验: query_artwork 汇总数据与 raw 逐字段一致(同实例, 缓存生效不重复请求)"""
    api: PixivArtwork = sample.api
    full = await api.query_artwork()
    body = sample.raw_data['body']

    assert full.pid == str(body['illustId'])
    assert full.title == body['illustTitle']
    assert full.uid == str(body['userId'])
    assert full.uname == body['userName']
    assert full.width == body['width']
    assert full.height == body['height']
    # 统计字段为易变数据, raw 抓取与 query_artwork 请求间可能变化, 核验单调不降
    assert full.bookmark_count >= body['bookmarkCount']
    assert full.like_count >= body['likeCount']
    assert full.view_count >= body['viewCount']
    assert full.page_count == body['pageCount']
    assert full.illust_type == body['illustType']
    assert full.sanity_level == body['xRestrict']
    assert full.ai_level == body['aiType']
    assert full.orig_url == body['urls']['original']
    assert full.regular_url == body['urls']['regular']
    assert len(full.index_pages) == len(sample.raw_pages['body'])

    # 依据 raw 独立推导 is_r18/is_ai 期望值并比对
    raw_tags = [x['tag'] for x in body['tags']['tags']]
    raw_tags.extend(t for x in body['tags']['tags'] for t in x.get('translation', {}).values())
    expected_r18 = body['xRestrict'] >= 1 or any(re.fullmatch(r'[Rr]-18[Gg]?', x) for x in raw_tags)
    expected_ai = body['aiType'] >= 2 or any(
        re.fullmatch(r'([Nn]ovel[Aa][Ii]([Dd]iffusion)?|[Ss]table[Dd]iffusion)', x)
        or re.fullmatch(r'(AI|ai)(生成|-[Gg]enerated|イラスト|绘图)', x)
        for x in raw_tags
    )
    assert full.is_r18 == expected_r18
    assert full.is_ai == expected_ai
    if full.is_ai:
        assert full.tags[0] == 'AI生成'
        assert not any(re.fullmatch(r'(AI|ai)(生成|-[Gg]enerated|イラスト|绘图)', x) for x in full.tags[1:])

    # 缓存核验: 重复查询返回同一对象且不重复请求
    assert await api.query_artwork() is full

    # 动图样本核验: ugoira_meta 与 raw 一致, 非动图作品不应携带动图元数据
    if body['illustType'] == 2:
        assert full.ugoira_meta is not None
        if sample.raw_ugoira is not None:
            assert full.ugoira_meta.src == sample.raw_ugoira['body']['src']
            assert len(full.ugoira_meta.frames) == len(sample.raw_ugoira['body']['frames'])
    else:
        assert full.ugoira_meta is None


def _assert_user_raw(sample: SimpleNamespace) -> None:
    """用户样本核验: data/profile 原始响应断言 + 模型交叉核验"""
    from src.utils.pixiv_api.model import PixivUserData, PixivUserProfile

    raw = sample.raw_user
    assert raw.get('error') is False, f'user {sample.api.uid} data error: {raw.get("message")}'
    body = raw['body']
    assert str(body['userId']) == sample.api.uid
    assert isinstance(body['name'], str)
    assert body['name'], 'user name is empty'
    assert body['image'].startswith('https://i.pximg.net/')
    assert body['imageBig'].startswith('https://i.pximg.net/')

    data = PixivUserData.model_validate(raw)
    assert data.body.userId == str(body['userId'])
    assert data.body.name == body['name']

    raw_profile = sample.raw_profile
    assert raw_profile.get('error') is False, f'user {sample.api.uid} profile error: {raw_profile.get("message")}'
    profile_body = raw_profile['body']

    # raw 核验: 作品索引为 {pid: 内容|null} 映射, 无内容时该类型为空列表(接口实际行为)
    for key in ('illusts', 'manga', 'novels'):
        content_map = profile_body[key]
        if isinstance(content_map, list):
            assert content_map == [], f'{key} is non-empty list: {content_map}'
            continue
        assert isinstance(content_map, dict), f'{key} is not dict: {type(content_map)}'
        assert all(re.fullmatch(r'\d+', str(pid)) for pid in content_map), f'illegal pid in {key}'
        assert all(v is None or isinstance(v, dict) for v in content_map.values())

    # 模型交叉核验
    profile = PixivUserProfile.model_validate(raw_profile)
    assert profile.body.illust_list == _content_keys(profile_body['illusts'])
    assert profile.body.manga_list == _content_keys(profile_body['manga'])
    assert profile.body.novel_list == _content_keys(profile_body['novels'])


async def _assert_user_full(sample: SimpleNamespace) -> None:
    """用户样本方法层核验: query_user 汇总数据与 raw 逐字段一致(同实例, 缓存生效不重复请求)"""
    api: PixivUser = sample.api
    full = await api.query_user()

    assert full.user_id == str(sample.raw_user['body']['userId'])
    assert full.name == sample.raw_user['body']['name']
    assert full.image.startswith('https://i.pximg.net/')
    assert full.illusts == _content_keys(sample.raw_profile['body']['illusts'])
    assert full.manga == _content_keys(sample.raw_profile['body']['manga'])
    assert full.novels == _content_keys(sample.raw_profile['body']['novels'])

    # manga_illusts 必须为数值降序
    combined = full.manga_illusts
    assert combined == sorted(combined, key=int, reverse=True)

    # 缓存核验
    assert await api.query_user() is full


def _require_following_samples(following_users_samples: SimpleNamespace) -> list[SimpleNamespace]:
    """关注列表样本准入核验: 关注列表为空时跳过, 返回用户样本列表"""
    raw_following = following_users_samples.raw_following
    assert raw_following.get('error') is False, f'following users error: {raw_following.get("message")}'

    samples = following_users_samples.samples
    if not samples:
        pytest.skip('Session 用户关注列表为空')
    # 取样数量应为关注数与前 5 的较小值
    assert len(samples) == min(5, len(raw_following['body']['users']))
    return samples


@require_real_test
@pytest.mark.usefixtures('_throttle_requests')
class TestPixivCommon:
    """Pixiv 主站通用接口(真实请求 + 原始 JSON 核验)"""

    async def test_query_ranking(self):
        from src.utils.pixiv_api import PixivCommon
        from src.utils.pixiv_api.model import PixivRanking

        url = f'{PixivCommon._get_root_url()}/ranking.php'
        raw_p1 = await throttled_get_json(
            url=url, params={'format': 'json', 'mode': 'daily', 'p': 1, 'content': 'illust'}
        )
        raw_p2 = await PixivCommon._get_resource_as_json(
            url=url, params={'format': 'json', 'mode': 'daily', 'p': 2, 'content': 'illust'}
        )

        # raw 核验: 每页 50 条, rank 连续递增
        assert len(raw_p1['contents']) == 50, f'page1 contents length unexpected: {len(raw_p1["contents"])}'
        assert len(raw_p2['contents']) == 50, f'page2 contents length unexpected: {len(raw_p2["contents"])}'
        assert [x['rank'] for x in raw_p1['contents']] == list(range(1, 51))
        assert [x['rank'] for x in raw_p2['contents']] == list(range(51, 101))
        for item in raw_p1['contents'][:5]:
            assert_numeric(item['illust_id'], 'illust_id')
            # ranking 接口的 url 字段为作品缩略图链接而非作品页链接
            assert item['url'].startswith('https://i.pximg.net/'), f'illegal url: {item["url"]!r}'

        # 模型交叉核验
        ranking_p1 = PixivRanking.model_validate(raw_p1)
        assert ranking_p1.page == raw_p1['page'] == 1
        assert [x.illust_id for x in ranking_p1.contents] == [str(x['illust_id']) for x in raw_p1['contents']]
        assert [x.user_id for x in ranking_p1.contents] == [str(x['user_id']) for x in raw_p1['contents']]
        assert [x.rank for x in ranking_p1.contents] == [x['rank'] for x in raw_p1['contents']]

        # 方法层核验: 翻页后 get_ranking 按全局名次取页内条目
        ranking_p2 = await PixivCommon.query_ranking(mode='daily', content='illust', page=2)
        assert ranking_p2.page == 2
        assert ranking_p2.get_ranking(60).rank == 60
        assert ranking_p2.get_ranking(51).rank == 51
        assert ranking_p2.get_ranking(100).rank == 100
        with pytest.raises(ValueError, match='Ranking num not in this page'):
            ranking_p2.get_ranking(10)

    async def test_search(self):
        from urllib.parse import quote

        from src.utils.pixiv_api import PixivCommon
        from src.utils.pixiv_api.model import PixivSearchingResult

        word = '原创'
        url = f'{PixivCommon._get_root_url()}/ajax/search/illustrations/{quote(word, safe="")}'
        params = {'order': 'date_d', 'mode': 'safe', 'p': '1', 's_mode': 's_tag', 'lang': 'zh'}
        raw = await PixivCommon._get_resource_as_json(url=url, params=params)

        # raw 核验
        assert_no_error(raw, 'search')
        body = raw['body']
        assert body['illust']['data'], 'search result illust data is empty'
        assert isinstance(body['illust']['total'], int)
        assert body['illust']['total'] > 0
        for item in body['illust']['data'][:5]:
            assert_numeric(item['id'], 'id')
            assert_numeric(item['userId'], 'userId')
            assert isinstance(item['title'], str)
            assert item['title'], 'title is empty'
            assert isinstance(item['tags'], list)
            assert all(isinstance(x, str) for x in item['tags']), 'tags element is not str'

        # 模型交叉核验
        result = PixivSearchingResult.model_validate(raw)
        assert result.error is False
        assert isinstance(result.message, str)
        assert [x.id for x in result.body.illust.data] == [str(x['id']) for x in body['illust']['data']]
        assert [x.tags for x in result.body.illust.data] == [x['tags'] for x in body['illust']['data']]
        assert [x.id for x in result.artworks] == [
            str(x['id']) for content in (body.get('illustManga'), body.get('illust'), body.get('manga'))
            if content for x in content['data']
        ]

        # 方法层核验(动态接口, 仅结构断言)
        method_result = await PixivCommon.search(word=word, domain='illustrations')
        assert method_result.error is False
        assert method_result.body.illust.data, 'search method returned empty data'

    async def test_search_popular_condition(self):
        from src.exception import WebSourceException
        from src.utils.pixiv_api import PixivCommon

        # popular_d 排序为 pixiv 高级会员限定, 非会员账号接口将返回 error, 两种行为均核验
        exception = None
        try:
            result = await PixivCommon.search_by_default_popular_condition(word='阿米娅')
        except WebSourceException as e:
            exception = e

        if exception is not None:
            assert exception.status_code == 400
            assert exception.message, 'error message is empty'
            return
        assert result.error is False
        assert result.body.illust.data, 'popular search returned empty data'

    async def test_query_discovery_artworks(self):
        from src.utils.pixiv_api import PixivCommon
        from src.utils.pixiv_api.model import PixivDiscovery

        url = f'{PixivCommon._get_root_url()}/ajax/discovery/artworks'
        raw = await PixivCommon._get_resource_as_json(url=url, params={'mode': 'safe', 'limit': 60, 'lang': 'zh'})

        assert_no_error(raw, 'discovery')
        body = raw['body']
        assert body['recommendedIllusts'], 'discovery recommendedIllusts is empty'
        for item in body['recommendedIllusts'][:5]:
            assert_numeric(item['illustId'], 'illustId')
        assert body['thumbnails']['illust'], 'discovery thumbnails illust is empty'
        for item in body['thumbnails']['illust'][:5]:
            assert isinstance(item['urls'], dict)
            assert '250x250' in item['urls']

        result = PixivDiscovery.model_validate(raw)
        assert result.recommend_pids == [str(x['illustId']) for x in body['recommendedIllusts']]
        assert [x.id for x in result.recommend_illusts] == [str(x['id']) for x in body['thumbnails']['illust']]

        method_result = await PixivCommon.query_discovery_artworks()
        assert method_result.error is False
        assert method_result.recommend_pids, 'discovery method returned empty pids'

    async def test_query_top_illust(self):
        from src.utils.pixiv_api import PixivCommon
        from src.utils.pixiv_api.model import PixivTop

        url = f'{PixivCommon._get_root_url()}/ajax/top/illust'
        raw = await PixivCommon._get_resource_as_json(url=url, params={'mode': 'all', 'lang': 'zh'})

        assert_no_error(raw, 'top illust')
        body = raw['body']
        assert body['page']['recommend']['ids'], 'top illust recommend ids is empty'
        for pid in body['page']['recommend']['ids'][:10]:
            assert_numeric(pid, 'recommend id')

        result = PixivTop.model_validate(raw)
        assert result.recommend_pids == [str(x) for x in body['page']['recommend']['ids']]

        method_result = await PixivCommon.query_top_illust()
        assert method_result.error is False
        assert method_result.recommend_pids, 'top illust method returned empty pids'

    async def test_query_following_user_latest_illust(self, artwork_pool_sample: SimpleNamespace):
        from src.utils.pixiv_api import PixivCommon
        from src.utils.pixiv_api.model import PixivFollowLatestIllust

        # 复用作品池样本已抓取的关注动态第 1 页原始响应, 不重复请求
        raw = artwork_pool_sample.raw_follow_latest
        assert_no_error(raw, 'follow latest', hint='cookies may be invalid')
        body = raw['body']
        assert isinstance(body['page']['ids'], list)
        for pid in body['page']['ids']:
            assert_numeric(pid, 'id')
        assert isinstance(body['page']['isLastPage'], bool)
        assert isinstance(body['thumbnails']['illust'], list)

        result = PixivFollowLatestIllust.model_validate(raw)
        assert result.illust_ids == [str(x) for x in body['page']['ids']]

        method_result = await PixivCommon.query_following_user_latest_illust(page=1)
        assert method_result.error is False

    async def test_query_bookmarks(self, artwork_pool_sample: SimpleNamespace):
        from src.utils.pixiv_api import PixivCommon
        from src.utils.pixiv_api.model import PixivBookmark

        # 复用作品池样本已抓取的收藏第 1 页原始响应, 不重复请求
        raw = artwork_pool_sample.raw_bookmarks
        assert_no_error(raw, 'bookmarks', hint='cookies may be invalid')
        body = raw['body']
        assert isinstance(body['total'], int)
        assert body['total'] >= 0
        assert isinstance(body['works'], list)
        assert body['total'] >= len(body['works'])
        for item in body['works'][:5]:
            assert_numeric(item['id'], 'id')

        result = PixivBookmark.model_validate(raw)
        assert result.total == body['total']
        assert result.illust_ids == [str(x['id']) for x in body['works']]

        method_result = await PixivCommon.query_bookmarks()
        assert method_result.error is False
        assert method_result.total == body['total']


@require_real_test
@pytest.mark.usefixtures('_throttle_requests')
class TestPixivArtwork:
    """Pixiv 作品接口(真实请求 + 原始 JSON 核验, 样本动态取自最新收藏与关注动态)"""

    @pytest.mark.parametrize(
        ('fixture_name', 'skip_reason'),
        [
            ('bookmark_artwork_sample', '收藏为空或候选作品均不可用'),
            ('latest_artwork_sample', '关注动态为空或候选作品均不可用'),
        ],
        ids=['bookmark', 'latest'],
    )
    async def test_artwork_raw(self, fixture_name: str, skip_reason: str, request: pytest.FixtureRequest):
        sample: SimpleNamespace | None = request.getfixturevalue(fixture_name)
        if sample is None:
            pytest.skip(skip_reason)
        _assert_artwork_raw(sample)

    async def test_ugoira_meta_raw(self, ugoira_artwork_sample: SimpleNamespace | None):
        from src.utils.pixiv_api.model import PixivIllustUgoiraMeta

        if ugoira_artwork_sample is None:
            pytest.skip('候选池前 10 条中无动图作品')

        # 样本应为动图
        assert ugoira_artwork_sample.raw_data['body']['illustType'] == 2, 'sample is not ugoira'

        raw = ugoira_artwork_sample.raw_ugoira
        assert raw.get('error') is False, f'ugoira meta error: {raw.get("message")}'
        body = raw['body']
        assert body['src'].startswith('https://')
        assert body['originalSrc'].startswith('https://')
        assert isinstance(body['mime_type'], str)
        assert body['mime_type'], 'mime_type is empty'
        assert body['frames'], 'ugoira frames is empty'
        for frame in body['frames']:
            assert isinstance(frame['file'], str)
            assert frame['file'], 'frame file is empty'
            assert isinstance(frame['delay'], int)
            assert frame['delay'] > 0

        meta = PixivIllustUgoiraMeta.model_validate(raw)
        assert meta.body.src == body['src']
        assert len(meta.body.frames) == len(body['frames'])
        assert [x.file for x in meta.body.frames] == [x['file'] for x in body['frames']]

    async def test_query_artwork_full(
            self,
            bookmark_artwork_sample: SimpleNamespace | None,
            latest_artwork_sample: SimpleNamespace | None,
            ugoira_artwork_sample: SimpleNamespace | None,
    ):
        samples = [
            sample
            for sample in (bookmark_artwork_sample, latest_artwork_sample, ugoira_artwork_sample)
            if sample is not None
        ]
        if not samples:
            pytest.skip('无可用作品样本')
        for sample in samples:
            await _assert_artwork_full(sample)
            await asyncio.sleep(1)

    async def test_query_recommend(self, bookmark_artwork_sample: SimpleNamespace | None):
        from src.utils.pixiv_api.model import PixivIllustRecommend

        if bookmark_artwork_sample is None:
            pytest.skip('收藏为空或候选作品均不可用')

        api: PixivArtwork = bookmark_artwork_sample.api
        raw = await api._get_resource_as_json(url=api.recommend_url, params={'limit': 18, 'lang': 'zh'})

        assert raw.get('error') is False, f'recommend error: {raw.get("message")}'
        body = raw['body']
        assert body['illusts'], 'recommend illusts is empty'
        assert isinstance(body.get('nextIds'), list)
        for item in body['illusts'][:5]:
            assert re.fullmatch(r'\d+', str(item['id'])), f'illegal id: {item["id"]!r}'

        result = PixivIllustRecommend.model_validate(raw)
        assert [x.id for x in result.body.illusts] == [str(x['id']) for x in body['illusts']]
        assert result.illust_ids == [str(x['id']) for x in body['illusts']]

        method_result = await api.query_recommend()
        assert method_result.error is False
        assert method_result.body.illusts, 'recommend method returned empty illusts'
        assert method_result.illust_ids, 'recommend method returned empty illust_ids'

    async def test_get_resource_as_bytes(self, latest_artwork_sample: SimpleNamespace | None):
        from src.utils.pixiv_api import PixivArtwork

        if latest_artwork_sample is None:
            pytest.skip('关注动态为空或候选作品均不可用')

        # 下载作品 regular 图, 核验 referer 链路有效且内容为真实图片
        image_url = latest_artwork_sample.raw_data['body']['urls']['regular']
        content = await PixivArtwork.get_resource_as_bytes(url=image_url, timeout=60)
        assert len(content) > 1024, f'image content too small: {len(content)}'
        assert (
                content.startswith(b'\xff\xd8')  # JPEG
                or content.startswith(b'\x89PNG')  # PNG
                or (content.startswith(b'RIFF') and content[8:12] == b'WEBP')  # WEBP
        ), f'unexpected image magic bytes: {content[:12]!r}'

    async def test_query_artwork_not_found(self):
        from src.exception import WebSourceException
        from src.utils.pixiv_api import PixivArtwork

        # 不存在/已删除的作品: 接口返回 404 状态码或 error 响应体, 两种路径均应包装为 WebSourceException
        api = PixivArtwork(pid=99999999999)
        with pytest.raises(WebSourceException) as exc_info:
            await api.query_artwork()
        assert exc_info.value.status_code in (400, 404)
        assert f'Query {api!r} data failed' in exc_info.value.message


@require_real_test
@pytest.mark.usefixtures('_throttle_requests')
class TestPixivUser:
    """Pixiv 用户接口(真实请求 + 原始 JSON/HTML 核验, 样本动态取自 Session 用户及其关注列表)"""

    async def test_session_user_raw(self, session_user_sample: SimpleNamespace):
        from src.utils.pixiv_api import PixivCommon

        # Session 用户 uid 应与 cookie 推导的默认用户一致
        assert session_user_sample.api.uid == PixivCommon._get_default_user_id()
        _assert_user_raw(session_user_sample)

    async def test_query_session_user_full(self, session_user_sample: SimpleNamespace):
        await _assert_user_full(session_user_sample)

    async def test_following_users_raw(self, following_users_samples: SimpleNamespace):
        for sample in _require_following_samples(following_users_samples):
            _assert_user_raw(sample)

    async def test_following_users_full(self, following_users_samples: SimpleNamespace):
        for sample in _require_following_samples(following_users_samples):
            await _assert_user_full(sample)
            await asyncio.sleep(1)

    async def test_query_user_bookmarks(self):
        from src.utils.pixiv_api import PixivUser

        # 使用 cookie 对应的默认用户, 核验分页 offset/limit 生效
        api = PixivUser.init_default_user()
        page1 = await api.query_user_bookmarks(page=1)
        assert page1.error is False

        if page1.total > 48:
            await asyncio.sleep(1)
            page2 = await api.query_user_bookmarks(page=2)
            assert page2.error is False
            assert page2.total == page1.total
            assert not set(page1.illust_ids) & set(page2.illust_ids), 'page1 and page2 contents overlap'
        else:
            assert len(page1.illust_ids) == page1.total

    async def test_query_user_following_users(
            self,
            session_user_sample: SimpleNamespace,
            following_users_samples: SimpleNamespace,
    ):
        api: PixivUser = session_user_sample.api
        # 复用关注列表样本已抓取的原始响应, 不重复请求
        raw = following_users_samples.raw_following

        assert raw.get('error') is False, f'following users error: {raw.get("message")}'
        body = raw['body']
        assert isinstance(body['total'], int)
        assert body['total'] >= 0
        assert isinstance(body['users'], list)
        for item in body['users'][:5]:
            assert re.fullmatch(r'\d+', str(item['userId'])), f'illegal userId: {item["userId"]!r}'
            assert isinstance(item['userName'], str)
            assert item['userName'], 'userName is empty'
            assert isinstance(item['profileImageUrl'], str)

        # followUserTags 元素为标签名 str 列表
        assert isinstance(body.get('followUserTags'), list)
        for tag in body.get('followUserTags', []):
            assert isinstance(tag, str), f'unexpected followUserTags element type: {type(tag)}'

        result = await api.query_user_following_users()
        assert result.error is False
        assert result.body.total == body['total']
        assert [x.userId for x in result.body.users] == [str(x['userId']) for x in body['users']]
        assert result.body.followUserTags == body.get('followUserTags', [])

    async def test_search_user(self, following_users_samples: SimpleNamespace):
        from src.utils.pixiv_api import PixivUser
        from src.utils.pixiv_api.helper import PixivParser

        # 搜索关键词动态取首个关注用户的昵称
        if not following_users_samples.samples:
            pytest.skip('Session 用户关注列表为空, 无法确定搜索关键词')
        nick = following_users_samples.samples[0].raw_user['body']['name']

        # 抓取原始 HTML, 解析结果与独立基准逐项比对
        url = f'{PixivUser._get_root_url()}/search/users'
        content = await PixivUser.get_resource_as_text(url=url, params={'nick': nick, 's_mode': 's_usr', 'p': 1})
        assert '__next' in content, 'unexpected page content, maybe not logged in or page structure changed'

        gt = _gt_user_search_page(content)
        if not gt['users']:
            pytest.skip(f'搜索用户 {nick!r} 无结果, 跳过页面解析比对')

        parsed = await PixivParser.parse_user_searching_result_page(content=content)
        assert parsed.search_name == gt['title']
        assert parsed.count == gt['count']
        assert len(parsed.users) == len(gt['users']), (
            f'parsed user count {len(parsed.users)} != ground truth {len(gt["users"])}'
        )
        for user in parsed.users:
            assert user.user_id in gt['users'], f'user_id {user.user_id} not found in page /users/ links'
            assert user.user_name == gt['users'][user.user_id], (
                f'user_name mismatch for {user.user_id}: {user.user_name!r} != {gt["users"][user.user_id]!r}'
            )
            # 作品预览图核验: 与 HTML 中该用户卡片内的 img 一致(动态加载导致两边都为空也是合法结果)
            assert user.illusts_thumb_urls == gt['thumbs'].get(user.user_id, []), (
                f'thumb urls mismatch for {user.user_id}: {user.illusts_thumb_urls} != {gt["thumbs"].get(user.user_id)}'
            )


@require_real_test
@pytest.mark.usefixtures('_throttle_requests')
class TestPixivision:
    """Pixivision 接口(真实请求 + 原始 HTML 核验)"""

    async def test_illustration_list(self, show_page: SimpleNamespace):
        gt = _gt_pixivision_show_page(show_page.content)
        assert gt, 'ground truth extraction found no cards, page structure changed?'

        parsed = show_page.parsed
        assert len(parsed.illustrations) == len(gt), (
            f'parsed count {len(parsed.illustrations)} != ground truth {len(gt)}'
        )
        for item, gt_item in zip(parsed.illustrations, gt):
            assert item.aid == gt_item['aid']
            assert item.title == gt_item['title']
            assert item.url == f'{show_page.root_url}{gt_item["href"]}'
            assert item.thumbnail == gt_item['thumbnail']
            assert item.all_tags_id == [x['id'] for x in gt_item['tags']]

    async def test_article_artwork_type(self, article_pages_sample: list[SimpleNamespace]):
        # 取导览页首篇特辑, 同一份 HTML 上比对解析结果与独立基准
        page = article_pages_sample[0]
        parsed = page.parsed

        gt = _gt_pixivision_article_page(page.content)
        assert parsed.title == gt['title']
        assert parsed.eyecatch_image == gt['eyecatch']
        # description 核验内容忠实性(忽略换行/空白分隔差异)
        assert ''.join(parsed.description.split()) == ''.join(gt['description'].split())
        assert len(parsed.artwork_list) == len(gt['artworks']), (
            f'parsed artworks {len(parsed.artwork_list)} != ground truth {len(gt["artworks"])}'
        )
        for item, gt_item in zip(parsed.artwork_list, gt['artworks']):
            assert gt_item['pid'] is not None
            assert item.artwork_id == gt_item['pid']
            assert item.artwork_url == gt_item['url']
            assert item.artwork_title == gt_item['title']
            assert item.artwork_user == gt_item['user']
            assert item.image_url == gt_item['image']

    async def test_article_collection_type(self, article_pages_sample: list[SimpleNamespace]):
        from src.utils.pixiv_api import Pixivision

        # 合集型特辑动态取样: 导览页前 10 篇中首篇正文为特辑卡片合集的文章
        root_url = Pixivision._get_root_url()
        sample_page = None
        for page in article_pages_sample:
            if _gt_pixivision_article_page(page.content)['collections']:
                sample_page = page
                break
        if sample_page is None:
            pytest.skip('当前导览页前 10 篇特辑均非合集型')

        gt = _gt_pixivision_article_page(sample_page.content)
        assert gt['collections'], '样本页面中未找到合集卡片, 页面结构可能已变化'

        parsed = sample_page.parsed

        # 文章基础信息与文章级 tag 核验
        assert parsed.title == gt['title']
        # description 核验内容忠实性(忽略换行/空白分隔差异)
        assert ''.join(parsed.description.split()) == ''.join(gt['description'].split())
        assert [x.tag_id for x in parsed.tags_list] == [x['id'] for x in gt['tags']]
        assert [x.tag_name for x in parsed.tags_list] == [x['name'] for x in gt['tags']]

        # 合集条目核验
        assert len(parsed.illustration_list) == len(gt['collections'])
        for sub, gt_sub in zip(parsed.illustration_list, gt['collections']):
            assert sub.aid == gt_sub['aid']
            assert sub.title == gt_sub['title']
            assert sub.url == f'{root_url}{gt_sub["href"]}'
            assert sub.thumbnail == gt_sub['thumbnail']
            assert sub.all_tags_id == [x['id'] for x in gt_sub['tags']]
            assert sub.all_tags_name == [x['name'] for x in gt_sub['tags']]

    async def test_download_eyecatch(self, article_pages_sample: list[SimpleNamespace]):
        from src.resource import TemporaryResource
        from src.utils.pixiv_api import Pixivision

        # 找一篇有头图的特辑并下载
        for page in article_pages_sample[:5]:
            if page.parsed.eyecatch_image is None:
                continue

            file = await Pixivision.download_article_eyecatch_image(
                article_data=page.parsed, save_folder=TemporaryResource('test_pixiv')
            )
            assert file.is_file, f'downloaded file not exists: {file}'
            assert file.file_size > 0, 'downloaded eyecatch image is empty'
            return

        pytest.skip('当前导览页前 5 篇特辑均无头图')


class TestPixivParser:
    """PixivParser 纯本地核验(无网络请求)"""

    def test_parse_pid_from_url(self):
        from src.utils.pixiv_api.helper import PixivParser

        # url 模式: 匹配完整 pixiv 链接
        assert PixivParser.parse_pid_from_url('https://www.pixiv.net/artworks/12345') == 12345
        assert PixivParser.parse_pid_from_url('https://www.pixiv.net/artworks/12345?utm_source=x') == 12345
        assert PixivParser.parse_pid_from_url('https://www.pixiv.net/artworks/12345/') == 12345
        assert PixivParser.parse_pid_from_url('https://www.pixiv.net/artworks/12345#comment') == 12345
        assert PixivParser.parse_pid_from_url('https://www.pixiv.net/i/12345') == 12345
        assert PixivParser.parse_pid_from_url('https://touch.pixiv.net/artworks/12345') == 12345
        assert PixivParser.parse_pid_from_url(
            'https://www.pixiv.net/member_illust.php?mode=medium&illust_id=678'
        ) == 678
        assert PixivParser.parse_pid_from_url(
            'https://www.pixiv.net/member_illust.php?illust_id=678&mode=m'
        ) == 678
        assert PixivParser.parse_pid_from_url(
            'https://www.pixiv.net/member_illust.php?mode=medium&illust_id=678#frag'
        ) == 678
        assert PixivParser.parse_pid_from_url('https://www.pixiv.net/users/12345') is None
        assert PixivParser.parse_pid_from_url('不是链接') is None
        # 域名边界: 形似域名不应识别
        assert PixivParser.parse_pid_from_url('https://evilpixiv.net/artworks/12345') is None
        assert PixivParser.parse_pid_from_url('https://pixiv.net.evil.com/artworks/12345') is None
        assert PixivParser.parse_pid_from_url(
            'https://www.pixiv.net.evil.com/member_illust.php?illust_id=678'
        ) is None

        # 文本模式: 匹配任何字符串中的 pixiv 链接
        assert PixivParser.parse_pid_from_url('看这个 https://www.pixiv.net/artworks/999 不错', url_mode=False) == 999
        assert PixivParser.parse_pid_from_url(
            '链接 https://www.pixiv.net/member_illust.php?mode=medium&illust_id=111', url_mode=False
        ) == 111
        assert PixivParser.parse_pid_from_url('没有链接', url_mode=False) is None
        assert PixivParser.parse_pid_from_url(
            '看这个 https://evilpixiv.net/artworks/999 不是 pixiv 链接', url_mode=False
        ) is None


def _make_ranking(page: int, ranks: list[int]):
    """离线构造 PixivRanking 模型(仅 page/rank 有实际意义, 其余字段为占位值)"""
    from src.utils.pixiv_api.model import PixivRanking

    contents = [
        {
            'title': f'title_{rank}',
            'date': '2026-09-23T00:00:00+09:00',
            'tags': [],
            'url': 'https://i.pximg.net/example.jpg',
            'illust_id': str(100000 + rank),
            'illust_type': '0',
            'illust_book_style': '0',
            'illust_page_count': '1',
            'width': 1000,
            'height': 1000,
            'user_id': '1',
            'user_name': 'user',
            'profile_img': 'https://i.pximg.net/profile.jpg',
            'rank': rank,
            'yes_rank': 0,
            'rating_count': 0,
            'view_count': 0,
            'illust_upload_timestamp': 1700000000,
            'attr': 'original',
            'is_masked': False,
            'is_bookmarked': False,
            'bookmarkable': True,
        }
        for rank in ranks
    ]
    return PixivRanking.model_validate({
        'content': 'illust',
        'contents': contents,
        'mode': 'daily',
        'page': page,
        'date': '20260923',
        'date_range_text': '',
        'prev': page > 1,
        'prev_date': False,
        'next': True,
        'next_date': False,
        'rank_total': 230,
    })


def _make_recommend(illust_ids: list[str | int], *, error: bool = False, message: str = ''):
    """离线构造 PixivIllustRecommend 模型(仅 id 有实际意义, 其余字段为占位值)"""
    from src.utils.pixiv_api.model import PixivIllustRecommend

    illusts = [
        {
            'id': pid,
            'title': f'title_{pid}',
            'illustType': 0,
            'aiType': 0,
            'xRestrict': 0,
            'restrict': 0,
            'description': '',
            'userId': '1',
            'userName': 'user',
            'width': 1000,
            'height': 1000,
            'pageCount': 1,
            'isBookmarkable': True,
        }
        for pid in illust_ids
    ]
    return PixivIllustRecommend.model_validate({
        'body': {'illusts': illusts, 'nextIds': []},
        'error': error,
        'message': message,
    })


class TestPixivModel:
    """数据模型纯本地核验(无网络请求)"""

    def test_get_ranking_full_page(self):
        # 整页(50 条): 页内首末名次可取, 页外及非法名次抛出
        ranking = _make_ranking(page=2, ranks=list(range(51, 101)))
        assert ranking.get_ranking(51).rank == 51
        assert ranking.get_ranking(100).rank == 100
        with pytest.raises(ValueError, match='Ranking num not in this page'):
            ranking.get_ranking(50)
        with pytest.raises(ValueError, match='Ranking num not in this page'):
            ranking.get_ranking(101)
        with pytest.raises(ValueError, match='Ranking num not in this page'):
            ranking.get_ranking(0)
        with pytest.raises(ValueError, match='Ranking num not in this page'):
            ranking.get_ranking(-1)

    def test_get_ranking_partial_last_page(self):
        # 末页不足整页(30 条, 名次 201-230): 以页内首条目 rank 为基准定位
        ranking = _make_ranking(page=5, ranks=list(range(201, 231)))
        assert ranking.get_ranking(201).rank == 201
        assert ranking.get_ranking(230).rank == 230
        with pytest.raises(ValueError, match='Ranking num not in this page'):
            ranking.get_ranking(200)
        with pytest.raises(ValueError, match='Ranking num not in this page'):
            ranking.get_ranking(231)

    def test_get_ranking_empty_contents(self):
        ranking = _make_ranking(page=1, ranks=[])
        with pytest.raises(ValueError, match='Ranking num not in this page'):
            ranking.get_ranking(1)

    def test_illust_recommend_illust_ids(self):
        # 多个作品: 保序返回, 与 body.illusts 逐项一致, 元素均为 str
        recommend = _make_recommend(['1001', '1002', '1003'])
        assert recommend.illust_ids == ['1001', '1002', '1003']
        assert recommend.illust_ids == [x.id for x in recommend.body.illusts]
        assert all(isinstance(x, str) for x in recommend.illust_ids)

    def test_illust_recommend_illust_ids_coerce_numeric_id(self):
        # 接口返回数字型 id: 由 coerce_numbers_to_str 统一转为 str
        recommend = _make_recommend([1001, 1002])
        assert recommend.illust_ids == ['1001', '1002']
        assert all(isinstance(x, str) for x in recommend.illust_ids)

    def test_illust_recommend_illust_ids_empty_and_error(self):
        # 空推荐与 error 响应(body 为空)均返回空列表而非抛出异常, 与 PixivBookmark.illust_ids 惯例一致
        assert _make_recommend([]).illust_ids == []
        assert _make_recommend([], error=True, message='not found').illust_ids == []
