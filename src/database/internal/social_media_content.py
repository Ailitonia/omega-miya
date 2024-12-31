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

from sqlalchemy import desc, select

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayerModel, BaseDataQueryResultModel
from ..schema import SocialMediaContentOrm


class SocialMediaContent(BaseDataQueryResultModel):
    """社交媒体平台内容 Model"""
    source: str
    m_id: str
    m_type: str
    m_uid: str
    content: str
    ref_content: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SocialMediaContentDAL(BaseDataAccessLayerModel[SocialMediaContentOrm, SocialMediaContent]):
    """社交媒体平台内容 数据库操作对象"""

    async def query_unique(self, source: str, m_id: str) -> SocialMediaContent:
        stmt = (select(SocialMediaContentOrm)
                .where(SocialMediaContentOrm.source == source)
                .where(SocialMediaContentOrm.m_id == m_id))
        session_result = await self.db_session.execute(stmt)
        return SocialMediaContent.model_validate(session_result.scalar_one())

    async def query_all(self) -> list[SocialMediaContent]:
        raise NotImplementedError

    async def query_source_all(self, source: str) -> list[SocialMediaContent]:
        """查询指定来源平台所有记录行"""
        stmt = (select(SocialMediaContentOrm)
                .where(SocialMediaContentOrm.source == source)
                .order_by(desc(SocialMediaContentOrm.m_id)))
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[SocialMediaContent], session_result.scalars().all())

    async def query_source_all_mids(self, source: str) -> list[str]:
        """查询指定来源平台所有记录行中的 mid"""
        stmt = (select(SocialMediaContentOrm.m_id)
                .where(SocialMediaContentOrm.source == source)
                .order_by(desc(SocialMediaContentOrm.m_id)))
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[str], session_result.scalars().all())

    async def query_source_exists_mids(self, source: str, mids: Sequence[str]) -> list[str]:
        """根据提供的 mids 查询其中已经存在于数据库记录中的条目"""
        stmt = (select(SocialMediaContentOrm.m_id)
                .where(SocialMediaContentOrm.source == source)
                .where(SocialMediaContentOrm.m_id.in_(mids))
                .order_by(desc(SocialMediaContentOrm.m_id)))
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[str], session_result.scalars().all())

    async def query_source_not_exists_mids(self, source: str, mids: Sequence[str]) -> list[str]:
        """根据提供的 mids 查询其中不存在于数据库记录中的条目"""
        exists_mids = await self.query_source_exists_mids(source=source, mids=mids)
        return sorted(list(set(mids) - set(exists_mids)), reverse=True)

    async def query_user_all(self, source: str, uid: str) -> list[SocialMediaContent]:
        """查询指定来源平台指定用户所有记录行"""
        stmt = (select(SocialMediaContentOrm)
                .where(SocialMediaContentOrm.source == source)
                .where(SocialMediaContentOrm.m_uid == uid)
                .order_by(desc(SocialMediaContentOrm.m_id)))
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[SocialMediaContent], session_result.scalars().all())

    async def query_user_all_mids(self, source: str, uid: str) -> list[str]:
        """查询指定来源平台指定用户所有记录行中的 mid"""
        stmt = (select(SocialMediaContentOrm.m_id)
                .where(SocialMediaContentOrm.source == source)
                .where(SocialMediaContentOrm.m_uid == uid)
                .order_by(desc(SocialMediaContentOrm.m_id)))
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[str], session_result.scalars().all())

    async def query_user_exists_mids(self, source: str, uid: str, mids: Sequence[str]) -> list[str]:
        """根据提供的 mids 查询对应用户其中已经存在于数据库记录中的条目"""
        stmt = (select(SocialMediaContentOrm.m_id)
                .where(SocialMediaContentOrm.source == source)
                .where(SocialMediaContentOrm.m_uid == uid)
                .where(SocialMediaContentOrm.m_id.in_(mids))
                .order_by(desc(SocialMediaContentOrm.m_id)))
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[str], session_result.scalars().all())

    async def query_user_not_exists_mids(self, source: str, uid: str, mids: Sequence[str]) -> list[str]:
        """根据提供的 mids 查询对应用户其中不存在于数据库记录中的条目"""
        exists_mids = await self.query_user_exists_mids(source=source, uid=uid, mids=mids)
        return sorted(list(set(mids) - set(exists_mids)), reverse=True)

    async def add(
            self,
            source: str,
            m_id: str,
            m_type: str,
            m_uid: str,
            title: str,
            content: str,
            ref_content: str = '',
    ) -> None:
        new_obj = SocialMediaContentOrm(source=source, m_id=m_id, m_type=m_type, m_uid=m_uid,
                                        title=title[:255], content=content[:4096], ref_content=ref_content[:4096],
                                        created_at=datetime.now())
        await self._add(new_obj)

    async def upsert(
            self,
            source: str,
            m_id: str,
            m_type: str,
            m_uid: str,
            title: str,
            content: str,
            ref_content: str = '',
    ) -> None:
        new_obj = SocialMediaContentOrm(source=source, m_id=m_id, m_type=m_type, m_uid=m_uid,
                                        title=title[:255], content=content[:4096], ref_content=ref_content[:4096],
                                        updated_at=datetime.now())
        await self._merge(new_obj)

    async def update(self, *args, **kwargs) -> None:
        raise NotImplementedError

    async def delete(self, *args, **kwargs) -> None:
        raise NotImplementedError


__all__ = [
    'SocialMediaContent',
    'SocialMediaContentDAL',
]
