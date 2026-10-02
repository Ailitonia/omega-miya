"""
@Author         : Ailitonia
@Date           : 2026/8/31 20:47
@FileName       : test_bot
@Project        : omega-miya
@Description    : bot.py 数据库 CRUD 单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import random
import string
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.exc import IntegrityError, NoResultFound

if TYPE_CHECKING:
    from src.database.internal.bot import BotSelfDAL


@pytest.fixture(scope='class')
async def test_bot_info() -> str:
    return f'TEST_INFO_{"".join(random.choices(string.ascii_letters + string.digits, k=64))}'


@pytest.fixture(scope='class')
async def bot_dal() -> AsyncGenerator['BotSelfDAL', None]:
    from src.database.internal.bot import BotSelfDAL

    async with BotSelfDAL.create() as dal:
        yield dal


@pytest.fixture(autouse=True)
async def _clean_table(bot_dal) -> None:
    """每个测试用例执行前清空数据表"""
    await bot_dal._clear_all()
    await bot_dal.commit_session()


class TestBotSelfDAL:
    """BotSelfDAL CRUD 单元测试"""

    # ------------------------------------------------------------------ #
    # add
    # ------------------------------------------------------------------ #

    async def test_add_basic(
            self,
            bot_dal,
            test_bot_type,
            test_bot_self_id,
            test_bot_info,
    ) -> None:
        """插入一条记录, 用 query_unique 查回验证所有字段正确"""
        result = await bot_dal.add(
            bot_type=test_bot_type,
            self_id=test_bot_self_id,
            bot_status=1,
            bot_info=test_bot_info,
        )
        await bot_dal.commit_session()

        assert result.self_id == test_bot_self_id
        assert result.bot_type == test_bot_type
        assert result.bot_status == 1
        assert result.bot_info == test_bot_info

        queried = await bot_dal.query_unique(test_bot_type, test_bot_self_id, None)
        assert queried.bot_status == 1
        assert queried.bot_info == test_bot_info

    async def test_add_without_info(self, bot_dal, test_bot_type, test_bot_self_id) -> None:
        """bot_info=None 插入, 验证 bot_info 为 None"""
        result = await bot_dal.add(
            bot_type=test_bot_type,
            self_id=test_bot_self_id,
            bot_status=1,
        )
        await bot_dal.commit_session()

        assert result.bot_info is None

        queried = await bot_dal.query_unique(test_bot_type, test_bot_self_id, None)
        assert queried.bot_info is None

    async def test_add_different_bot_types(self, bot_dal) -> None:
        """分别用不同 BotType 插入, 验证 bot_type 字段正确"""
        test_cases = [
            ('Console', 'console_bot'),
            ('OneBot V11', 'qq_bot'),
            ('Telegram', 'tg_bot'),
        ]
        for bot_type, self_id in test_cases:
            result = await bot_dal.add(bot_type=bot_type, self_id=self_id, bot_status=1)
            await bot_dal.commit_session()
            assert result.bot_type == bot_type

            queried = await bot_dal.query_unique(bot_type, self_id, None)
            assert queried.bot_type == bot_type

    async def test_add_invalid_bot_type_raises(self, bot_dal, test_bot_self_id) -> None:
        """bot_type='InvalidType' 插入, 预期 ValueError (BotType 枚举校验)"""
        with pytest.raises(ValueError, match='is not a valid BotType'):
            await bot_dal.add(
                bot_type='InvalidType',
                self_id=test_bot_self_id,
                bot_status=1,
            )

    async def test_add_duplicate_raises(
            self,
            bot_dal,
            test_bot_type,
            test_bot_self_id,
            test_bot_info,
    ) -> None:
        """相同 (bot_type, self_id) 插入两次, 预期 IntegrityError"""
        await bot_dal.add(
            bot_type=test_bot_type,
            self_id=test_bot_self_id,
            bot_status=1,
            bot_info=test_bot_info,
        )
        await bot_dal.commit_session()

        with pytest.raises(IntegrityError):
            await bot_dal.add(
                bot_type=test_bot_type,
                self_id=test_bot_self_id,
                bot_status=0,
            )

        # 回滚到正常状态
        await bot_dal.rollback_session()

        queried = await bot_dal.query_unique(test_bot_type, test_bot_self_id, None)
        assert queried.bot_status == 1
        assert queried.bot_info == test_bot_info

    @pytest.mark.parametrize(
        ('status_input', 'expected_member_name'),
        [
            (1, 'ENABLED'),
            (0, 'DISABLED'),
            (-1, 'IGNORED'),
            ('ENABLED', 'ENABLED'),  # 字符串标记: 入参直接传 BotStatus 枚举成员 (IntEnum 兼容 int 签名)
        ],
    )
    async def test_add_bot_status_values(
            self,
            status_input: int | str,
            expected_member_name: str,
            bot_dal,
            test_bot_type,
            test_bot_self_id,
    ) -> None:
        """bot_status 传 int 或枚举成员, 验证返回及查回字段为 BotStatus 枚举成员且取值正确"""
        from src.database.internal.bot import BotStatus

        status = BotStatus[status_input] if isinstance(status_input, str) else status_input
        expected_member = BotStatus[expected_member_name]

        result = await bot_dal.add(bot_type=test_bot_type, self_id=test_bot_self_id, bot_status=status)
        await bot_dal.commit_session()
        assert result.bot_status == expected_member
        assert result.bot_status is expected_member

        queried = await bot_dal.query_unique(test_bot_type, test_bot_self_id, None)
        assert queried.bot_status is expected_member

    async def test_add_invalid_bot_status_raises(self, bot_dal, test_bot_type) -> None:
        """bot_status 传未定义的枚举值插入, 预期 ValueError (BotStatus 枚举校验) 且不产生写入"""
        with pytest.raises(ValueError, match='is not a valid BotStatus'):
            await bot_dal.add(bot_type=test_bot_type, self_id='bot_invalid_status', bot_status=2)

        assert await bot_dal._count_all() == 0

    # ------------------------------------------------------------------ #
    # query_unique — 多策略全覆盖
    # ------------------------------------------------------------------ #

    async def test_query_unique_by_bot_type_and_self_id(
            self,
            bot_dal,
            test_bot_type,
            test_bot_self_id,
            test_bot_info,
    ) -> None:
        """提供 (bot_type, self_id, None) 正常查询验证字段"""
        await bot_dal.add(
            bot_type=test_bot_type, self_id=test_bot_self_id, bot_status=1, bot_info=test_bot_info,
        )
        await bot_dal.commit_session()

        queried = await bot_dal.query_unique(test_bot_type, test_bot_self_id, None)
        assert queried.self_id == test_bot_self_id
        assert queried.bot_type == test_bot_type
        assert queried.bot_status == 1
        assert queried.bot_info == test_bot_info

    async def test_query_unique_by_index_id(
            self,
            bot_dal,
            test_bot_type,
            test_bot_self_id,
            test_bot_info,
    ) -> None:
        """提供 (None, None, index_id) 正常查询验证字段"""
        added = await bot_dal.add(
            bot_type=test_bot_type, self_id=test_bot_self_id, bot_status=1, bot_info=test_bot_info,
        )
        await bot_dal.commit_session()

        queried = await bot_dal.query_unique(None, None, added.id)
        assert queried.id == added.id
        assert queried.self_id == test_bot_self_id
        assert queried.bot_type == test_bot_type
        assert queried.bot_status == 1
        assert queried.bot_info == test_bot_info

    async def test_query_unique_index_id_takes_precedence(
            self,
            bot_dal,
            test_bot_type,
    ) -> None:
        """三参数都提供时 index_id 优先, 返回 index_id 对应的记录"""
        await bot_dal.add(bot_type=test_bot_type, self_id='bot_a', bot_status=1)
        bot_2 = await bot_dal.add(bot_type=test_bot_type, self_id='bot_b', bot_status=1)
        await bot_dal.commit_session()

        # 传 bot_a 的 bot_type+self_id, 但传 bot_b 的 index_id
        result = await bot_dal.query_unique(test_bot_type, 'bot_a', bot_2.id)
        assert result.id == bot_2.id
        assert result.self_id == 'bot_b'

    @pytest.mark.parametrize(
        ('bot_type', 'self_id', 'index_id'),
        [
            ('Console', 'nonexistent_self_id', None),  # 按 bot_type+self_id 查不存在
            (None, None, 999999),  # 按 index_id 查不存在
        ],
    )
    async def test_query_unique_not_found(
            self,
            bot_type: str | None,
            self_id: str | None,
            index_id: int | None,
            bot_dal,
    ) -> None:
        """查询不存在的记录, 预期 NoResultFound"""
        with pytest.raises(NoResultFound):
            await bot_dal.query_unique(bot_type, self_id, index_id)

    @pytest.mark.parametrize(
        ('bot_type', 'self_id', 'index_id'),
        [
            (None, None, None),  # 全部缺省
            ('OneBot V11', None, None),  # 仅提供 bot_type
            (None, 'nonexistent_self_id', None),  # 仅提供 self_id
        ],
    )
    async def test_query_unique_insufficient_params_raises(
            self,
            bot_type: str | None,
            self_id: str | None,
            index_id: int | None,
            bot_dal,
    ) -> None:
        """query_unique 参数不完整时抛 ValueError (与部分缺省统一走 index_id 缺省错误消息)"""
        with pytest.raises(ValueError, match='must both be provided'):
            await bot_dal.query_unique(bot_type, self_id, index_id)

    # ------------------------------------------------------------------ #
    # query_all
    # ------------------------------------------------------------------ #

    async def test_query_all_multiple(self, bot_dal) -> None:
        """插入多条, 验证返回全部且按 self_id 排序"""
        # 故意按非字典序插入
        await bot_dal.add(bot_type='Console', self_id='bot_charlie', bot_status=1)
        await bot_dal.add(bot_type='Console', self_id='bot_alpha', bot_status=1)
        await bot_dal.add(bot_type='Console', self_id='bot_bravo', bot_status=1)
        await bot_dal.commit_session()

        result = await bot_dal.query_all()
        assert len(result) == 3
        assert [item.self_id for item in result] == ['bot_alpha', 'bot_bravo', 'bot_charlie']

    async def test_query_all_empty(self, bot_dal) -> None:
        """空表返回空列表"""
        result = await bot_dal.query_all()
        assert result == []

    async def test_query_all_filtered_by_bot_type(self, bot_dal) -> None:
        """bot_type 过滤只返回匹配的记录"""
        await bot_dal.add(bot_type='Console', self_id='bot_a', bot_status=1)
        await bot_dal.add(bot_type='QQ', self_id='bot_b', bot_status=1)
        await bot_dal.add(bot_type='Console', self_id='bot_c', bot_status=1)
        await bot_dal.commit_session()

        result = await bot_dal.query_all(bot_type='Console')
        assert len(result) == 2
        assert all(item.bot_type == 'Console' for item in result)
        assert {item.self_id for item in result} == {'bot_a', 'bot_c'}

        result_qq = await bot_dal.query_all(bot_type='QQ')
        assert len(result_qq) == 1
        assert result_qq[0].self_id == 'bot_b'

    # ------------------------------------------------------------------ #
    # query_all_online
    # ------------------------------------------------------------------ #

    async def test_query_all_online_filtered(self, bot_dal) -> None:
        """插入多条 (enabled/disabled/ignored), 验证只返回 enabled 记录"""
        from src.database.internal.bot import BotStatus

        await bot_dal.add(bot_type='Console', self_id='bot_a', bot_status=1)
        await bot_dal.add(bot_type='Console', self_id='bot_b', bot_status=0)
        await bot_dal.add(bot_type='Console', self_id='bot_c', bot_status=1)
        await bot_dal.add(bot_type='Console', self_id='bot_d', bot_status=-1)
        await bot_dal.commit_session()

        result = await bot_dal.query_all_online()
        assert len(result) == 2
        assert [item.self_id for item in result] == ['bot_a', 'bot_c']
        for item in result:
            assert item.bot_status is BotStatus.ENABLED

    async def test_query_all_online_ordering(self, bot_dal) -> None:
        """验证结果按 self_id 排序"""
        await bot_dal.add(bot_type='Console', self_id='bot_zeta', bot_status=1)
        await bot_dal.add(bot_type='Console', self_id='bot_alpha', bot_status=1)
        await bot_dal.commit_session()

        result = await bot_dal.query_all_online()
        assert [item.self_id for item in result] == ['bot_alpha', 'bot_zeta']

    async def test_query_all_online_empty(self, bot_dal) -> None:
        """无在线记录时返回空列表"""
        await bot_dal.add(bot_type='Console', self_id='bot_offline', bot_status=0)
        await bot_dal.commit_session()

        result = await bot_dal.query_all_online()
        assert result == []

    async def test_query_all_online_filtered_by_bot_type(self, bot_dal) -> None:
        """bot_type + online 双重过滤"""
        await bot_dal.add(bot_type='Console', self_id='bot_a', bot_status=1)
        await bot_dal.add(bot_type='QQ', self_id='bot_b', bot_status=1)
        await bot_dal.add(bot_type='Console', self_id='bot_c', bot_status=0)
        await bot_dal.commit_session()

        result = await bot_dal.query_all_online(bot_type='Console')
        assert len(result) == 1
        assert result[0].self_id == 'bot_a'
        assert result[0].bot_type == 'Console'
        assert result[0].bot_status == 1

    # ------------------------------------------------------------------ #
    # add_update_exist
    # ------------------------------------------------------------------ #

    async def test_add_update_exist_insert(
            self,
            bot_dal,
            test_bot_type,
            test_bot_self_id,
            test_bot_info,
    ) -> None:
        """首次调用 add_update_exist, 验证为插入行为"""
        result = await bot_dal.add_update_exist(
            bot_type=test_bot_type,
            self_id=test_bot_self_id,
            bot_status=1,
            bot_info=test_bot_info,
        )
        await bot_dal.commit_session()

        assert result.self_id == test_bot_self_id
        assert result.bot_type == test_bot_type
        assert result.bot_status == 1
        assert result.bot_info == test_bot_info

        queried = await bot_dal.query_unique(test_bot_type, test_bot_self_id, None)
        assert queried.bot_status == 1
        assert queried.bot_info == test_bot_info

    async def test_add_update_exist_update(
            self,
            bot_dal,
            test_bot_type,
            test_bot_self_id,
            test_bot_info,
    ) -> None:
        """先 add 插入, 再 add_update_exist 更新 status/info, 验证返回新值"""
        await bot_dal.add(
            bot_type=test_bot_type,
            self_id=test_bot_self_id,
            bot_status=1,
            bot_info=test_bot_info,
        )
        await bot_dal.commit_session()

        # 同一 (bot_type, self_id) 触发更新分支
        result = await bot_dal.add_update_exist(
            bot_type=test_bot_type,
            self_id=test_bot_self_id,
            bot_status=0,
            bot_info='updated info',
        )
        await bot_dal.commit_session()

        assert result.bot_type == test_bot_type
        assert result.bot_status == 0
        assert result.bot_info == 'updated info'

        queried = await bot_dal.query_unique(test_bot_type, test_bot_self_id, None)
        assert queried.bot_type == test_bot_type
        assert queried.bot_status == 0
        assert queried.bot_info == 'updated info'

    async def test_add_update_exist_with_none_info(
            self,
            bot_dal,
            test_bot_type,
            test_bot_self_id,
            test_bot_info,
    ) -> None:
        """先 add 带 info, 再 add_update_exist 用 info=None 更新, 验证 info 被更新为 None"""
        await bot_dal.add(
            bot_type=test_bot_type,
            self_id=test_bot_self_id,
            bot_status=1,
            bot_info=test_bot_info,
        )
        await bot_dal.commit_session()

        result = await bot_dal.add_update_exist(
            bot_type=test_bot_type,
            self_id=test_bot_self_id,
            bot_status=1,
            bot_info=None,
        )
        await bot_dal.commit_session()

        assert result.bot_info is None

        queried = await bot_dal.query_unique(test_bot_type, test_bot_self_id, None)
        assert queried.bot_info is None

    async def test_add_update_exist_invalid_bot_status_raises(
            self,
            bot_dal,
            test_bot_type,
            test_bot_self_id,
    ) -> None:
        """bot_status 传未定义的枚举值调用 add_update_exist, 预期 ValueError 且不产生写入"""
        with pytest.raises(ValueError, match='is not a valid BotStatus'):
            await bot_dal.add_update_exist(
                bot_type=test_bot_type,
                self_id=test_bot_self_id,
                bot_status=2,
            )

        assert await bot_dal._count_all() == 0

    # ------------------------------------------------------------------ #
    # add_update_exist — 嵌套事务 (SAVEPOINT) 路径
    # ------------------------------------------------------------------ #

    async def test_add_update_exist_in_nested_transaction_insert(
            self,
            bot_dal,
            test_bot_type,
            test_bot_self_id,
            test_bot_info,
    ) -> None:
        """外层已有活动事务时插入分支走 SAVEPOINT, 外层 rollback 后插入应被撤销"""
        from src.database.config import database_config
        if database_config.database == 'sqlite':
            # SQLite 后端 (aiosqlite 默认 legacy 事务控制, 会话事务不显式发送 BEGIN) 下,
            # 外层事务的首个语句若为 SAVEPOINT 则物理事务由 SAVEPOINT 开启且 RELEASE 即提交,
            # 外层 rollback 无法撤销插入, 属驱动层限制而非 DAL 逻辑问题, 故本平台跳过该用例
            pytest.skip('SQLite 驱动 legacy 事务控制下嵌套插入无法被外层事务回滚, 跳过')

        await bot_dal.db_session.begin()
        result = await bot_dal.add_update_exist(
            bot_type=test_bot_type,
            self_id=test_bot_self_id,
            bot_status=1,
            bot_info=test_bot_info,
        )
        assert result.self_id == test_bot_self_id
        assert result.bot_info == test_bot_info
        assert await bot_dal._count_all() == 1

        await bot_dal.rollback_session()
        assert await bot_dal._count_all() == 0

    async def test_add_update_exist_in_nested_transaction_update(
            self,
            bot_dal,
            test_bot_type,
            test_bot_self_id,
            test_bot_info,
    ) -> None:
        """外层已有活动事务时更新分支走 SAVEPOINT, 外层 rollback 后更新应被撤销"""
        await bot_dal.add(
            bot_type=test_bot_type, self_id=test_bot_self_id, bot_status=1, bot_info=test_bot_info,
        )
        await bot_dal.commit_session()

        await bot_dal.db_session.begin()
        result = await bot_dal.add_update_exist(
            bot_type=test_bot_type,
            self_id=test_bot_self_id,
            bot_status=0,
            bot_info='nested updated info',
        )
        assert result.bot_status == 0
        assert result.bot_info == 'nested updated info'

        # 外层事务内可见更新
        queried = await bot_dal.query_unique(test_bot_type, test_bot_self_id, None)
        assert queried.bot_status == 0
        assert queried.bot_info == 'nested updated info'

        await bot_dal.rollback_session()

        # 外层 rollback 后恢复为更新前的值
        queried = await bot_dal.query_unique(test_bot_type, test_bot_self_id, None)
        assert queried.bot_status == 1
        assert queried.bot_info == test_bot_info

    # ------------------------------------------------------------------ #
    # delete
    # ------------------------------------------------------------------ #

    async def test_delete_existing(self, bot_dal, test_bot_type, test_bot_self_id) -> None:
        """插入一条, delete 后用 query_unique 查不到 (NoResultFound)"""
        await bot_dal.add(bot_type=test_bot_type, self_id=test_bot_self_id, bot_status=1)
        await bot_dal.commit_session()

        await bot_dal.delete(bot_type=test_bot_type, self_id=test_bot_self_id)
        await bot_dal.commit_session()

        with pytest.raises(NoResultFound):
            await bot_dal.query_unique(test_bot_type, test_bot_self_id, None)

    async def test_delete_non_existing(self, bot_dal) -> None:
        """删除不存在的 self_id, 不抛异常"""
        await bot_dal.delete(bot_type='Console', self_id='nonexistent_self_id')
        await bot_dal.commit_session()

        assert await bot_dal._count_all() == 0

    async def test_delete_only_affects_target(self, bot_dal, test_bot_type, test_bot_self_id) -> None:
        """插入多条, delete 只删除目标记录, 其他不受影响"""
        await bot_dal.add(bot_type=test_bot_type, self_id=test_bot_self_id, bot_status=1)
        await bot_dal.add(bot_type=test_bot_type, self_id='other_bot', bot_status=1)
        await bot_dal.commit_session()

        await bot_dal.delete(bot_type=test_bot_type, self_id=test_bot_self_id)
        await bot_dal.commit_session()

        # 目标记录已删除
        with pytest.raises(NoResultFound):
            await bot_dal.query_unique(test_bot_type, test_bot_self_id, None)

        # 其他记录仍在
        remaining = await bot_dal.query_all()
        assert len(remaining) == 1
        assert remaining[0].self_id == 'other_bot'

        assert await bot_dal._count_all() == 1

    async def test_delete_only_affects_same_bot_type(self, bot_dal) -> None:
        """相同 self_id 不同 bot_type 的记录, delete 只删除匹配 bot_type 的目标记录"""
        await bot_dal.add(bot_type='Console', self_id='shared_bot_id', bot_status=1)
        await bot_dal.add(bot_type='QQ', self_id='shared_bot_id', bot_status=1)
        await bot_dal.commit_session()

        await bot_dal.delete(bot_type='Console', self_id='shared_bot_id')
        await bot_dal.commit_session()

        # Console 端记录已删除
        with pytest.raises(NoResultFound):
            await bot_dal.query_unique('Console', 'shared_bot_id', None)

        # QQ 端同名记录仍在
        remaining = await bot_dal.query_unique('QQ', 'shared_bot_id', None)
        assert remaining.self_id == 'shared_bot_id'
        assert remaining.bot_type == 'QQ'

        assert await bot_dal._count_all() == 1
