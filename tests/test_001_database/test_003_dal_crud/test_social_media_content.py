"""
@Author         : Ailitonia
@Date           : 2026/9/2 22:45
@FileName       : test_social_media_content
@Project        : omega-miya
@Description    : social_media_content.py 数据库 CRUD 单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

import pytest
from sqlalchemy.exc import IntegrityError, NoResultFound

from tests.test_001_database.test_003_dal_crud.conftest import define_dal_fixtures
from tests.utils import unique_test_id

if TYPE_CHECKING:
    from src.database.internal.social_media_content import SocialMediaContentDAL

smc_dal, _clean_table = define_dal_fixtures(
    'src.database.internal.social_media_content.SocialMediaContentDAL', 'smc_dal',
)


async def _add_smc_records(smc_dal: 'SocialMediaContentDAL', *records: tuple[str, str, str, str]) -> None:
    """批量播种社交内容记录, 每条为 (source, m_type, m_id, m_uid), title 按播种序号占位 (t1/t2/...)"""
    for index, (source, m_type, m_id, m_uid) in enumerate(records, start=1):
        await smc_dal.add(
            source=source,
            m_type=m_type,
            m_id=m_id,
            m_uid=m_uid,
            title=f't{index}',
            raw_data={},
        )


@pytest.fixture(scope='class')
def test_smc_source() -> str:
    return unique_test_id('TEST_SMC_SOURCE')


@pytest.fixture(scope='class')
def test_smc_m_type() -> str:
    return unique_test_id('TEST_SMC_M_TYPE')


@pytest.fixture(scope='class')
def test_smc_m_id() -> str:
    return unique_test_id('TEST_SMC_M_ID')


@pytest.fixture(scope='class')
def test_smc_m_uid() -> str:
    return unique_test_id('TEST_SMC_M_UID')


@pytest.fixture(scope='class')
def test_smc_title() -> str:
    return unique_test_id('TEST_SMC_TITLE')


@pytest.fixture(scope='class')
def test_smc_content() -> str:
    return unique_test_id('TEST_SMC_CONTENT')


@pytest.fixture(scope='class')
def test_content_raw_data(
        test_smc_source: str,
        test_smc_m_type: str,
        test_smc_m_id: str,
        test_smc_m_uid: str,
        test_smc_title: str,
        test_smc_content: str,
) -> dict[str, Any]:
    return {
        'id': test_smc_m_id,
        'type': test_smc_m_type,
        'uid': test_smc_m_uid,
        'content': {
            'title': test_smc_title,
            'body': test_smc_content,
        },
        'source': test_smc_source,
    }


class TestSocialMediaContentDAL:
    """SocialMediaContentDAL CRUD 单元测试"""

    # ------------------------------------------------------------------ #
    # add
    # ------------------------------------------------------------------ #

    async def test_add_basic(
            self,
            smc_dal,
            test_smc_source,
            test_smc_m_type,
            test_smc_m_id,
            test_smc_m_uid,
            test_smc_title,
            test_content_raw_data,
            test_smc_content,
    ) -> None:
        """插入一条记录, 验证所有字段正确 (含 JSON raw_data 往返)"""
        published = datetime(2026, 1, 1, 12, 0, 0)
        result = await smc_dal.add(
            source=test_smc_source,
            m_type=test_smc_m_type,
            m_id=test_smc_m_id,
            m_uid=test_smc_m_uid,
            title=test_smc_title,
            raw_data=test_content_raw_data,
            content=test_smc_content,
            ref_content='ref content text',
            published_at=published,
        )
        await smc_dal.commit_session()

        assert result.source == test_smc_source
        assert result.m_type == test_smc_m_type
        assert result.m_id == test_smc_m_id
        assert result.m_uid == test_smc_m_uid
        assert result.title == test_smc_title
        assert result.raw_data == test_content_raw_data
        assert result.content == test_smc_content
        assert result.ref_content == 'ref content text'
        assert result.published_at == published

    async def test_add_without_optional(
            self,
            smc_dal,
            test_smc_source,
            test_smc_m_type,
            test_smc_m_id,
            test_smc_m_uid,
            test_smc_title,
            test_content_raw_data,
    ) -> None:
        """content/ref_content/published_at 均为 None 验证"""
        result = await smc_dal.add(
            source=test_smc_source,
            m_type=test_smc_m_type,
            m_id=test_smc_m_id,
            m_uid=test_smc_m_uid,
            title=test_smc_title,
            raw_data=test_content_raw_data,
        )
        await smc_dal.commit_session()

        assert result.content is None
        assert result.ref_content is None
        assert result.published_at is None

    async def test_add_title_truncated(
            self,
            smc_dal,
            test_smc_source,
            test_smc_m_type,
            test_smc_m_id,
            test_smc_m_uid,
            test_content_raw_data,
    ) -> None:
        """title 超过 255 字符被截断为 255"""
        long_title = 'T' * 300
        result = await smc_dal.add(
            source=test_smc_source,
            m_type=test_smc_m_type,
            m_id=test_smc_m_id,
            m_uid=test_smc_m_uid,
            title=long_title,
            raw_data=test_content_raw_data,
        )
        await smc_dal.commit_session()

        assert len(result.title) == 255
        assert result.title == long_title[:255]

    async def test_add_json_roundtrip(
            self,
            smc_dal,
            test_smc_source,
            test_smc_m_type,
            test_smc_m_id,
            test_smc_m_uid,
            test_smc_title,
    ) -> None:
        """嵌套 dict raw_data 往返完整"""
        nested_raw = {
            'meta': {'level1': {'level2': {'deep': 'value'}}, 'nums': [1, 2, 3]},
            'tags': ['a', 'b', 'c'],
            'count': 42,
        }
        await smc_dal.add(
            source=test_smc_source,
            m_type=test_smc_m_type,
            m_id=test_smc_m_id,
            m_uid=test_smc_m_uid,
            title=test_smc_title,
            raw_data=nested_raw,
        )
        await smc_dal.commit_session()

        queried = await smc_dal.query_unique(test_smc_source, test_smc_m_type, test_smc_m_id)
        assert queried.raw_data == nested_raw

    async def test_add_duplicate_raises(
            self,
            smc_dal,
            test_smc_source,
            test_smc_m_type,
            test_smc_m_id,
            test_smc_m_uid,
            test_smc_title,
            test_content_raw_data,
    ) -> None:
        """相同 (source, m_type, m_id) 插入两次, 预期 IntegrityError"""
        await smc_dal.add(
            source=test_smc_source,
            m_type=test_smc_m_type,
            m_id=test_smc_m_id,
            m_uid=test_smc_m_uid,
            title=test_smc_title,
            raw_data=test_content_raw_data,
        )
        await smc_dal.commit_session()

        with pytest.raises(IntegrityError):
            await smc_dal.add(
                source=test_smc_source,
                m_type=test_smc_m_type,
                m_id=test_smc_m_id,
                m_uid='another_uid',
                title='another title',
                raw_data={},
            )

        # 回滚到正常状态
        await smc_dal.db_session.rollback()

        queried = await smc_dal.query_unique(test_smc_source, test_smc_m_type, test_smc_m_id)
        assert queried.title == test_smc_title
        assert queried.raw_data == test_content_raw_data

    # ------------------------------------------------------------------ #
    # query_unique
    # ------------------------------------------------------------------ #

    async def test_query_unique_normal(
            self,
            smc_dal,
            test_smc_source,
            test_smc_m_type,
            test_smc_m_id,
            test_smc_m_uid,
            test_smc_title,
            test_content_raw_data,
    ) -> None:
        """插入后按 (source, m_type, m_id) 查回验证字段"""
        await smc_dal.add(
            source=test_smc_source,
            m_type=test_smc_m_type,
            m_id=test_smc_m_id,
            m_uid=test_smc_m_uid,
            title=test_smc_title,
            raw_data=test_content_raw_data,
        )
        await smc_dal.commit_session()

        result = await smc_dal.query_unique(test_smc_source, test_smc_m_type, test_smc_m_id)
        assert result.source == test_smc_source
        assert result.m_type == test_smc_m_type
        assert result.m_id == test_smc_m_id
        assert result.m_uid == test_smc_m_uid
        assert result.title == test_smc_title
        assert result.raw_data == test_content_raw_data

    async def test_query_unique_not_found(self, smc_dal) -> None:
        """查询不存在的记录, 预期 NoResultFound"""
        with pytest.raises(NoResultFound):
            await smc_dal.query_unique('nonexistent_source', 'nonexistent_type', 'nonexistent_id')

    # ------------------------------------------------------------------ #
    # query_source_all
    # ------------------------------------------------------------------ #

    async def test_query_source_all_by_source(self, smc_dal) -> None:
        """仅按 source 过滤 (不同 m_type 记录混合)"""
        await _add_smc_records(
            smc_dal,
            ('src_a', 'type_1', 'mid_01', 'uid_a'),
            ('src_a', 'type_2', 'mid_02', 'uid_b'),
            ('src_b', 'type_1', 'mid_03', 'uid_a'),
        )
        await smc_dal.commit_session()

        result = await smc_dal.query_source_all('src_a')
        assert len(result) == 2
        assert all(item.source == 'src_a' for item in result)

    async def test_query_source_all_with_m_type(self, smc_dal) -> None:
        """source + m_type 过滤"""
        await _add_smc_records(
            smc_dal,
            ('src_a', 'type_1', 'mid_01', 'uid_a'),
            ('src_a', 'type_2', 'mid_02', 'uid_a'),
            ('src_a', 'type_1', 'mid_03', 'uid_b'),
        )
        await smc_dal.commit_session()

        result = await smc_dal.query_source_all('src_a', m_type='type_1')
        assert len(result) == 2
        assert all(item.m_type == 'type_1' for item in result)

    async def test_query_source_all_with_m_uid(self, smc_dal) -> None:
        """source + m_uid 过滤"""
        await _add_smc_records(
            smc_dal,
            ('src_a', 'type_1', 'mid_01', 'uid_x'),
            ('src_a', 'type_2', 'mid_02', 'uid_y'),
            ('src_a', 'type_1', 'mid_03', 'uid_x'),
        )
        await smc_dal.commit_session()

        result = await smc_dal.query_source_all('src_a', m_uid='uid_x')
        assert len(result) == 2
        assert all(item.m_uid == 'uid_x' for item in result)

    async def test_query_source_all_with_m_type_and_m_uid(self, smc_dal) -> None:
        """双条件过滤"""
        await _add_smc_records(
            smc_dal,
            ('src_a', 'type_1', 'mid_01', 'uid_x'),
            ('src_a', 'type_1', 'mid_02', 'uid_y'),
            ('src_a', 'type_2', 'mid_03', 'uid_x'),
        )
        await smc_dal.commit_session()

        result = await smc_dal.query_source_all('src_a', m_type='type_1', m_uid='uid_x')
        assert len(result) == 1
        assert result[0].m_id == 'mid_01'

    async def test_query_source_all_ordering(self, smc_dal) -> None:
        """按 m_id DESC 排序 (字符串排序, 非降序插入验证)"""
        # 按升序插入, 查询应返回降序
        await _add_smc_records(
            smc_dal,
            ('src_a', 'type_1', 'mid_01', 'uid_a'),
            ('src_a', 'type_1', 'mid_02', 'uid_a'),
            ('src_a', 'type_1', 'mid_03', 'uid_a'),
        )
        await smc_dal.commit_session()

        result = await smc_dal.query_source_all('src_a')
        assert [item.m_id for item in result] == ['mid_03', 'mid_02', 'mid_01']

    async def test_query_source_all_empty(self, smc_dal) -> None:
        """不匹配返回空列表"""
        result = await smc_dal.query_source_all('nonexistent_source')
        assert result == []

    # ------------------------------------------------------------------ #
    # query_source_all_m_ids
    # ------------------------------------------------------------------ #

    async def test_query_source_all_m_ids_filtered(self, smc_dal) -> None:
        """source + m_type + m_uid 条件组合, 返回 m_id 列表"""
        await _add_smc_records(
            smc_dal,
            ('src_a', 'type_1', 'mid_01', 'uid_x'),
            ('src_a', 'type_2', 'mid_02', 'uid_x'),
            ('src_a', 'type_1', 'mid_03', 'uid_y'),
            ('src_b', 'type_1', 'mid_04', 'uid_x'),
        )
        await smc_dal.commit_session()

        # 仅 source
        result = await smc_dal.query_source_all_m_ids('src_a')
        assert sorted(result) == ['mid_01', 'mid_02', 'mid_03']

        # source + m_type
        result = await smc_dal.query_source_all_m_ids('src_a', m_type='type_1')
        assert sorted(result) == ['mid_01', 'mid_03']

        # source + m_uid
        result = await smc_dal.query_source_all_m_ids('src_a', m_uid='uid_x')
        assert sorted(result) == ['mid_01', 'mid_02']

        # source + m_type + m_uid
        result = await smc_dal.query_source_all_m_ids('src_a', m_type='type_1', m_uid='uid_y')
        assert result == ['mid_03']

    async def test_query_source_all_m_ids_ordering(self, smc_dal) -> None:
        """m_id DESC 排序"""
        await _add_smc_records(
            smc_dal,
            ('src_a', 'type_1', 'mid_01', 'uid_a'),
            ('src_a', 'type_1', 'mid_02', 'uid_a'),
            ('src_a', 'type_1', 'mid_03', 'uid_a'),
        )
        await smc_dal.commit_session()

        result = await smc_dal.query_source_all_m_ids('src_a')
        assert result == ['mid_03', 'mid_02', 'mid_01']

    async def test_query_source_all_m_ids_empty(self, smc_dal) -> None:
        """不匹配返回空列表"""
        result = await smc_dal.query_source_all_m_ids('nonexistent_source')
        assert result == []

    # ------------------------------------------------------------------ #
    # query_source_exists_m_ids — 三参数各形态
    # ------------------------------------------------------------------ #

    async def test_query_exists_m_ids_basic(self, smc_dal) -> None:
        """基础存在性: 部分存在部分不存在"""
        await _add_smc_records(
            smc_dal,
            ('src_a', 'type_1', 'mid_01', 'uid_a'),
            ('src_a', 'type_1', 'mid_02', 'uid_a'),
        )
        await smc_dal.commit_session()

        exists = await smc_dal.query_source_exists_m_ids(
            source='src_a', m_type='type_1', m_uid='uid_a', m_ids=['mid_01', 'mid_02', 'mid_99'],
        )
        assert sorted(exists) == ['mid_01', 'mid_02']
        assert 'mid_99' not in exists

    async def test_query_exists_m_ids_source_forms(self, smc_dal) -> None:
        """source 为 None/str/list 三种形态"""
        await _add_smc_records(
            smc_dal,
            ('src_a', 'type_1', 'mid_01', 'uid_a'),
            ('src_b', 'type_1', 'mid_02', 'uid_a'),
            ('src_c', 'type_1', 'mid_03', 'uid_a'),
        )
        await smc_dal.commit_session()

        m_ids = ['mid_01', 'mid_02', 'mid_03']

        # None 匹配所有来源
        result = await smc_dal.query_source_exists_m_ids(None, 'type_1', 'uid_a', m_ids)
        assert sorted(result) == m_ids

        # str 单一来源
        result = await smc_dal.query_source_exists_m_ids('src_a', 'type_1', 'uid_a', m_ids)
        assert result == ['mid_01']

        # list 多来源
        result = await smc_dal.query_source_exists_m_ids(['src_a', 'src_b'], 'type_1', 'uid_a', m_ids)
        assert sorted(result) == ['mid_01', 'mid_02']

    async def test_query_exists_m_ids_m_type_forms(self, smc_dal) -> None:
        """m_type 为 None/str/list 三种形态"""
        await _add_smc_records(
            smc_dal,
            ('src_a', 'type_1', 'mid_01', 'uid_a'),
            ('src_a', 'type_2', 'mid_02', 'uid_a'),
            ('src_a', 'type_3', 'mid_03', 'uid_a'),
        )
        await smc_dal.commit_session()

        m_ids = ['mid_01', 'mid_02', 'mid_03']

        # None 匹配所有类型
        result = await smc_dal.query_source_exists_m_ids('src_a', None, 'uid_a', m_ids)
        assert sorted(result) == m_ids

        # str 单一类型
        result = await smc_dal.query_source_exists_m_ids('src_a', 'type_2', 'uid_a', m_ids)
        assert result == ['mid_02']

        # list 多类型
        result = await smc_dal.query_source_exists_m_ids('src_a', ['type_1', 'type_3'], 'uid_a', m_ids)
        assert sorted(result) == ['mid_01', 'mid_03']

    async def test_query_exists_m_ids_m_uid_forms(self, smc_dal) -> None:
        """m_uid 为 None/str/list 三种形态"""
        await _add_smc_records(
            smc_dal,
            ('src_a', 'type_1', 'mid_01', 'uid_x'),
            ('src_a', 'type_1', 'mid_02', 'uid_y'),
            ('src_a', 'type_1', 'mid_03', 'uid_z'),
        )
        await smc_dal.commit_session()

        m_ids = ['mid_01', 'mid_02', 'mid_03']

        # None 匹配所有用户
        result = await smc_dal.query_source_exists_m_ids('src_a', 'type_1', None, m_ids)
        assert sorted(result) == m_ids

        # str 单一用户
        result = await smc_dal.query_source_exists_m_ids('src_a', 'type_1', 'uid_y', m_ids)
        assert result == ['mid_02']

        # list 多用户
        result = await smc_dal.query_source_exists_m_ids('src_a', 'type_1', ['uid_x', 'uid_z'], m_ids)
        assert sorted(result) == ['mid_01', 'mid_03']

    async def test_query_exists_m_ids_ordering(self, smc_dal) -> None:
        """结果按 m_id DESC 排序"""
        await _add_smc_records(
            smc_dal,
            ('src_a', 'type_1', 'mid_01', 'uid_a'),
            ('src_a', 'type_1', 'mid_02', 'uid_a'),
            ('src_a', 'type_1', 'mid_03', 'uid_a'),
        )
        await smc_dal.commit_session()

        result = await smc_dal.query_source_exists_m_ids(
            'src_a', 'type_1', 'uid_a', ['mid_01', 'mid_02', 'mid_03'],
        )
        assert result == ['mid_03', 'mid_02', 'mid_01']

    async def test_query_exists_m_ids_no_match(self, smc_dal) -> None:
        """无匹配返回空列表"""
        await _add_smc_records(smc_dal, ('src_a', 'type_1', 'mid_01', 'uid_a'))
        await smc_dal.commit_session()

        result = await smc_dal.query_source_exists_m_ids(
            'src_a', 'type_1', 'uid_a', ['mid_99', 'mid_98'],
        )
        assert result == []

    # ------------------------------------------------------------------ #
    # query_source_not_exists_m_ids
    # ------------------------------------------------------------------ #

    async def test_query_not_exists_m_ids_basic(self, smc_dal) -> None:
        """补集 (部分存在部分不存在)"""
        await _add_smc_records(
            smc_dal,
            ('src_a', 'type_1', 'mid_01', 'uid_a'),
            ('src_a', 'type_1', 'mid_02', 'uid_a'),
        )
        await smc_dal.commit_session()

        not_exists = await smc_dal.query_source_not_exists_m_ids(
            'src_a', 'type_1', 'uid_a', ['mid_01', 'mid_02', 'mid_03', 'mid_04'],
        )
        assert sorted(not_exists) == ['mid_03', 'mid_04']
        assert 'mid_01' not in not_exists
        assert 'mid_02' not in not_exists

    async def test_query_not_exists_m_ids_all_exists(self, smc_dal) -> None:
        """全部存在返回空列表"""
        await _add_smc_records(
            smc_dal,
            ('src_a', 'type_1', 'mid_01', 'uid_a'),
            ('src_a', 'type_1', 'mid_02', 'uid_a'),
        )
        await smc_dal.commit_session()

        not_exists = await smc_dal.query_source_not_exists_m_ids(
            'src_a', 'type_1', 'uid_a', ['mid_01', 'mid_02'],
        )
        assert not_exists == []

    async def test_query_not_exists_m_ids_none_exists(self, smc_dal) -> None:
        """全部不存在返回全部 (sorted reverse)"""
        await _add_smc_records(smc_dal, ('src_a', 'type_1', 'mid_01', 'uid_a'))
        await smc_dal.commit_session()

        not_exists = await smc_dal.query_source_not_exists_m_ids(
            'src_b', 'type_1', 'uid_a', ['mid_02', 'mid_03', 'mid_04'],
        )
        assert not_exists == ['mid_04', 'mid_03', 'mid_02']

    # ------------------------------------------------------------------ #
    # 边界条件
    # ------------------------------------------------------------------ #

    async def test_query_exists_m_ids_empty_input(self, smc_dal) -> None:
        """m_ids 为空列表时返回空列表"""
        await _add_smc_records(smc_dal, ('src_a', 'type_1', 'mid_01', 'uid_a'))
        await smc_dal.commit_session()

        result = await smc_dal.query_source_exists_m_ids(None, None, None, [])
        assert result == []

    async def test_query_not_exists_m_ids_empty_input(self, smc_dal) -> None:
        """m_ids 为空列表时 not_exists 返回空列表"""
        result = await smc_dal.query_source_not_exists_m_ids(None, None, None, [])
        assert result == []

    async def test_query_exists_m_ids_empty_sequence_filter(self, smc_dal) -> None:
        """过滤器传空序列时匹配为空 (与 None 匹配全部的语义不同)"""
        await _add_smc_records(smc_dal, ('src_a', 'type_1', 'mid_01', 'uid_a'))
        await smc_dal.commit_session()

        m_ids = ['mid_01']

        # None 匹配全部来源
        result = await smc_dal.query_source_exists_m_ids(None, None, None, m_ids)
        assert result == ['mid_01']

        # 空序列不匹配任何记录
        result = await smc_dal.query_source_exists_m_ids([], None, None, m_ids)
        assert result == []

        result = await smc_dal.query_source_exists_m_ids(None, [], None, m_ids)
        assert result == []

        result = await smc_dal.query_source_exists_m_ids(None, None, [], m_ids)
        assert result == []

    async def test_query_not_exists_m_ids_duplicate_input(self, smc_dal) -> None:
        """输入 m_ids 含重复值时输出去重"""
        result = await smc_dal.query_source_not_exists_m_ids(
            None, None, None, ['mid_02', 'mid_01', 'mid_02', 'mid_01'],
        )
        assert result == ['mid_02', 'mid_01']

    async def test_query_not_exists_m_ids_natural_order(self, smc_dal) -> None:
        """m_id 按数值感知倒序 ('mid_10' 排在 'mid_9' 之前), 与 exists 查询的 SQL 排序语义一致"""
        result = await smc_dal.query_source_not_exists_m_ids(
            None, None, None, ['mid_9', 'mid_10', 'mid_2'],
        )
        assert result == ['mid_10', 'mid_9', 'mid_2']

    async def test_query_exists_m_ids_natural_order(self, smc_dal) -> None:
        """exists 查询按 m_id 数值感知倒序, not_exists 在部分已存在时保持相同排序语义"""
        await _add_smc_records(
            smc_dal,
            ('src_a', 'type_1', 'mid_9', 'uid_a'),
            ('src_a', 'type_1', 'mid_10', 'uid_a'),
            ('src_a', 'type_1', 'mid_2', 'uid_a'),
        )
        await smc_dal.commit_session()

        result = await smc_dal.query_source_exists_m_ids('src_a', None, None, ['mid_9', 'mid_10', 'mid_2'])
        assert result == ['mid_10', 'mid_9', 'mid_2']

        # 剩余不存在条目的排序语义与 exists 一致 ('mid_100' 数值感知上大于 'mid_20')
        result = await smc_dal.query_source_not_exists_m_ids(
            'src_a', None, None, ['mid_9', 'mid_10', 'mid_2', 'mid_100', 'mid_20'],
        )
        assert result == ['mid_100', 'mid_20']
