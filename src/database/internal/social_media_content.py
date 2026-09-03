"""
@Author         : Ailitonia
@Date           : 2024/10/23 19:54
@FileName       : social_media_content
@Project        : omega-miya
@Description    : SocialMediaContent DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import delete, desc, func, select

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayer, BaseDataOutModel
from ..schema import SocialMediaContentOrm


class SocialMediaContent(BaseDataOutModel):
    """社交媒体平台内容数据"""
    id: int
    source: str
    m_type: str
    m_id: str
    m_uid: str
    title: str
    raw_data: dict[str, Any]
    content: str | None
    ref_content: str | None
    published_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None


class SocialMediaContentDAL(BaseDataAccessLayer[SocialMediaContentOrm, SocialMediaContent]):
    """社交媒体平台内容"""

    async def _count_all(self) -> int:
        """查询全表行数"""
        stmt = select(func.count()).select_from(SocialMediaContentOrm)
        return (await self.db_session.execute(stmt)).scalar_one()

    async def _clear_all(self) -> None:
        """清空全表, 敏感操作, 方法内不执行 commit, 可由外层事务 rollback"""
        await self.db_session.execute(delete(SocialMediaContentOrm))
        self.db_session.expunge_all()

    async def _select_unique(
            self,
            source: str,
            m_type: str,
            m_id: str,
            *,
            populate_existing: bool = False,
            with_for_update: bool = False,
            nowait_for_update: bool = False,
    ) -> SocialMediaContentOrm:
        stmt = (select(SocialMediaContentOrm)
                .where(SocialMediaContentOrm.source == source)
                .where(SocialMediaContentOrm.m_type == m_type)
                .where(SocialMediaContentOrm.m_id == m_id))

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        if with_for_update:
            stmt = stmt.with_for_update(nowait=nowait_for_update)

        return (await self.db_session.execute(stmt)).scalar_one()

    async def query_unique(
            self,
            source: str,
            m_type: str,
            m_id: str,
            *,
            populate_existing: bool = False,
    ) -> SocialMediaContent:
        item = await self._select_unique(
            source,
            m_type,
            m_id,
            populate_existing=populate_existing,
        )
        return SocialMediaContent.model_validate(item)

    async def query_source_all(
            self,
            source: str,
            *,
            m_type: str | None = None,
            m_uid: str | None = None,
            populate_existing: bool = False,
    ) -> list[SocialMediaContent]:
        """查询指定来源平台(指定类型的)所有记录行"""
        stmt = select(SocialMediaContentOrm).where(SocialMediaContentOrm.source == source)

        if m_type is not None:
            stmt = stmt.where(SocialMediaContentOrm.m_type == m_type)

        if m_uid is not None:
            stmt = stmt.where(SocialMediaContentOrm.m_uid == m_uid)

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        # 按 m_id 数值感知排序
        stmt = stmt.order_by(desc(func.length(SocialMediaContentOrm.m_id)), desc(SocialMediaContentOrm.m_id))

        return parse_obj_as(list[SocialMediaContent], (await self.db_session.execute(stmt)).scalars().all())

    async def query_source_all_m_ids(
            self,
            source: str,
            *,
            m_type: str | None = None,
            m_uid: str | None = None,
            populate_existing: bool = False,
    ) -> list[str]:
        """查询指定来源平台(指定类型的)所有记录行中的 mid"""
        stmt = select(SocialMediaContentOrm.m_id).where(SocialMediaContentOrm.source == source)

        if m_type is not None:
            stmt = stmt.where(SocialMediaContentOrm.m_type == m_type)

        if m_uid is not None:
            stmt = stmt.where(SocialMediaContentOrm.m_uid == m_uid)

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        # 按 m_id 数值感知排序
        stmt = stmt.order_by(desc(func.length(SocialMediaContentOrm.m_id)), desc(SocialMediaContentOrm.m_id))

        return parse_obj_as(list[str], (await self.db_session.execute(stmt)).scalars().all())

    async def query_source_exists_m_ids(
            self,
            source: str | Sequence[str] | None,
            m_type: str | Sequence[str] | None,
            m_uid: str | Sequence[str] | None,
            m_ids: Sequence[str],
    ) -> list[str]:
        """根据提供的来源类型及 m_id 清单查询其中已经存在于数据库记录中的条目"""
        stmt = select(SocialMediaContentOrm.m_id)

        if source is None:
            # 匹配所有来源
            pass
        elif isinstance(source, str):
            # 匹配单一来源
            stmt = stmt.where(SocialMediaContentOrm.source == source)
        else:
            # 匹配多个来源
            stmt = stmt.where(SocialMediaContentOrm.source.in_(source))

        if m_type is None:
            # 匹配所有类型
            pass
        elif isinstance(m_type, str):
            # 匹配单一类型
            stmt = stmt.where(SocialMediaContentOrm.m_type == m_type)
        else:
            # 匹配多个类型
            stmt = stmt.where(SocialMediaContentOrm.m_type.in_(m_type))

        if m_uid is None:
            # 匹配所有用户
            pass
        elif isinstance(m_uid, str):
            # 匹配单一用户
            stmt = stmt.where(SocialMediaContentOrm.m_uid == m_uid)
        else:
            # 匹配多个用户
            stmt = stmt.where(SocialMediaContentOrm.m_uid.in_(m_uid))

        stmt = (stmt
                .where(SocialMediaContentOrm.m_id.in_(m_ids))
                .order_by(desc(func.length(SocialMediaContentOrm.m_id)), desc(SocialMediaContentOrm.m_id)))

        return parse_obj_as(list[str], (await self.db_session.execute(stmt)).scalars().all())

    async def query_source_not_exists_m_ids(
            self,
            source: str | Sequence[str] | None,
            m_type: str | Sequence[str] | None,
            m_uid: str | Sequence[str] | None,
            m_ids: Sequence[str],
    ) -> list[str]:
        """根据提供的来源类型及 m_id 清单查询其中不存在于数据库记录中的条目"""
        exists_m_ids = await self.query_source_exists_m_ids(source=source, m_type=m_type, m_uid=m_uid, m_ids=m_ids)
        # 与 query_source_exists_m_ids 的 SQL 数值感知排序 (长度优先, 同长度字典序) 保持一致
        return sorted(set(m_ids) - set(exists_m_ids), key=lambda x: (len(x), x), reverse=True)

    async def add(
            self,
            source: str,
            m_type: str,
            m_id: str,
            m_uid: str,
            title: str,
            raw_data: dict[str, Any],
            content: str | None = None,
            ref_content: str | None = None,
            published_at: datetime | None = None,
    ) -> SocialMediaContent:
        """向数据库插入新行, 不校验唯一性

        尽量保证插入的是新数据时才使用, 冲突直接抛出异常
        原则上此表保存社交媒体内容原始副本, 不进行更新
        """
        raw_data = parse_obj_as(dict[str, Any], raw_data)

        new_obj = SocialMediaContentOrm(
            source=source,
            m_type=m_type,
            m_id=m_id,
            m_uid=m_uid,
            title=title[:255],
            raw_data=raw_data,
            content=content,
            ref_content=ref_content,
            published_at=published_at,
        )
        self.db_session.add(new_obj)
        await self.db_session.flush()
        return SocialMediaContent.model_validate(new_obj)


__all__ = [
    'SocialMediaContent',
    'SocialMediaContentDAL',
]
