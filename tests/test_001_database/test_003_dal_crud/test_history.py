"""
@Author         : Ailitonia
@Date           : 2026/8/30 14:07
@FileName       : test_history
@Project        : omega-miya
@Description    : history.py  数据库 CRUD 单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import random
import string
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import TYPE_CHECKING, Any

import pytest
from sqlalchemy.exc import IntegrityError, NoResultFound

if TYPE_CHECKING:
    from src.database.internal.history import HistoryDAL


@pytest.fixture(scope='class')
async def test_history_message_id() -> str:
    return f'MESSAGE_ID_{"".join(random.sample(string.ascii_letters + string.digits, k=8))}'


@pytest.fixture(scope='class')
async def test_history_bot_self_id() -> str:
    return f'BOT_SELF_ID_{"".join(random.sample(string.ascii_letters + string.digits, k=8))}'


@pytest.fixture(scope='class')
async def test_history_event_entity_id() -> str:
    return f'EVENT_ENTITY_ID_{"".join(random.sample(string.ascii_letters + string.digits, k=8))}'


@pytest.fixture(scope='class')
async def test_history_user_entity_id() -> str:
    return f'USER_ENTITY_ID_{"".join(random.sample(string.ascii_letters + string.digits, k=8))}'


@pytest.fixture(scope='class')
async def test_history_message_type() -> str:
    return f'MESSAGE_TYPE_{"".join(random.sample(string.ascii_letters + string.digits, k=8))}'


@pytest.fixture(scope='class')
async def test_history_message_plain_text() -> str:
    return f'MESSAGE_PLAIN_TEXT_{"".join(random.choices(string.ascii_letters + string.digits, k=1024))}'


@pytest.fixture(scope='class')
async def test_history_message_raw(
        test_history_message_id,
        test_history_bot_self_id,
        test_history_event_entity_id,
        test_history_user_entity_id,
        test_history_message_type,
        test_history_message_plain_text,
) -> dict[str, Any]:
    return {
        'id': test_history_message_id,
        'bot_id': test_history_bot_self_id,
        'event_id': test_history_event_entity_id,
        'user_id': test_history_user_entity_id,
        'message': {
            'type': test_history_message_type,
            'content': test_history_message_plain_text,
        },
        'mid': "".join(random.sample(string.ascii_letters + string.digits, k=8)),
    }


@pytest.fixture(scope='class')
async def history_dal() -> AsyncGenerator['HistoryDAL', None]:
    from src.database.internal.history import HistoryDAL

    async with HistoryDAL.create() as dal:
        yield dal


class TestHistoryDAL:
    """HistoryDAL CRUD 单元测试"""

    async def test_check_clear_table(self, history_dal) -> None:
        """清空数据表, 查回验证表行数为空"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        rows_num = await history_dal._count_all()

        assert rows_num == 0

    async def test_clear_all_rollback(
            self,
            history_dal,
            test_history_message_id,
            test_history_bot_self_id,
            test_history_event_entity_id,
            test_history_user_entity_id,
            test_history_message_type,
            test_history_message_plain_text,
            test_history_message_raw,
    ) -> None:
        """_clear_all 不执行 commit, 外层事务 rollback 后数据应恢复"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        now_timestamp = int(datetime.now().timestamp())
        await history_dal.add(
            received_timestamp=now_timestamp,
            message_id=test_history_message_id,
            bot_self_id=test_history_bot_self_id,
            event_entity_id=test_history_event_entity_id,
            user_entity_id=test_history_user_entity_id,
            message_type=test_history_message_type,
            message_plain_text=test_history_message_plain_text,
            message_raw=test_history_message_raw,
        )
        await history_dal.commit_session()

        await history_dal._clear_all()
        assert await history_dal._count_all() == 0

        await history_dal.rollback_session()
        assert await history_dal._count_all() == 1

    # ------------------------------------------------------------------ #
    # add
    # ------------------------------------------------------------------ #

    async def test_add_basic(
            self,
            history_dal,
            test_history_message_id,
            test_history_bot_self_id,
            test_history_event_entity_id,
            test_history_user_entity_id,
            test_history_message_type,
            test_history_message_plain_text,
            test_history_message_raw,
    ) -> None:
        """插入一条记录, 验证返回值所有字段正确 (含 JSON 字段往返)"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        now_timestamp = int(datetime.now().timestamp())
        result = await history_dal.add(
            received_timestamp=now_timestamp,
            message_id=test_history_message_id,
            bot_self_id=test_history_bot_self_id,
            event_entity_id=test_history_event_entity_id,
            user_entity_id=test_history_user_entity_id,
            message_type=test_history_message_type,
            message_plain_text=test_history_message_plain_text,
            message_raw=test_history_message_raw,
        )
        await history_dal.commit_session()

        assert result.received_timestamp == now_timestamp
        assert result.message_id == test_history_message_id
        assert result.bot_self_id == test_history_bot_self_id
        assert result.event_entity_id == test_history_event_entity_id
        assert result.user_entity_id == test_history_user_entity_id
        assert result.message_type == test_history_message_type
        assert result.message_plain_text == test_history_message_plain_text
        assert result.message_raw == test_history_message_raw

    async def test_add_json_roundtrip(
            self,
            history_dal,
            test_history_bot_self_id,
    ) -> None:
        """插入含嵌套 dict 的 message_raw, 查回验证嵌套结构完整"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        nested_raw = {'msg': {'segments': [{'type': 'text', 'data': {'text': 'hello'}}]}, 'meta': {'count': 3}}
        now_timestamp = int(datetime.now().timestamp())
        await history_dal.add(
            received_timestamp=now_timestamp,
            message_id='msg_json',
            bot_self_id=test_history_bot_self_id,
            event_entity_id='event_json',
            user_entity_id='user_json',
            message_type='private',
            message_plain_text='hello',
            message_raw=nested_raw,
        )
        await history_dal.commit_session()

        queried = await history_dal.query_unique('msg_json', test_history_bot_self_id, 'event_json', 'user_json')
        assert queried.received_timestamp == now_timestamp
        assert queried.message_raw == nested_raw

    async def test_add_multi_distinct_ids(self, history_dal, test_history_bot_self_id) -> None:
        """插入多条 (不同 message_id + 不同 entity 组合), 验证 id 递增且 _count_all 递增"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        base_ts = int(datetime.now().timestamp())
        ids = []
        for i in range(5):
            result = await history_dal.add(
                received_timestamp=base_ts + i,
                message_id=f'msg_id_{i}',
                bot_self_id=test_history_bot_self_id,
                event_entity_id=f'event_{i}',
                user_entity_id=f'user_{i}',
                message_type='group',
                message_plain_text=f'text_{i}',
                message_raw={},
            )
            ids.append(result.id)
            assert await history_dal._count_all() == i + 1

        # id 递增
        assert ids == sorted(ids)
        assert len(set(ids)) == 5

    async def test_add_duplicate_raises_integrity(
            self,
            history_dal,
            test_history_message_id,
            test_history_bot_self_id,
            test_history_event_entity_id,
            test_history_user_entity_id,
            test_history_message_type,
            test_history_message_plain_text,
            test_history_message_raw,
    ) -> None:
        """相同 (bot_self_id, message_id) 插入两次, 预期 IntegrityError (唯一约束 1)"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        now_timestamp = int(datetime.now().timestamp())
        await history_dal.add(
            received_timestamp=now_timestamp,
            message_id=test_history_message_id,
            bot_self_id=test_history_bot_self_id,
            event_entity_id=test_history_event_entity_id,
            user_entity_id=test_history_user_entity_id,
            message_type=test_history_message_type,
            message_plain_text=test_history_message_plain_text,
            message_raw=test_history_message_raw,
        )
        await history_dal.commit_session()

        with pytest.raises(IntegrityError):
            await history_dal.add(
                received_timestamp=now_timestamp + 1,
                message_id=test_history_message_id,
                bot_self_id=test_history_bot_self_id,
                event_entity_id='different_event',
                user_entity_id='different_user',
                message_type=test_history_message_type,
                message_plain_text='other text',
                message_raw={},
            )
            await history_dal.commit_session()

        # 回滚到正常状态
        await history_dal.rollback_session()

        queried = await history_dal.query_unique(
            test_history_message_id,
            test_history_bot_self_id,
            test_history_event_entity_id,
            test_history_user_entity_id,
        )
        assert queried.message_plain_text == test_history_message_plain_text
        assert queried.message_raw == test_history_message_raw

    async def test_add_duplicate_raises_full_unique(
            self,
            history_dal,
            test_history_message_id,
            test_history_bot_self_id,
            test_history_event_entity_id,
            test_history_user_entity_id,
            test_history_message_type,
            test_history_message_plain_text,
            test_history_message_raw,
    ) -> None:
        """相同四元组插入两次 (message_id, bot_self_id, event_entity_id, user_entity_id), 预期 IntegrityError (唯一约束 2)"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        now_timestamp = int(datetime.now().timestamp())
        await history_dal.add(
            received_timestamp=now_timestamp,
            message_id=test_history_message_id,
            bot_self_id=test_history_bot_self_id,
            event_entity_id=test_history_event_entity_id,
            user_entity_id=test_history_user_entity_id,
            message_type=test_history_message_type,
            message_plain_text=test_history_message_plain_text,
            message_raw=test_history_message_raw,
        )
        await history_dal.commit_session()

        with pytest.raises(IntegrityError):
            await history_dal.add(
                received_timestamp=now_timestamp,
                message_id=test_history_message_id,
                bot_self_id=test_history_bot_self_id,
                event_entity_id=test_history_event_entity_id,
                user_entity_id=test_history_user_entity_id,
                message_type=test_history_message_type,
                message_plain_text='other text',
                message_raw={},
            )
            await history_dal.commit_session()

        # 回滚到正常状态
        await history_dal.rollback_session()

        queried = await history_dal.query_unique(
            test_history_message_id,
            test_history_bot_self_id,
            test_history_event_entity_id,
            test_history_user_entity_id,
        )
        assert queried.message_plain_text == test_history_message_plain_text
        assert queried.message_raw == test_history_message_raw

    # ------------------------------------------------------------------ #
    # query_unique
    # ------------------------------------------------------------------ #

    async def test_query_unique_not_found(self, history_dal) -> None:
        """查询不存在的记录, 预期 NoResultFound"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        with pytest.raises(NoResultFound):
            await history_dal.query_unique(
                'nonexistent_msg',
                'nonexistent_bot',
                'nonexistent_event',
                'nonexistent_user',
            )

    async def test_query_unique_normal(
            self,
            history_dal,
            test_history_message_id,
            test_history_bot_self_id,
            test_history_event_entity_id,
            test_history_user_entity_id,
            test_history_message_type,
            test_history_message_plain_text,
            test_history_message_raw,
    ) -> None:
        """插入后按四元组查询, 验证返回字段"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        now_timestamp = int(datetime.now().timestamp())
        await history_dal.add(
            received_timestamp=now_timestamp,
            message_id=test_history_message_id,
            bot_self_id=test_history_bot_self_id,
            event_entity_id=test_history_event_entity_id,
            user_entity_id=test_history_user_entity_id,
            message_type=test_history_message_type,
            message_plain_text=test_history_message_plain_text,
            message_raw=test_history_message_raw,
        )
        await history_dal.commit_session()

        queried = await history_dal.query_unique(
            test_history_message_id,
            test_history_bot_self_id,
            test_history_event_entity_id,
            test_history_user_entity_id,
        )
        assert queried.received_timestamp == now_timestamp
        assert queried.message_id == test_history_message_id
        assert queried.bot_self_id == test_history_bot_self_id
        assert queried.event_entity_id == test_history_event_entity_id
        assert queried.user_entity_id == test_history_user_entity_id
        assert queried.message_type == test_history_message_type
        assert queried.message_plain_text == test_history_message_plain_text
        assert queried.message_raw == test_history_message_raw

    # ------------------------------------------------------------------ #
    # query_records_by_condition
    # ------------------------------------------------------------------ #

    async def test_query_records_by_event_entity_id(self, history_dal) -> None:
        """按 event_entity_id 过滤"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        base_ts = int(datetime.now().timestamp())
        await history_dal.add(received_timestamp=base_ts, message_id='m1', bot_self_id='bot1',
                              event_entity_id='event_a', user_entity_id='user_a', message_type='group',
                              message_plain_text='t1', message_raw={})
        await history_dal.add(received_timestamp=base_ts + 1, message_id='m2', bot_self_id='bot1',
                              event_entity_id='event_b', user_entity_id='user_b', message_type='group',
                              message_plain_text='t2', message_raw={})
        await history_dal.add(received_timestamp=base_ts + 2, message_id='m3', bot_self_id='bot1',
                              event_entity_id='event_a', user_entity_id='user_c', message_type='group',
                              message_plain_text='t3', message_raw={})
        await history_dal.commit_session()

        result = await history_dal.query_records_by_condition(bot_self_id='bot1', event_entity_id='event_a')
        assert len(result) == 2
        assert all(item.event_entity_id == 'event_a' for item in result)

    async def test_query_records_by_user_entity_id(self, history_dal) -> None:
        """按 user_entity_id 过滤"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        base_ts = int(datetime.now().timestamp())
        await history_dal.add(received_timestamp=base_ts, message_id='m1', bot_self_id='bot1',
                              event_entity_id='event_a', user_entity_id='user_x', message_type='group',
                              message_plain_text='t1', message_raw={})
        await history_dal.add(received_timestamp=base_ts + 1, message_id='m2', bot_self_id='bot1',
                              event_entity_id='event_b', user_entity_id='user_y', message_type='group',
                              message_plain_text='t2', message_raw={})
        await history_dal.add(received_timestamp=base_ts + 2, message_id='m3', bot_self_id='bot1',
                              event_entity_id='event_c', user_entity_id='user_x', message_type='group',
                              message_plain_text='t3', message_raw={})
        await history_dal.commit_session()

        result = await history_dal.query_records_by_condition(bot_self_id='bot1', user_entity_id='user_x')
        assert len(result) == 2
        assert all(item.user_entity_id == 'user_x' for item in result)

    async def test_query_records_by_event_and_user(self, history_dal) -> None:
        """同时按 event_entity_id + user_entity_id 过滤"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        base_ts = int(datetime.now().timestamp())
        await history_dal.add(received_timestamp=base_ts, message_id='m1', bot_self_id='bot1',
                              event_entity_id='event_shared', user_entity_id='user_shared', message_type='group',
                              message_plain_text='t1', message_raw={})
        await history_dal.add(received_timestamp=base_ts + 1, message_id='m2', bot_self_id='bot1',
                              event_entity_id='event_shared', user_entity_id='user_other', message_type='group',
                              message_plain_text='t2', message_raw={})
        await history_dal.add(received_timestamp=base_ts + 2, message_id='m3', bot_self_id='bot1',
                              event_entity_id='event_other', user_entity_id='user_shared', message_type='group',
                              message_plain_text='t3', message_raw={})
        await history_dal.commit_session()

        result = await history_dal.query_records_by_condition(bot_self_id='bot1', event_entity_id='event_shared',
                                                              user_entity_id='user_shared')
        assert len(result) == 1
        assert result[0].event_entity_id == 'event_shared'
        assert result[0].user_entity_id == 'user_shared'

    async def test_query_records_by_message_type(self, history_dal) -> None:
        """加 message_type 过滤"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        base_ts = int(datetime.now().timestamp())
        await history_dal.add(received_timestamp=base_ts, message_id='m1', bot_self_id='bot1',
                              event_entity_id='event_a', user_entity_id='user_a', message_type='group',
                              message_plain_text='t1', message_raw={})
        await history_dal.add(received_timestamp=base_ts + 1, message_id='m2', bot_self_id='bot1',
                              event_entity_id='event_a', user_entity_id='user_b', message_type='private',
                              message_plain_text='t2', message_raw={})
        await history_dal.add(received_timestamp=base_ts + 2, message_id='m3', bot_self_id='bot1',
                              event_entity_id='event_a', user_entity_id='user_c', message_type='group',
                              message_plain_text='t3', message_raw={})
        await history_dal.commit_session()

        result = await history_dal.query_records_by_condition(bot_self_id='bot1', event_entity_id='event_a',
                                                              message_type='group')
        assert len(result) == 2
        assert all(item.message_type == 'group' for item in result)

    async def test_query_records_by_time_range(self, history_dal) -> None:
        """start_time + end_time (datetime) 过滤"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        base_dt = datetime(2025, 1, 1, 0, 0, 0)
        base_ts = int(base_dt.timestamp())
        await history_dal.add(received_timestamp=base_ts, message_id='m1', bot_self_id='bot1',
                              event_entity_id='event_a', user_entity_id='user_a', message_type='group',
                              message_plain_text='t1', message_raw={})
        await history_dal.add(received_timestamp=base_ts + 100, message_id='m2', bot_self_id='bot1',
                              event_entity_id='event_a', user_entity_id='user_b', message_type='group',
                              message_plain_text='t2', message_raw={})
        await history_dal.add(received_timestamp=base_ts + 200, message_id='m3', bot_self_id='bot1',
                              event_entity_id='event_a', user_entity_id='user_c', message_type='group',
                              message_plain_text='t3', message_raw={})
        await history_dal.commit_session()

        result = await history_dal.query_records_by_condition(
            bot_self_id='bot1',
            event_entity_id='event_a',
            start_time=base_dt,
            end_time=datetime.fromtimestamp(base_ts + 100),
        )
        assert len(result) == 2
        timestamps = {item.received_timestamp for item in result}
        assert timestamps == {base_ts, base_ts + 100}

    async def test_query_records_exclude_bot_self(self, history_dal) -> None:
        """exclude_bot_self_message=True 排除 bot_self_id == user_entity_id 的记录"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        base_ts = int(datetime.now().timestamp())
        # bot_self_id == user_entity_id (bot 自身消息)
        await history_dal.add(received_timestamp=base_ts, message_id='m1', bot_self_id='bot1',
                              event_entity_id='event_a', user_entity_id='bot1', message_type='group',
                              message_plain_text='t1', message_raw={})
        # bot_self_id != user_entity_id (普通用户消息)
        await history_dal.add(received_timestamp=base_ts + 1, message_id='m2', bot_self_id='bot1',
                              event_entity_id='event_a', user_entity_id='user_a', message_type='group',
                              message_plain_text='t2', message_raw={})
        await history_dal.commit_session()

        result = await history_dal.query_records_by_condition(
            bot_self_id='bot1',
            event_entity_id='event_a',
            exclude_bot_self_message=True,
        )
        assert len(result) == 1
        assert result[0].user_entity_id != 'bot1'

    async def test_query_records_limit(self, history_dal) -> None:
        """limit 限制返回数量, 取最近 (timestamp 最大) 的记录"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        base_ts = int(datetime.now().timestamp())
        for i in range(5):
            await history_dal.add(
                received_timestamp=base_ts + i,
                message_id=f'm{i}',
                bot_self_id='bot1',
                event_entity_id='event_a',
                user_entity_id='user_a',
                message_type='group',
                message_plain_text=f't{i}',
                message_raw={},
            )
        await history_dal.commit_session()

        result = await history_dal.query_records_by_condition(
            bot_self_id='bot1',
            event_entity_id='event_a',
            limit=2,
        )
        assert len(result) == 2
        # DESC 排序, 取最近的两条 (timestamp 最大)
        assert result[0].received_timestamp == base_ts + 4
        assert result[1].received_timestamp == base_ts + 3

    async def test_query_records_ordering_desc(self, history_dal) -> None:
        """验证结果按 received_timestamp DESC 排序"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        timestamps = [1000000000, 1000000005, 1000000003, 1000000001, 1000000004]
        for i, ts in enumerate(timestamps):
            await history_dal.add(
                received_timestamp=ts, message_id=f'm{i}', bot_self_id='bot1',
                event_entity_id='event_a', user_entity_id='user_a', message_type='group',
                message_plain_text=f't{i}', message_raw={},
            )
        await history_dal.commit_session()

        result = await history_dal.query_records_by_condition(bot_self_id='bot1', event_entity_id='event_a')
        result_timestamps = [item.received_timestamp for item in result]
        assert result_timestamps == sorted(timestamps, reverse=True)

    async def test_query_records_empty(self, history_dal) -> None:
        """条件不匹配返回空列表"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        await history_dal.add(
            received_timestamp=1000000000,
            message_id='m1',
            bot_self_id='bot1',
            event_entity_id='event_a',
            user_entity_id='user_a',
            message_type='group',
            message_plain_text='t1',
            message_raw={},
        )
        await history_dal.commit_session()

        result = await history_dal.query_records_by_condition(bot_self_id='bot1', event_entity_id='nonexistent_event')
        assert result == []

    async def test_query_records_raises_no_entity(self, history_dal) -> None:
        """event_entity_id 和 user_entity_id 都为 None, 预期 ValueError"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        with pytest.raises(ValueError):
            await history_dal.query_records_by_condition(bot_self_id='bot1')

    # ------------------------------------------------------------------ #
    # count_records_by_condition
    # ------------------------------------------------------------------ #

    async def test_count_by_event_entity_id(self, history_dal) -> None:
        """按 event_entity_id 过滤计数"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        base_ts = int(datetime.now().timestamp())
        await history_dal.add(received_timestamp=base_ts, message_id='m1', bot_self_id='bot1',
                              event_entity_id='event_a', user_entity_id='user_a', message_type='group',
                              message_plain_text='t1', message_raw={})
        await history_dal.add(received_timestamp=base_ts + 1, message_id='m2', bot_self_id='bot1',
                              event_entity_id='event_b', user_entity_id='user_b', message_type='group',
                              message_plain_text='t2', message_raw={})
        await history_dal.add(received_timestamp=base_ts + 2, message_id='m3', bot_self_id='bot1',
                              event_entity_id='event_a', user_entity_id='user_c', message_type='group',
                              message_plain_text='t3', message_raw={})
        await history_dal.commit_session()

        assert await history_dal.count_records_by_condition(bot_self_id='bot1', event_entity_id='event_a') == 2
        assert await history_dal.count_records_by_condition(bot_self_id='bot1', event_entity_id='event_b') == 1

    async def test_count_by_user_entity_id(self, history_dal) -> None:
        """按 user_entity_id 过滤计数"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        base_ts = int(datetime.now().timestamp())
        await history_dal.add(received_timestamp=base_ts, message_id='m1', bot_self_id='bot1',
                              event_entity_id='event_a', user_entity_id='user_x', message_type='group',
                              message_plain_text='t1', message_raw={})
        await history_dal.add(received_timestamp=base_ts + 1, message_id='m2', bot_self_id='bot1',
                              event_entity_id='event_b', user_entity_id='user_y', message_type='group',
                              message_plain_text='t2', message_raw={})
        await history_dal.add(received_timestamp=base_ts + 2, message_id='m3', bot_self_id='bot1',
                              event_entity_id='event_c', user_entity_id='user_x', message_type='group',
                              message_plain_text='t3', message_raw={})
        await history_dal.commit_session()

        assert await history_dal.count_records_by_condition(bot_self_id='bot1', user_entity_id='user_x') == 2

    async def test_count_with_message_type(self, history_dal) -> None:
        """加 message_type 过滤计数"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        base_ts = int(datetime.now().timestamp())
        await history_dal.add(received_timestamp=base_ts, message_id='m1', bot_self_id='bot1',
                              event_entity_id='event_a', user_entity_id='user_a', message_type='group',
                              message_plain_text='t1', message_raw={})
        await history_dal.add(received_timestamp=base_ts + 1, message_id='m2', bot_self_id='bot1',
                              event_entity_id='event_a', user_entity_id='user_b', message_type='private',
                              message_plain_text='t2', message_raw={})
        await history_dal.add(received_timestamp=base_ts + 2, message_id='m3', bot_self_id='bot1',
                              event_entity_id='event_a', user_entity_id='user_c', message_type='group',
                              message_plain_text='t3', message_raw={})
        await history_dal.commit_session()

        assert await history_dal.count_records_by_condition(bot_self_id='bot1', event_entity_id='event_a',
                                                            message_type='group') == 2
        assert await history_dal.count_records_by_condition(bot_self_id='bot1', event_entity_id='event_a',
                                                            message_type='private') == 1

    async def test_count_with_time_range(self, history_dal) -> None:
        """时间范围过滤计数"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        base_dt = datetime(2025, 1, 1, 0, 0, 0)
        base_ts = int(base_dt.timestamp())
        await history_dal.add(received_timestamp=base_ts, message_id='m1', bot_self_id='bot1',
                              event_entity_id='event_a', user_entity_id='user_a', message_type='group',
                              message_plain_text='t1', message_raw={})
        await history_dal.add(received_timestamp=base_ts + 100, message_id='m2', bot_self_id='bot1',
                              event_entity_id='event_a', user_entity_id='user_b', message_type='group',
                              message_plain_text='t2', message_raw={})
        await history_dal.add(received_timestamp=base_ts + 200, message_id='m3', bot_self_id='bot1',
                              event_entity_id='event_a', user_entity_id='user_c', message_type='group',
                              message_plain_text='t3', message_raw={})
        await history_dal.commit_session()

        assert await history_dal.count_records_by_condition(
            bot_self_id='bot1', event_entity_id='event_a', start_time=base_dt,
            end_time=datetime.fromtimestamp(base_ts + 100),
        ) == 2

    async def test_count_exclude_bot_self(self, history_dal) -> None:
        """排除 bot 自身消息后的计数"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        base_ts = int(datetime.now().timestamp())
        await history_dal.add(received_timestamp=base_ts, message_id='m1', bot_self_id='bot1',
                              event_entity_id='event_a', user_entity_id='bot1', message_type='group',
                              message_plain_text='t1', message_raw={})
        await history_dal.add(received_timestamp=base_ts + 1, message_id='m2', bot_self_id='bot1',
                              event_entity_id='event_a', user_entity_id='user_a', message_type='group',
                              message_plain_text='t2', message_raw={})
        await history_dal.add(received_timestamp=base_ts + 2, message_id='m3', bot_self_id='bot1',
                              event_entity_id='event_a', user_entity_id='bot1', message_type='group',
                              message_plain_text='t3', message_raw={})
        await history_dal.commit_session()

        total = await history_dal.count_records_by_condition(bot_self_id='bot1', event_entity_id='event_a')
        assert total == 3

        excluded = await history_dal.count_records_by_condition(bot_self_id='bot1', event_entity_id='event_a',
                                                                exclude_bot_self_message=True)
        assert excluded == 1

    async def test_count_zero(self, history_dal) -> None:
        """不匹配返回 0"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        await history_dal.add(
            received_timestamp=1000000000,
            message_id='m1',
            bot_self_id='bot1',
            event_entity_id='event_a',
            user_entity_id='user_a',
            message_type='group',
            message_plain_text='t1',
            message_raw={},
        )
        await history_dal.commit_session()

        assert await history_dal.count_records_by_condition(bot_self_id='bot1', event_entity_id='nonexistent') == 0

    async def test_count_raises_no_entity(self, history_dal) -> None:
        """event_entity_id 和 user_entity_id 都为 None, 预期 ValueError"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        with pytest.raises(ValueError):
            await history_dal.count_records_by_condition(bot_self_id='bot1')

    # ------------------------------------------------------------------ #
    # delete_period_older
    # ------------------------------------------------------------------ #

    async def test_delete_period_older_basic(self, history_dal) -> None:
        """删除 received_timestamp <= before_timestamp 的记录, 验证剩余"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        base_ts = int(datetime.now().timestamp())
        await history_dal.add(received_timestamp=base_ts, message_id='m1', bot_self_id='bot1',
                              event_entity_id='event_a', user_entity_id='user_a', message_type='group',
                              message_plain_text='t1', message_raw={})
        await history_dal.add(received_timestamp=base_ts + 100, message_id='m2', bot_self_id='bot1',
                              event_entity_id='event_b', user_entity_id='user_b', message_type='group',
                              message_plain_text='t2', message_raw={})
        await history_dal.add(received_timestamp=base_ts + 200, message_id='m3', bot_self_id='bot1',
                              event_entity_id='event_c', user_entity_id='user_c', message_type='group',
                              message_plain_text='t3', message_raw={})
        await history_dal.commit_session()

        await history_dal.delete_period_older(base_ts + 100)
        await history_dal.commit_session()

        assert await history_dal._count_all() == 1
        remaining = await history_dal.query_records_by_condition(bot_self_id='bot1', event_entity_id='event_c')
        assert len(remaining) == 1
        assert remaining[0].received_timestamp == base_ts + 200

    async def test_delete_period_older_with_bot_self_id(self, history_dal) -> None:
        """指定 bot_self_id 只删该 bot 的过期记录, 其他 bot 的同 timestamp 记录保留"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        base_ts = int(datetime.now().timestamp())
        await history_dal.add(received_timestamp=base_ts, message_id='m1', bot_self_id='bot1',
                              event_entity_id='event_a', user_entity_id='user_a', message_type='group',
                              message_plain_text='t1', message_raw={})
        await history_dal.add(received_timestamp=base_ts, message_id='m2', bot_self_id='bot2',
                              event_entity_id='event_a', user_entity_id='user_b', message_type='group',
                              message_plain_text='t2', message_raw={})
        await history_dal.add(received_timestamp=base_ts + 200, message_id='m3', bot_self_id='bot1',
                              event_entity_id='event_b', user_entity_id='user_c', message_type='group',
                              message_plain_text='t3', message_raw={})
        await history_dal.commit_session()

        await history_dal.delete_period_older(base_ts, bot_self_id='bot1')
        await history_dal.commit_session()

        assert await history_dal._count_all() == 2
        remaining_bots = set()
        for event_id in ['event_a', 'event_b']:
            records = await history_dal.query_records_by_condition(bot_self_id='bot2', event_entity_id=event_id)
            remaining_bots.update(item.bot_self_id for item in records)
        # bot2's record at base_ts should still exist
        bot1_remaining = await history_dal.query_records_by_condition(bot_self_id='bot1', event_entity_id='event_b')
        assert len(bot1_remaining) == 1

    async def test_delete_period_older_no_match(self, history_dal) -> None:
        """before_timestamp 小于所有记录, 不删除"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        base_ts = int(datetime.now().timestamp())
        await history_dal.add(received_timestamp=base_ts, message_id='m1', bot_self_id='bot1',
                              event_entity_id='event_a', user_entity_id='user_a', message_type='group',
                              message_plain_text='t1', message_raw={})
        await history_dal.add(received_timestamp=base_ts + 100, message_id='m2', bot_self_id='bot1',
                              event_entity_id='event_b', user_entity_id='user_b', message_type='group',
                              message_plain_text='t2', message_raw={})
        await history_dal.commit_session()

        await history_dal.delete_period_older(base_ts - 1)
        await history_dal.commit_session()

        assert await history_dal._count_all() == 2

    async def test_delete_period_older_all(self, history_dal) -> None:
        """before_timestamp 大于所有记录, 全部删除"""
        await history_dal._clear_all()
        await history_dal.commit_session()

        base_ts = int(datetime.now().timestamp())
        await history_dal.add(received_timestamp=base_ts, message_id='m1', bot_self_id='bot1',
                              event_entity_id='event_a', user_entity_id='user_a', message_type='group',
                              message_plain_text='t1', message_raw={})
        await history_dal.add(received_timestamp=base_ts + 100, message_id='m2', bot_self_id='bot1',
                              event_entity_id='event_b', user_entity_id='user_b', message_type='group',
                              message_plain_text='t2', message_raw={})
        await history_dal.commit_session()

        await history_dal.delete_period_older(base_ts + 200)
        await history_dal.commit_session()

        assert await history_dal._count_all() == 0
