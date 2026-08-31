"""
@Author         : Ailitonia
@Date           : 2026/08/30 22:24
@FileName       : test_artwork_collection
@Project        : omega-miya
@Description    : artwork_collection.py  数据库 CRUD 单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import random
import string
from collections.abc import AsyncGenerator, Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol

import pytest
from sqlalchemy.exc import NoResultFound

if TYPE_CHECKING:
    from src.database.internal.artwork_collection import ArtworkCollectionDAL


class TagsGeneratorProtocol(Protocol):
    def __call__(self, prefix: str = '', separator: str = ', ') -> str: ...


@pytest.fixture(scope='class')
async def test_random_id_generator() -> Callable[[], str]:
    def _generate_random_id() -> str:
        return ''.join(random.sample(string.ascii_letters + string.digits, k=8))

    return _generate_random_id


@pytest.fixture(scope='class')
async def test_random_tags_generator() -> TagsGeneratorProtocol:
    def _generate_random_tag() -> str:
        return ''.join(random.sample(string.ascii_letters + string.digits, k=8))

    def _generate_random_tags(prefix: str = '', separator: str = ', ') -> str:
        return separator.join(f'{prefix}{_generate_random_tag()}' for _ in range(8))

    return _generate_random_tags


@pytest.fixture(scope='class')
async def test_basic_artwork_kwargs_generator(test_random_id_generator) -> Callable[[], dict[str, Any]]:
    """测试用作品参数生成器, 默认满足 query_by_condition 的默认过滤条件 (classification=2, rating=0)"""

    def _generate_basic_artwork_kwargs() -> dict[str, Any]:
        return {
            'origin': f'test_origin',
            'aid': f'test_aid_{test_random_id_generator()}',
            'uid': f'test_uid_{test_random_id_generator()}',
            'uname': f'test_uname_{test_random_id_generator()}',
            'title': f'test_title_{test_random_id_generator()}',
            'classification': 2,
            'rating': 0,
            'width': 1920,
            'height': 1080,
            'url': f'https://example.com/artwork/{test_random_id_generator()}',
        }

    return _generate_basic_artwork_kwargs


@pytest.fixture(scope='class')
async def test_full_artwork_kwargs_generator(
        test_random_id_generator,
        test_random_tags_generator,
        test_basic_artwork_kwargs_generator,
) -> Callable[[], dict[str, Any]]:
    """测试用作品参数生成器, 补全可选参数, 默认满足 query_by_condition 的默认过滤条件 (classification=2, rating=0)"""

    def _generate_full_artwork_kwargs() -> dict[str, Any]:
        kwargs = test_basic_artwork_kwargs_generator()
        kwargs.update({
            'source': f'https://example.com/source/{test_random_id_generator()}',
            'cover_page': f'https://example.com/images/{test_random_id_generator()}',
            'raw_tags': test_random_tags_generator(),
            'description': ''.join(random.choices(string.ascii_letters + string.digits, k=1024)),
            'published_at': datetime(2020, 2, 12, 1, 0, 0)
        })
        return kwargs

    return _generate_full_artwork_kwargs


@pytest.fixture(scope='class')
async def test_artwork_hashtag_handler() -> Callable[[str], list[tuple[str, str | None]]]:
    """构造测试 #tag 形态的标签处理器"""

    def _handler(raw_tags: str) -> list[tuple[str, str | None]]:
        return [(tag.strip().lower(), None) for tag in raw_tags.split('#')]

    return _handler


@pytest.fixture(scope='class')
async def artwork_dal() -> AsyncGenerator['ArtworkCollectionDAL', None]:
    from src.database.internal.artwork_collection import ArtworkCollectionDAL

    async with ArtworkCollectionDAL.create() as dal:
        yield dal


class TestArtworkCollectionDAL:
    """ArtworkCollectionDAL CRUD 单元测试"""

    async def test_check_clear_table(self, artwork_dal) -> None:
        """清空数据表, 查回验证表行数为空"""
        await artwork_dal._clear_all()
        await artwork_dal.commit_session()

        assert await artwork_dal._count_artwork_all() == 0
        assert await artwork_dal._count_artwork_review_record_all() == 0
        assert await artwork_dal._count_artwork_tag_all() == 0
        assert await artwork_dal._count_artwork_with_tags_all() == 0

    async def test_clear_all_rollback(
            self,
            artwork_dal,
            test_basic_artwork_kwargs_generator,
    ) -> None:
        """_clear_all 不执行 commit, 外层事务 rollback 后数据应恢复"""
        await artwork_dal._clear_all()
        await artwork_dal.commit_session()

        await artwork_dal.add_artwork_update_exist(**test_basic_artwork_kwargs_generator())
        await artwork_dal.commit_session()

        await artwork_dal._clear_all()
        assert await artwork_dal._count_artwork_all() == 0

        await artwork_dal.rollback_session()
        assert await artwork_dal._count_artwork_all() == 1
    # ------------------------------------------------------------------ #
    # add_artwork_update_exist
    # ------------------------------------------------------------------ #

    async def test_add_new_with_tags(
            self,
            artwork_dal,
            test_basic_artwork_kwargs_generator,
    ) -> None:
        """新增带标签作品, 验证字段往返及标签解析 (去重/小写/去空标签)"""
        await artwork_dal._clear_all()
        await artwork_dal.commit_session()

        artwork_kwargs = test_basic_artwork_kwargs_generator()
        artwork_kwargs['raw_tags'] = 'Neko, nekomimi,,NEKO '
        result = await artwork_dal.add_artwork_update_exist(**artwork_kwargs)

        assert result.origin == 'test_origin'
        assert result.aid == artwork_kwargs['aid']
        assert result.uid == artwork_kwargs['uid']
        assert result.uname == artwork_kwargs['uname']
        assert result.title == artwork_kwargs['title']
        assert result.classification == artwork_kwargs['classification']
        assert result.rating == artwork_kwargs['rating']
        assert result.orientation == 1  # width > height 横图
        assert result.url == artwork_kwargs['url']
        assert result.raw_tags == 'Neko, nekomimi,,NEKO '
        assert sorted(tag.tag_name for tag in result.tags_name_artwork_had) == ['neko', 'nekomimi']

        assert await artwork_dal._count_artwork_all() == 1
        assert await artwork_dal._count_artwork_with_tags_all() == 2

    async def test_add_new_without_tags(
            self,
            artwork_dal,
            test_basic_artwork_kwargs_generator,
    ) -> None:
        """新增无标签作品, 验证标签列表为空且返回模型可正常校验"""
        await artwork_dal._clear_all()
        await artwork_dal.commit_session()

        artwork_kwargs = test_basic_artwork_kwargs_generator()
        result = await artwork_dal.add_artwork_update_exist(**artwork_kwargs)

        assert result.origin == 'test_origin'
        assert result.aid == artwork_kwargs['aid']
        assert result.raw_tags is None
        assert result.tags_name_artwork_had == []

        assert await artwork_dal._count_artwork_all() == 1

    async def test_add_new_with_empty_raw_tags(
            self,
            artwork_dal,
            test_basic_artwork_kwargs_generator,
    ) -> None:
        """raw_tags 为空字符串/仅分隔符时不应插入空标签行"""
        await artwork_dal._clear_all()
        await artwork_dal.commit_session()

        artwork_kwargs = test_basic_artwork_kwargs_generator()
        artwork_kwargs['raw_tags'] = ', ,'
        result = await artwork_dal.add_artwork_update_exist(**artwork_kwargs)

        assert result.origin == 'test_origin'
        assert result.aid == artwork_kwargs['aid']
        assert result.tags_name_artwork_had == []

    async def test_add_update_exist_updates_fields_and_rebuild_tags(
            self,
            artwork_dal,
            test_full_artwork_kwargs_generator,
    ) -> None:
        """相同 (origin, aid) 再次添加应更新字段 (含 url) 并重建 tag 关联"""
        await artwork_dal._clear_all()
        await artwork_dal.commit_session()

        artwork_kwargs = test_full_artwork_kwargs_generator()
        await artwork_dal.add_artwork_update_exist(**artwork_kwargs)

        artwork_kwargs.update({
            'uid': 'update_uid_v2',
            'uname': 'update_uname_v2',
            'title': 'update_title_v2',
            'url': 'https://example.com/artwork/update_uid_v2',
            'raw_tags': None,
            'width': 1080,
            'height': 1920,
        })

        result = await artwork_dal.add_artwork_update_exist(**artwork_kwargs)

        assert result.uid == 'update_uid_v2'
        assert result.uname == 'update_uname_v2'
        assert result.title == 'update_title_v2'
        assert result.url == 'https://example.com/artwork/update_uid_v2'
        assert result.orientation == -1  # width < height 竖图
        assert result.tags_name_artwork_had == []  # raw_tags 为 None 时同样重建关联, 即清空已有标签关联

        # 更新而非新增, 全表仍只有一行
        assert await artwork_dal._count_artwork_all() == 1
        assert await artwork_dal._count_artwork_with_tags_all() == 0  # tag 关联被清空

    async def test_add_update_exist_tag_handler(
            self,
            artwork_dal,
            test_basic_artwork_kwargs_generator,
            test_random_tags_generator,
    ) -> None:
        """使用自定义 tag_handler 解析标签"""
        await artwork_dal._clear_all()
        await artwork_dal.commit_session()

        artwork_kwargs = test_basic_artwork_kwargs_generator()
        artwork_kwargs.update({
            'raw_tags': 'foo bar|baz qux',
            'tag_handler': lambda raw: [(x.strip(), None) for x in raw.split('|')],
        })
        result = await artwork_dal.add_artwork_update_exist(**artwork_kwargs)

        assert sorted(tag.tag_name for tag in result.tags_name_artwork_had) == ['baz qux', 'foo bar']

    async def test_add_update_exist_tag_handler_dedup(
            self,
            artwork_dal,
            test_basic_artwork_kwargs_generator,
            test_random_tags_generator,
    ) -> None:
        """tag_handler 返回同名不同别名的标签时按 tag_name 去重, 不触发关联表主键冲突"""
        await artwork_dal._clear_all()
        await artwork_dal.commit_session()

        artwork_kwargs = test_basic_artwork_kwargs_generator()
        artwork_kwargs.update({
            'raw_tags': 'dup_tag',
            'tag_handler': lambda raw: [(raw, 'alt_1'), (raw, 'alt_2')],
        })

        result = await artwork_dal.add_artwork_update_exist(**artwork_kwargs)

        assert [tag.tag_name for tag in result.tags_name_artwork_had] == ['dup_tag']

    # ------------------------------------------------------------------ #
    # add_artwork_ignore_exist
    # ------------------------------------------------------------------ #

    async def test_add_ignore_exist_insert_new(
            self,
            artwork_dal,
            test_basic_artwork_kwargs_generator,
    ) -> None:
        """插入不存在的新作品, 验证为插入行为"""
        await artwork_dal._clear_all()
        await artwork_dal.commit_session()

        artwork_kwargs = test_basic_artwork_kwargs_generator()
        artwork_kwargs['raw_tags'] = 'Neko, nekomimi,,NEKO '
        result = await artwork_dal.add_artwork_update_exist(**artwork_kwargs)

        assert result.origin == 'test_origin'
        assert result.aid == artwork_kwargs['aid']
        assert result.uid == artwork_kwargs['uid']
        assert result.uname == artwork_kwargs['uname']
        assert result.title == artwork_kwargs['title']
        assert result.classification == artwork_kwargs['classification']
        assert result.rating == artwork_kwargs['rating']
        assert result.orientation == 1  # width > height 横图
        assert result.url == artwork_kwargs['url']
        assert result.raw_tags == 'Neko, nekomimi,,NEKO '
        assert sorted(tag.tag_name for tag in result.tags_name_artwork_had) == ['neko', 'nekomimi']

        assert await artwork_dal._count_artwork_all() == 1
        assert await artwork_dal._count_artwork_with_tags_all() == 2

    async def test_add_ignore_exist(
            self,
            artwork_dal,
            test_full_artwork_kwargs_generator,
    ) -> None:
        """相同 (origin, aid) 再次添加应忽略, 已有数据保持不变"""
        await artwork_dal._clear_all()
        await artwork_dal.commit_session()

        artwork_kwargs = test_full_artwork_kwargs_generator()
        await artwork_dal.add_artwork_ignore_exist(**artwork_kwargs)

        update_kwargs = artwork_kwargs.copy()
        update_kwargs.update({
            'uid': 'update_uid_v2',
            'uname': 'update_uname_v2',
            'title': 'update_title_v2',
            'url': 'https://example.com/artwork/update_uid_v2',
            'raw_tags': None,
            'width': 1080,
            'height': 1920,
        })

        result = await artwork_dal.add_artwork_ignore_exist(**artwork_kwargs)

        assert result.uid == artwork_kwargs['uid']
        assert result.uname == artwork_kwargs['uname']
        assert result.title == artwork_kwargs['title']
        assert result.orientation == 1  # width > height 横图
        assert result.url == artwork_kwargs['url']

        assert await artwork_dal._count_artwork_all() == 1
        assert await artwork_dal._count_artwork_with_tags_all() == 8  # tag 关联未被清空

    # ------------------------------------------------------------------ #
    # query_unique
    # ------------------------------------------------------------------ #

    async def test_query_unique_not_found(self, artwork_dal) -> None:
        """查询不存在的作品, 预期 NoResultFound"""
        await artwork_dal._clear_all()
        await artwork_dal.commit_session()

        with pytest.raises(NoResultFound):
            await artwork_dal.query_unique('nonexistent_origin', 'nonexistent_aid')

    # ------------------------------------------------------------------ #
    # query_by_condition
    # ------------------------------------------------------------------ #

    async def test_query_by_condition_tag_keyword(
            self,
            artwork_dal,
            test_basic_artwork_kwargs_generator,
    ) -> None:
        """关键词搜索仅命中作品自身关联的标签, 且结果无重复行"""
        await artwork_dal._clear_all()
        await artwork_dal.commit_session()

        # a1 关联两个均含 neko 的标签, 用于验证结果去重
        a1_kwargs = test_basic_artwork_kwargs_generator()
        a1_kwargs['raw_tags'] = 'neko,nekomimi'
        await artwork_dal.add_artwork_update_exist(**a1_kwargs)

        a2_kwargs = test_basic_artwork_kwargs_generator()
        a2_kwargs['title'] = 'inu_girl'
        await artwork_dal.add_artwork_update_exist(**a2_kwargs)

        result = await artwork_dal.query_by_condition('test_origin', keywords=['neko'], size=10)
        assert [item.aid for item in result] == [a1_kwargs['aid']]

        result = await artwork_dal.query_by_condition('test_origin', keywords=['inu'], size=10)
        assert [item.aid for item in result] == [a2_kwargs['aid']]

        result = await artwork_dal.query_by_condition('test_origin', keywords=['nomatch'], size=10)
        assert result == []

    async def test_query_by_condition_multi_keywords_and(
            self,
            artwork_dal,
            test_basic_artwork_kwargs_generator,
    ) -> None:
        """多关键词为 AND 语义, 每个关键词须各自命中标题/用户名/标签中的任一字段"""
        await artwork_dal._clear_all()
        await artwork_dal.commit_session()

        a1_kwargs = test_basic_artwork_kwargs_generator()
        a1_kwargs['aid'] = '1001'
        a1_kwargs['title'] = 'alpha_art'
        a1_kwargs['raw_tags'] = 'foo'
        await artwork_dal.add_artwork_update_exist(**a1_kwargs)

        a2_kwargs = test_basic_artwork_kwargs_generator()
        a2_kwargs['aid'] = '1002'
        a2_kwargs['title'] = 'beta_art'
        a2_kwargs['raw_tags'] = 'bar'
        await artwork_dal.add_artwork_update_exist(**a2_kwargs)

        a3_kwargs = test_basic_artwork_kwargs_generator()
        a3_kwargs['aid'] = '1003'
        a3_kwargs['title'] = 'gamma_art'
        a3_kwargs['raw_tags'] = 'foo,bar'
        await artwork_dal.add_artwork_update_exist(**a3_kwargs)

        # 仅标签命中
        result = await artwork_dal.query_by_condition('test_origin', ['foo'], size=10, order_mode='aid_desc')
        assert [item.aid for item in result] == ['1003', '1001']

        # 仅标题命中
        result = await artwork_dal.query_by_condition('test_origin', ['alpha'], size=10, order_mode='aid_desc')
        assert [item.aid for item in result] == ['1001']

        # 多关键词与关系: 需同时命中
        result = await artwork_dal.query_by_condition('test_origin', ['foo', 'bar'], size=10, order_mode='aid_desc')
        assert [item.aid for item in result] == ['1003']

        # 多关键词与关系: 无同时命中项
        result = await artwork_dal.query_by_condition('test_origin', ['alpha', 'bar'], size=10, order_mode='aid_desc')
        assert result == []

        # 无命中关键词
        result = await artwork_dal.query_by_condition('test_origin', ['nomatch'], size=10, order_mode='aid_desc')
        assert result == []

    async def test_query_by_condition_no_keywords(
            self,
            artwork_dal,
            test_basic_artwork_kwargs_generator,
    ) -> None:
        """无关键词时不应附加关键词过滤条件, 空 origin 序列应匹配所有来源, 返回全部满足分类/分级条件的作品"""
        await artwork_dal._clear_all()
        await artwork_dal.commit_session()

        a1_kwargs = test_basic_artwork_kwargs_generator()
        await artwork_dal.add_artwork_update_exist(**a1_kwargs)

        a2_kwargs = test_basic_artwork_kwargs_generator()
        await artwork_dal.add_artwork_update_exist(**a2_kwargs)

        a3_kwargs = test_basic_artwork_kwargs_generator()
        a3_kwargs['origin'] = 'test_another_origin'
        await artwork_dal.add_artwork_update_exist(**a3_kwargs)

        result = await artwork_dal.query_by_condition('test_origin', keywords=None, size=10)
        assert {item.aid for item in result} == {a1_kwargs['aid'], a2_kwargs['aid']}

        result = await artwork_dal.query_by_condition(None, keywords=None, size=10)
        assert {item.aid for item in result} == {a1_kwargs['aid'], a2_kwargs['aid'], a3_kwargs['aid']}

    async def test_query_by_condition_acc_mode(
            self,
            artwork_dal,
            test_basic_artwork_kwargs_generator,
    ) -> None:
        """精确搜索模式, 标题/用户名/标签名精确匹配"""
        await artwork_dal._clear_all()
        await artwork_dal.commit_session()

        artwork_kwargs = test_basic_artwork_kwargs_generator()
        artwork_kwargs['aid'] = 'acc1001'
        artwork_kwargs['title'] = 'ExactTitle'
        artwork_kwargs['uname'] = 'exact_uname'
        artwork_kwargs['raw_tags'] = 'nekomimi'
        await artwork_dal.add_artwork_update_exist(**artwork_kwargs)

        result = await artwork_dal.query_by_condition('test_origin', keywords=['ExactTitle'], size=10, acc_mode=True)
        assert [item.aid for item in result] == ['acc1001']

        result = await artwork_dal.query_by_condition('test_origin', keywords=['exact_uname'], size=10, acc_mode=True)
        assert [item.aid for item in result] == ['acc1001']

        result = await artwork_dal.query_by_condition('test_origin', keywords=['nekomimi'], size=10, acc_mode=True)
        assert [item.aid for item in result] == ['acc1001']

        # 非精确匹配不应命中
        result = await artwork_dal.query_by_condition('test_origin', keywords=['Exact'], size=10, acc_mode=True)
        assert result == []
        result = await artwork_dal.query_by_condition('test_origin', keywords=['neko'], size=10, acc_mode=True)
        assert result == []

    async def test_query_by_condition_ratio(
            self,
            artwork_dal,
            test_basic_artwork_kwargs_generator,
    ) -> None:
        """按图片长宽类型筛选"""
        await artwork_dal._clear_all()
        await artwork_dal.commit_session()

        a1_kwargs = test_basic_artwork_kwargs_generator()
        a1_kwargs['aid'] = '1001'
        a1_kwargs['width'] = 320
        a1_kwargs['height'] = 640
        await artwork_dal.add_artwork_update_exist(**a1_kwargs)

        a2_kwargs = test_basic_artwork_kwargs_generator()
        a2_kwargs['aid'] = '1002'
        a2_kwargs['width'] = 1920
        a2_kwargs['height'] = 1080
        await artwork_dal.add_artwork_update_exist(**a2_kwargs)

        a3_kwargs = test_basic_artwork_kwargs_generator()
        a3_kwargs['aid'] = '1003'
        a3_kwargs['width'] = 512
        a3_kwargs['height'] = 512
        await artwork_dal.add_artwork_update_exist(**a3_kwargs)

        result = await artwork_dal.query_by_condition('test_origin', None, size=10, ratio=-1)
        assert [item.aid for item in result] == ['1001']

        result = await artwork_dal.query_by_condition('test_origin', None, size=10, ratio=1)
        assert [item.aid for item in result] == ['1002']

        result = await artwork_dal.query_by_condition('test_origin', None, size=10, ratio=0)
        assert [item.aid for item in result] == ['1003']

    async def test_query_by_condition_invalid_params(self, artwork_dal) -> None:
        """非法参数校验"""
        with pytest.raises(ValueError, match='classification_min must be less than classification_max'):
            await artwork_dal.query_by_condition(None, None, classification_min=3, classification_max=2)

        with pytest.raises(ValueError, match='rating_min must be less than rating_max'):
            await artwork_dal.query_by_condition(None, None, rating_min=1, rating_max=0)

        with pytest.raises(ValueError, match='page must be a positive integer'):
            await artwork_dal.query_by_condition(None, None, page=0)

        with pytest.raises(ValueError, match='size must be a positive integer'):
            await artwork_dal.query_by_condition(None, None, size=0)

    # ------------------------------------------------------------------ #
    # query_classification_statistic / query_rating_statistic
    # ------------------------------------------------------------------ #

    async def test_query_classification_statistic(
            self,
            artwork_dal,
            test_basic_artwork_kwargs_generator,
    ) -> None:
        """按分类统计, 验证各分类桶计数及总数"""
        await artwork_dal._clear_all()
        await artwork_dal.commit_session()

        a1_kwargs = test_basic_artwork_kwargs_generator()
        a1_kwargs['aid'] = '1001'
        a1_kwargs['classification'] = 0
        a1_kwargs['raw_tags'] = 'neko'
        await artwork_dal.add_artwork_update_exist(**a1_kwargs)

        a2_kwargs = test_basic_artwork_kwargs_generator()
        a2_kwargs['aid'] = '1002'
        a2_kwargs['classification'] = 1
        await artwork_dal.add_artwork_update_exist(**a2_kwargs)

        a3_kwargs = test_basic_artwork_kwargs_generator()
        a3_kwargs['aid'] = '1003'
        a3_kwargs['classification'] = 2
        await artwork_dal.add_artwork_update_exist(**a3_kwargs)

        a4_kwargs = test_basic_artwork_kwargs_generator()
        a4_kwargs['aid'] = '1004'
        a4_kwargs['classification'] = 2
        await artwork_dal.add_artwork_update_exist(**a4_kwargs)

        a5_kwargs = test_basic_artwork_kwargs_generator()
        a5_kwargs['aid'] = '1005'
        a5_kwargs['classification'] = 3
        a5_kwargs['raw_tags'] = 'neko, nekomimi'
        await artwork_dal.add_artwork_update_exist(**a5_kwargs)

        a6_kwargs = test_basic_artwork_kwargs_generator()
        a6_kwargs['aid'] = '1006'
        a6_kwargs['classification'] = -10086
        await artwork_dal.add_artwork_update_exist(**a6_kwargs)

        result = await artwork_dal.query_classification_statistic('test_origin')

        assert result.unused == 1
        assert result.unclassified == 1
        assert result.ai_generated == 1
        assert result.automatic == 2
        assert result.confirmed == 1
        assert result.total == 6

        # 关键词仅命中标签作品
        statistic = await artwork_dal.query_classification_statistic('test_origin', keywords=['neko'])
        assert statistic.total == 2
        assert statistic.unclassified == 1
        assert statistic.confirmed == 1

        statistic = await artwork_dal.query_classification_statistic('test_origin', keywords=['nekomimi'])
        assert statistic.total == 1
        assert statistic.unclassified == 0
        assert statistic.confirmed == 1

    async def test_query_rating_statistic(
            self,
            artwork_dal,
            test_basic_artwork_kwargs_generator,
    ) -> None:
        """按分级统计, 验证各分级桶计数及总数"""
        await artwork_dal._clear_all()
        await artwork_dal.commit_session()

        a1_kwargs = test_basic_artwork_kwargs_generator()
        a1_kwargs['aid'] = '1001'
        a1_kwargs['rating'] = 0
        a1_kwargs['raw_tags'] = 'neko'
        await artwork_dal.add_artwork_update_exist(**a1_kwargs)

        a2_kwargs = test_basic_artwork_kwargs_generator()
        a2_kwargs['aid'] = '1002'
        a2_kwargs['rating'] = 0
        await artwork_dal.add_artwork_update_exist(**a2_kwargs)

        a3_kwargs = test_basic_artwork_kwargs_generator()
        a3_kwargs['aid'] = '1003'
        a3_kwargs['rating'] = 1
        await artwork_dal.add_artwork_update_exist(**a3_kwargs)

        a4_kwargs = test_basic_artwork_kwargs_generator()
        a4_kwargs['aid'] = '1004'
        a4_kwargs['rating'] = 2
        await artwork_dal.add_artwork_update_exist(**a4_kwargs)

        a5_kwargs = test_basic_artwork_kwargs_generator()
        a5_kwargs['aid'] = '1005'
        a5_kwargs['rating'] = 3
        a5_kwargs['raw_tags'] = 'neko, nekomimi'
        await artwork_dal.add_artwork_update_exist(**a5_kwargs)

        a6_kwargs = test_basic_artwork_kwargs_generator()
        a6_kwargs['aid'] = '1006'
        a6_kwargs['rating'] = -1
        await artwork_dal.add_artwork_update_exist(**a6_kwargs)

        result = await artwork_dal.query_rating_statistic('test_origin')

        assert result.unknown == 1
        assert result.general == 2
        assert result.sensitive == 1
        assert result.questionable == 1
        assert result.explicit == 1
        assert result.total == 6

        # 关键词仅命中标签作品
        statistic = await artwork_dal.query_rating_statistic('test_origin', keywords=['neko'])
        assert statistic.total == 2
        assert statistic.general == 1
        assert statistic.explicit == 1

        statistic = await artwork_dal.query_rating_statistic('test_origin', keywords=['nekomimi'])
        assert statistic.total == 1
        assert statistic.general == 0
        assert statistic.explicit == 1

    # ------------------------------------------------------------------ #
    # query_exists_aids / query_not_exists_aids
    # ------------------------------------------------------------------ #

    async def test_query_exists_and_not_exists_aids(
            self,
            artwork_dal,
            test_basic_artwork_kwargs_generator,
    ) -> None:
        """存在性查询, 验证存在/不存在及分类分级过滤"""
        await artwork_dal._clear_all()
        await artwork_dal.commit_session()

        a1_kwargs = test_basic_artwork_kwargs_generator()
        a1_kwargs['aid'] = '1001'
        a1_kwargs['classification'] = 2
        await artwork_dal.add_artwork_update_exist(**a1_kwargs)

        a2_kwargs = test_basic_artwork_kwargs_generator()
        a2_kwargs['aid'] = '1002'
        a2_kwargs['classification'] = 3
        await artwork_dal.add_artwork_update_exist(**a2_kwargs)

        exists = await artwork_dal.query_exists_aids('test_origin', ['1001', '1002', '1999'])
        assert sorted(exists) == ['1001', '1002']

        exists = await artwork_dal.query_exists_aids('test_origin', ['1001', '1002'], filter_classification=2)
        assert exists == ['1001']

        not_exists = await artwork_dal.query_not_exists_aids('test_origin', ['1001', '1999'])
        assert not_exists == ['1999']

        not_exists = await artwork_dal.query_not_exists_aids(
            'test_origin', ['1001', '1002'], exclude_classification=2,
        )
        assert not_exists == ['1002']

    # ------------------------------------------------------------------ #
    # query_user_all_artworks / query_user_all_aids
    # ------------------------------------------------------------------ #

    async def test_query_user_all_artworks(
            self,
            artwork_dal,
            test_basic_artwork_kwargs_generator,
    ) -> None:
        """按 uid/uname 查询用户作品, 同时提供时为 AND 语义, 均不提供预期 ValueError"""
        await artwork_dal._clear_all()
        await artwork_dal.commit_session()

        a1_kwargs = test_basic_artwork_kwargs_generator()
        a1_kwargs['aid'] = '1001'
        a1_kwargs['uid'] = 'uid_1'
        a1_kwargs['uname'] = 'uname_1'
        await artwork_dal.add_artwork_update_exist(**a1_kwargs)

        a2_kwargs = test_basic_artwork_kwargs_generator()
        a2_kwargs['aid'] = '1002'
        a2_kwargs['uid'] = 'uid_1'
        a2_kwargs['uname'] = 'uname_2'
        await artwork_dal.add_artwork_update_exist(**a2_kwargs)

        a3_kwargs = test_basic_artwork_kwargs_generator()
        a3_kwargs['aid'] = '1003'
        a3_kwargs['uid'] = 'uid_2'
        a3_kwargs['uname'] = 'uname_1'
        await artwork_dal.add_artwork_update_exist(**a3_kwargs)

        by_uid = await artwork_dal.query_user_all_artworks('test_origin', uid='uid_1')
        assert sorted(item.aid for item in by_uid) == ['1001', '1002']

        by_uname = await artwork_dal.query_user_all_artworks('test_origin', uname='uname_1')
        assert sorted(item.aid for item in by_uname) == ['1001', '1003']

        by_both = await artwork_dal.query_user_all_artworks('test_origin', uid='uid_1', uname='uname_1')
        assert [item.aid for item in by_both] == ['1001']

        aids = await artwork_dal.query_user_all_aids('test_origin', uid='uid_1')
        assert sorted(aids) == ['1001', '1002']

        with pytest.raises(ValueError, match='need at least one of the uid and uname parameters'):
            await artwork_dal.query_user_all_artworks('test_origin')

    # ------------------------------------------------------------------ #
    # add_artwork_review_record
    # ------------------------------------------------------------------ #

    async def test_add_artwork_review_record(
            self,
            artwork_dal,
            test_basic_artwork_kwargs_generator,
    ) -> None:
        """为已存在作品插入评审记录, 验证字段及关联作品"""
        await artwork_dal._clear_all()
        await artwork_dal.commit_session()

        artwork_kwargs = test_basic_artwork_kwargs_generator()
        await artwork_dal.add_artwork_update_exist(**artwork_kwargs)

        result = await artwork_dal.add_artwork_review_record(
            origin=artwork_kwargs['origin'],
            aid=artwork_kwargs['aid'],
            review_timestamp=1000000000,
            review_classification=3,
            review_rating=1,
            review_from='test_reviewer',
            review_info='test review info',
        )
        await artwork_dal.commit_session()

        assert result.review_timestamp == 1000000000
        assert result.review_classification == 3
        assert result.review_rating == 1
        assert result.review_from == 'test_reviewer'
        assert result.review_info == 'test review info'
        assert result.review_record_parent_artwork.aid == artwork_kwargs['aid']

    async def test_add_artwork_review_record_not_found(self, artwork_dal) -> None:
        """为不存在的作品插入评审记录, 预期 NoResultFound"""
        await artwork_dal._clear_all()
        await artwork_dal.commit_session()

        with pytest.raises(NoResultFound):
            await artwork_dal.add_artwork_review_record(
                origin='nonexistent_origin',
                aid='nonexistent_aid',
                review_timestamp=1000000000,
                review_classification=3,
                review_rating=1,
                review_from='test_reviewer',
                review_info='test review info',
            )

    # ------------------------------------------------------------------ #
    # delete
    # ------------------------------------------------------------------ #

    async def test_delete(
            self,
            artwork_dal,
            test_basic_artwork_kwargs_generator,
    ) -> None:
        """删除作品后查询应抛出 NoResultFound"""
        await artwork_dal._clear_all()
        await artwork_dal.commit_session()

        artwork_kwargs = test_basic_artwork_kwargs_generator()
        await artwork_dal.add_artwork_update_exist(**artwork_kwargs)
        assert await artwork_dal._count_artwork_all() == 1

        await artwork_dal.delete('test_origin', artwork_kwargs['aid'])
        await artwork_dal.commit_session()

        # 删除不存在的作品不抛异常
        await artwork_dal.delete('test_origin', 'nonexistent_aid')
        await artwork_dal.commit_session()

        assert await artwork_dal._count_artwork_all() == 0
        with pytest.raises(NoResultFound):
            await artwork_dal.query_unique('test_origin', artwork_kwargs['aid'])

    # ------------------------------------------------------------------ #
    # aid 数值感知排序
    # ------------------------------------------------------------------ #

    async def test_aid_natural_ordering(
            self,
            artwork_dal,
            test_basic_artwork_kwargs_generator,
    ) -> None:
        """纯数字 aid 按数值感知顺序排序, 而非字典序"""
        await artwork_dal._clear_all()
        await artwork_dal.commit_session()

        a1_kwargs = test_basic_artwork_kwargs_generator()
        a1_kwargs['aid'] = '8'
        a1_kwargs['uid'] = '99'
        await artwork_dal.add_artwork_update_exist(**a1_kwargs)

        a2_kwargs = test_basic_artwork_kwargs_generator()
        a2_kwargs['aid'] = '9'
        a2_kwargs['uid'] = '99'
        await artwork_dal.add_artwork_update_exist(**a2_kwargs)

        a3_kwargs = test_basic_artwork_kwargs_generator()
        a3_kwargs['aid'] = '10'
        a3_kwargs['uid'] = '100'
        await artwork_dal.add_artwork_update_exist(**a3_kwargs)

        asc_result = await artwork_dal.query_by_condition('test_origin', keywords=None, size=10, order_mode='aid')
        assert [item.aid for item in asc_result] == ['8', '9', '10']

        desc_result = await artwork_dal.query_by_condition(
            'test_origin', keywords=None, size=10, order_mode='aid_desc'
        )
        assert [item.aid for item in desc_result] == ['10', '9', '8']

        user_aids = await artwork_dal.query_user_all_aids('test_origin', uid='99')
        assert user_aids == ['9', '8']

        exists = await artwork_dal.query_exists_aids('test_origin', ['8', '9', '10'])
        assert exists == ['10', '9', '8']

        not_exists = await artwork_dal.query_not_exists_aids('test_origin', ['8', '9', '10', '11', '101'])
        assert not_exists == ['101', '11']
